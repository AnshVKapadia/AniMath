from __future__ import annotations
import ast
import json
import subprocess
import shutil
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter
from app.rendering import _normalize_code

IMAGE='manimcommunity/manim:v0.19.0'

@dataclass
class Observation:
    rendered: bool
    category: str
    details: str = ''
    seconds: float = 0.0
    video: str | None = None
    trace: dict | None = None
    infrastructure_error: bool = False


def classify(details):
    for needle,category in [('SyntaxError','syntax'),('IndentationError','syntax'),
        ('ModuleNotFoundError','import'),('ImportError','import'),
        ('NameError','undefined_name'),('AttributeError','api_attribute'),
        ('TypeError','api_signature'),('ValueError','runtime_value'),
        ('ZeroDivisionError','math_domain'),('FloatingPointError','math_domain'),
        ('LaTeX','latex_toolchain')]:
        if needle in details: return category
    return 'runtime_other'


def source_check(code):
    tree=ast.parse(code)
    scenes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GeneratedScene']
    if len(scenes)!=1: raise ValueError('Define exactly one GeneratedScene')
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            names=[x.name for x in n.names] if isinstance(n,ast.Import) else [n.module or '']
            if any(x.split('.')[0] not in {'manim','numpy','math'} for x in names):
                raise ValueError('Only manim, numpy and math imports are allowed')
        if isinstance(n,ast.Name) and n.id in {'exec','eval','open','compile','__import__','getattr','setattr','globals','locals','vars','breakpoint'}:
            raise ValueError('Unsupported introspection or process/file operation')
        if isinstance(n,ast.Attribute) and n.attr.startswith('__'):
            raise ValueError('Unsupported introspection')
    # This filter improves hygiene. Container isolation remains required.

class DockerExecutor:
    def __init__(self, timeout=150, image=IMAGE):
        self.timeout=timeout
        self.image=image

    def preflight(self):
        if not shutil.which('docker'): raise RuntimeError('Docker is not installed; no generated code was executed')
        for args in [['docker','info'],['docker','image','inspect',self.image]]:
            p=subprocess.run(args,capture_output=True,text=True,timeout=15)
            if p.returncode: raise RuntimeError(f'Render infrastructure unavailable: {args[:2]}')

    def render(self, code, directory):
        directory=Path(directory).resolve()
        directory.mkdir(parents=True,exist_ok=False)
        started=perf_counter()
        code=_normalize_code(code)
        (directory/'candidate.py').write_text(code)
        try:
            source_check(code)
        except SyntaxError as exc:
            return Observation(False,'syntax',str(exc))
        except ValueError as exc:
            return Observation(False,'source_policy',str(exc))
        inputs=directory/'input'; outputs=directory/'output'
        inputs.mkdir(); outputs.mkdir(); outputs.chmod(0o777)
        probe=Path(__file__).with_name('runtime_probe.py').read_text()
        (inputs/'probe.py').write_text(probe)
        (inputs/'scene.py').write_text(code+'\nfrom probe import install\ninstall(GeneratedScene)\n')
        name='mathimate-'+uuid.uuid4().hex
        command=['docker','run','--name',name,'--rm','--network','none',
            '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','128','--memory','2g','--cpus','2',
            '--tmpfs','/tmp:rw,nosuid,size=512m','-e','HOME=/tmp',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/input',
            '-v',f'{inputs}:/input:ro','-v',f'{outputs}:/out',
            '-w','/out',self.image,'manim','-ql','--disable_caching',
            '/input/scene.py','GeneratedScene','--media_dir','/out/media']
        try:
            with (directory/'render.log').open('w') as log:
                process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,
                                       text=True,timeout=self.timeout)
            with (directory/'render.log').open('rb') as log:
                log.seek(0,2);log.seek(max(0,log.tell()-12000))
                details=log.read().decode('utf-8',errors='replace')
            videos=[p for p in outputs.rglob('GeneratedScene.mp4') if p.stat().st_size>0]
            rendered=process.returncode==0 and len(videos)==1
            trace_path=outputs/'trace.json'
            trace=json.loads(trace_path.read_text()) if trace_path.exists() else None
            infra=process.returncode in (125,126,127)
            if rendered and (not trace or any('probe_error' in s for s in trace.get('snapshots',[]))):
                return Observation(True,'probe_error','Runtime instrumentation missing or failed',
                    perf_counter()-started,str(videos[0]),trace,True)
            return Observation(rendered,'ok' if rendered else ('infrastructure' if infra else classify(details)),
                details[-12000:],perf_counter()-started,str(videos[0]) if rendered else None,trace,infra)
        except subprocess.TimeoutExpired:
            return Observation(False,'timeout','Render wall-time limit exceeded',perf_counter()-started)
        except (OSError,json.JSONDecodeError) as exc:
            return Observation(False,'infrastructure',type(exc).__name__,perf_counter()-started,infrastructure_error=True)
        finally:
            subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)

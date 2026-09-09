"""Trusted runner instrumentation copied into an isolated render directory.

Finite observations of actually displayed Manim objects, not model self-reports.
This is a measurement mechanism, not an adversarial security boundary or proof.
"""
import json
import math
from pathlib import Path
import numpy as np
from manim import Axes, Scene, Dot, Line


def install(scene_class, output='/out/trace.json'):
    graphs = []
    snapshots = []
    original_plot = Axes.plot
    original_play = Scene.play
    original_wait = Scene.wait
    original_render = Scene.render

    def plot(axes, *args, **kwargs):
        graph = original_plot(axes,*args,**kwargs)
        graphs.append((axes,graph))
        return graph

    def snapshot(scene):
        try:
            family = list(dict.fromkeys(m for root in scene.mobjects for m in root.get_family()))
            ids = {id(m) for m in family}
            axes_list = [m for m in family if isinstance(m,Axes)]
            axes_members = {id(child) for axes in axes_list for child in axes.get_family()}
            frame = {'t':float(scene.time),'graphs':[],'points':[],'lines':[],
                     'texts':[],'out_of_frame':[]}
            for m in family:
                if hasattr(m,'text'):
                    frame['texts'].append(str(m.text))
                elif hasattr(m,'tex_string'):
                    frame['texts'].append(str(m.tex_string))
            for axes,graph in graphs:
                if id(graph) in ids and id(axes) in ids:
                    points = [axes.p2c(graph.point_from_proportion(float(a))).tolist()
                              for a in np.linspace(0,1,33)]
                    if all(math.isfinite(v) for p in points for v in p):
                        frame['graphs'].append({'id':id(graph),'points':points})
            for axes in axes_list:
                for m in family:
                    if id(m) in axes_members:
                        continue
                    if isinstance(m,Dot):
                        frame['points'].append({'id':id(m),'axes':id(axes),
                                                'xy':axes.p2c(m.get_center()).tolist()})
                    elif type(m) is Line:
                        frame['lines'].append({'id':id(m),'axes':id(axes),
                            'start':axes.p2c(m.get_start()).tolist(),
                            'end':axes.p2c(m.get_end()).tolist()})
            # Coarse diagnostics only: groups/axes and temporary offscreen objects can mislead.
            for root in scene.mobjects:
                if root.width and root.height:
                    if root.get_left()[0] < -7.12 or root.get_right()[0] > 7.12 or root.get_top()[1] > 4 or root.get_bottom()[1] < -4:
                        frame['out_of_frame'].append(type(root).__name__)
            snapshots.append(frame)
        except Exception as exc:
            snapshots.append({'probe_error':type(exc).__name__})

    def play(scene,*args,**kwargs):
        snapshot(scene)
        result=original_play(scene,*args,**kwargs)
        snapshot(scene)
        return result

    def wait(scene,*args,**kwargs):
        result=original_wait(scene,*args,**kwargs)
        snapshot(scene)
        return result

    def render(scene,*args,**kwargs):
        try:
            return original_render(scene,*args,**kwargs)
        finally:
            snapshot(scene)
            Path(output).write_text(json.dumps({'version':'0.1','snapshots':snapshots},allow_nan=False))

    Axes.plot=plot
    Scene.play=play
    Scene.wait=wait
    scene_class.render=render

from __future__ import annotations

import os
import time
from pathlib import Path, PurePosixPath

from vercel.sandbox import NetworkPolicy, SandboxResources, SnapshotSource
from vercel.sandbox import sync as sandbox_sync


REMOTE_JOB_DIR = PurePosixPath("/vercel/sandbox/job")
MANIM_IMAGE = "manimcommunity/manim:v0.19.0"


def render_scene_in_sandbox(
    scene_path: Path,
    media_dir: Path,
) -> tuple[bool, str, Path | None]:
    snapshot_id = os.getenv("VERCEL_SANDBOX_SNAPSHOT_ID")
    if not snapshot_id:
        return False, "VERCEL_SANDBOX_SNAPSHOT_ID is not configured.", None

    sandbox_session_id: str | None = None
    sandbox_project_id: str | None = None
    try:
        with sandbox_sync.create_sandbox(
            source=SnapshotSource(snapshot_id=snapshot_id),
            execution_time_limit=240,
            resources=SandboxResources(vcpus=4),
            network_policy=NetworkPolicy("deny-all", {}),
            snapshot_expiration=86_400,
        ) as sandbox:
            sandbox_session_id = sandbox.current_session_id
            sandbox_project_id = sandbox.project_id
            sandbox.fs.mkdir(REMOTE_JOB_DIR)
            remote_scene = REMOTE_JOB_DIR / "scene.py"
            remote_media = REMOTE_JOB_DIR / "media"
            sandbox.fs.write_text(remote_scene, scene_path.read_text(encoding="utf-8"))

            sandbox.create_process(
                "dockerd",
                ["--log-level", "error"],
                sudo=True,
                kill_after=230,
            )
            docker_error = _wait_for_docker(sandbox)
            if docker_error:
                return False, docker_error, None

            process = sandbox.run_process(
                "docker",
                [
                    "run",
                    "--rm",
                    "-v",
                    f"{REMOTE_JOB_DIR}:/manim",
                    MANIM_IMAGE,
                    "manim",
                    _quality_flag(),
                    "/manim/scene.py",
                    "GeneratedScene",
                    "--media_dir",
                    "/manim/media",
                ],
                sudo=True,
                kill_after=200,
                capture_output=True,
            )
            details = _process_output(process.stdout, process.stderr)
            if process.returncode != 0:
                return False, details or "Sandbox Manim render failed.", None

            match = sandbox.run_process(
                "find",
                [str(remote_media), "-name", "GeneratedScene.mp4", "-print", "-quit"],
                capture_output=True,
            )
            remote_video = (match.stdout or "").strip()
            if match.returncode != 0 or not remote_video:
                return False, details or "Render completed but no mp4 file was found.", None

            video_bytes = sandbox.fs.read_bytes(remote_video)
    except Exception as exc:
        return False, f"Vercel Sandbox error: {exc}", None
    finally:
        _delete_session_snapshots(
            sandbox_session_id,
            project_id=sandbox_project_id,
            base_snapshot_id=snapshot_id,
        )

    media_dir.mkdir(parents=True, exist_ok=True)
    video_path = media_dir / "GeneratedScene.mp4"
    video_path.write_bytes(video_bytes)
    return True, details, video_path


def _delete_session_snapshots(
    session_id: str | None,
    *,
    project_id: str | None,
    base_snapshot_id: str,
) -> None:
    if not session_id:
        return
    try:
        snapshots = sandbox_sync.query_snapshots(
            project_id=project_id,
            page_size=20,
            sort_order="desc",
        )
        for snapshot in snapshots:
            if snapshot.source_session_id == session_id and snapshot.id != base_snapshot_id:
                snapshot.delete()
    except Exception:
        # Snapshot cleanup must not discard an otherwise successful render.
        pass


def _wait_for_docker(sandbox: object) -> str | None:
    last_error = "Docker did not become ready in the Vercel Sandbox."
    for _ in range(20):
        result = sandbox.run_process(
            "docker",
            ["info"],
            sudo=True,
            kill_after=5,
            capture_output=True,
        )
        if result.returncode == 0:
            return None
        last_error = _process_output(result.stdout, result.stderr) or last_error
        time.sleep(0.5)
    return last_error


def _quality_flag() -> str:
    flag = os.getenv("MANIM_QUALITY_FLAG", "-ql")
    return flag if flag in {"-ql", "-qm", "-qh"} else "-ql"


def _process_output(stdout: str | None, stderr: str | None) -> str:
    return "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())

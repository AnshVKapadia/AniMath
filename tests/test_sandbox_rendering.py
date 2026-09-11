from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from app import sandbox_rendering


class SandboxRenderingTests(unittest.TestCase):
    def test_missing_snapshot_configuration_fails_cleanly(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            success, details, video = sandbox_rendering.render_scene_in_sandbox(
                Path("scene.py"), Path("media")
            )

        self.assertFalse(success)
        self.assertIn("VERCEL_SANDBOX_SNAPSHOT_ID", details)
        self.assertIsNone(video)

    def test_rendered_video_is_downloaded_from_sandbox(self) -> None:
        scene_path = Path("virtual-scene.py")
        media_dir = Path("virtual-media")
        docker_ready = Mock(returncode=0, stdout="ready", stderr="")
        rendered = Mock(returncode=0, stdout="rendered", stderr="")
        found = Mock(
            returncode=0,
            stdout="/vercel/sandbox/job/media/GeneratedScene.mp4\n",
            stderr="",
        )
        sandbox = MagicMock()
        sandbox.current_session_id = "sbx_render"
        sandbox.project_id = "prj_test"
        sandbox.run_process.side_effect = [docker_ready, rendered, found]
        sandbox.fs.read_bytes.return_value = b"video-bytes"
        operation = MagicMock()
        operation.__enter__.return_value = sandbox
        derived_snapshot = MagicMock(
            id="snap_child",
            source_session_id="sbx_render",
        )

        with (
            patch.dict(
                "os.environ",
                {"VERCEL_SANDBOX_SNAPSHOT_ID": "snap_test"},
                clear=True,
            ),
            patch.object(
                sandbox_rendering.sandbox_sync,
                "create_sandbox",
                return_value=operation,
            ) as create_sandbox,
            patch.object(
                sandbox_rendering.sandbox_sync,
                "query_snapshots",
                return_value=iter([derived_snapshot]),
            ) as query_snapshots,
            patch.object(Path, "read_text", return_value="from manim import *\n"),
            patch.object(Path, "mkdir"),
            patch.object(Path, "write_bytes") as write_bytes,
        ):
            success, details, video = sandbox_rendering.render_scene_in_sandbox(
                scene_path, media_dir
            )

        self.assertTrue(success)
        self.assertEqual(details, "rendered")
        self.assertEqual(video, media_dir / "GeneratedScene.mp4")
        write_bytes.assert_called_once_with(b"video-bytes")
        sandbox.create_process.assert_called_once()
        sandbox.fs.write_text.assert_called_once()
        self.assertEqual(create_sandbox.call_args.kwargs["snapshot_expiration"], 86_400)
        self.assertEqual(create_sandbox.call_args.kwargs["resources"].vcpus, 4)
        query_snapshots.assert_called_once_with(
            project_id="prj_test",
            page_size=20,
            sort_order="desc",
        )
        derived_snapshot.delete.assert_called_once_with()

    def test_base_snapshot_is_never_deleted(self) -> None:
        base_snapshot = MagicMock(
            id="snap_base",
            source_session_id="sbx_render",
        )
        with patch.object(
            sandbox_rendering.sandbox_sync,
            "query_snapshots",
            return_value=iter([base_snapshot]),
        ):
            sandbox_rendering._delete_session_snapshots(
                "sbx_render",
                project_id="prj_test",
                base_snapshot_id="snap_base",
            )

        base_snapshot.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()

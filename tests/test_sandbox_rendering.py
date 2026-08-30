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
        sandbox.run_process.side_effect = [docker_ready, rendered, found]
        sandbox.fs.read_bytes.return_value = b"video-bytes"
        operation = MagicMock()
        operation.__enter__.return_value = sandbox

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
            ),
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


if __name__ == "__main__":
    unittest.main()

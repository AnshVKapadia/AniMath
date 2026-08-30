from __future__ import annotations

import base64
import os
import unittest
from unittest.mock import Mock, patch

from app import main


class VercelVideoResponseTests(unittest.TestCase):
    def test_vercel_video_is_returned_as_an_inline_data_url(self) -> None:
        video_path = Mock()
        video_path.stat.return_value.st_size = len(b"small-video")
        video_path.read_bytes.return_value = b"small-video"

        with patch.object(main, "IS_VERCEL", True):
            url = main._video_url(video_path)

        self.assertEqual(
            url,
            "data:video/mp4;base64," + base64.b64encode(b"small-video").decode("ascii"),
        )

    def test_vercel_rejects_video_that_would_exceed_response_budget(self) -> None:
        video_path = Mock()
        video_path.stat.return_value.st_size = 5

        with (
            patch.object(main, "IS_VERCEL", True),
            patch.dict(os.environ, {"VERCEL_INLINE_VIDEO_MAX_BYTES": "4"}),
            self.assertRaisesRegex(ValueError, "too large"),
        ):
            main._video_url(video_path)


if __name__ == "__main__":
    unittest.main()

"""The encoder choice: NVENC when usable, x264 otherwise, and the film's options left exactly as delivered."""
import os
import unittest
from unittest import mock

from elenavid.video import encode

# the film was delivered with exactly these video options; reproducing it needs them unchanged
FILM_NVENC = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "17", "-b:v", "24M",
              "-maxrate", "48M", "-bufsize", "96M", "-profile:v", "high", "-pix_fmt", "yuv420p"]


class EncoderChoice(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"ELENA_ENCODER": "auto"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def choose_with(self, nvenc, names):
        with mock.patch.object(encode, "nvenc_available", return_value=nvenc), \
                mock.patch.object(encode, "encoders", return_value=frozenset(names)):
            return encode.choose()

    def test_nvenc_when_the_gpu_can_encode(self):
        self.assertEqual(self.choose_with(True, {"h264_nvenc", "libx264"}), "nvenc")

    def test_x264_when_nvenc_is_listed_but_unusable(self):
        # ffmpeg builds list h264_nvenc with or without an NVIDIA GPU
        self.assertEqual(self.choose_with(False, {"h264_nvenc", "libx264"}), "x264")

    def test_openh264_as_the_last_resort(self):
        self.assertEqual(self.choose_with(False, {"libopenh264"}), "openh264")

    def test_explicit_preferences(self):
        self.assertEqual(encode.choose("x264"), "x264")
        self.assertEqual(encode.choose("nvenc"), "nvenc")
        with self.assertRaises(ValueError):
            encode.choose("prores")

    def test_environment_variable(self):
        with mock.patch.dict(os.environ, {"ELENA_ENCODER": "x264"}):
            self.assertEqual(encode.choose(), "x264")


class EncoderArguments(unittest.TestCase):
    def test_film_nvenc_options_are_unchanged(self):
        self.assertEqual(encode.video_args("nvenc", encode.quality("film")), FILM_NVENC)

    def test_full_opera_x264_options(self):
        args = encode.video_args("x264", encode.quality("full"), gop=60)
        self.assertEqual(args[:2], ["-c:v", "libx264"])
        self.assertEqual(args[args.index("-crf") + 1], "21")
        self.assertEqual(args[-2:], ["-g", "60"])

    def test_options_override_the_defaults(self):
        q = encode.quality("full", {"--crf": "18", "--maxrate": "20M"})
        self.assertEqual((q["crf"], q["maxrate"]), ("18", "20M"))
        self.assertIn("40M", encode.video_args("x264", q))     # bufsize is twice the maxrate


if __name__ == "__main__":
    unittest.main()

"""The command line and the edition and project settings (each run in a fresh interpreter, because
elenavid.config reads the environment once, when it is first imported)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(args, **env):
    e = dict(os.environ, **env)
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=REPO, env=e)


class CommandLine(unittest.TestCase):
    def test_help_and_version(self):
        r = run(["-m", "elenavid", "--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage: elenavid", r.stdout)
        self.assertIn("ElenaVid", run(["-m", "elenavid", "version"]).stdout)

    def test_unknown_command_and_tool(self):
        self.assertEqual(run(["-m", "elenavid", "dance"]).returncode, 2)
        self.assertEqual(run(["-m", "elenavid", "qa", "nothing"]).returncode, 2)

    def test_bad_edition(self):
        self.assertEqual(run(["-m", "elenavid", "encoder", "--edition", "opera"]).returncode, 2)


class Configuration(unittest.TestCase):
    def test_editions_and_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = "import elenavid.config as c; print(c.EDITION); print(c.OUT); print(c.CACHE_DIR)"
            r = run(["-c", code], ELENA_EDITION="full", ELENA_ROOT=tmp, ELENA_CACHE=str(Path(tmp) / "cache"))
            self.assertEqual(r.returncode, 0, r.stderr)
            edition, out, cache = r.stdout.split("\n")[:3]
            self.assertEqual(edition, "full")
            self.assertEqual(Path(out), Path(tmp).resolve() / "output" / "full")
            self.assertEqual(Path(cache), Path(tmp) / "cache")
            r = run(["-c", code], ELENA_EDITION="film", ELENA_ROOT=tmp)
            self.assertEqual(Path(r.stdout.split("\n")[1]), Path(tmp).resolve() / "output")

    def test_rejects_unknown_edition(self):
        r = run(["-c", "import elenavid.config"], ELENA_EDITION="opera")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()

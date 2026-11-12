import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAKE_CLAUDE = ROOT / "tests" / "fake" / "claude"


class Sandbox(unittest.TestCase):
    """Fresh HOME (with a space in its name) and a fakebin dir in front of PATH."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="ack-test-"))
        self.addCleanup(shutil.rmtree, str(self.root), True)
        self.home = self.root / "home dir"
        self.fakebin = self.root / "fakebin"
        self.home.mkdir()
        self.fakebin.mkdir()
        shutil.copy(str(FAKE_CLAUDE), str(self.fakebin / "claude"))
        (self.fakebin / "claude").chmod(0o755)
        path = "%s:/usr/bin:/bin" % self.fakebin
        self.env = {"HOME": str(self.home), "PATH": path}
        if os.name == "nt":
            # bash needs its own directories and the Windows system dirs.
            self.env["PATH"] = "%s;%s" % (self.fakebin, os.environ["PATH"])
            for k in ("SYSTEMROOT", "TEMP", "TMP"):
                if k in os.environ:
                    self.env[k] = os.environ[k]

    def run_cmd(self, *argv, env=None, input=None):
        full = dict(self.env)
        full.update(env or {})
        argv = list(argv)
        exe = shutil.which(argv[0], path=full["PATH"])
        if exe and os.name == "nt" and not exe.lower().endswith((".exe", ".com")):
            argv = ["bash", exe] + argv[1:]  # Windows cannot exec a shebang script
        elif exe:
            argv[0] = exe
        try:
            return subprocess.run(argv, env=full, input=input, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            return subprocess.CompletedProcess(argv, 127, "", str(e))

    def fake(self, name, script):
        p = self.fakebin / name
        p.write_text(script)
        p.chmod(0o755)
        return p

    def write(self, relpath, text, mode=0o644):
        p = self.home / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        p.chmod(mode)
        return p

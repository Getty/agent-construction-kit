import os
import re
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAKE_CLAUDE = ROOT / "tests" / "fake" / "claude"


def sandbox_env(home, fakebin):
    """The environment every sandboxed child gets; reads os.environ at call time."""
    env = {"HOME": str(home), "PATH": "%s:/usr/bin:/bin" % fakebin}
    if os.name == "nt":
        # Windows: the sandbox PATH is fakebin plus the host PATH (bash needs
        # its own directories), so isolation is weaker there, by necessity.
        env["PATH"] = "%s;%s" % (fakebin, os.environ["PATH"])
        for k in ("SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "TEMP", "TMP"):
            if k in os.environ:
                env[k] = os.environ[k]
    return env


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
        self.env = sandbox_env(self.home, self.fakebin)

    def run_cmd(self, *argv, env=None, input=None):
        full = dict(self.env)
        full.update(env or {})
        argv = self._launchable(argv, full["PATH"])
        if os.name == "nt" and os.path.basename(argv[0]).lower() == "bash.exe":
            argv = self._quoted(argv)   # only MSYS programs; cmd.exe parses differently
        try:
            return subprocess.run(argv, env=full, input=input, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            return subprocess.CompletedProcess(argv, 127, "", str(e))

    @staticmethod
    def _quoted(argv):
        """One Windows command line with every argument in double quotes.

        The MSYS runtime globs and brace-expands unquoted arguments that come
        from a native program ("MODEL=${X}" would arrive as "MODEL=$X"), and
        Python only quotes arguments that contain whitespace.
        """
        def q(a):
            a = re.sub(r'(\\*)"', lambda m: m.group(1) * 2 + '\\"', a)
            a = re.sub(r'(\\+)$', lambda m: m.group(1) * 2, a)
            return '"%s"' % a
        return " ".join(q(a) for a in argv)

    @staticmethod
    def _launchable(argv, path):
        """Resolve argv[0] on the sandbox PATH; on Windows run scripts via Git's bash."""
        argv = list(argv)
        if os.name != "nt":
            hit = shutil.which(argv[0], path=path)
            return [hit] + argv[1:] if hit else argv
        git = shutil.which("git")
        bash = str(pathlib.Path(git).parent.parent / "bin" / "bash.exe") if git else ""
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "bash"
        if argv[0] == "bash":
            return [bash] + argv[1:]
        for d in path.split(os.pathsep):
            hit = pathlib.Path(d) / argv[0]
            if not d:
                continue
            if hit.is_file():
                if hit.suffix.lower() in (".exe", ".com"):
                    return [str(hit)] + argv[1:]
                return [bash, str(hit)] + argv[1:]
            exe = pathlib.Path(d) / (argv[0] + ".exe")
            if exe.is_file():
                return [str(exe)] + argv[1:]
        return argv

    def fake(self, name, script):
        p = self.fakebin / name
        with open(str(p), "w", newline="") as f:
            f.write(script)
        p.chmod(0o755)
        return p

    def write(self, relpath, text, mode=0o644):
        p = self.home / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(str(p), "w", newline="") as f:
            f.write(text)
        p.chmod(mode)
        return p

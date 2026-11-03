"""Per project settings, read from a json config the launcher points at.

Mirrors how script-panel finds its config: an environment variable holds the path to a
json file, and "__THIS_FILE__" inside it is replaced with that file's own path so entries
can be written relative to it.

    {
        "preview_mesh": "//depot/path/to/SK_PreviewMesh.fbx"
    }

A preview mesh given as a depot path (//...) is synced and resolved to its local path in
the workspace. A local path is synced too when it lives in a workspace, and used as is
when it does not.
"""

import json
import os
import subprocess

from . import mocap_browser_constants as k
from .mocap_browser_logger import get_logger

log = get_logger()


class ProjectConfig(object):
    def __init__(self, config_path=None, data=None):
        self.config_path = config_path or ""
        self.data = data or {}

    @classmethod
    def from_path(cls, config_path):
        if not config_path or not os.path.isfile(config_path):
            return cls()

        try:
            with open(config_path, "r") as fp:
                raw = fp.read()
        except OSError as exc:
            log.warning("Could not read project config {}: {}".format(config_path, exc))
            return cls()

        # Escaped for json, since the path lands inside string literals.
        raw = raw.replace("__THIS_FILE__", json.dumps(os.path.abspath(config_path))[1:-1])
        try:
            data = json.loads(raw)
        except ValueError as exc:
            log.warning("Could not parse project config {}: {}".format(config_path, exc))
            return cls()

        return cls(config_path, data)

    @property
    def is_valid(self):
        return bool(self.config_path)

    @property
    def project_name(self):
        """Explicit "project_name", else the folder the config sits in."""
        if not self.is_valid:
            return ""
        return self.data.get(k.ProjectConfigKeys.project_name) or os.path.basename(
            os.path.dirname(os.path.abspath(self.config_path)))

    @property
    def preview_mesh(self):
        """The preview mesh as written in the config, which may be a depot path."""
        return self.data.get(k.ProjectConfigKeys.preview_mesh, "")

    def get_p4_cwd(self):
        """p4 finds its P4CONFIG by walking up from the working directory."""
        p4_root = os.environ.get("P4ROOT")
        if p4_root and os.path.isdir(p4_root):
            return p4_root
        if self.config_path:
            return os.path.dirname(os.path.abspath(self.config_path))
        return None


def sync_and_resolve(path, cwd=None):
    """Sync `path` from perforce and return its local path, or "" if it can't be found.

    Called off the main thread, so everything goes to the log rather than a dialog.
    """
    if not path:
        return ""

    is_depot_path = path.startswith("//")

    _run_p4(["sync", path], cwd)

    if not is_depot_path:
        return path if os.path.isfile(path) else ""

    local_path = _run_p4(["-ztag", "-F", "%path%", "where", path], cwd).strip()
    # A path mapped more than once lists every mapping; the last one wins in p4.
    local_path = local_path.splitlines()[-1] if local_path else ""
    if local_path and os.path.isfile(local_path):
        return local_path

    log.warning("Preview mesh {} is not synced to this workspace".format(path))
    return ""


def _run_p4(args, cwd=None):
    startupinfo = None
    if os.name == "nt":
        # Keeps a console window from flashing up when running inside Maya.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # p4 trusts PWD over the real working directory when it is set, which shells like
    # Git Bash do, so it has to agree with cwd for P4CONFIG to be found.
    env = None
    if cwd:
        env = dict(os.environ, PWD=cwd)

    try:
        result = subprocess.run(
            ["p4"] + args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
        )
    except OSError as exc:
        log.warning("Could not run p4: {}".format(exc))
        return ""

    # "file(s) up-to-date" is reported on stderr and is not a problem.
    stderr = result.stderr.strip()
    if result.returncode != 0 or (stderr and "up-to-date" not in stderr):
        log.info("p4 {}: {}".format(" ".join(args), stderr))

    return result.stdout

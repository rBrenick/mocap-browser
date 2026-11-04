"""Per project settings, read from a json config the launcher points at.

Mirrors how script-panel finds its config: an environment variable holds the path to a
json file, and "__THIS_FILE__" inside it is replaced with that file's own path so entries
can be written relative to it.

    {
        "preview_mesh": "//depot/path/to/SK_PreviewMesh.fbx"
    }
"""

import json
import os
import subprocess

from .mocap_browser_logger import get_logger

log = get_logger()


def get_project_name(config_path):
    """The folder the config sits in, which is how the launcher lays out projects."""
    return os.path.basename(os.path.dirname(os.path.abspath(config_path)))


def load_config(config_path):
    with open(config_path, "r") as fp:
        raw = fp.read()

    # Escaped for json, since the path lands inside string literals.
    raw = raw.replace("__THIS_FILE__", json.dumps(os.path.abspath(config_path))[1:-1])
    return json.loads(raw)


def sync_preview_mesh(config_path):
    """Sync the config's preview mesh from perforce and return its local path.

    Returns "" when the config has no preview mesh, and raises when it has one that
    can't be found on disk afterwards.
    """
    mesh_path = load_config(config_path).get("preview_mesh", "")
    if not mesh_path:
        return ""

    # p4 finds its P4CONFIG by walking up from here, and the config lives in the workspace.
    cwd = os.path.dirname(os.path.abspath(config_path))
    _run_p4(["sync", mesh_path], cwd)

    local_path = mesh_path
    if mesh_path.startswith("//"):
        local_path = _run_p4(["-ztag", "-F", "%path%", "where", mesh_path], cwd).strip()
        # A path mapped more than once lists every mapping; the last one wins in p4.
        local_path = local_path.splitlines()[-1] if local_path else ""

    if not local_path or not os.path.isfile(local_path):
        raise IOError("Project preview mesh could not be synced: {}".format(mesh_path))

    return local_path


def _run_p4(args, cwd):
    startupinfo = None
    if os.name == "nt":
        # Keeps a console window from flashing up when running inside Maya.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    result = subprocess.run(
        ["p4"] + args,
        cwd=cwd,
        # p4 trusts PWD over the real working directory when it is set, which shells like
        # Git Bash do, so it has to agree with cwd for P4CONFIG to be found.
        env=dict(os.environ, PWD=cwd),
        capture_output=True,
        text=True,
        startupinfo=startupinfo,
    )

    # "file(s) up-to-date" is reported on stderr and is not a problem.
    stderr = result.stderr.strip()
    if result.returncode != 0 or (stderr and "up-to-date" not in stderr):
        log.info("p4 {}: {}".format(" ".join(args), stderr))

    return result.stdout

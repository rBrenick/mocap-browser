def main(*args, **kwargs):
    from . import mocap_browser_ui
    return mocap_browser_ui.main(*args, **kwargs)


def reload_modules():
    import sys
    if sys.version_info.major >= 3:
        from importlib import reload
    else:
        from imp import reload
    
    # only present when the Python FBX SDK is installed, see mocap_browser_ui
    try:
        from . import fbx_utils
    except ImportError:
        fbx_utils = None

    from .gl_utils import scene_utils
    from . import mocap_browser_constants
    from . import mocap_browser_logger
    from . import mocap_browser_dcc_core
    from . import mocap_browser_dcc_maya
    from . import mocap_browser_system
    from . import mocap_browser_ui
    if fbx_utils is not None:
        reload(fbx_utils)
    reload(scene_utils)
    reload(mocap_browser_constants)
    reload(mocap_browser_logger)
    reload(mocap_browser_dcc_core)
    reload(mocap_browser_dcc_maya)
    reload(mocap_browser_system)
    reload(mocap_browser_ui)
    

def startup():
    # from maya import cmds
    # cmds.optionVar(query="") # example of finding a maya optionvar
    pass





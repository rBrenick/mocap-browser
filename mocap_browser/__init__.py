def main(*args, **kwargs):
    from . import mocap_browser_ui
    return mocap_browser_ui.main(*args, **kwargs)


def reload_modules():
    import sys
    if sys.version_info.major >= 3:
        from importlib import reload
    else:
        from imp import reload
    
    from . import fbx_utils
    from .gl_utils import scene_utils
    from . import mocap_browser_dcc_core
    from . import mocap_browser_system
    from . import mocap_browser_ui
    reload(fbx_utils)
    reload(scene_utils)
    reload(mocap_browser_dcc_core)
    reload(mocap_browser_system)
    reload(mocap_browser_ui)
    

def startup():
    # from maya import cmds
    # cmds.optionVar(query="") # example of finding a maya optionvar
    pass





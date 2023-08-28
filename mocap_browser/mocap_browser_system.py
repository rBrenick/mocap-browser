import os
import sys

active_dcc_is_maya = "maya" in os.path.basename(sys.executable)

if active_dcc_is_maya:
    from . import mocap_browser_dcc_maya as dcc_module
    dcc = dcc_module.MocapBrowserMaya()
else:
    from . import mocap_browser_dcc_core as dcc_module
    dcc = dcc_module.MocapBrowserCoreInterface()





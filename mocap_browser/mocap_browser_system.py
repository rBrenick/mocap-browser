import os
import sys
import traceback
import importlib

from . import mocap_browser_constants as k
from . import mocap_browser_logger

log = mocap_browser_logger.get_logger()

def import_extensions(refresh=False):
    if refresh:
        modules_to_pop = []
        for mod_key in sys.modules.keys():
            if mod_key.startswith(k.ModuleConstants.extension_file_prefix):
                modules_to_pop.append(mod_key)

        for mod_key in modules_to_pop:
            sys.modules.pop(mod_key)

    # look through sys.path for extension modules
    modules_to_import = list()
    for sys_path in sys.path:
        if not os.path.isdir(sys_path):
            continue

        # for every .py file with the proper prefix, import it
        for sys_path_name in os.listdir(sys_path):
            if not sys_path_name.startswith(k.ModuleConstants.extension_file_prefix):
                continue

            module_name = os.path.splitext(sys_path_name)[0]
            modules_to_import.append(module_name)

    modules_to_import = list(set(modules_to_import))

    for module_import_str in modules_to_import:
        if not module_import_str:
            continue

        try:
            importlib.import_module(module_import_str)
            log.info("Imported extension: {}".format(module_import_str))
        except Exception as e:
            traceback.print_exc()


try:
    import_extensions()
except Exception as e:
    traceback.print_exc()


active_dcc_is_maya = "maya" in os.path.basename(sys.executable)

if active_dcc_is_maya:
    from . import mocap_browser_dcc_maya as dcc_module

    extension_sub_classes = dcc_module.MocapBrowserMaya.__subclasses__()
    if extension_sub_classes:
        dcc = extension_sub_classes[0]()  # type: dcc_module.MocapBrowserMaya
    else:
        dcc = dcc_module.MocapBrowserMaya()
    log.info("DCC class: {}".format(dcc))
else:
    from . import mocap_browser_dcc_core as dcc_module

    dcc = dcc_module.MocapBrowserCoreInterface()  # type: dcc_module.MocapBrowserCoreInterface


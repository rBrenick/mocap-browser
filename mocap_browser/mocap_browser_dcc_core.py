import os

from . import mocap_browser_constants as k
from . import mocap_browser_logger
log = mocap_browser_logger.get_logger()


class MocapBrowserCoreInterface(object):
    def get_default_expand_depth(self):
        return None

    def get_default_folder_configs(self):
        return []

    def get_project_config_path(self):
        """json config with per project settings, see mocap_browser_project"""
        return os.environ.get(k.ModuleConstants.project_config_env_key, "")

    def get_tree_right_click_actions(self):
        """
        a list of dictionaries, the function will be sent the selected file paths from the tree view
        ex: {"Import to Mocap Clipper": import_to_mocap_clipper}
        """
        return [{}]

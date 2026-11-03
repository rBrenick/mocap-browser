import os

from . import mocap_browser_constants as k
from . import mocap_browser_logger
log = mocap_browser_logger.get_logger()


class MocapBrowserCoreInterface(object):
    def get_default_expand_depth(self):
        return None

    def get_default_folder_configs(self):
        return []

    def get_project_config_paths(self):
        """
        json configs with per project settings, see mocap_browser_project
        more than one (separated by os.pathsep) lets the user switch between projects
        """
        env_str = os.environ.get(k.ModuleConstants.project_config_env_key, "")
        return [path for path in env_str.split(os.pathsep) if path]

    def get_tree_right_click_actions(self):
        """
        a list of dictionaries, the function will be sent the selected file paths from the tree view
        ex: {"Import to Mocap Clipper": import_to_mocap_clipper}
        """
        return [{}]

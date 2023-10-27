from . import mocap_browser_logger
log = mocap_browser_logger.get_logger()


class MocapBrowserCoreInterface(object):
    def get_default_folder_configs(self):
        return []

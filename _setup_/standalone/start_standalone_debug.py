
# build window
import mocap_browser.mocap_browser_ui
win = mocap_browser.mocap_browser_ui.MocapBrowserWindow()
win.main()

# set ui_utils properties
from mocap_browser import ui_utils
ui_utils.standalone_app_window = win
win.resize(ui_utils.QtCore.QSize(720, 480))

# test root folder
win.file_tree.set_active_folder(r"D:\Google Drive\Maya_Home\Brekel Recordings\SecondAttempt")

# test perforce config
from mocap_browser import qt_file_tree
p4_config = qt_file_tree.PerforceFolderConfig(r"C:\Users\Richa\Perforce\LocalWorkspace")
p4_config.file_extensions = [".blend"]
win.file_tree.tree_view.add_folder_config(p4_config)

# exec
from mocap_browser.resources import stylesheets
stylesheets.apply_standalone_stylesheet()
import sys
sys.exit(mocap_browser.mocap_browser_ui.standalone_app.exec_())

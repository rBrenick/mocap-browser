import sys
import os

from . import ui_utils
from .ui_utils import QtCore, QtWidgets, QtGui, QtOpenGL
from .resources import get_image_path

# Requires PyOpenGL and the Python FBX SDK
from .qt_time_slider import TimeSliderWidget
from .qt_file_tree import QtFileTree, FolderConfig
from .fbx_viewport import FBXViewportWidget, ViewportSceneDescription

standalone_app = None
if not QtWidgets.QApplication.instance():
    standalone_app = QtWidgets.QApplication(sys.argv)


class MocapBrowserViewportWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

        # OpenGL Widget
        self.fbx_viewport = FBXViewportWidget(self)
        self.main_layout.addWidget(self.fbx_viewport)

        # time slider
        self.timeline = TimeSliderWidget(precision=0)
        self.timeline.setMaximumHeight(30)
        self.main_layout.addWidget(self.timeline)
        
        # connect signals
        self.timeline.value_changed.connect(self.fbx_viewport.set_frame)
        self.fbx_viewport.frame_changed.connect(self.timeline.set_value)
        self.fbx_viewport.scene_content_updated.connect(self.update_timeline_from_loaded_fbxs)

        # create hotkeys
        ui_utils.add_hotkey(self, "Left", lambda: self.fbx_viewport.increment_frame(-1))
        ui_utils.add_hotkey(self, "Right", lambda: self.fbx_viewport.increment_frame(1))
        ui_utils.add_hotkey(self, "Shift+Left", lambda: self.fbx_viewport.increment_frame(-15))
        ui_utils.add_hotkey(self, "Shift+Right", lambda: self.fbx_viewport.increment_frame(15))
        ui_utils.add_hotkey(self, "Home", self.fbx_viewport.go_to_start_frame)
        ui_utils.add_hotkey(self, "End", self.fbx_viewport.go_to_end_frame)
        ui_utils.add_hotkey(self, "Space", self.fbx_viewport.toggle_play)

    def load_fbx_files(self, fbx_paths=None):
        self.fbx_viewport.load_fbx_files(fbx_paths)

    def update_timeline_from_loaded_fbxs(self, _):
        self.timeline.set_minimum(self.fbx_viewport.start_frame)
        self.timeline.set_maximum(self.fbx_viewport.end_frame)
        self.timeline.set_value(self.fbx_viewport.active_frame)
        self.timeline.reset_selection()


class MocapSkeletonTree(QtWidgets.QWidget):

    set_node_visibility = QtCore.Signal(str, list, bool)

    def __init__(self, parent):
        super().__init__(parent)

        self.main_layout = QtWidgets.QVBoxLayout()

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setIndentation(10)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemClicked.connect(self.tree_item_check_changed)

        self.main_layout.addWidget(self.tree_widget)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        self.setLayout(self.main_layout)
    
    def populate_skeleton_tree(self, viewport_scene):
        if 0:
            viewport_scene = ViewportSceneDescription()
        
        self.tree_widget.clear()
        for fbx_file, scene_data in viewport_scene.transform_hierarchy.items():
            root_widget = QtWidgets.QTreeWidgetItem(self.tree_widget.invisibleRootItem())
            root_widget.setText(0, os.path.basename(fbx_file))
            root_widget.setText(1, fbx_file)
            root_widget.setCheckState(0, QtCore.Qt.CheckState.Checked)

            node_widgets = {}
            for child_name, parent_name in scene_data.items():
                parent_widget = node_widgets.get(parent_name, root_widget)
                widget_item = QtWidgets.QTreeWidgetItem(parent_widget)
                widget_item.setText(0, child_name)
                widget_item.setText(1, fbx_file)
                widget_item.setCheckState(0, QtCore.Qt.CheckState.Checked)
                node_widgets[child_name] = widget_item

        if len(viewport_scene.transform_hierarchy.keys()) == 1:
            self.tree_widget.expandAll()

    def tree_item_check_changed(self, widget):
        if 0:
            widget = QtWidgets.QTreeWidgetItem()

        fbx_path = widget.text(1)
        state = widget.checkState(0)
        node_names = ui_utils.recursive_set_checkstate(widget, state)
        self.set_node_visibility.emit(fbx_path, node_names, state is QtCore.Qt.CheckState.Checked)


class FBXFolderConfig(FolderConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_icon = ui_utils.create_qicon(get_image_path("fbx_icon"))


class MocapFileTree(QtWidgets.QWidget):

    file_double_clicked = QtCore.Signal(str)

    def __init__(self, parent):
        super().__init__(parent)

        self.folder_path = QtWidgets.QLineEdit()
        self.folder_path.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.folder_path.setPlaceholderText("Root folder")

        self.search_line_edit = QtWidgets.QLineEdit()
        self.search_line_edit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.search_line_edit.setPlaceholderText("Search...")
        self.search_line_edit.textChanged.connect(self._set_filter)

        self.set_folder_button = QtWidgets.QPushButton("...")
        self.set_folder_button.clicked.connect(self.set_active_folder)

        self.tree_view = QtFileTree()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # tree config
        self.tree_view.default_folder_config_cls = FBXFolderConfig
        self.tree_view.file_double_clicked.connect(self.file_double_clicked)

        self.main_layout = QtWidgets.QVBoxLayout()
        file_line_layout = QtWidgets.QHBoxLayout()
        file_line_layout.addWidget(self.folder_path)
        file_line_layout.addWidget(self.set_folder_button)

        self.main_layout.addLayout(file_line_layout)
        self.main_layout.addWidget(self.search_line_edit)
        self.main_layout.addWidget(self.tree_view)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        self.setLayout(self.main_layout)

    def _set_filter(self):
        self.tree_view.set_filter(self.search_line_edit.text())

    def set_active_folder(self, folder_path=None):
        if not folder_path:
            folder_path = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Choose Mocap Folder",
                dir=self.get_folder(),
                )
        if not folder_path:
            return
        
        self._set_folder(folder_path)
    
    def get_selected_paths(self):
        return self.tree_view.get_selected_file_paths()

    def get_folder(self):
        return self.folder_path.text()

    def _set_folder(self, folder_path):
        self.tree_view.set_folder(folder_path, file_exts=[".fbx"])
        self.folder_path.setText(folder_path)


class MocapBrowserWindow(ui_utils.ToolWindow):
    def __init__(self):
        super(MocapBrowserWindow, self).__init__()
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setWindowTitle("Mocap Browser")

        main_splitter = QtWidgets.QSplitter()
        self.file_tree = MocapFileTree(self)
        self.viewport = MocapBrowserViewportWidget(self)
        self.skeleton_tree = MocapSkeletonTree(self)
        main_splitter.addWidget(self.file_tree)
        main_splitter.addWidget(self.viewport)
        main_splitter.addWidget(self.skeleton_tree)
        main_splitter.setStretchFactor(0, 0.7)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([250, 600, 0])

        # connect signals between widgets
        self.file_tree.file_double_clicked.connect(self.viewport.load_fbx_files)
        self.file_tree.tree_view.customContextMenuRequested.connect(self.context_menu)
        self.viewport.fbx_viewport.scene_content_updated.connect(self.skeleton_tree.populate_skeleton_tree)
        self.skeleton_tree.set_node_visibility.connect(self.viewport.fbx_viewport.set_node_visibility)

        main_layout.addWidget(main_splitter)
        self.setCentralWidget(main_widget)
        self.context_menu_actions = [
            {"Load all selected": self.load_all_selected},
        ]

    def context_menu(self):
        return ui_utils.build_menu_from_action_list(self.context_menu_actions)

    def load_all_selected(self):
        self.viewport.load_fbx_files(self.file_tree.get_selected_paths())

    
def main(refresh=False, active_folder=None):
    win = MocapBrowserWindow()
    win.main(refresh=refresh)
    win.resize(QtCore.QSize(720, 480))
    
    if active_folder:
        if os.path.exists(active_folder):
            win.file_tree.set_active_folder(active_folder)

    if standalone_app:
        ui_utils.standalone_app_window = win
        from .resources import stylesheets
        stylesheets.apply_standalone_stylesheet()
        sys.exit(standalone_app.exec_())


if __name__ == "__main__":
    main()

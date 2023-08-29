import sys
import os

from . import ui_utils
from .ui_utils import QtCore, QtWidgets, QtGui, QtOpenGL

# Requires FBX SDK
import fbx, FbxCommon
from . import fbx_utils
from . import fbx_gl_utils

# Requires PyOpenGL
from OpenGL import GL
from .gl_utils import camera
from .gl_utils import scene_utils

from .qt_time_slider import TimeSliderWidget

standalone_app = None
if not QtWidgets.QApplication.instance():
    standalone_app = QtWidgets.QApplication(sys.argv)


class BaseViewportWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        QtOpenGL.QGLWidget.__init__(self, QtOpenGL.QGLFormat(QtOpenGL.QGL.SampleBuffers), parent)

        # viewport control things
        self.background_color = QtGui.QColor.fromRgb(80, 120, 150, 0.0)
        self.prev_mouse_x = 0
        self.prev_mouse_y = 0
        self.main_camera = camera.Camera()
        self.main_camera.setSceneRadius(100.0)
        self.reset_camera()

        ui_utils.add_hotkey(self, "R", self.reset_camera)
        ui_utils.add_hotkey(self, "F", self.reset_camera)
    
    def reset_camera(self):
        self.main_camera.reset(800, 500, 800)
        self.update()

    def initializeGL(self):
        self.qglClearColor(self.background_color)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        self.main_camera.transform()
        scene_utils.draw_origin_grid()
        scene_utils.draw_axis_helper()

    def resizeGL(self, widthInPixels, heightInPixels):
        self.main_camera.setViewportDimensions(widthInPixels, heightInPixels)
        GL.glViewport(0, 0, widthInPixels, heightInPixels)

    def mousePressEvent(self, event):
        self.prev_mouse_x = event.x()
        self.prev_mouse_y = event.y()

    def mouseMoveEvent(self, event):
        """Viewport controls"""
        delta_x = event.x() - self.prev_mouse_x
        delta_y = event.y() - self.prev_mouse_y
        mouse_zoom_speed = 3

        # Orbit
        if event.buttons() == QtCore.Qt.LeftButton:
            self.main_camera.orbit(self.prev_mouse_x, self.prev_mouse_y, event.x(), event.y())

        # Zoom
        elif event.buttons() == QtCore.Qt.RightButton:
            self.main_camera.dollyCameraForward((delta_x + delta_y) * mouse_zoom_speed, False)

        # Panning
        elif event.buttons() == QtCore.Qt.MidButton:
            self.main_camera.translateSceneRightAndUp(delta_x, -delta_y)

        self.prev_mouse_x = event.x()
        self.prev_mouse_y = event.y()
        self.update()

    def wheelEvent(self, event):
        zoom_multiplier = 0.5
        self.main_camera.dollyCameraForward(event.delta() * zoom_multiplier, False)
        self.update()


class AnimationViewportWidget(BaseViewportWidget):

    frame_changed = QtCore.Signal(int)

    def __init__(self, parent):
        super().__init__(parent)

        self.play_active = False
        self.active_frame = 0
        self.start_frame = 0
        self.end_frame = 0

        # frame timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.play_next_frame)
        self.timer.start(30)

    def timerEvent(self, event):
        self.update()

    def toggle_play(self):
        self.play_active = not self.play_active

        if self.play_active:
            self.startTimer(1)

    def set_frame(self, frame):
        if self.play_active:
            return
        self.active_frame = frame
        self.update()

    def play_next_frame(self):
        if self.play_active:
            if self.active_frame >= self.end_frame:
                self.active_frame = self.start_frame
            else:
                self.active_frame += 1
        self.frame_changed.emit(self.active_frame)

    def increment_frame(self, value=1):
        next_frame = self.active_frame + value
        self.active_frame = max(self.start_frame, min(next_frame, self.end_frame))
        self.update()


class FBXViewportWidget(AnimationViewportWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.fbx_handlers = []
        self.time = fbx.FbxTime()

    def paintGL(self):
        super().paintGL()

        for fbx_handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            if not fbx_handler.is_loaded:
                continue

            self.time.SetTime(0, 0, 0, self.active_frame)
            fbx_gl_utils.recursive_draw_fbx_skeleton(
                fbx_handler.scene.GetRootNode(), 
                self.time,
                fbx_handler.display_color,
                )
            
    def load_fbx_files(self, fbx_file_paths=None):
        if not fbx_file_paths:
            return

        self.remove_existing_handlers()

        if not isinstance(fbx_file_paths, list):
            fbx_file_paths = [fbx_file_paths]

        start_times = []
        end_times = []
        for fbx_file in fbx_file_paths:

            if not os.path.exists(fbx_file):
                print(f"Failed to find fbx file: {fbx_file}")
                continue

            fbx_handler = fbx_utils.FbxHandler()
            fbx_handler.load_scene(fbx_file)
            self.fbx_handlers.append(fbx_handler)
            start_times.append(fbx_handler.get_start_frame())
            end_times.append(fbx_handler.get_end_frame())

            # assign random color to distinguish multiple clips
            if len(fbx_file_paths) > 1:
                fbx_handler.display_color = ui_utils.get_random_color()

        self.start_frame = min(start_times)
        self.end_frame = max(end_times)
        self.active_frame = self.start_frame
        self.update()
    
    def remove_existing_handlers(self):
        for handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            handler.unload_scene()
        self.fbx_handlers.clear()


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

        # create hotkeys
        ui_utils.add_hotkey(self, "Left", lambda: self.fbx_viewport.increment_frame(-1))
        ui_utils.add_hotkey(self, "Right", lambda: self.fbx_viewport.increment_frame(1))
        ui_utils.add_hotkey(self, "Shift+Left", lambda: self.fbx_viewport.increment_frame(-15))
        ui_utils.add_hotkey(self, "Shift+Right", lambda: self.fbx_viewport.increment_frame(15))
        ui_utils.add_hotkey(self, "Space", self.fbx_viewport.toggle_play)

    def load_fbx_files(self, fbx_paths=None):
        self.fbx_viewport.load_fbx_files(fbx_paths)
        self.timeline.set_minimum(self.fbx_viewport.start_frame)
        self.timeline.set_maximum(self.fbx_viewport.end_frame)
        self.timeline.reset_selection()


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

        self.model = QtWidgets.QFileSystemModel()
        self.model.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllEntries)
        self.model.setNameFilters(["*.fbx"])
        self.model.setNameFilterDisables(False)

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_view.setModel(self.model)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.doubleClicked.connect(self.emit_file_signal)

        self.main_layout = QtWidgets.QVBoxLayout()
        file_line_layout = QtWidgets.QHBoxLayout()
        file_line_layout.addWidget(self.folder_path)
        file_line_layout.addWidget(self.set_folder_button)

        self.main_layout.addLayout(file_line_layout)
        self.main_layout.addWidget(self.search_line_edit)
        self.main_layout.addWidget(self.tree_view)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        self.setLayout(self.main_layout)

    def emit_file_signal(self):
        index = self.tree_view.currentIndex()
        if not self.model.isDir(index):
            self.file_double_clicked.emit(self.get_selected_path())

    def _set_filter(self):
        filters = []
        for filter_string in self.search_line_edit.text().split(","):
            filter_string = filter_string.replace(" ", "")
            filters.append("*{}*.fbx".format(filter_string))
        self.tree_view.expandAll()
        self.model.setNameFilters(filters)

    def set_active_folder(self, folder_path=None):
        if not folder_path:
            folder_path = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Choose Mocap Folder",
                dir=self.get_folder()
                )
        if not folder_path:
            return
        
        self._set_folder(folder_path)
            
    def get_selected_path(self):
        index = self.tree_view.currentIndex()
        file_path = self.model.filePath(index)
        return file_path.replace("\\", "/")
            
    def get_selected_paths(self):
        file_paths = []
        for index in self.tree_view.selectedIndexes():
            file_path = self.model.filePath(index).replace("\\", "/")
            file_paths.append(file_path)
        return file_paths

    def get_folder(self):
        return self.folder_path.text()

    def _set_folder(self, folder_path):
        self.model.setRootPath(folder_path)
        self.tree_view.setRootIndex(self.model.index(folder_path))
        self.folder_path.setText(folder_path)


class MocapBrowserWindow(ui_utils.ToolWindow):
    def __init__(self):
        super(MocapBrowserWindow, self).__init__()
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(main_layout)

        main_splitter = QtWidgets.QSplitter()
        self.browser_file_tree = MocapFileTree(self)
        self.browser_viewport_widget = MocapBrowserViewportWidget(self)
        main_splitter.addWidget(self.browser_file_tree)
        main_splitter.addWidget(self.browser_viewport_widget)
        main_splitter.setStretchFactor(1, 6)

        # connect signals between widgets
        self.browser_file_tree.file_double_clicked.connect(self.browser_viewport_widget.load_fbx_files)
        self.browser_file_tree.tree_view.customContextMenuRequested.connect(self.context_menu)

        main_layout.addWidget(main_splitter)
        self.setCentralWidget(main_widget)
        self.context_menu_actions = [
            {"Load all selected": self.load_all_selected},
        ]

    def context_menu(self):
        return ui_utils.build_menu_from_action_list(self.context_menu_actions)

    def load_all_selected(self):
        self.browser_viewport_widget.load_fbx_files(self.browser_file_tree.get_selected_paths())

    
def main(refresh=False):
    win = MocapBrowserWindow()
    win.main(refresh=refresh)
    win.resize(QtCore.QSize(720, 480))

    if standalone_app:

        # just gonna leave this debug thing here for now
        test_folder = r"D:\Google Drive\Maya_Home\Brekel Recordings\SecondAttempt"
        if os.path.exists(test_folder):
            win.browser_file_tree.set_active_folder(test_folder)
        
        ui_utils.standalone_app_window = win
        from .resources import stylesheets
        stylesheets.apply_standalone_stylesheet()
        sys.exit(standalone_app.exec_())


if __name__ == "__main__":
    main()

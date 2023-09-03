
from . import ui_utils
from .ui_utils import QtCore, QtWidgets, QtGui, QtOpenGL

# Requires PyOpenGL
from OpenGL import GL
from .gl_utils import camera
from .gl_utils import scene_utils


class BaseViewportWidget(QtOpenGL.QGLWidget):
    """Super Basic 3D Viewport with navigation controls"""
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
    """Basic viewport, but now with logic for keeping track of Time"""

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
        if not self.play_active:
            return
        
        if self.active_frame >= self.end_frame:
            self.set_active_frame(self.start_frame)
        else:
            self.set_active_frame(self.active_frame + 1)
    
    def increment_frame(self, value=1):
        target_frame = self.active_frame + value
        target_frame = max(self.start_frame, min(target_frame, self.end_frame)) # clamp within timeline
        self.set_active_frame(target_frame)
    
    def go_to_start_frame(self):
        self.set_active_frame(self.start_frame)
    
    def go_to_end_frame(self):
        self.set_active_frame(self.end_frame)
    
    def set_active_frame(self, value):
        self.active_frame = value
        self.update()
        self.frame_changed.emit(self.active_frame)

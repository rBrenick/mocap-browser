import os

from . import ui_utils
from .ui_utils import QtCore, QtWidgets

# Requires PyOpenGL
from OpenGL import GL

# Requires FBX SDK
import fbx
from . import fbx_utils
from . import fbx_gl_utils

# Base Viewport Widget
from .qt_viewport import AnimationViewportWidget


class ViewportSceneDescription(object):
    def __init__(self):
        self.transform_hierarchy = {}


class FBXViewportWidget(AnimationViewportWidget):
    """3D OpenGL Viewport that knows how to display FBX files"""

    scene_content_updated = QtCore.Signal(ViewportSceneDescription)

    def __init__(self, parent):
        super().__init__(parent)

        self.fbx_handlers = []
        self.time = fbx.FbxTime()

        self.hidden_nodes = []

        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():  # only if file or link is dropped
            return
        
        fbx_paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path.lower().endswith(".fbx"):
                fbx_paths.append(local_path)

        if not fbx_paths:
            QtWidgets.QMessageBox.warning(self, "Invalid Paths", "Could not find any .fbx's in the dropped files")
            return

        self.load_fbx_files(fbx_paths)

    def paintGL(self):
        super().paintGL()

        GL.glLineWidth(4.0)
        GL.glBegin(GL.GL_LINES)
        for fbx_handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            if not fbx_handler.is_loaded:
                continue

            hidden_nodes = fbx_handler.hidden_nodes

            self.time.SetTime(0, 0, 0, int(self.active_frame))

            # get skeleton at current frame
            skel_points = fbx_gl_utils.recursive_get_fbx_skeleton_positions(
                fbx_handler.scene.GetRootNode(), 
                self.time,
                fbx_handler.display_color,
                )

            # draw skeleton
            GL.glColor(*fbx_handler.display_color)
            for bone_name, pos_list in skel_points.items():
                if bone_name in hidden_nodes:
                    continue

                node_pos = pos_list[0]
                parent_pos = pos_list[1]
                GL.glVertex(node_pos[0], node_pos[1], node_pos[2])
                GL.glVertex(parent_pos[0], parent_pos[1], parent_pos[2])
        GL.glEnd()
    
    def load_fbx_files(self, fbx_file_paths=None):
        if not fbx_file_paths:
            return

        self.remove_existing_handlers()

        if not isinstance(fbx_file_paths, list):
            fbx_file_paths = [fbx_file_paths]

        scene_desc = ViewportSceneDescription()

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

            # assign random skeleton color to distinguish multiple clips
            if len(fbx_file_paths) > 1:
                fbx_handler.display_color = ui_utils.get_random_color()
            
            # send scene data to tree widget
            scene_hiearchy = fbx_utils.recursive_get_fbx_skeleton_hierarchy(
                fbx_handler.scene.GetRootNode(),
                )
            scene_desc.transform_hierarchy[fbx_file] = scene_hiearchy

        self.start_frame = min(start_times)
        self.end_frame = max(end_times)
        self.active_frame = self.start_frame
        self.scene_content_updated.emit(scene_desc)
        self.update()
    
    def remove_existing_handlers(self):
        for handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            handler.unload_scene()
        self.fbx_handlers.clear()
    
    def set_node_visibility(self, fbx_path, node_names, state):
        for fbx_handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            if fbx_handler.file_path != fbx_path:
                continue

            if state:
                for node in node_names:
                    if node in fbx_handler.hidden_nodes:
                        fbx_handler.hidden_nodes.remove(node)
            else:
                for node in node_names:
                    fbx_handler.hidden_nodes.append(node)
        
        self.update()

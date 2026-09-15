import os

from . import ui_utils
from .ui_utils import QtCore, QtWidgets
from .mocap_browser_logger import get_logger

# Requires PyOpenGL
from OpenGL import GL

# Requires FBX SDK
import fbx
from . import fbx_utils
from . import fbx_gl_utils
from . import fbx_skinning
from .gl_utils import scene_utils

# Base Viewport Widget
from .qt_viewport import AnimationViewportWidget

log = get_logger()


class ViewportSceneDescription(object):
    def __init__(self):
        self.transform_hierarchy = {}


class FBXViewportWidget(AnimationViewportWidget):
    """3D OpenGL Viewport that knows how to display FBX files"""

    scene_content_updated = QtCore.Signal(ViewportSceneDescription)
    preview_mesh_changed = QtCore.Signal(str)

    def __init__(self, parent):
        super().__init__(parent)

        self.fbx_handlers = []
        self.time = fbx.FbxTime()

        self.hidden_nodes = []

        # A preview mesh is a skinned character loaded from its own file and driven by
        # whichever clip is open, so mocap can be reviewed on a body instead of on bones.
        # Clips that ship their own meshes use those instead.
        self.preview_mesh_path = ""
        self.preview_meshes = []

        self.show_meshes = True
        self.show_skeleton = True

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

        self.time.SetTime(0, 0, 0, int(self.active_frame))

        drew_meshes = self.draw_meshes()

        if self.show_skeleton:
            # With a mesh in the way the bones would be buried inside it, so they are drawn
            # through it - the same x-ray joints every animation package defaults to.
            self.draw_skeletons(xray=drew_meshes)

    def draw_meshes(self):
        """Draw the skinned meshes of every loaded clip. Returns True if anything drew."""
        if not self.show_meshes:
            return False

        drew_anything = False
        for fbx_handler in self.fbx_handlers:  # type: fbx_utils.FbxHandler
            if not fbx_handler.is_loaded:
                continue

            # Multiple clips get a random colour each to tell them apart; toned down a
            # little because a fully saturated diffuse colour washes out under the light.
            mesh_color = tuple(channel * 0.75 for channel in fbx_handler.display_color)

            for binding in fbx_handler.mesh_bindings:
                if binding.mesh.name in fbx_handler.hidden_nodes:
                    continue

                positions, normals = binding.evaluate(self.time, self.active_frame)
                scene_utils.draw_mesh(positions, normals, binding.mesh.triangles, mesh_color)
                drew_anything = True

        return drew_anything

    def draw_skeletons(self, xray=False):
        if xray:
            GL.glDisable(GL.GL_DEPTH_TEST)

        GL.glLineWidth(4.0)
        GL.glBegin(GL.GL_LINES)
        for fbx_handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            if not fbx_handler.is_loaded:
                continue

            hidden_nodes = fbx_handler.hidden_nodes

            # get skeleton at current frame
            skel_points = fbx_gl_utils.recursive_get_fbx_skeleton_positions(
                fbx_handler.scene.GetRootNode(),
                self.time,
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

        if xray:
            GL.glEnable(GL.GL_DEPTH_TEST)

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
            if not fbx_handler.load_scene(fbx_file):
                print(f"Failed to load fbx file: {fbx_file}")
                continue

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

        if not self.fbx_handlers:
            return

        self.bind_meshes_to_clips()

        self.start_frame = min(start_times)
        self.end_frame = max(end_times)
        self.active_frame = self.start_frame
        self.scene_content_updated.emit(scene_desc)
        self.update()

    def remove_existing_handlers(self):
        for handler in self.fbx_handlers: # type: fbx_utils.FbxHandler
            handler.unload_scene()
        self.fbx_handlers.clear()

    #########################################################
    # Skinned mesh preview

    def bind_meshes_to_clips(self):
        """Point every loaded clip's skeleton at the meshes it should deform.

        A clip that ships its own meshes deforms those; anything else falls back to the
        preview mesh, matched up bone name by bone name.
        """
        for fbx_handler in self.fbx_handlers:  # type: fbx_utils.FbxHandler
            meshes = fbx_handler.meshes if fbx_handler.meshes else self.preview_meshes
            fbx_handler.bind_meshes(meshes)

    def set_preview_mesh(self, fbx_file_path, warn=True):
        """Load a skinned mesh to drape over loaded clips. Returns True on success.

        `warn` is off while restoring a mesh remembered from a previous session, where a
        modal dialog would block the window from ever finishing construction.
        """
        if not fbx_file_path:
            self.clear_preview_mesh()
            return True

        def report(title, message):
            if warn:
                QtWidgets.QMessageBox.warning(self, title, message)
            else:
                log.warning("%s - %s", title, " ".join(message.split()))

        if fbx_skinning.np is None:
            report(
                "numpy Required",
                "Previewing a skinned mesh needs numpy, which could not be imported:"
                "\n\n{}".format(fbx_skinning.NUMPY_ERROR),
            )
            return False

        if not os.path.exists(fbx_file_path):
            report("Invalid Path", "Could not find:\n\n{}".format(fbx_file_path))
            return False

        mesh_handler = fbx_utils.FbxHandler()
        if not mesh_handler.load_scene(fbx_file_path):
            report("Load Failed", "Could not read:\n\n{}".format(fbx_file_path))
            return False

        # A SkinnedMesh is plain numpy once extracted, so the scene it came out of can go
        # straight back out of memory - only the mocap scenes need to stay loaded.
        meshes = mesh_handler.meshes
        mesh_handler.unload_scene()

        if not meshes:
            report("No Meshes", "No meshes were found in:\n\n{}".format(fbx_file_path))
            return False

        self.preview_meshes = meshes
        self.preview_mesh_path = fbx_file_path
        self.bind_meshes_to_clips()
        self.preview_mesh_changed.emit(self.preview_mesh_path)
        self.update()
        return True

    def clear_preview_mesh(self):
        self.preview_meshes = []
        self.preview_mesh_path = ""
        self.bind_meshes_to_clips()
        self.preview_mesh_changed.emit(self.preview_mesh_path)
        self.update()

    def get_unbound_bone_report(self):
        """Bones the preview mesh wanted but the loaded clips do not have.

        Worth surfacing, because a mesh whose skeleton does not line up with the clip is
        the one failure that looks like a rendering bug rather than a mismatch.
        """
        missing = set()
        for fbx_handler in self.fbx_handlers:  # type: fbx_utils.FbxHandler
            for binding in fbx_handler.mesh_bindings:
                missing.update(binding.missing_bones)
        return sorted(missing)

    def set_show_meshes(self, state):
        self.show_meshes = bool(state)
        self.update()

    def set_show_skeleton(self, state):
        self.show_skeleton = bool(state)
        self.update()

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

import sys
import fbx

from . import fbx_skinning


def InitializeSdkObjects():
    # The first thing to do is to create the FBX SDK manager which is the
    # object allocator for almost all the classes in the SDK.
    lSdkManager = fbx.FbxManager.Create()
    if not lSdkManager:
        sys.exit(0)

    # Create an IOSettings object
    ios = fbx.FbxIOSettings.Create(lSdkManager, fbx.IOSROOT)
    lSdkManager.SetIOSettings(ios)

    # Create the entity that will hold the scene.
    lScene = fbx.FbxScene.Create(lSdkManager, "")

    return (lSdkManager, lScene)


def LoadScene(pSdkManager, pScene, pFileName):
    lImporter = fbx.FbxImporter.Create(pSdkManager, "")
    result = lImporter.Initialize(pFileName, -1, pSdkManager.GetIOSettings())
    if not result:
        return False

    if lImporter.IsFBX():
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_MATERIAL, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_TEXTURE, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_EMBEDDED, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_SHAPE, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GOBO, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_ANIMATION, True)
        pSdkManager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GLOBAL_SETTINGS, True)

    result = lImporter.Import(pScene)
    lImporter.Destroy()
    return result


class FbxHandler():
    def __init__(self):
        self.file_path = ""
        self.manager, self.scene = InitializeSdkObjects()
        self.anim_stack = None
        self.anim_layer = None
        self.is_loaded = False
        self.display_color = (1.0, 1.0, 1.0)
        self.hidden_nodes = []

        # Skinning support. `meshes` are the ones this file carries itself; `pose` is this
        # file's skeleton, which can just as well drive meshes loaded from another file.
        self.meshes = []
        self.pose = None
        self.mesh_bindings = []

    def load_scene(self, file_path):
        if not LoadScene(self.manager, self.scene, file_path):
            return False

        self.file_path = file_path
        self.anim_stack = self.scene.GetSrcObject(fbx.FbxCriteria().ObjectType(fbx.FbxAnimStack.ClassId), 0)
        # A mesh-only FBX has no animation to speak of, which is fine - it still has a
        # skeleton worth binding to.
        if self.anim_stack:
            self.anim_layer = self.anim_stack.GetSrcObject(fbx.FbxCriteria().ObjectType(fbx.FbxAnimLayer.ClassId), 0)

        self.meshes = fbx_skinning.extract_skinned_meshes(self.scene)
        self.pose = fbx_skinning.SkeletonPose(self.scene)
        self.is_loaded = True
        return True

    def unload_scene(self):
        self.meshes = []
        self.mesh_bindings = []
        self.pose = None
        self.manager.Destroy()
        self.is_loaded = False

    def bind_meshes(self, meshes):
        """Drive `meshes` with this file's skeleton, matching bones up by name."""
        self.mesh_bindings = [
            fbx_skinning.SkinnedMeshBinding(mesh, self.pose) for mesh in meshes
        ]
        return self.mesh_bindings

    def get_start_frame(self):
        if not self.anim_stack:
            return 0
        return self.anim_stack.GetLocalTimeSpan().GetStart().GetFrameCount()

    def get_end_frame(self):
        if not self.anim_stack:
            return 0
        return self.anim_stack.GetLocalTimeSpan().GetStop().GetFrameCount()

    
def recursive_get_fbx_skeleton_hierarchy(node, parent_name=None, output_dict=None):
    if output_dict is None:
        output_dict = dict()
    
    node_name = None
    node_attribute = node.GetNodeAttribute()
    if node_attribute:
        node_name = node.GetName()
        output_dict[node_name] = parent_name

    for i in range(node.GetChildCount()):
        recursive_get_fbx_skeleton_hierarchy(node.GetChild(i), node_name, output_dict)
    
    return output_dict

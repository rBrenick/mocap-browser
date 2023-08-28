import FbxCommon
import fbx

class FbxHandler():
    def __init__(self):
        self.manager, self.scene = FbxCommon.InitializeSdkObjects()
        self.anim_stack = None
        self.anim_layer = None
        self.is_loaded = False
        self.display_color = (1.0, 1.0, 1.0)

    def load_scene(self, file_path):
        self.result = FbxCommon.LoadScene(self.manager, self.scene, file_path)
        self.anim_stack = self.scene.GetSrcObject(fbx.FbxCriteria().ObjectType(fbx.FbxAnimStack.ClassId), 0)
        self.anim_layer = self.anim_stack.GetSrcObject(fbx.FbxCriteria().ObjectType(fbx.FbxAnimLayer.ClassId), 0)
        self.is_loaded = True

    def unload_scene(self):
        self.manager.Destroy()
        self.is_loaded = False

    def get_start_frame(self):
        return self.anim_stack.GetLocalTimeSpan().GetStart().GetFrameCount()

    def get_end_frame(self):
        return self.anim_stack.GetLocalTimeSpan().GetStop().GetFrameCount()
import FbxCommon
import fbx

class FbxHandler():
    def __init__(self):
        self.file_path = ""
        self.manager, self.scene = FbxCommon.InitializeSdkObjects()
        self.anim_stack = None
        self.anim_layer = None
        self.is_loaded = False
        self.display_color = (1.0, 1.0, 1.0)
        self.hidden_nodes = []

    def load_scene(self, file_path):
        FbxCommon.LoadScene(self.manager, self.scene, file_path)
        self.file_path = file_path
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

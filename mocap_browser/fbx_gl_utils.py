from .gl_utils.scene_utils import  draw_locator, draw_line
import FbxCommon
SKELETON_NODE_TYPE = FbxCommon.FbxNodeAttribute.eSkeleton

def recursive_draw_fbx_skeleton(node, time, color, parent_pos=None):
    node_pos = None
    node_attribute = node.GetNodeAttribute()
    if node_attribute:
        if node_attribute.GetAttributeType() == SKELETON_NODE_TYPE:
            node_pos = node.EvaluateGlobalTransform(time).GetT()
            if parent_pos is not None:
                draw_line(node_pos, parent_pos, color)

    for i in range(node.GetChildCount()):
        recursive_draw_fbx_skeleton(node.GetChild(i), time, color, node_pos)
        
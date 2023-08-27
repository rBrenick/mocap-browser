from .gl_utils.scene_utils import  draw_locator, draw_line
import FbxCommon
SKELETON_NODE_TYPE = FbxCommon.FbxNodeAttribute.eSkeleton

def recursive_draw_fbx_skeleton(node, time, color):
    for i in range(node.GetChildCount()):
        recursive_draw_fbx_skeleton(node.GetChild(i), time, color)
    
    node_attribute = node.GetNodeAttribute()
    if not node_attribute:
        return

    if node_attribute.GetAttributeType() != SKELETON_NODE_TYPE:
        return
    
    node_transform = node.EvaluateGlobalTransform(time) # type: fbx.FbxAMatrix

    parent_transform = node.GetParent().EvaluateGlobalTransform(time) # type: fbx.FbxAMatrix
    parent_pos = parent_transform.GetT()
    parent_at_origo = all(coord == 0.0 for coord in parent_pos)

    if not parent_at_origo:
        draw_line(node_transform.GetT(), parent_pos, color)
    
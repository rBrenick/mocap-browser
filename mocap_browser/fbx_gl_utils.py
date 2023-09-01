from .gl_utils.scene_utils import  draw_locator, draw_line
import FbxCommon
SKELETON_NODE_TYPE = FbxCommon.FbxNodeAttribute.eSkeleton

def recursive_get_fbx_skeleton_positions(node, time, parent_pos=None, output_dict=None):
    if output_dict is None:
        output_dict = dict()
    
    node_pos = None
    node_attribute = node.GetNodeAttribute()
    if node_attribute:
        if node_attribute.GetAttributeType() == SKELETON_NODE_TYPE:
            node_pos = node.EvaluateGlobalTransform(time).GetT()
            node_name = node.GetInitialName()
            if parent_pos is not None:
                output_dict[node_name] = (node_pos, parent_pos)

    for i in range(node.GetChildCount()):
        recursive_get_fbx_skeleton_positions(node.GetChild(i), time, node_pos, output_dict)
    
    return output_dict
        
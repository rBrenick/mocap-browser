"""Pull skinned geometry out of an FBX scene and evaluate it on the CPU.

The viewport draws bones as lines, which is cheap enough to do with immediate mode GL.
A character mesh is not - the preview mesh in this repo is ~20k vertices across 7 meshes,
so the per-frame work is vectorised with numpy and handed to GL as a vertex array.

Skinning happens at the control point level. Normals stored per polygon vertex are
averaged down to their control point while loading, which loses hard edges but keeps the
per-frame cost proportional to the control point count instead of the triangle count.
"""

import fbx

try:
    import numpy as np
    NUMPY_ERROR = None
except ImportError as exc:  # numpy ships with Maya, but a bare standalone venv may lack it
    np = None
    NUMPY_ERROR = str(exc)


# The FBX SDK moved its enums into nested EType/EDeformerType/EPivotSet classes at some
# point. Older bindings (FBX SDK 2020.3.7 and earlier) expose them flat on the parent.
try:
    MESH_NODE_TYPE = fbx.FbxNodeAttribute.EType.eMesh
except AttributeError:
    MESH_NODE_TYPE = fbx.FbxNodeAttribute.eMesh

try:
    SKIN_DEFORMER_TYPE = fbx.FbxDeformer.EDeformerType.eSkin
except AttributeError:
    SKIN_DEFORMER_TYPE = fbx.FbxDeformer.eSkin

try:
    SOURCE_PIVOT = fbx.FbxNode.EPivotSet.eSourcePivot
except AttributeError:
    SOURCE_PIVOT = fbx.FbxNode.eSourcePivot

try:
    BY_CONTROL_POINT = fbx.FbxLayerElement.EMappingMode.eByControlPoint
    BY_POLYGON_VERTEX = fbx.FbxLayerElement.EMappingMode.eByPolygonVertex
    INDEX_TO_DIRECT = fbx.FbxLayerElement.EReferenceMode.eIndexToDirect
except AttributeError:
    BY_CONTROL_POINT = fbx.FbxLayerElement.eByControlPoint
    BY_POLYGON_VERTEX = fbx.FbxLayerElement.eByPolygonVertex
    INDEX_TO_DIRECT = fbx.FbxLayerElement.eIndexToDirect


# Influences kept per vertex. Four is what every real time engine uses, and dropping the
# tail keeps the per-frame matrix blend to a fixed number of numpy operations.
MAX_INFLUENCES = 4


def to_numpy_matrix(fbx_matrix):
    """FbxAMatrix -> (4, 4) numpy array that transforms column vectors.

    FbxAMatrix.Get(row, column) uses the row vector convention (translation lives in row
    3), so the array is the transpose of what Get() reports. That makes `matrix @ point`
    agree with FbxAMatrix.MultT().
    """
    return np.array(
        [[fbx_matrix.Get(j, i) for j in range(4)] for i in range(4)],
        dtype=np.float32,
    )


def get_geometric_transform(node):
    """The mesh offset FBX keeps separate from the node transform."""
    geometric_transform = fbx.FbxAMatrix()
    geometric_transform.SetTRS(
        node.GetGeometricTranslation(SOURCE_PIVOT),
        node.GetGeometricRotation(SOURCE_PIVOT),
        node.GetGeometricScaling(SOURCE_PIVOT),
    )
    return geometric_transform


class SkinnedMesh(object):
    """Bind pose geometry plus the bone weights needed to pose it.

    Everything here is plain numpy, so the FBX scene the mesh came from can be unloaded
    once extraction is done. The bones are referenced by name, which is what lets a
    preview mesh be driven by the skeleton of a completely different mocap file.
    """

    def __init__(self, name):
        self.name = name

        self.positions = None  # (V, 4) bind pose control points, homogeneous
        self.normals = None  # (V, 3) bind pose normals
        self.triangles = None  # (T * 3,) indices into the control points

        # Bone slot `b` is driven by the scene node called bone_names[b]. The last slot is
        # always the mesh's own fallback and may be None, see extract_skinned_mesh.
        self.bone_names = []
        self.inverse_bind = None  # (B, 4, 4) bone space <- geometry space, at bind time
        self.bind_matrices = None  # (B, 4, 4) skinning matrices that reproduce the bind pose

        self.skin_indices = None  # (V, MAX_INFLUENCES) into bone_names
        self.skin_weights = None  # (V, MAX_INFLUENCES) normalised per vertex

    @property
    def vertex_count(self):
        return 0 if self.positions is None else len(self.positions)

    @property
    def triangle_count(self):
        return 0 if self.triangles is None else len(self.triangles) // 3

    def build_skin_matrices(self, pose, time):
        """One (B, 4, 4) stack of geometry-space -> world-space matrices for `time`.

        A bone the driving skeleton does not have keeps its bind matrix, so vertices
        weighted to it stay where they sat at bind time rather than collapsing.
        """
        skin_matrices = self.bind_matrices.copy()
        for bone_index, bone_name in enumerate(self.bone_names):
            bone_global = pose.get_matrix(bone_name, time)
            if bone_global is None:
                continue
            skin_matrices[bone_index] = bone_global @ self.inverse_bind[bone_index]
        return skin_matrices

    def evaluate(self, pose, time):
        """Pose the mesh, returning (positions, normals) as float32 (V, 3) arrays."""
        skin_matrices = self.build_skin_matrices(pose, time)

        # Linear blend skinning is linear in the matrices, so blending the matrices first
        # costs one gather instead of one matrix-vector product per influence.
        blended = np.einsum(
            "vk,vkij->vij", self.skin_weights, skin_matrices[self.skin_indices]
        )

        # Slicing the matrix rather than the result keeps both outputs C-contiguous, which
        # is what glVertexPointer/glNormalPointer need to read them without a copy.
        positions = np.einsum("vij,vj->vi", blended[:, :3, :], self.positions)
        normals = np.einsum("vij,vj->vi", blended[:, :3, :3], self.normals)

        # Skinning can scale normals; GL_NORMALIZE would fix the lighting but normalising
        # here is cheap and keeps the fixed function state simpler.
        lengths = np.linalg.norm(normals, axis=1)
        np.maximum(lengths, 1e-8, out=lengths)
        normals /= lengths[:, None]

        return positions, normals


def _extract_triangles(mesh):
    """Fan triangulate the polygons into a flat index array of control points."""
    polygon_vertices = mesh.GetPolygonVertices()
    polygon_count = mesh.GetPolygonCount()

    triangles = []
    start = 0
    for polygon_index in range(polygon_count):
        size = mesh.GetPolygonSize(polygon_index)
        if size >= 3:
            first = polygon_vertices[start]
            for corner in range(1, size - 1):
                triangles.append(first)
                triangles.append(polygon_vertices[start + corner])
                triangles.append(polygon_vertices[start + corner + 1])
        start += size

    return np.array(triangles, dtype=np.uint32)


def _extract_normals(mesh, vertex_count):
    """Per control point normals, averaging polygon vertex normals where needed."""
    layer = mesh.GetLayer(0)
    layer_normals = layer.GetNormals() if layer else None
    if layer_normals is None:
        return None

    direct_array = list(layer_normals.GetDirectArray())
    if not direct_array:
        return None

    def normal_at(element_index):
        if layer_normals.GetReferenceMode() == INDEX_TO_DIRECT:
            element_index = layer_normals.GetIndexArray().GetAt(element_index)
        value = direct_array[element_index]
        return value[0], value[1], value[2]

    mapping_mode = layer_normals.GetMappingMode()

    if mapping_mode == BY_CONTROL_POINT:
        if len(direct_array) < vertex_count:
            return None
        return np.array(
            [normal_at(i) for i in range(vertex_count)], dtype=np.float32
        )

    if mapping_mode == BY_POLYGON_VERTEX:
        normals = np.zeros((vertex_count, 3), dtype=np.float32)
        polygon_vertices = mesh.GetPolygonVertices()
        for element_index, control_point in enumerate(polygon_vertices):
            if element_index >= len(direct_array):
                break
            normals[control_point] += normal_at(element_index)
        return normals

    return None


def _extract_skin_weights(mesh, vertex_count, static_slot):
    """Top MAX_INFLUENCES bone weights per control point, plus the bone name per slot."""
    bone_names = []
    influences = [[] for _ in range(vertex_count)]

    for deformer_index in range(mesh.GetDeformerCount(SKIN_DEFORMER_TYPE)):
        skin = mesh.GetDeformer(deformer_index, SKIN_DEFORMER_TYPE)
        for cluster_index in range(skin.GetClusterCount()):
            cluster = skin.GetCluster(cluster_index)
            link = cluster.GetLink()
            if link is None:
                continue

            bone_index = len(bone_names)
            bone_names.append(link.GetName())

            control_points = cluster.GetControlPointIndices()
            weights = cluster.GetControlPointWeights()
            for control_point, weight in zip(control_points, weights):
                if weight > 0.0 and control_point < vertex_count:
                    influences[control_point].append((weight, bone_index))

    # The fallback slot catches vertices no cluster reached, and carries unskinned meshes
    # whose only "bone" is the mesh node itself.
    bone_names.append(static_slot)
    fallback_index = len(bone_names) - 1

    skin_indices = np.zeros((vertex_count, MAX_INFLUENCES), dtype=np.int32)
    skin_weights = np.zeros((vertex_count, MAX_INFLUENCES), dtype=np.float32)

    for vertex, vertex_influences in enumerate(influences):
        if not vertex_influences:
            skin_indices[vertex, 0] = fallback_index
            skin_weights[vertex, 0] = 1.0
            continue

        vertex_influences.sort(reverse=True)
        kept = vertex_influences[:MAX_INFLUENCES]
        total = sum(weight for weight, _ in kept)
        if total <= 0.0:
            skin_indices[vertex, 0] = fallback_index
            skin_weights[vertex, 0] = 1.0
            continue

        for slot, (weight, bone_index) in enumerate(kept):
            skin_indices[vertex, slot] = bone_index
            skin_weights[vertex, slot] = weight / total

    return bone_names, skin_indices, skin_weights


def extract_skinned_mesh(node):
    """Build a SkinnedMesh from a mesh node, or None if there is nothing to draw."""
    mesh = node.GetNodeAttribute()
    if mesh is None or mesh.GetAttributeType() != MESH_NODE_TYPE:
        return None

    vertex_count = mesh.GetControlPointsCount()
    if vertex_count == 0 or mesh.GetPolygonCount() == 0:
        return None

    skinned_mesh = SkinnedMesh(node.GetName())

    control_points = mesh.GetControlPoints()
    positions = np.ones((vertex_count, 4), dtype=np.float32)
    positions[:, :3] = [(p[0], p[1], p[2]) for p in control_points]
    skinned_mesh.positions = positions

    skinned_mesh.triangles = _extract_triangles(mesh)
    if skinned_mesh.triangles.size == 0:
        return None

    normals = _extract_normals(mesh, vertex_count)
    if normals is None:
        normals = _face_normals(positions, skinned_mesh.triangles)
    skinned_mesh.normals = normals

    geometric_transform = get_geometric_transform(node)
    has_skin = mesh.GetDeformerCount(SKIN_DEFORMER_TYPE) > 0

    if has_skin:
        # A vertex the skin never reached stays wherever the mesh sat at bind time, so the
        # fallback slot is deliberately nameless - no skeleton will ever resolve it.
        static_slot = None
    else:
        # Nothing is deforming this mesh, so the mesh node drives it like a single bone.
        static_slot = node.GetName()

    bone_names, skin_indices, skin_weights = _extract_skin_weights(
        mesh, vertex_count, static_slot
    )
    skinned_mesh.bone_names = bone_names
    skinned_mesh.skin_indices = skin_indices
    skinned_mesh.skin_weights = skin_weights

    bone_count = len(bone_names)
    inverse_bind = np.zeros((bone_count, 4, 4), dtype=np.float32)
    bind_matrices = np.zeros((bone_count, 4, 4), dtype=np.float32)

    mesh_bind_transform = None
    bone_index = 0
    for deformer_index in range(mesh.GetDeformerCount(SKIN_DEFORMER_TYPE)):
        skin = mesh.GetDeformer(deformer_index, SKIN_DEFORMER_TYPE)
        for cluster_index in range(skin.GetClusterCount()):
            cluster = skin.GetCluster(cluster_index)
            if cluster.GetLink() is None:
                continue

            # The mesh's global transform at bind time, including the geometric offset.
            mesh_at_bind = fbx.FbxAMatrix()
            cluster.GetTransformMatrix(mesh_at_bind)
            mesh_at_bind = mesh_at_bind * geometric_transform

            # The bone's global transform at bind time.
            bone_at_bind = fbx.FbxAMatrix()
            cluster.GetTransformLinkMatrix(bone_at_bind)

            inverse_bind[bone_index] = to_numpy_matrix(
                bone_at_bind.Inverse() * mesh_at_bind
            )
            bind_matrices[bone_index] = to_numpy_matrix(mesh_at_bind)
            mesh_bind_transform = bind_matrices[bone_index]
            bone_index += 1

    if has_skin:
        # Leftover vertices sit at the mesh's bind pose.
        fallback = mesh_bind_transform
        if fallback is None:
            fallback = to_numpy_matrix(geometric_transform)
        inverse_bind[bone_index] = fallback
        bind_matrices[bone_index] = fallback
    else:
        node_transform = to_numpy_matrix(node.EvaluateGlobalTransform())
        geometry = to_numpy_matrix(geometric_transform)
        inverse_bind[bone_index] = geometry
        bind_matrices[bone_index] = node_transform @ geometry

    skinned_mesh.inverse_bind = inverse_bind
    skinned_mesh.bind_matrices = bind_matrices

    return skinned_mesh


def _face_normals(positions, triangles):
    """Smooth normals accumulated from the triangles, for meshes that ship without any."""
    normals = np.zeros((len(positions), 3), dtype=np.float32)
    corners = triangles.reshape(-1, 3)
    a = positions[corners[:, 0], :3]
    b = positions[corners[:, 1], :3]
    c = positions[corners[:, 2], :3]
    face = np.cross(b - a, c - a)
    for corner in range(3):
        np.add.at(normals, corners[:, corner], face)
    return normals


def extract_skinned_meshes(scene):
    """Every drawable mesh in the scene, as SkinnedMesh objects."""
    if np is None:
        return []

    meshes = []

    def walk(node):
        attribute = node.GetNodeAttribute()
        if attribute is not None and attribute.GetAttributeType() == MESH_NODE_TYPE:
            skinned_mesh = extract_skinned_mesh(node)
            if skinned_mesh is not None:
                meshes.append(skinned_mesh)
        for child_index in range(node.GetChildCount()):
            walk(node.GetChild(child_index))

    walk(scene.GetRootNode())
    return meshes


class SkeletonPose(object):
    """World matrices for the skeleton driving the meshes, cached per frame.

    Meshes normally share one skeleton - the preview mesh in this repo is 7 meshes over the
    same 61 bones - so evaluating each bone once per frame rather than once per mesh is
    worth roughly half the per-frame cost.
    """

    def __init__(self, scene):
        self.nodes = {}
        self._frame = None
        self._matrices = {}

        def walk(node):
            name = node.GetName()
            # First one wins; duplicate names in an FBX are ambiguous either way.
            if name not in self.nodes:
                self.nodes[name] = node
            for child_index in range(node.GetChildCount()):
                walk(node.GetChild(child_index))

        walk(scene.GetRootNode())

    def has_bone(self, bone_name):
        return bone_name is not None and bone_name in self.nodes

    def set_frame(self, frame):
        if frame != self._frame:
            self._frame = frame
            self._matrices.clear()

    def get_matrix(self, bone_name, time):
        """World matrix of `bone_name` at `time`, or None if this skeleton lacks it."""
        if bone_name is None:
            return None

        matrix = self._matrices.get(bone_name)
        if matrix is None:
            node = self.nodes.get(bone_name)
            if node is None:
                return None
            matrix = to_numpy_matrix(node.EvaluateGlobalTransform(time))
            self._matrices[bone_name] = matrix
        return matrix


class SkinnedMeshBinding(object):
    """A SkinnedMesh wired up to the skeleton that should drive it.

    The mesh and the skeleton can come from different files - that is the whole point, it
    is what lets a shared preview mesh follow whichever mocap clip is loaded.
    """

    def __init__(self, mesh, pose):
        self.mesh = mesh
        self.pose = pose
        self.missing_bones = [
            name
            for name in mesh.bone_names
            if name is not None and not pose.has_bone(name)
        ]

        self._cached_frame = None
        self._cached_result = None

    @property
    def is_bound(self):
        """Did any bone resolve? An unbound mesh would just sit at its bind pose."""
        return any(self.pose.has_bone(name) for name in self.mesh.bone_names)

    def evaluate(self, time, frame):
        """Posed (positions, normals) for `frame`, reusing the last result when possible.

        paintGL runs on every camera move, not just on every frame change, so caching here
        keeps orbiting a loaded clip free of skinning work.
        """
        if frame != self._cached_frame:
            self.pose.set_frame(frame)
            self._cached_result = self.mesh.evaluate(self.pose, time)
            self._cached_frame = frame
        return self._cached_result

from OpenGL import GL

def draw_locator(pos, size=10):
    GL.glLineWidth(2.0)

    # X
    GL.glBegin(GL.GL_LINES)
    GL.glColor(1.0, 0.0, 0.0)
    GL.glVertex(pos[0]-size, pos[1], pos[2])
    GL.glVertex(pos[0]+size, pos[1], pos[2])
    GL.glEnd()

    # Y
    GL.glBegin(GL.GL_LINES)
    GL.glColor(0.0, 1.0, 0.0)
    GL.glVertex(pos[0], pos[1]-size, pos[2])
    GL.glVertex(pos[0], pos[1]+size, pos[2])
    GL.glEnd()

    # Z
    GL.glBegin(GL.GL_LINES)
    GL.glColor(0.0, 0.0, 1.0)
    GL.glVertex(pos[0], pos[1], pos[2]-size)
    GL.glVertex(pos[0], pos[1], pos[2]+size)
    GL.glEnd()


def draw_line(start_pos, end_pos, color=(1.0, 1.0, 1.0)):
    GL.glLineWidth(4.0)
    GL.glBegin(GL.GL_LINES)
    GL.glColor(*color)
    GL.glVertex(start_pos[0], start_pos[1], start_pos[2])
    GL.glVertex(end_pos[0], end_pos[1], end_pos[2])
    GL.glEnd()


def draw_origin_grid(grid_scale=50, grid_line_count=12):
    GL.glLineWidth(1.0)
    GL.glBegin(GL.GL_LINES)
    GL.glColor(0.25, 0.25, 0.25)

    for i in range(-grid_line_count, grid_line_count+1):
        # lines along X
        GL.glVertex3d(grid_line_count * grid_scale, 0, i * grid_scale)
        GL.glVertex3d(-grid_line_count * grid_scale, 0, i * grid_scale)

        # lines along Z
        GL.glVertex3d(i * grid_scale, 0, grid_line_count * grid_scale)
        GL.glVertex3d(i * grid_scale, 0, -grid_line_count * grid_scale)
    
    GL.glEnd()


def draw_axis_helper(scale=10):
    GL.glLineWidth(2.0)

    # X
    GL.glBegin(GL.GL_LINES)
    GL.glColor(1.0, 0.0, 0.0)
    GL.glVertex(0, 0, 0)
    GL.glVertex(scale, 0, 0)
    GL.glEnd()

    # Y
    GL.glBegin(GL.GL_LINES)
    GL.glColor(0.0, 1.0, 0.0)
    GL.glVertex(0, 0, 0)
    GL.glVertex(0, scale, 0)
    GL.glEnd()

    # Z
    GL.glBegin(GL.GL_LINES)
    GL.glColor(0.0, 0.0, 1.0)
    GL.glVertex(0, 0, 0)
    GL.glVertex(0, 0, scale)
    GL.glEnd()


# A character mesh is far too many triangles to push through glBegin/glEnd one glVertex
# call at a time, so meshes go through client side vertex arrays instead: one GL call per
# mesh rather than one per vertex.
def draw_mesh(positions, normals, triangles, color=(0.75, 0.75, 0.78)):
    """Draw an indexed triangle mesh, lit by a headlight.

    positions and normals are float32 (V, 3) arrays, triangles a flat uint32 index array.
    """
    GL.glEnable(GL.GL_LIGHTING)
    GL.glEnable(GL.GL_LIGHT0)

    # The light is positioned with an identity modelview so it stays fixed to the camera
    # rather than to the scene - the mesh is then lit from wherever you are looking at it.
    GL.glPushMatrix()
    GL.glLoadIdentity()
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (0.3, 0.5, 1.0, 0.0))
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (0.8, 0.8, 0.78, 1.0))
    GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
    GL.glPopMatrix()

    # Ambient and diffuse are kept under 1.0 together, otherwise the lit side clips to
    # white and the silhouette is all you can read of the pose.
    GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, (0.22, 0.23, 0.28, 1.0))
    # Mocap meshes are not always consistently wound, and nothing is culled, so backfaces
    # get lit too instead of showing up as black holes.
    GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, 1)

    GL.glEnable(GL.GL_COLOR_MATERIAL)
    GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
    GL.glColor(*color)

    GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
    GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
    GL.glVertexPointer(3, GL.GL_FLOAT, 0, positions)
    GL.glNormalPointer(GL.GL_FLOAT, 0, normals)
    GL.glDrawElements(GL.GL_TRIANGLES, len(triangles), GL.GL_UNSIGNED_INT, triangles)
    GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
    GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

    GL.glDisable(GL.GL_COLOR_MATERIAL)
    GL.glDisable(GL.GL_LIGHT0)
    GL.glDisable(GL.GL_LIGHTING)

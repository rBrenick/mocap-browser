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

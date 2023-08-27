#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
yoinked from https://raw.githubusercontent.com/perelo/Cubical3DPath/master/src/geom.py
same as camera.py
"""

__authors__ = 'McGuffin, Eloi Perdereau'
__date__ = '17-06-2013'


import math

from .util import signum

COORDINATES = (0, 1, 2)

class Point2D(object):
    def __init__(self,x=0,y=0):
        self.coordinates = [float(x),float(y)]
    def x(self):
        return self.coordinates[0]
    def y(self):
        return self.coordinates[1]
    def __repr__(self):
        return "Point2D("+str(self.x())+","+str(self.y())+")"
    def __str__(self):
        return "P2("+str(self.x())+","+str(self.y())+")"
    def get(self):
        return self.coordinates
    def returnCopy(self):
        return Point2D( self.x(), self.y() )
    def average(self,other):
        return Point2D( (self.x()+other.x())*0.5, (self.y()+other.y())*0.5 )
    def dominate(self,other):
        return self.x() <= other.x() and \
               self.y() <= other.y()
    def __add__(self,other):
        return Point2D( self.x()+other.x(), self.y()+other.y() )
    def __hash__(self):
        return hash(self.coordinates[0]) + hash(self.coordinates[1])
    def __eq__(self,other):
        return self.x()==other.x() and self.y()==other.y()
    def __ne__(self,other):
        return not (self==other)
    def is_in_rectangle(self, diagonal, open_seg=False):
        if open_seg:
            return ((diagonal.a.x() <=  diagonal.b.x() and diagonal.a.x() <=  self.x() <=  diagonal.b.x()) or
                    (diagonal.a.x() >=  diagonal.b.x() and diagonal.a.x() >=  self.x() >=  diagonal.b.x())) \
               and ((diagonal.a.y() <=  diagonal.b.y() and diagonal.a.y() <=  self.y() <=  diagonal.b.y()) or
                    (diagonal.a.y() >=  diagonal.b.y() and diagonal.a.y() >=  self.y() >=  diagonal.b.y()))
        else:
            return ((diagonal.a.x() <  diagonal.b.x() and diagonal.a.x() <  self.x() <  diagonal.b.x()) or
                    (diagonal.a.x() >  diagonal.b.x() and diagonal.a.x() >  self.x() >  diagonal.b.x()) or
                    (diagonal.a.x() == diagonal.b.x() and diagonal.a.x() == self.x() == diagonal.b.x())) \
               and ((diagonal.a.y() <  diagonal.b.y() and diagonal.a.y() <  self.y() <  diagonal.b.y()) or
                    (diagonal.a.y() >  diagonal.b.y() and diagonal.a.y() >  self.y() >  diagonal.b.y()) or
                    (diagonal.a.y() == diagonal.b.y() and diagonal.a.y() == self.y() == diagonal.b.y()))

class Point3D(object):
    def __init__(self,x=0,y=0,z=0):
        self.coordinates = [float(x),float(y),float(z)]
    def x(self):
        return self.coordinates[0]
    def y(self):
        return self.coordinates[1]
    def z(self):
        return self.coordinates[2]
    def __repr__(self):
        return "Point3D("+str(self.x())+","+str(self.y())+","+str(self.z())+")"
    def __str__(self):
        return "P3("+str(self.x())+","+str(self.y())+","+str(self.z())+")"
    def get(self):
        return self.coordinates
    def returnCopy(self):
        return Point3D( self.x(), self.y(), self.z() )
    def asVector3D(self):
        return Vector3D( self.x(), self.y(), self.z() )
    def distance(self,other):
        return (other-self).length()
    def average(self,other):
        return Point3D( (self.x()+other.x())*0.5, (self.y()+other.y())*0.5, (self.z()+other.z())*0.5 )
    def dominate(self,other):
        return self.x() <= other.x() and \
               self.y() <= other.y() and \
               self.z() <= other.z()
    def __add__(self,other):
        return Point3D( self.x()+other.x(), self.y()+other.y(), self.z()+other.z() )
    def __sub__(self,other):
        if isinstance(other,Vector3D):
            return Point3D( self.x()-other.x(), self.y()-other.y(), self.z()-other.z() )
        return Vector3D( self.x()-other.x(), self.y()-other.y(), self.z()-other.z() )
    def __hash__(self):
        return hash(self.coordinates[0]) + hash(self.coordinates[1]) + hash(self.coordinates[2])
    def __eq__(self,other):
        return self.x()==other.x() and self.y()==other.y() and self.z()==other.z()
    def __ne__(self,other):
        return not (self==other)
    def copy_2D(self,x,y):
        return Point2D(x(self),y(self))

class Segment(object):
    def __init__(self,a=Point3D(),b=Point3D()):
        self.a = a
        self.b = b
    def __hash__(self):
        return hash(self.a) + hash(self.b)
    def __repr__(self):
        return "Segment("+str(self.a)+","+str(self.b)+")"
    def __str__(self):
        return "S("+str(self.a)+","+str(self.b)+")"
    def __eq__(self,other):
        return (self.a==other.a and self.b==other.b) or (self.b==other.a and self.a==other.b)
    def __ne__(self,other):
        return not (self==other)
    def asLine2D(self):
        A = self.a.y()-self.b.y()
        B = self.b.x()-self.a.x()
        C = -(A * self.a.x()) - (B * self.a.y())
        return Line2D(A,B,C)
    def asLine3D(self):
        return Line3D(self.a, Vector3D.vector_from_two_points(self.a, self.b).normalized())
    def intersection(self,other,open_seg=False):
        p = self.asLine2D().intersection(other)
        return p if p is not None and p.is_in_rectangle(self, open_seg) and p.is_in_rectangle(other, open_seg) else None
    def middle(self):
        coord = [sum(t)/2 for t in zip([float(c) for c in self.a.get()], self.b.get())]
        return type(self.a)(*coord)

class Line2D(object):
    def __init__(self,A=0,B=0,C=0):
        self.A = A
        self.B = B
        self.C = C
    def intersection(self, other, open_seg=False):
        line = other
        other_is_segment = False
        if isinstance(other, Segment):
            line = line.asLine2D()
            other_is_segment = True

        det = self.A * line.B - line.A * self.B;
        if det == 0:
            return None
        x = (self.B * line.C - line.B * self.C) / det;
        y = (line.A * self.C - self.A * line.C) / det;
        p = Point2D(x, y)
        return None if other_is_segment and not p.is_in_rectangle(other, open_seg) else p
    def side(self,p):
        """
           Find the side of the line on which the point lies
           return < 0 if it lies on one side, > 0 if on the other side,
                  = 0 if it lies on this Line
        """
        return signum(A * p.x() + B * p.y() + C)

class Line3D(object):
    def __init__(self,p,v):
        self.p = p # point passing through self
        self.v = v # vector director of self
    def __str__(self):
        return 'Line3D(' + str(self.p) + ', ' + str(self.v) + ')'
    def point_at(self, val, axis):
        fctsp = ( (Point3D.x, Point3D.y, Point3D.z),
                  (Point3D.y, Point3D.x, Point3D.z),
                  (Point3D.z, Point3D.x, Point3D.y) )
        fctsv = ( (Vector3D.x, Vector3D.y, Vector3D.z),
                  (Vector3D.y, Vector3D.x, Vector3D.z),
                  (Vector3D.z, Vector3D.x, Vector3D.y) )
        create_pts = ( lambda x, y, z: Point3D(x, y, z),
                       lambda x, y, z: Point3D(y, x, z),
                       lambda x, y, z: Point3D(y, z, x) )
        xp, yp, zp = dict(zip(COORDINATES, fctsp))[axis]
        xv, yv, zv = dict(zip(COORDINATES, fctsv))[axis]
        create_pt  = dict(zip(COORDINATES, create_pts))[axis]
        # compute the damn thing
        if xv(self.v) != 0:     # else, return None
            param =  (val - xp(self.p)) / xv(self.v)
            y = yp(self.p) + (param * yv(self.v))
            z = zp(self.p) + (param * zv(self.v))
            return create_pt(val, y, z)

class LineAxis3D(Line3D):
    _create_pt_fcts = ( lambda x, y, z: Point3D(z, x, y),
                        lambda x, y, z: Point3D(x, z, y),
                        lambda x, y, z: Point3D(x, y, z) )
    _coord_pts_fcts  = ( (Point3D.y, Point3D.z, Point3D.x),
                         (Point3D.x, Point3D.z, Point3D.y),
                         (Point3D.x, Point3D.y, Point3D.z) )
    dict_create_point = dict(zip(COORDINATES, _create_pt_fcts))
    dict_coord_points = dict(zip(COORDINATES, _coord_pts_fcts))

    def __init__(self,x,y,t):
        p = LineAxis3D.dict_create_point[t](x,y,0)
        v = Vector3D.vector_from_two_points(p, LineAxis3D.dict_create_point[t](x,y,1))
        super(LineAxis3D, self).__init__(p,v)
        self.orientation = t
        self.coordinates = [x,y]
        self.create_point = LineAxis3D.dict_create_point[t]
        self.coord_points = LineAxis3D.dict_coord_points[t]
    def get(self):
        return self.coordinates

class Plane(object):
    def __init__(self,p,v):
        if not v:
            raise Exception('Cannot instantiate Plane with nul vector')
        self.p = p # point passing through self or 'd' in the equation
        self.v = v # normal vector of self
    def _d(self):
        if isinstance(self.p, Point3D):
            return - (self.p.x()*self.v.x()) - (self.p.y()*self.v.y()) - (self.p.z()*self.v.z())
        else:
            return self.p
    def intersection(self,other):
        if isinstance(other, Line3D):
            if self.v * other.v == 0:
                # other (line) and the normal vector of self are orthogonal
                # now check if other.p lies on self
                return other if other.p in self else None
            else:
                # we have a unique intersection point
                # first compute the parameter of the line
                t = - (self.v.x()*other.p.x() + self.v.y()*other.p.y() + self.v.z()*other.p.z() + self._d()) \
                    / (self.v.x()*other.v.x() + self.v.y()*other.v.y() + self.v.z()*other.v.z())
                # than deduce the coordinates of the intersection point
                return Point3D(
                    other.p.x() + other.v.x()*t,
                    other.p.y() + other.v.y()*t,
                    other.p.z() + other.v.z()*t )
    def __contains__(self, other):
        if isinstance(other, Point3D):
            return 0 == self.v.x()*other.x() + self.v.y()*other.y() + self.v.z()*other.z() + self._d()
    def __str__(self):
        return 'Plane(' + str(self.p) + ', ' + str(self.v) + ')'

    @staticmethod
    def plane_from_3_points(p,q,r):
        v1 = Vector3D.vector_from_two_points(p, q)
        v2 = Vector3D.vector_from_two_points(p, r)
        n = v1 ^ v2 # normal vector
        return Plane(p, n.normalized())


class Edge3D(Segment):
    # edge types
    UNKNOWN = 0
    CONVEX  = 1
    CONCAVE1 = 2 # up than flat
    CONCAVE2 = 3 # flat than up
    def __init__(self,a=Point3D(),b=Point3D(),type=UNKNOWN):
        super(Edge3D, self).__init__(a,b)
        self.type = type
    def asLineAxis3D(self):
        l = LineAxis3D(0, 0, self.orientation())
        l.get()[0] = l.coord_points[0](self.a)
        l.get()[1] = l.coord_points[1](self.a)
        return l
    def orientation(self):
        ori = (self.a.x() != self.b.x(),
               self.a.y() != self.b.y(),
               self.a.z() != self.b.z())
        return dict(zip(ori, COORDINATES))[True]
    def same_coordinates(self, other):
        ori1 = self.orientation()
        ori2 = other.orientation()
        l1 = LineAxis3D(0,0,ori1)
        l2 = LineAxis3D(0,0,ori2)
        if ori1 == ori2:
            return (l1.coord_points[0](self.a), l1.coord_points[1](self.a)) < \
                   (l2.coord_points[0](other.a), l2.coord_points[1](other.a))
        else:
            if (ori1, ori2) == (COORDINATES[0], COORDINATES[1]) or \
               (ori2, ori1) == (COORDINATES[0], COORDINATES[1]):
               t = Point3D.z
            if (ori1, ori2) == (COORDINATES[0], COORDINATES[2]) or \
               (ori2, ori1) == (COORDINATES[0], COORDINATES[2]):
               t = Point3D.y
            if (ori1, ori2) == (COORDINATES[1], COORDINATES[2]) or \
               (ori2, ori1) == (COORDINATES[1], COORDINATES[2]):
               t = Point3D.x
            return t(self.a) < t(other.a)
    def __contains__(self,other):
        if isinstance(other, Point3D):
            cs = ( (Point3D.x, Point3D.y, Point3D.z),
                   (Point3D.y, Point3D.x, Point3D.z),
                   (Point3D.z, Point3D.x, Point3D.y) )
            c = dict(zip(COORDINATES, cs))[self.orientation()]
            # we assume that c[1](self.a) == c[1](self.b), same for c[2]
            return ((c[0](other) <= c[0](self.a) and \
                     c[0](other) >= c[0](self.b)) or \
                    (c[0](other) <= c[0](self.b) and \
                     c[0](other) >= c[0](self.a))) and \
                   c[1](other) == c[1](self.a) and \
                   c[2](other) == c[2](self.a)


class Vector3D(object):
    def __init__(self,x=0,y=0,z=0):
        self.coordinates = [float(x),float(y),float(z)]
    def x(self):
        return self.coordinates[0]
    def y(self):
        return self.coordinates[1]
    def z(self):
        return self.coordinates[2]
    def __repr__(self):
        return "Vector3D("+str(self.x())+","+str(self.y())+","+str(self.z())+")"
    def __str__(self):
        return "V("+str(self.x())+","+str(self.y())+","+str(self.z())+")"
    def get(self):
        return self.coordinates
    def returnCopy(self):
        return Vector3D( self.x(), self.y(), self.z() )
    def asPoint3D(self):
        return Point3D( self.x(), self.y(), self.z() )
    def lengthSquared(self):
        return self.x()*self.x()+self.y()*self.y()+self.z()*self.z()
    def length(self):
        return math.sqrt( self.lengthSquared() )
    def normalized(self):
        l = self.length()
        if ( l > 0 ):
            return Vector3D( self.x()/l, self.y()/l, self.z()/l )
        return self.returnCopy()
    def __neg__(self):
        return Vector3D( -self.x(), -self.y(), -self.z() )
    def __add__(self,other):
        if isinstance(other,Point3D):
            return Point3D( self.x()+other.x(), self.y()+other.y(), self.z()+other.z() )
        return Vector3D( self.x()+other.x(), self.y()+other.y(), self.z()+other.z() )
    def __sub__(self,other):
        return Vector3D( self.x()-other.x(), self.y()-other.y(), self.z()-other.z() )
    def __mul__(self,other):
        if isinstance(other,Vector3D):
           # dot product
           return self.x()*other.x() + self.y()*other.y() + self.z()*other.z()
        # scalar product
        return Vector3D( self.x()*other, self.y()*other, self.z()*other )
    def __rmul__(self,other):
        return self*other
    def __div__(self,other):
        return Vector3D( self.x()/other, self.y()/other, self.z()/other )
    def __xor__(self,other):   # cross product
        return Vector3D(
            self.y()*other.z() - self.z()*other.y(),
            self.z()*other.x() - self.x()*other.z(),
            self.x()*other.y() - self.y()*other.x() )
    def __eq__(self,other):
        return self.x()==other.x() and self.y()==other.y() and self.z()==other.z()
    def __ne__(self,other):
        return not (self==other)
    def __nonzero__(self):
        return self.coordinates != [0,0,0]
    @staticmethod
    def vector_from_two_points(p,q):
        return Vector3D(q.x()-p.x(), q.y()-p.y(), q.z()-p.z())

class Matrix4x4(object):
    def __init__(self):
        self.setToIdentity()
    def __str__(self):
        return str(self.m[0:4]) + "\n" + str(self.m[4:8]) + "\n" + str(self.m[8:12]) + "\n" + str(self.m[12:16])
    def get(self):
        return self.m
    def returnCopy(self):
        M = Matrix4x4()
        M.m = list(self.m)  # copy the list
        return M
    def setToIdentity(self):
        self.m = [ 1.0, 0.0, 0.0, 0.0,
                   0.0, 1.0, 0.0, 0.0,
                   0.0, 0.0, 1.0, 0.0,
                   0.0, 0.0, 0.0, 1.0 ]

    @staticmethod
    def rotationAroundOrigin(angleInRadians, axisVector):
        # assumes axisVector is normalized
        c = math.cos( angleInRadians )
        s = math.sin( angleInRadians )
        one_minus_c = 1-c
        M = Matrix4x4()
        M.m[ 0] = c + one_minus_c * axisVector.x()*axisVector.x()
        M.m[ 5] = c + one_minus_c * axisVector.y()*axisVector.y()
        M.m[10] = c + one_minus_c * axisVector.z()*axisVector.z()
        M.m[ 1] = M.m[ 4] = one_minus_c * axisVector.x()*axisVector.y();
        M.m[ 2] = M.m[ 8] = one_minus_c * axisVector.x()*axisVector.z();
        M.m[ 6] = M.m[ 9] = one_minus_c * axisVector.y()*axisVector.z();
        xs = axisVector.x() * s
        ys = axisVector.y() * s
        zs = axisVector.z() * s
        M.m[ 1] += zs;  M.m[ 4] -= zs;
        M.m[ 2] -= ys;  M.m[ 8] += ys;
        M.m[ 6] += xs;  M.m[ 9] -= xs;

        M.m[12] = 0.0;
        M.m[13] = 0.0;
        M.m[14] = 0.0;
        M.m[ 3] = 0.0;   M.m[ 7] = 0.0;   M.m[11] = 0.0;   M.m[15] = 1.0;
        return M


    def __mul__(a, b):   # a is really self
        if isinstance(b,Matrix4x4):
            M = Matrix4x4()
            M.m[ 0] = a.m[ 0]*b.m[ 0] + a.m[ 4]*b.m[ 1] + a.m[ 8]*b.m[ 2] + a.m[12]*b.m[ 3];
            M.m[ 1] = a.m[ 1]*b.m[ 0] + a.m[ 5]*b.m[ 1] + a.m[ 9]*b.m[ 2] + a.m[13]*b.m[ 3];
            M.m[ 2] = a.m[ 2]*b.m[ 0] + a.m[ 6]*b.m[ 1] + a.m[10]*b.m[ 2] + a.m[14]*b.m[ 3];
            M.m[ 3] = a.m[ 3]*b.m[ 0] + a.m[ 7]*b.m[ 1] + a.m[11]*b.m[ 2] + a.m[15]*b.m[ 3];

            M.m[ 4] = a.m[ 0]*b.m[ 4] + a.m[ 4]*b.m[ 5] + a.m[ 8]*b.m[ 6] + a.m[12]*b.m[ 7];
            M.m[ 5] = a.m[ 1]*b.m[ 4] + a.m[ 5]*b.m[ 5] + a.m[ 9]*b.m[ 6] + a.m[13]*b.m[ 7];
            M.m[ 6] = a.m[ 2]*b.m[ 4] + a.m[ 6]*b.m[ 5] + a.m[10]*b.m[ 6] + a.m[14]*b.m[ 7];
            M.m[ 7] = a.m[ 3]*b.m[ 4] + a.m[ 7]*b.m[ 5] + a.m[11]*b.m[ 6] + a.m[15]*b.m[ 7];

            M.m[ 8] = a.m[ 0]*b.m[ 8] + a.m[ 4]*b.m[ 9] + a.m[ 8]*b.m[10] + a.m[12]*b.m[11];
            M.m[ 9] = a.m[ 1]*b.m[ 8] + a.m[ 5]*b.m[ 9] + a.m[ 9]*b.m[10] + a.m[13]*b.m[11];
            M.m[10] = a.m[ 2]*b.m[ 8] + a.m[ 6]*b.m[ 9] + a.m[10]*b.m[10] + a.m[14]*b.m[11];
            M.m[11] = a.m[ 3]*b.m[ 8] + a.m[ 7]*b.m[ 9] + a.m[11]*b.m[10] + a.m[15]*b.m[11];

            M.m[12] = a.m[ 0]*b.m[12] + a.m[ 4]*b.m[13] + a.m[ 8]*b.m[14] + a.m[12]*b.m[15];
            M.m[13] = a.m[ 1]*b.m[12] + a.m[ 5]*b.m[13] + a.m[ 9]*b.m[14] + a.m[13]*b.m[15];
            M.m[14] = a.m[ 2]*b.m[12] + a.m[ 6]*b.m[13] + a.m[10]*b.m[14] + a.m[14]*b.m[15];
            M.m[15] = a.m[ 3]*b.m[12] + a.m[ 7]*b.m[13] + a.m[11]*b.m[14] + a.m[15]*b.m[15];

            return M
        elif isinstance(b,Vector3D):
            # We treat the vector as if its (homogeneous) 4th component were zero.
            return Vector3D(
                a.m[ 0]*b.x() + a.m[ 4]*b.y() + a.m[ 8]*b.z(), # + a.m[12]*b.w(),
                a.m[ 1]*b.x() + a.m[ 5]*b.y() + a.m[ 9]*b.z(), # + a.m[13]*b.w(),
                a.m[ 2]*b.x() + a.m[ 6]*b.y() + a.m[10]*b.z()  # + a.m[14]*b.w(),
                # a.m[ 3]*b.x() + a.m[ 7]*b.y() + a.m[11]*b.z() + a.m[15]*b.w()
                )
        elif isinstance(b,Point3D):
            # We treat the point as if its (homogeneous) 4th component were one.
            return Point3D(
                a.m[ 0]*b.x() + a.m[ 4]*b.y() + a.m[ 8]*b.z() + a.m[12],
                a.m[ 1]*b.x() + a.m[ 5]*b.y() + a.m[ 9]*b.z() + a.m[13],
                a.m[ 2]*b.x() + a.m[ 6]*b.y() + a.m[10]*b.z() + a.m[14]
                )

def orientation(p, q, r):
    """
        Compute the orientation of three given points
        return < 0 if it's a left turn,
               > 0 if it's a right turn,
               = 0 if points are aligned
    """
    return signum((p.x() - r.x()) * (q.y() - r.y()) - (p.y() - r.y()) * (q.x() - r.x()));

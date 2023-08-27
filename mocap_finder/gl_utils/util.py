#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
yoinked from https://github.com/perelo/Cubical3DPath
"""

__author__ = 'Eloi Perdereau'
__date__ = '21-06-2013'


def flat_points(points):
    return [p.get() for p in points]

def flat_segments(segments):
    return [coord for s in segments for coord in (s.a.get(), s.b.get())]

def signum(x):
    return cmp(x, 0)

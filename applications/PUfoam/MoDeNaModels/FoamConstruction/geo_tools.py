#!/usr/bin/env python
"""
@brief      Manipulates .geo input files for gmsh.
@author     Pavel Ferkl
"""
from __future__ import print_function
import re
import shutil
import subprocess as sp
import numpy as np
NAMES = {
    'point': 'Point',
    'line': 'Line',
    'line_loop': 'Line Loop',
    'surface': 'Plane Surface',
    'surface_loop': 'Surface Loop',
    'volume': 'Volume',
    'periodic_surface_X': 'Periodic Surface',
    'periodic_surface_Y': 'Periodic Surface',
    'physical_surface': 'Physical Surface',
    'physical_volume': 'Physical Volume'
}
NAME_LIST = [
    'point',
    'line',
    'line_loop',
    'surface',
    'surface_loop',
    'volume',
    'periodic_surface_X',
    'periodic_surface_Y',
    'physical_surface',
    'physical_volume'
]
def my_find_all(regex, text):
    """My definition of findall. Returns top level group in list."""
    matches = re.finditer(regex, text)
    my_list = []
    for match in matches:
        my_list.append(match.group(0))
    return my_list

def read_geo(geo_file):
    """Reads geometry input file for gmsh."""
    with open(geo_file, "r") as text_file:
        text = text_file.read()
        sdat = {}
        sdat['point'] = my_find_all(
            # r'Point\s[(][0-9]+[)]\s[=]\s[{]'
            # + r'[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)[,]'
            # + r'[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)[,]'
            # + r'[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)[}][;]',
            # text
            r'Point\s?[(][0-9]+[)]\s[=]\s[{](.*?)[}][;]',
            text
        )
        sdat['line'] = my_find_all(
            r'Line\s?[(][0-9]+[)]\s[=]\s[{][0-9]+[,]\s?[0-9]+[}][;]', text
        )
        sdat['line_loop'] = my_find_all(
            r'Line\sLoop\s?[(][0-9]+[)]\s[=]\s[{]([+-]?[0-9]+[,]?\s?)+[}][;]',
            text
        )
        sdat['surface'] = my_find_all(
            r'Plane\sSurface\s?[(][0-9]+[)]\s[=]\s[{]([0-9]+[,]?\s?)+[}][;]',
            text
            # r'(Surface\s[(][0-9]+[)]\s[=]\s[{]([0-9]+[,]?)+[}][;])'
            # + r'(?!.*Physical.*)',
            # text
        )
        sdat['physical_surface'] = my_find_all(
            r'Physical\sSurface\s?[(][0-9]+[)]\s[=]\s[{]([0-9]+[,]?\s?)+[}][;]',
            text
        )
        sdat['surface_loop'] = my_find_all(
            r'Surface\sLoop\s?[(][0-9]+[)]\s[=]\s[{]([+-]?[0-9]+[,]?\s?)+[}][;]',
            text
        )
        sdat['volume'] = my_find_all(
            r'Volume\s?[(][0-9]+[)]\s[=]\s[{]([0-9]+[,]?\s?)+[}][;]',
            text
        )
        return sdat

def fix_strings(strings):
    """
    Removes negative sign (orientation); opencascade has problems otherwise.
    """
    for i, line in enumerate(strings):
        strings[i] = re.sub('[-]', '', line)

def save_geo(geo_file, sdat, opencascade=True):
    """Saves geometry input file for gmsh."""
    with open(geo_file, "w") as text_file:
        if opencascade:
            text_file.write('SetFactory("OpenCASCADE");\n')
            text_file.write('Mesh.CharacteristicLengthMax = 0.1;\n')
        for key in NAME_LIST:
            if key in sdat:
                for line in sdat[key]:
                    text_file.write("{}\n".format(line))

def extract_data(sdat):
    """Extracts geo data to lists from list of geo strings."""
    edat = {}
    for key in sdat:
        lines = [None]*len(sdat[key])
        index = [None]*len(sdat[key])
        for i, line in enumerate(sdat[key]):
            part = line.split("(")
            ind = int(part[1].split(")")[0])
            fraction = line.split("{")
            fraction = fraction[1].split("}")
            fraction = fraction[0].split(",")
            if key == "point":
                fraction = np.array(fraction[0:2])
                fraction = fraction.astype(np.float)
            else:
                fraction = np.array(fraction)
                fraction = np.absolute(fraction.astype(np.int)).tolist()
            lines[i] = fraction
            index[i] = ind
        edat[key] = lines
        edat[key+'_index'] = index
    return edat

def collect_strings(edat):
    """Creates lists of geo strings from geo data."""
    sdat = {}
    for key in edat:
        sdat[key] = []
        if key == 'periodic_surface_X':
            for i, j in enumerate(edat[key]):
                sdat[key].append(
                    '{0} {{{1}}} = {{{2}}} Translate{{-1,0,0}};'.format(
                        NAMES[key], j[0], j[1]
                    )
                )
        elif key == 'periodic_surface_Y':
            for i, j in enumerate(edat[key]):
                sdat[key].append(
                    '{0} {{{1}}} = {{{2}}} Translate{{0,-1,0}};'.format(
                        NAMES[key], j[0], j[1]
                    )
                )
        else:
            for i, j in enumerate(edat[key]):
                j = ','.join(str(e) for e in j)
                sdat[key].append('{0} ({1}) = {{{2}}};'.format(
                    NAMES[key], i + 1, j
                ))
    return sdat

def surfaces_in_z_plane(edat, z_coord):
    """Finds surafces that lie completely lie in z plane"""
    points_in_plane = []
    for i, point in enumerate(edat['point']):
        if point[2] == z_coord:
            points_in_plane.append(i+1)
    lines_in_plane = []
    for i, line in enumerate(edat['line']):
        if line[0] in points_in_plane and line[1] in points_in_plane:
            lines_in_plane.append(i+1)
    line_loops_in_plane = []
    for i, line_loop in enumerate(edat['line_loop']):
        log = True
        for line in line_loop:
            if line not in lines_in_plane:
                log = False
        if log:
            line_loops_in_plane.append(i+1)
    surfaces_in_plane = line_loops_in_plane
    return surfaces_in_plane

def other_surfaces(surface_loops, surf0, surf1):
    """
    Returns list of boundary surfaces, which are not in surf0 or surf1.
    """
    all_surfaces = []
    for surface_loop in surface_loops:
        all_surfaces += surface_loop
    count = dict()
    for surface in all_surfaces:
        if surface in count:
            count[surface] += 1
        else:
            count[surface] = 1
    surf = [
        i for i, j in count.items() if j == 1
        and i not in surf0 and i not in surf1
    ]
    return surf

def periodic_surfaces(edat, surfaces, vec):
    """Returns list of periodic surface pairs."""
    surface_points = [[]]*len(edat['line_loop'])
    boundary_points_ind = []
    for surface in surfaces:
        for line in edat['line_loop'][surface - 1]:
            for point in edat['line'][line - 1]:
                if point not in surface_points[surface - 1]:
                    surface_points[surface - 1] = surface_points[surface - 1] \
                        + [point]
                if point not in boundary_points_ind:
                    boundary_points_ind.append(point)
    boundary_points = []
    for point in boundary_points_ind:
        boundary_points.append(edat['point'][point - 1])
    for i, point in enumerate(surface_points):
        point.sort()
        surface_points[i] = point
    # print(surface_points)
    # print(boundary_points_ind)
    # print(boundary_points)
    eps = 1e-8
    periodic_points = [None]*len(edat['point'])
    for i, firstpoint in enumerate(boundary_points):
        for j, secondpoint in enumerate(boundary_points):
            if np.sum(np.abs(firstpoint + vec - secondpoint)) < eps:
                periodic_points[boundary_points_ind[i] - 1] = \
                    boundary_points_ind[j]
    # print(periodic_points)
    psurfs = []
    for i, surf in enumerate(surface_points):
        if surf:
            per_surf = []
            for point in surf:
                per_surf.append(periodic_points[point - 1])
            if None not in per_surf:
                per_surf.sort()
                if per_surf in surface_points:
                    psurfs.append(
                        [i + 1, surface_points.index(per_surf) + 1]
                    )
    # print(psurfs)
    return psurfs

def move_to_box(infile, wfile, outfile, volumes):
    """Moves periodic closed foam to periodic box."""
    with open(wfile, 'w') as wfl:
        mvol = max(volumes)
        wfl.write('SetFactory("OpenCASCADE");\n\n')
        wfl.write('Include "{0}";\n\n'.format(infile))
        wfl.write('Block({0}) = {{-1,-1,-1,3,3,1}};\n'.format(mvol + 1))
        wfl.write('Block({0}) = {{-1,-1, 1,3,3,1}};\n'.format(mvol + 2))
        wfl.write('Block({0}) = {{-1,-1, 0,3,3,1}};\n'.format(mvol + 3))
        wfl.write('Block({0}) = {{-1,-1,-1,3,1,3}};\n'.format(mvol + 4))
        wfl.write('Block({0}) = {{-1, 1,-1,3,1,3}};\n'.format(mvol + 5))
        wfl.write('Block({0}) = {{-1, 0,-1,3,1,3}};\n'.format(mvol + 6))
        wfl.write('Block({0}) = {{-1,-1,-1,1,3,3}};\n'.format(mvol + 7))
        wfl.write('Block({0}) = {{ 1,-1,-1,1,3,3}};\n'.format(mvol + 8))
        wfl.write('Block({0}) = {{ 0,-1,-1,1,3,3}};\n'.format(mvol + 9))
        wfl.write('\n')
        wfl.write(
            'zol() = BooleanIntersection'
            + '{{Volume{{1:{0}}};}}'.format(mvol)
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 1)
        )
        wfl.write(
            'zoh() = BooleanIntersection'
            + '{{Volume{{1:{0}}};}}'.format(mvol)
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 2)
        )
        wfl.write(
            'zin() = BooleanIntersection'
            + '{{Volume{{1:{0}}}; Delete;}}'.format(mvol)
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 3)
        )
        wfl.write('Translate{0,0, 1}{Volume{zol()};}\n')
        wfl.write('Translate{0,0,-1}{Volume{zoh()};}\n\n')
        wfl.write(
            'yol() = BooleanIntersection'
            + '{Volume{zol(),zoh(),zin()};}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 4)
        )
        wfl.write(
            'yoh() = BooleanIntersection'
            + '{Volume{zol(),zoh(),zin()};}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 5)
        )
        wfl.write(
            'yin() = BooleanIntersection'
            + '{Volume{zol(),zoh(),zin()}; Delete;}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 6)
        )
        wfl.write('Translate{0, 1,0}{Volume{yol()};}\n')
        wfl.write('Translate{0,-1,0}{Volume{yoh()};}\n\n')
        wfl.write(
            'xol() = BooleanIntersection'
            + '{Volume{yol(),yoh(),yin()};}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 7)
        )
        wfl.write(
            'xoh() = BooleanIntersection'
            + '{Volume{yol(),yoh(),yin()};}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 8)
        )
        wfl.write(
            'xin() = BooleanIntersection'
            + '{Volume{yol(),yoh(),yin()}; Delete;}'
            + '{{Volume{{{0}}}; Delete;}};\n'.format(mvol + 9)
        )
        wfl.write('Translate{ 1,0,0}{Volume{xol()};}\n')
        wfl.write('Translate{-1,0,0}{Volume{xoh()};}\n\n')
    call = sp.Popen(['gmsh', wfile, '-0'])
    call.wait()
    shutil.move(wfile+'_unrolled', outfile)

def main():
    """Main subroutine. Just for testing of functionality."""
    # sdat = read_geo("FoamClosed.geo") # string data
    # fix_strings(sdat['line_loop'])
    # fix_strings(sdat['surface_loop'])
    # sdat.pop('physical_surface')
    # save_geo("FoamClosedFixed.geo", sdat)
    # move_to_box(
    #     "FoamClosedFixed.geo", "move_to_box.geo", "FoamBox.geo",
    #     range(1, len(sdat['volume']) + 1)
    # )
    sdat = read_geo("FoamBox.geo") # string data
    edat = extract_data(sdat) # extracted data
    print(edat['volume'])
    print(edat['volume_index'])
    exit(0)
    surf0 = surfaces_in_z_plane(edat, 0.0)
    print(surf0)
    surf1 = surfaces_in_z_plane(edat, 1.0)
    print(surf1)
    surf = other_surfaces(edat['surface_loop'], surf0, surf1)
    print(surf)
    edat['physical_surface'] = [surf0, surf1, surf]
    edat['periodic_surface_X'] = periodic_surfaces(
        edat, surf, np.array([1, 0, 0])
    )
    print(edat['periodic_surface_X'])
    edat['periodic_surface_Y'] = periodic_surfaces(
        edat, surf, np.array([0, 1, 0])
    )
    print(edat['periodic_surface_Y'])
    edat['physical_volume'] = [[]]
    for i in edat['volume']:
        edat['physical_volume'][0] += i
    print(edat['physical_volume'])
    print(edat.keys())
    sdat2 = collect_strings(edat)
    print(sdat2.keys())
    print(sdat2['physical_volume'])
    save_geo("Foam2.geo", sdat2)

if __name__ == "__main__":
    main()

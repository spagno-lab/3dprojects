#!/usr/bin/env python3
"""Regenerate the printable three-object 3MF from the parametric case source.

Fusion remains the authoring environment, but every solid used by this case is
an axis-aligned box, a cylinder, or an elliptical vent. The preview recorder
already captures those operations directly from the Fusion builders. This
exporter replays the same operations through OpenSCAD, then packages the three
resulting triangle meshes as named 3MF objects.

The existing Bambu project settings are copied into the regenerated archive;
geometry, object names, placement, and mesh statistics are rebuilt.
"""
import argparse
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / 'raspberry.3mf'
CONTENT_TYPES = 'http://schemas.openxmlformats.org/package/2006/content-types'
RELATIONSHIPS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'


def number(value):
    """Stable compact decimal for OpenSCAD and 3MF XML."""
    return f'{value:.8f}'.rstrip('0').rstrip('.') or '0'


def primitive_scad(kind, params):
    if kind == 'box':
        x, y, z, length, width, height = params
        return (
            f'translate([{number(x)},{number(y)},{number(z)}]) '
            f'cube([{number(length)},{number(width)},{number(height)}]);'
        )
    if kind == 'cyl_z':
        center_x, center_y, z, radius, height = params
        return (
            f'translate([{number(center_x)},{number(center_y)},{number(z)}]) '
            f'cylinder(h={number(height)},r={number(radius)});'
        )
    if kind == 'cyl_y':
        center_x, y, center_z, radius, depth = params
        return (
            f'translate([{number(center_x)},{number(y)},{number(center_z)}]) '
            f'rotate([-90,0,0]) '
            f'cylinder(h={number(depth)},r={number(radius)});'
        )
    if kind == 'ellipse_z':
        center_x, center_y, z, major, minor, angle, height = params
        return (
            f'translate([{number(center_x)},{number(center_y)},{number(z)}]) '
            f'rotate([0,0,{number(math.degrees(angle))}]) '
            f'scale([{number(major)},{number(minor)},1]) '
            f'cylinder(h={number(height)},r=1);'
        )
    raise ValueError(f'unsupported recorded primitive: {kind}')


def part_scad(operations, z_offset=0.0):
    body = None
    for kind, operation, params in operations:
        primitive = primitive_scad(kind, params)
        if body is None:
            if operation == 'cut':
                raise ValueError('part starts with a cut operation')
            body = primitive
        elif operation == 'cut':
            body = f'difference() {{\n  {body}\n  {primitive}\n}}'
        else:
            body = f'union() {{\n  {body}\n  {primitive}\n}}'
    if body is None:
        raise ValueError('part contains no positive geometry')
    return (
        '$fn=96;\n'
        f'translate([0,0,{number(z_offset)}]) {{\n{body}\n}}\n'
    )


def read_binary_stl(path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f'{path.name}: truncated STL')
    triangle_count = struct.unpack_from('<I', data, 80)[0]
    expected = 84 + triangle_count * 50
    if len(data) != expected:
        raise ValueError(
            f'{path.name}: expected {expected} bytes for {triangle_count} '
            f'triangles, found {len(data)}')

    vertices = []
    triangles = []
    vertex_ids = {}
    offset = 84
    for _ in range(triangle_count):
        values = struct.unpack_from('<12fH', data, offset)
        face = []
        for start in (3, 6, 9):
            vertex = tuple(0.0 if abs(v) < 1e-7 else float(v)
                           for v in values[start:start + 3])
            vertex_id = vertex_ids.get(vertex)
            if vertex_id is None:
                vertex_id = len(vertices)
                vertex_ids[vertex] = vertex_id
                vertices.append(vertex)
            face.append(vertex_id)
        if len(set(face)) == 3:
            triangles.append(tuple(face))
        offset += 50
    if not triangles:
        raise ValueError(f'{path.name}: mesh has no triangles')

    # CGAL may emit the same mesh in a different traversal order. Canonicalize
    # vertices and faces so unchanged geometry produces an unchanged 3MF.
    ordered_vertices = sorted(vertices)
    ordered_ids = {vertex: new_id
                   for new_id, vertex in enumerate(ordered_vertices)}
    remap = {old_id: ordered_ids[vertex]
             for old_id, vertex in enumerate(vertices)}
    ordered_triangles = []
    for triangle in triangles:
        face = tuple(remap[index] for index in triangle)
        minimum = face.index(min(face))
        ordered_triangles.append(face[minimum:] + face[:minimum])
    ordered_triangles.sort()
    return ordered_vertices, ordered_triangles


def render_part(name, operations, directory, z_offset=0.0):
    scad_path = directory / f'{name}.scad'
    stl_path = directory / f'{name}.stl'
    scad_path.write_text(part_scad(operations, z_offset), encoding='utf-8')
    result = subprocess.run(
        ['openscad', '--hardwarnings', '--export-format', 'binstl',
         '-o', str(stl_path), str(scad_path)],
        check=False, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f'OpenSCAD failed for {name}:\n{result.stdout}{result.stderr}')
    vertices, triangles = read_binary_stl(stl_path)
    minimum = tuple(min(vertex[axis] for vertex in vertices)
                    for axis in range(3))
    maximum = tuple(max(vertex[axis] for vertex in vertices)
                    for axis in range(3))
    return {
        'name': name,
        'vertices': vertices,
        'triangles': triangles,
        'bounds': (minimum, maximum),
    }


def preserved_project_settings(path):
    if not path.exists():
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.read('Metadata/project_settings.config')
    except (KeyError, zipfile.BadZipFile):
        return None


def model_xml(parts):
    ET.register_namespace('', CORE)
    model = ET.Element(f'{{{CORE}}}model', {
        'unit': 'millimeter',
        '{http://www.w3.org/XML/1998/namespace}lang': 'en-US',
    })
    for key, value in (
        ('Application', 'OpenSCAD + export_3mf.py'),
        ('Title', 'Raspberry Pi 4 GPS case'),
        ('Description', 'Shell, ventilated GPS lid, and base plate'),
    ):
        node = ET.SubElement(model, f'{{{CORE}}}metadata', {'name': key})
        node.text = value
    resources = ET.SubElement(model, f'{{{CORE}}}resources')
    for object_id, part in enumerate(parts, 1):
        obj = ET.SubElement(resources, f'{{{CORE}}}object', {
            'id': str(object_id), 'type': 'model', 'name': part['name'],
        })
        mesh = ET.SubElement(obj, f'{{{CORE}}}mesh')
        vertices = ET.SubElement(mesh, f'{{{CORE}}}vertices')
        for x, y, z in part['vertices']:
            ET.SubElement(vertices, f'{{{CORE}}}vertex', {
                'x': number(x), 'y': number(y), 'z': number(z),
            })
        triangles = ET.SubElement(mesh, f'{{{CORE}}}triangles')
        for first, second, third in part['triangles']:
            ET.SubElement(triangles, f'{{{CORE}}}triangle', {
                'v1': str(first), 'v2': str(second), 'v3': str(third),
            })
    build = ET.SubElement(model, f'{{{CORE}}}build')
    placements = ((5.0, 5.0), (102.0, 5.0), (199.0, 5.0))
    for object_id, ((x, y), part) in enumerate(zip(placements, parts), 1):
        z = -part['bounds'][0][2]
        ET.SubElement(build, f'{{{CORE}}}item', {
            'objectid': str(object_id),
            'transform': (f'1 0 0 0 1 0 0 0 1 '
                          f'{number(x)} {number(y)} {number(z)}'),
            'printable': '1',
        })
    return ET.tostring(model, encoding='utf-8', xml_declaration=True)


def content_types_xml(include_project_settings):
    ET.register_namespace('', CONTENT_TYPES)
    root = ET.Element(f'{{{CONTENT_TYPES}}}Types')
    ET.SubElement(root, f'{{{CONTENT_TYPES}}}Default', {
        'Extension': 'rels',
        'ContentType': 'application/vnd.openxmlformats-package.relationships+xml',
    })
    ET.SubElement(root, f'{{{CONTENT_TYPES}}}Default', {
        'Extension': 'model',
        'ContentType': 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml',
    })
    if include_project_settings:
        ET.SubElement(root, f'{{{CONTENT_TYPES}}}Default', {
            'Extension': 'config', 'ContentType': 'application/octet-stream',
        })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def relationships_xml():
    ET.register_namespace('', RELATIONSHIPS)
    root = ET.Element(f'{{{RELATIONSHIPS}}}Relationships')
    ET.SubElement(root, f'{{{RELATIONSHIPS}}}Relationship', {
        'Target': '/3D/3dmodel.model', 'Id': 'rel0',
        'Type': 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel',
    })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def model_settings_xml(parts):
    root = ET.Element('config')
    for object_id, part in enumerate(parts, 1):
        obj = ET.SubElement(root, 'object', {'id': str(object_id)})
        ET.SubElement(obj, 'metadata', {'key': 'name', 'value': part['name']})
        ET.SubElement(obj, 'metadata', {'key': 'extruder', 'value': '1'})
        ET.SubElement(obj, 'metadata', {
            'face_count': str(len(part['triangles'])),
        })
        part_uuid = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f'https://github.com/spagno-lab/3dprojects/{part["name"]}',
        )
        child = ET.SubElement(obj, 'part', {
            'id': str(object_id), 'subtype': 'normal_part',
            'uuid': str(part_uuid),
        })
        ET.SubElement(child, 'metadata', {
            'key': 'name', 'value': part['name'],
        })
        ET.SubElement(child, 'mesh_stat', {
            'face_count': str(len(part['triangles'])),
            'edges_fixed': '0', 'degenerate_facets': '0',
            'facets_removed': '0', 'facets_reversed': '0',
            'backwards_edges': '0',
        })
    plate = ET.SubElement(root, 'plate')
    ET.SubElement(plate, 'metadata', {'key': 'plater_id', 'value': '1'})
    ET.SubElement(plate, 'metadata', {'key': 'plater_name', 'value': ''})
    ET.SubElement(plate, 'metadata', {'key': 'locked', 'value': 'false'})
    for object_id in range(1, len(parts) + 1):
        instance = ET.SubElement(plate, 'model_instance')
        ET.SubElement(instance, 'metadata', {
            'key': 'object_id', 'value': str(object_id),
        })
        ET.SubElement(instance, 'metadata', {
            'key': 'instance_id', 'value': '0',
        })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_3mf(path, parts, project_settings):
    def stable_write(archive, name, data):
        entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, data)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        stable_write(archive,
            '[Content_Types].xml', content_types_xml(project_settings is not None))
        stable_write(archive, '_rels/.rels', relationships_xml())
        stable_write(archive, '3D/3dmodel.model', model_xml(parts))
        stable_write(archive, 'Metadata/model_settings.config',
                     model_settings_xml(parts))
        if project_settings is not None:
            stable_write(archive, 'Metadata/project_settings.config',
                         project_settings)


def validate_3mf(path, expected_parts=3):
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f'corrupt archive entry: {bad}')
        model = ET.fromstring(archive.read('3D/3dmodel.model'))
        objects = model.findall(f'.//{{{CORE}}}object')
        items = model.findall(f'.//{{{CORE}}}item')
        if len(objects) != expected_parts or len(items) != expected_parts:
            raise ValueError(
                f'expected {expected_parts} objects/items, found '
                f'{len(objects)}/{len(items)}')
        for obj in objects:
            triangles = obj.findall(f'.//{{{CORE}}}triangle')
            if not triangles:
                raise ValueError(f'object {obj.get("id")} has no triangles')


def main():
    import preview

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not shutil.which('openscad'):
        raise SystemExit('OpenSCAD is required but was not found in PATH')

    project_settings = preserved_project_settings(args.output)
    with tempfile.TemporaryDirectory(prefix='raspberry-3mf-') as temp:
        directory = Path(temp)
        parts = [
            render_part('shell', preview.record(lambda: preview.case.shell(None)),
                        directory, -preview.case.PARTING_Z),
            render_part('lid', preview.record(lambda: preview.case.lid(None)),
                        directory),
            render_part('base', preview.record(lambda: preview.case.base_plate(None)),
                        directory),
        ]
    write_3mf(args.output, parts, project_settings)
    validate_3mf(args.output)
    counts = ', '.join(
        f"{part['name']}={len(part['triangles'])} triangles" for part in parts)
    print(f'wrote {args.output} ({counts})')
    if project_settings is not None:
        print('preserved Metadata/project_settings.config from the prior project')


if __name__ == '__main__':
    main()

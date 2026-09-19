#!/usr/bin/env python3
"""Render the case outside Fusion 360.

    python3 preview.py              # all parts, default resolution
    python3 preview.py --res 0.15   # finer, slower
    python3 preview.py base shell   # only some parts

Writes preview-<part>.png next to this file.

It does not re-describe the geometry: it imports the script with a stub in
place of the Fusion API, records the extrude calls the builders make, and
replays them onto a voxel grid in the same order. So what you see is what the
script would build, and a change to the script shows up here without anyone
remembering to update a second model.

Voxels rather than proper CSG because the box has no curved faces except the
SMA hole and the standoffs, and a 0.2 mm grid resolves every feature here: the
thinnest is the 0.8 mm snap tab.
"""
import argparse
import math
import sys
import types

import numpy as np
from PIL import Image


def _stub_fusion():
    class Any:
        def __getattr__(self, name):
            return Any()

        def __call__(self, *args, **kwargs):
            return Any()

    for name in ('adsk', 'adsk.core', 'adsk.fusion'):
        module = types.ModuleType(name)
        module.__getattr__ = lambda _name: Any()
        sys.modules[name] = module
    sys.modules['adsk'].core = sys.modules['adsk.core']
    sys.modules['adsk'].fusion = sys.modules['adsk.fusion']
    # Named, like the test suite does. Without this the operation enums come
    # back as opaque stubs, every cut reads as a union, and the preview is a
    # solid block that looks plausible from outside.
    sys.modules['adsk.fusion'].FeatureOperations = types.SimpleNamespace(
        NewBodyFeatureOperation='new-body',
        CutFeatureOperation='cut',
        JoinFeatureOperation='join',
    )


_stub_fusion()
import raspberry_pi4_gps_case as case  # noqa: E402

CUT = 'cut'


def _operation(op):
    """Fusion's operation enum is stubbed, so fall back on its repr."""
    text = str(op).lower()
    if 'cut' in text:
        return 'cut'
    if 'join' in text:
        return 'join'
    return 'new'


class Recorder:
    """Capture the solids each builder asks for, in order."""

    def __init__(self):
        self.ops = []

    def rectangle(self, comp, name, x, y, z, length, width, height,
                  operation=None, participant_bodies=None):
        self.ops.append(('box', _operation(operation),
                         (x, y, z, length, width, height)))
        return _Feature()

    def cylinder(self, comp, name, cx, cy, z, diameter, height,
                 operation=None, participant_bodies=None):
        self.ops.append(('cyl_z', _operation(operation),
                         (cx, cy, z, diameter / 2.0, height)))
        return _Feature()

    def circle_vents(self, comp, target_body, name, circles, height):
        for center_x, center_y, diameter in circles:
            self.ops.append(('cyl_z', 'cut',
                             (center_x, center_y, 0.0,
                              diameter / 2.0, height)))
        return _Feature()

    def ellipse_vents(self, comp, target_body, name, ellipses, height):
        for center_x, center_y, major, minor, angle in ellipses:
            self.ops.append(('ellipse_z', 'cut',
                             (center_x, center_y, 0.0,
                              major, minor, math.radians(angle), height)))
        return _Feature()

    def rear_hole(self, comp, target_body, name, center_x, center_z, wall_y,
                  diameter, depth):
        # Symmetric about the wall plane, along Y.
        self.ops.append(('cyl_y', 'cut',
                         (center_x, wall_y - depth, center_z,
                          diameter / 2.0, 2 * depth)))
        return _Feature()


class _Feature:
    """Stand-in for the Fusion feature the builders keep a body from."""

    class _Body:
        name = ''

    class _Bodies:
        def item(self, _index):
            return _Feature._Body()

    def __init__(self):
        self.bodies = _Feature._Bodies()

    name = ''


def record(builder):
    recorder = Recorder()
    originals = {
        'rectangle_feature': case.rectangle_feature,
        'cylinder_feature': case.cylinder_feature,
        'circle_vent_feature': case.circle_vent_feature,
        'ellipse_vent_feature': case.ellipse_vent_feature,
        'rear_wall_hole': case.rear_wall_hole,
    }
    case.rectangle_feature = recorder.rectangle
    case.cylinder_feature = recorder.cylinder
    case.circle_vent_feature = recorder.circle_vents
    case.ellipse_vent_feature = recorder.ellipse_vents
    case.rear_wall_hole = recorder.rear_hole
    try:
        builder()
    finally:
        for name, original in originals.items():
            setattr(case, name, original)
    return recorder.ops


def bounds(op_groups, pad=2.0):
    """Common bounding box, so several parts share one grid and one camera."""
    xs, ys, zs = [], [], []
    for ops in op_groups:
        for kind, _op, p in ops:
            if kind == 'box':
                xs += [p[0], p[0] + p[3]]
                ys += [p[1], p[1] + p[4]]
                zs += [p[2], p[2] + p[5]]
            elif kind == 'cyl_z':
                xs += [p[0] - p[3], p[0] + p[3]]
                ys += [p[1] - p[3], p[1] + p[3]]
                zs += [p[2], p[2] + p[4]]
            elif kind == 'ellipse_z':
                radius = max(p[3], p[4])
                xs += [p[0] - radius, p[0] + radius]
                ys += [p[1] - radius, p[1] + radius]
                zs += [p[2], p[2] + p[6]]
            else:
                xs += [p[0] - p[3], p[0] + p[3]]
                ys += [p[1], p[1] + p[4]]
                zs += [p[2] - p[3], p[2] + p[3]]
    origin = np.array([min(xs) - pad, min(ys) - pad, min(zs) - pad])
    far = np.array([max(xs) + pad, max(ys) + pad, max(zs) + pad])
    return origin, far


def voxelise(ops, resolution, origin=None, far=None):
    """Replay the recorded solids onto a boolean grid."""
    pad = 2.0
    xs, ys, zs = [], [], []
    for kind, _op, p in ops:
        if kind == 'box':
            xs += [p[0], p[0] + p[3]]
            ys += [p[1], p[1] + p[4]]
            zs += [p[2], p[2] + p[5]]
        elif kind == 'cyl_z':
            xs += [p[0] - p[3], p[0] + p[3]]
            ys += [p[1] - p[3], p[1] + p[3]]
            zs += [p[2], p[2] + p[4]]
        elif kind == 'ellipse_z':
            radius = max(p[3], p[4])
            xs += [p[0] - radius, p[0] + radius]
            ys += [p[1] - radius, p[1] + radius]
            zs += [p[2], p[2] + p[6]]
        else:
            xs += [p[0] - p[3], p[0] + p[3]]
            ys += [p[1], p[1] + p[4]]
            zs += [p[2] - p[3], p[2] + p[3]]

    if origin is None:
        origin = np.array([min(xs) - pad, min(ys) - pad, min(zs) - pad])
        far = np.array([max(xs) + pad, max(ys) + pad, max(zs) + pad])
    size = far - origin
    shape = np.maximum((size / resolution).astype(int) + 1, 1)
    grid = np.zeros(shape, dtype=bool)

    centres = [origin[axis] + (np.arange(shape[axis]) + 0.5) * resolution
               for axis in range(3)]
    gx = centres[0][:, None, None]
    gy = centres[1][None, :, None]
    gz = centres[2][None, None, :]

    for kind, op, p in ops:
        if kind == 'box':
            x, y, z, length, width, height = p
            mask = ((gx >= x) & (gx <= x + length)
                    & (gy >= y) & (gy <= y + width)
                    & (gz >= z) & (gz <= z + height))
        elif kind == 'cyl_z':
            cx, cy, z, radius, height = p
            mask = (((gx - cx) ** 2 + (gy - cy) ** 2 <= radius ** 2)
                    & (gz >= z) & (gz <= z + height))
        elif kind == 'ellipse_z':
            cx, cy, z, major, minor, angle, height = p
            local_x = ((gx - cx) * math.cos(angle)
                       + (gy - cy) * math.sin(angle))
            local_y = (-(gx - cx) * math.sin(angle)
                       + (gy - cy) * math.cos(angle))
            mask = (((local_x / major) ** 2 + (local_y / minor) ** 2 <= 1.0)
                    & (gz >= z) & (gz <= z + height))
        else:
            cx, y, cz, radius, depth = p
            mask = (((gx - cx) ** 2 + (gz - cz) ** 2 <= radius ** 2)
                    & (gy >= y) & (gy <= y + depth))
        if op == 'cut':
            grid &= ~mask
        else:
            grid |= mask
    return grid, origin


def surface_normals(grid):
    """Outward normal of every surface voxel, from the six-neighbourhood."""
    normal = np.zeros(grid.shape + (3,), dtype=np.float32)
    for axis in range(3):
        empty_below = ~np.roll(grid, 1, axis=axis)
        empty_above = ~np.roll(grid, -1, axis=axis)
        index = [slice(None)] * 3
        index[axis] = 0
        empty_below[tuple(index)] = True
        index[axis] = -1
        empty_above[tuple(index)] = True
        normal[..., axis] = empty_above.astype(np.float32) - empty_below
    length = np.linalg.norm(normal, axis=-1)
    surface = grid & (length > 0)
    with np.errstate(invalid='ignore', divide='ignore'):
        normal /= np.where(length[..., None] == 0, 1.0, length[..., None])
    return surface, normal


def render(layers, origin, resolution, width=1100, azimuth=-52.0,
           elevation=26.0):
    """Orthographic projection of the surface voxels, with a z-buffer.

    layers is a list of (grid, rgb). Later layers do not hide earlier ones:
    everything goes through one depth buffer, so the board really is seen
    through the openings rather than drawn on top of them.
    """
    points_all, normal_all, colour_all = [], [], []
    for grid, rgb in layers:
        surface, normals = surface_normals(grid)
        idx = np.argwhere(surface)
        if not len(idx):
            continue
        points_all.append(origin + (idx + 0.5) * resolution)
        normal_all.append(normals[tuple(idx.T)])
        colour_all.append(np.repeat(np.array(rgb, dtype=np.float32)[None, :],
                                    len(idx), axis=0))
    if not points_all:
        raise SystemExit('nothing to draw')
    points = np.concatenate(points_all)
    normal = np.concatenate(normal_all)
    colours = np.concatenate(colour_all)

    a = math.radians(azimuth)
    e = math.radians(elevation)
    right = np.array([math.cos(a), -math.sin(a), 0.0])
    view = np.array([math.sin(a) * math.cos(e),
                     math.cos(a) * math.cos(e),
                     -math.sin(e)])
    up = np.cross(right, view)
    # Cheap guard against the image coming out upside down, which is easy to
    # miss on a symmetrical box and would have the openings looking as though
    # they were open at the top.
    assert up[2] > 0, 'view basis is inverted'

    u = points @ right
    v = points @ up
    depth = points @ view

    margin = 30
    span_u, span_v = u.max() - u.min(), v.max() - v.min()
    scale = (width - 2 * margin) / span_u
    height = int(span_v * scale) + 2 * margin

    light = np.array([0.35, -0.5, 0.79])
    light = light / np.linalg.norm(light)
    shade = 0.30 + 0.70 * np.clip(normal @ light, 0, 1)

    # One voxel covers more than one pixel, so splat its whole footprint.
    # Drawing a single pixel each leaves the surfaces full of holes and the
    # part looks transparent.
    footprint = max(1, int(math.ceil(resolution * scale)))
    base_x = (u - u.min()) * scale + margin
    base_y = height - margin - (v - v.min()) * scale

    offsets = [(dx, dy) for dy in range(footprint) for dx in range(footprint)]
    px = np.concatenate([np.clip((base_x + dx).astype(np.int32), 0, width - 1)
                         for dx, _ in offsets])
    py = np.concatenate([np.clip((base_y + dy).astype(np.int32), 0, height - 1)
                         for _, dy in offsets])
    rep = len(offsets)
    zz = np.tile(depth, rep)
    cc = np.tile(shade[:, None] * colours, (rep, 1))

    # Painter's algorithm done properly: for every pixel keep the nearest
    # splat, chosen with a sort rather than by relying on assignment order.
    flat = py.astype(np.int64) * width + px
    order = np.lexsort((zz, flat))
    _, first = np.unique(flat[order], return_index=True)
    chosen = order[first]

    image = np.zeros((height * width, 3), dtype=np.float32)
    image[:] = np.array([0.12, 0.13, 0.15])
    zbuf = np.full(height * width, np.inf, dtype=np.float32)
    image[flat[chosen]] = cc[chosen]
    zbuf[flat[chosen]] = zz[chosen]
    image = image.reshape(height, width, 3)
    zbuf = zbuf.reshape(height, width)

    drawn = np.isfinite(zbuf)
    fog = np.zeros_like(zbuf)
    if drawn.any():
        lo, hi = depth.min(), depth.max()
        fog[drawn] = (zbuf[drawn] - lo) / max(hi - lo, 1e-6)
        image[drawn] *= (1.0 - 0.35 * fog[drawn])[..., None]
    return Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8))


CASE_COLOUR = (0.85, 0.55, 0.20)
BOARD_COLOUR = (0.20, 0.60, 0.45)

SINGLE = {
    'base': lambda: case.base_plate(None, 0.0),
    'shell': lambda: case.shell(None, 0.0),
    'lid': lambda: case.lid(None, 0.0),
    'collar': lambda: case.shell(None, 0.0,
                                 height_limit=case.test_collar_height()),
}

# Views with more than one body, drawn through a single depth buffer.
GROUPED = {
    # The board where the standoffs and the pads actually put it, inside the
    # two parts that have to close around it. This is the picture that would
    # have shown the connectors buried in the wall.
    'assembly': ((lambda: case.base_plate(None, 0.0), CASE_COLOUR),
                 (lambda: case.shell(None, 0.0), CASE_COLOUR),
                 (lambda: case.pi_reference(None), BOARD_COLOUR)),
    'fit': ((lambda: case.base_plate(None, 0.0), CASE_COLOUR),
            (lambda: case.pi_reference(None), BOARD_COLOUR)),
    'testprint': ((lambda: case.base_plate(None, 0.0), CASE_COLOUR),
                  (lambda: case.shell(None, 0.0,
                                      height_limit=case.test_collar_height()),
                   CASE_COLOUR),
                  (lambda: case.pi_reference(None), BOARD_COLOUR)),
}


def build(name, resolution):
    if name in SINGLE:
        groups = [(record(SINGLE[name]), CASE_COLOUR)]
    else:
        groups = [(record(builder), colour) for builder, colour in GROUPED[name]]
    origin, far = bounds([ops for ops, _ in groups])
    layers = [(voxelise(ops, resolution, origin, far)[0], colour)
              for ops, colour in groups]
    features = sum(len(ops) for ops, _ in groups)
    return layers, origin, features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('parts', nargs='*', default=None)
    parser.add_argument('--res', type=float, default=0.2,
                        help='voxel size in mm')
    parser.add_argument('--width', type=int, default=1100)
    parser.add_argument('--azimuth', type=float, default=-52.0)
    parser.add_argument('--elevation', type=float, default=26.0)
    args = parser.parse_args()

    known = list(SINGLE) + list(GROUPED)
    wanted = args.parts or ['base', 'shell', 'lid', 'assembly']
    for name in wanted:
        if name not in known:
            raise SystemExit(f'unknown part {name}, pick from {known}')
        layers, origin, features = build(name, args.res)
        volume = sum(grid.sum() for grid, _ in layers) * args.res ** 3
        image = render(layers, origin, args.res, width=args.width,
                       azimuth=args.azimuth, elevation=args.elevation)
        out = f'preview-{name}.png'
        image.save(out)
        print(f'{name:10s} {features:3d} features, {volume / 1000:6.1f} cm3, '
              f'{image.size[0]}x{image.size[1]} -> {out}')


if __name__ == '__main__':
    main()

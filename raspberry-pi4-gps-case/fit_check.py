#!/usr/bin/env python3
"""Audit the case geometry without opening Fusion 360.

Run it after every change to the script:

    python3 fit_check.py

It imports raspberry_pi4_gps_case.py with a stub in place of the Fusion API,
reads the layout functions, and checks the things that cannot be seen on
screen until the part is already printed. Exit status is non-zero when a check
fails, so it also works as a pre-commit hook.

It exists because two independent defects shipped together and both were
invisible in Fusion: the rear retaining lips reached 1.2 mm over the board
while the rear gap was 0.4 mm, so the board could never slide under them, and
the left lip sat on top of the 8.5 mm GPIO header. The board simply would not
go in.
"""
import sys
import types


def _stub_fusion():
    """Let the script import outside Fusion: it only needs the constants."""

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


_stub_fusion()
import raspberry_pi4_gps_case as case  # noqa: E402


# Dimensions come out of float arithmetic on millimetre constants, so a
# threshold is compared with a tolerance well below anything a printer resolves.
EPS = 1e-6
# Two 0.42 mm Arachne perimeters. Anything thinner prints hollow.
MIN_SKIN = 0.8

FAILURES = []
NOTES = []


def check(ok, label, detail):
    line = f"  {'ok  ' if ok else 'FAIL'}  {label}: {detail}"
    NOTES.append(line)
    if not ok:
        FAILURES.append(f'{label}: {detail}')


def overlap_1d(a0, a1, b0, b1):
    """Length of the overlap between two intervals, negative when they miss."""
    return min(a1, b1) - max(a0, b0)


def rect_overlap(first, second):
    """Overlap of two (x, y, length, width) rectangles as (dx, dy)."""
    ax, ay, al, aw = first
    bx, by, bl, bw = second
    return (overlap_1d(ax, ax + al, bx, bx + bl),
            overlap_1d(ay, ay + aw, by, by + bw))


def section(title):
    NOTES.append('')
    NOTES.append(title)


def check_board_envelope():
    section('Board in its pocket')
    pi = case.pi_layout()
    for axis, board, inner, start in (
        ('length', case.PI_BOARD_LENGTH, case.CASE_INNER_LENGTH, pi['x']),
        ('width', case.PI_BOARD_WIDTH, case.CASE_INNER_WIDTH, pi['y']),
    ):
        gap = inner - board
        check(gap >= 0.6,
              f'clearance across the {axis}',
              f'{gap:.2f} mm total, {gap / 2:.2f} mm per side '
              f'(FDM shrinks a pocket by about 0.2 mm)')
        check(abs((start - case.WALL) - gap / 2) < 1e-6,
              f'board centred across the {axis}',
              f'front offset {start - case.WALL:.2f} mm')


def check_connectors_clear_the_walls():
    """The pocket has to clear the board's real envelope, connectors included.

    This is the check that was missing. Everything else passed while the board
    physically could not be put in the case: the pocket was sized to the bare
    PCB, but USB and Ethernet stand 2.81 mm outside that outline, and the wall
    openings are closed at the top, so nothing can descend into position.
    """
    section('Connector envelope against the walls')
    pi = case.pi_layout()
    inner_top = case.FLOOR + case.CASE_INNER_HEIGHT

    for label, proud in (
        ('connector long edge', case.PI_CONNECTOR_PROUD_FRONT),
        ('USB and Ethernet edge', case.PI_CONNECTOR_PROUD_RIGHT),
    ):
        bite = proud - case.PI_SIDE_CLEARANCE
        check(bite <= 0, f'{label} against its wall',
              f'connectors stand {proud:.2f} mm proud against {case.PI_SIDE_CLEARANCE:.2f} mm '
              f'of clearance, so they bite {bite:+.2f} mm into the wall')

    blocked = []
    for opening in case.pi_io_openings():
        solid_above = inner_top - (opening['z'] + opening['height'])
        if solid_above > 0:
            blocked.append((opening['name'], solid_above))
    check(not blocked,
          'openings are open at the top so the board can be lowered in',
          f'{len(blocked)} of {len(case.pi_io_openings())} openings have solid '
          f'wall above them, up to '
          f'{max(b for _, b in blocked) if blocked else 0:.1f} mm'
          if blocked else 'every opening reaches the parting line')


def check_clips_clear_components():
    """No clip hook may overhang a stretch of edge carrying a component."""
    section('Clip hooks against the Pi 4 components')
    parts = case.pi_component_footprints()
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        tag = f"clip {index} ({clip['wall']} @ {clip['offset']:.0f} mm)"
        worst = None
        for name, rect, height in parts:
            dx, dy = rect_overlap(clip['hook'], rect)
            if dx > 0 and dy > 0:
                if worst is None or min(dx, dy) > worst[1]:
                    worst = (name, min(dx, dy), height)
        if worst:
            check(False, tag,
                  f'hook runs into {worst[0]} by {worst[1]:.2f} mm, '
                  f'and that part stands {worst[2]:.1f} mm above the PCB')
        else:
            margins = []
            for name, rect, _ in parts:
                dx, dy = rect_overlap(clip['hook'], rect)
                if max(dx, dy) > 0:
                    margins.append((-min(dx, dy), name))
            closest = min(margins) if margins else (99.0, 'nothing')
            check(True, tag,
                  f'clear, nearest is {closest[1]} at {closest[0]:.2f} mm')


def check_clips_clear_openings():
    """A clip must not be cut in half by a wall opening."""
    section('Clip arms against the wall openings')
    openings = case.pi_io_openings()
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        tag = f"clip {index} ({clip['wall']})"
        arm_x, arm_y, arm_l, arm_w = clip['arm']
        if clip['wall'] in ('front', 'rear'):
            span = (arm_x, arm_x + arm_l)
        else:
            span = (arm_y, arm_y + arm_w)
        hits = []
        for opening in openings:
            if opening['wall'] != clip['wall']:
                continue
            gap = overlap_1d(span[0], span[1], opening['start'],
                             opening['start'] + opening['span'])
            if gap > 0:
                hits.append((opening['name'], gap))
        if hits:
            check(False, tag,
                  ', '.join(f'crosses {n} by {g:.2f} mm' for n, g in hits))
        else:
            check(True, tag, 'sits on a solid stretch of wall')


def check_clip_holds_the_board():
    section('Retention')
    pi = case.pi_layout()
    board = (pi['x'], pi['y'], case.PI_BOARD_LENGTH, case.PI_BOARD_WIDTH)
    walls = set()
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        dx, dy = rect_overlap(clip['hook'], board)
        grip = min(dx, dy)
        check(abs(grip - case.PI_CLIP_OVERHANG) < 1e-6,
              f"clip {index} ({clip['wall']}) grip on the PCB",
              f'{grip:.2f} mm of the {case.PI_BOARD_THICKNESS:.1f} mm edge')
        walls.add(clip['wall'])
    check(len(walls) >= 3, 'clips spread around the board',
          f"{len(case.PI_CLIPS)} clips on {sorted(walls)}")


def check_vertical_insertion():
    """Nothing may need a sideways slide: the pocket has no room for one."""
    section('Straight-down insertion')
    pi = case.pi_layout()
    rear_gap = (case.WALL + case.CASE_INNER_WIDTH) - (pi['y'] + case.PI_BOARD_WIDTH)
    reach = max(min(rect_overlap(
        clip['hook'],
        (pi['x'], pi['y'], case.PI_BOARD_LENGTH, case.PI_BOARD_WIDTH)))
        for clip in case.pi_clip_layout())
    check(reach <= rear_gap + case.PI_SIDE_CLEARANCE,
          'no feature needs more slide than the pocket allows',
          f'deepest grip {reach:.2f} mm, rear gap {rear_gap:.2f} mm — '
          'the board drops in, it does not slide')
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        slices = case.pi_clip_lead_in_slices(clip, 0.0)
        depths = []
        for rect, _, _ in slices:
            depths.append(rect[3] if clip['wall'] in ('front', 'rear')
                          else rect[2])
        descending = all(b < a for a, b in zip(depths, depths[1:]))
        grip = case.PI_CLIP_OVERHANG
        clears = depths[-1] <= depths[0] - grip + EPS
        check(descending and clears,
              f'clip {index} lead-in ramps out of the way',
              f'{len(depths)} steps, {depths[0]:.2f} down to {depths[-1]:.2f} mm '
              f'over {case.PI_CLIP_LEAD_IN:.1f} mm of rise, so the top of the '
              f'ramp is flush with the board edge')


def check_snap_strain():
    section('Snap strain (PETG yields near 5 per cent)')
    arm_length = (case.FLOOR + case.PI_STANDOFF_HEIGHT + case.PI_BOARD_THICKNESS
                  + case.PI_CLIP_LEAD_IN + 1.2) - case.FLOOR
    for label, thickness, deflection, free_length in (
        ('PCB clip', case.PI_CLIP_THICKNESS,
         case.PI_CLIP_OVERHANG, arm_length),
        ('lid latch', case.LID_RIM_THICKNESS,
         case.LID_LATCH_DEPTH, case.LID_RIM_HEIGHT - case.LID_LATCH_BELOW_TOP),
    ):
        strain = 1.5 * thickness * deflection / free_length ** 2
        check(strain < 0.05, label,
              f'{strain:.1%} at {deflection:.1f} mm on a '
              f'{free_length:.1f} mm arm')


def check_wall_skin():
    section('Wall left behind the relief slots')
    outer_w = case.CASE_INNER_WIDTH + 2 * case.WALL
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        rx, ry, rl, rw = clip['relief']
        if clip['wall'] == 'front':
            skin = ry
        elif clip['wall'] == 'rear':
            skin = outer_w - (ry + rw)
        else:
            skin = rx
        check(skin >= MIN_SKIN - EPS, f"clip {index} ({clip['wall']}) outer skin",
              f'{skin:.2f} mm of solid wall outside the slot')


def check_sma_clear_of_clips():
    section('SMA hole against the rear clips')
    outer_l = case.CASE_INNER_LENGTH + 2 * case.WALL
    outer_w = case.CASE_INNER_WIDTH + 2 * case.WALL
    gps = case.gps_cradle_layout(outer_l, outer_w)
    sma_x = outer_l - gps['sma_center_x']
    half = case.SMA_RECESS_DIAMETER / 2
    for index, clip in enumerate(case.pi_clip_layout(), 1):
        if clip['wall'] != 'rear':
            continue
        ax, _, al, _ = clip['arm']
        gap = -overlap_1d(ax - case.PI_CLIP_POCKET_MARGIN,
                          ax + al + case.PI_CLIP_POCKET_MARGIN,
                          sma_x - half, sma_x + half)
        check(gap > 0, f'clip {index} versus the SMA counterbore',
              f'{gap:.2f} mm apart along the rear wall')


def check_standoffs():
    section('Standoffs')
    pi = case.pi_layout()
    radius = case.PI_STANDOFF_DIAMETER / 2
    check(radius <= case.PI_MOUNT_EDGE_OFFSET + EPS,
          'standoffs stay under the board',
          f'{radius:.2f} mm radius against a {case.PI_MOUNT_EDGE_OFFSET:.1f} mm '
          f'hole inset, {case.PI_MOUNT_EDGE_OFFSET - radius:.2f} mm to spare')
    top = pi['bottom_z'] + case.PI_BOARD_THICKNESS
    tallest = max(h for _, _, h in case.pi_component_footprints())
    headroom = case.FLOOR + case.CASE_INNER_HEIGHT - (top + tallest)
    check(headroom > 0, 'headroom over the tallest connector',
          f'{headroom:.2f} mm under the lid')


def main():
    check_board_envelope()
    check_connectors_clear_the_walls()
    check_clips_clear_components()
    check_clips_clear_openings()
    check_clip_holds_the_board()
    check_vertical_insertion()
    check_snap_strain()
    check_wall_skin()
    check_sma_clear_of_clips()
    check_standoffs()

    print('\n'.join(NOTES))
    print()
    if FAILURES:
        print(f'{len(FAILURES)} check(s) failed:')
        for failure in FAILURES:
            print(f'  - {failure}')
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())

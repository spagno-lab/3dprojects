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


def check_assembly_is_possible():
    """The reason the box is split: the board's real envelope, connectors
    included, is wider than any pocket that also has to retain it."""
    section('Assembly')
    pi = case.pi_layout()

    for label, proud in (
        ('connector long edge', case.PI_CONNECTOR_PROUD_FRONT),
        ('USB and Ethernet edge', case.PI_CONNECTOR_PROUD_RIGHT),
    ):
        bite = proud - case.PI_SIDE_CLEARANCE
        check(bite > 0, f'{label} reaches into its wall',
              f'connectors stand {proud:.2f} mm proud against '
              f'{case.PI_SIDE_CLEARANCE:.2f} mm of clearance, so they must '
              f'enter the wall by {bite:.2f} mm — only an open-bottomed '
              f'opening lets that happen')

    check(abs(case.PARTING_Z - pi['top_z']) < EPS,
          'parting plane is the top face of the PCB',
          f"z {case.PARTING_Z:.2f}, board top {pi['top_z']:.2f}: above it the "
          f'board is gone and only connectors remain')

    closed = []
    for opening in case.pi_io_openings():
        if opening.get('part') != 'shell':
            continue
        if not opening.get('open_bottom'):
            closed.append(opening['name'])
        elif abs(opening['z'] - case.PARTING_Z) > EPS:
            closed.append(opening['name'])
    check(not closed, 'every connector opening is open at the parting plane',
          'the shell can be lowered onto the board'
          if not closed else f'{closed} would trap the connectors')

    for opening in case.pi_io_openings():
        if opening.get('part') != 'base':
            continue
        top = opening['z'] + opening['height']
        check(top <= case.PARTING_Z + EPS,
              f"{opening['name']} stays in the base",
              f'ends at z {top:.2f}, parting plane {case.PARTING_Z:.2f}')


def check_connectors_sit_in_their_openings():
    """Each connector must clear its own opening on all sides.

    This is what the preview shows and what nothing checked: an opening can be
    open at the bottom and still be too short, too narrow or in the wrong
    place for the connector it is cut for.
    """
    section('Connectors inside their openings')
    pi = case.pi_layout()
    openings = {o['name']: o for o in case.pi_io_openings()}
    parts = {name: (rect, height)
             for name, rect, height in case.pi_component_footprints()}

    for name, opening in openings.items():
        part_name = name.replace(' opening', '')
        if part_name not in parts:
            continue
        rect, height = parts[part_name]
        if opening['wall'] == 'front':
            lo, hi = rect[0], rect[0] + rect[2]
        else:
            lo, hi = rect[1], rect[1] + rect[3]
        side = min(lo - opening['start'],
                   opening['start'] + opening['span'] - hi)
        top = (opening['z'] + opening['height']) - (pi['top_z'] + height)
        check(side > 0 and top > 0, part_name,
              f'{side:.2f} mm each side, {top:.2f} mm above it')


def check_pads_clear_components():
    """No press pad may land on a component."""
    section('Press pads against the Pi 4 components')
    parts = case.pi_component_footprints()
    for name, rect, _z, _h in case.pi_pad_layout():
        worst = None
        for part_name, part_rect, height in parts:
            dx, dy = rect_overlap(rect, part_rect)
            if dx > 0 and dy > 0 and (worst is None or min(dx, dy) > worst[1]):
                worst = (part_name, min(dx, dy), height)
        if worst:
            check(False, name,
                  f'lands on {worst[0]} by {worst[1]:.2f} mm, '
                  f'and that part stands {worst[2]:.1f} mm above the PCB')
        else:
            margins = [(-min(rect_overlap(rect, r)), n)
                       for n, r, _ in parts
                       if max(rect_overlap(rect, r)) > 0]
            closest = min(margins) if margins else (99.0, 'nothing')
            check(True, name,
                  f'clear, nearest is {closest[1]} at {closest[0]:.2f} mm')


def check_pads_hold_the_board():
    section('Board clamped between standoffs and shell')
    pi = case.pi_layout()
    board = (pi['x'], pi['y'], case.PI_BOARD_LENGTH, case.PI_BOARD_WIDTH)
    walls = set()
    for name, rect, pad_z, _h in case.pi_pad_layout():
        dx, dy = rect_overlap(rect, board)
        grip = min(dx, dy)
        check(abs(grip - case.PI_PAD_REACH) < EPS, f'{name} reach over the PCB',
              f'{grip:.2f} mm')
        check(pad_z < case.PARTING_Z - EPS, f'{name} preload',
              f'reaches {case.PARTING_Z - pad_z:.2f} mm below the parting '
              f'plane, so the board is clamped, not rattling')
        walls.add(name.split()[3])
    check(len(walls) >= 3, 'pads spread around the board',
          f'{len(case.PI_PADS)} pads on {sorted(walls)}')


def check_tabs_clear_components():
    """A snap tab lives inside the wall, where the connectors also reach."""
    section('Snap tabs against the connectors')
    pi = case.pi_layout()
    parts = case.pi_component_footprints()
    for index, tab in enumerate(case.base_tab_layout(), 1):
        label = f"tab {index} ({tab['wall']} @ {tab['start']:.1f} mm)"
        envelope = tab['bump'] if tab['wall'] != 'left' else tab['bump']
        span = (min(tab['arm'][0], envelope[0]), min(tab['arm'][1], envelope[1]),
                max(tab['arm'][2], envelope[2]) + abs(tab['arm'][0] - envelope[0]),
                max(tab['arm'][3], envelope[3]) + abs(tab['arm'][1] - envelope[1]))
        hits = [(n, min(rect_overlap(span, r))) for n, r, _ in parts
                if min(rect_overlap(span, r)) > 0]
        if hits:
            worst = max(hits, key=lambda h: h[1])
            check(False, label, f'runs into {worst[0]} by {worst[1]:.2f} mm')
        else:
            margins = [(-min(rect_overlap(span, r)), n) for n, r, _ in parts
                       if max(rect_overlap(span, r)) > 0]
            closest = min(margins) if margins else (99.0, 'nothing')
            check(True, label,
                  f'clear, nearest is {closest[1]} at {closest[0]:.2f} mm')


def check_tabs_clear_openings():
    section('Snap tabs against the wall openings')
    openings = case.pi_io_openings()
    for index, tab in enumerate(case.base_tab_layout(), 1):
        label = f"tab {index} ({tab['wall']})"
        if tab['wall'] in ('front', 'rear'):
            span = (tab['arm'][0], tab['arm'][0] + tab['arm'][2])
        else:
            span = (tab['arm'][1], tab['arm'][1] + tab['arm'][3])
        hits = [(o['name'], overlap_1d(span[0], span[1], o['start'],
                                      o['start'] + o['span']))
                for o in openings if o['wall'] == tab['wall']]
        clash = [h for h in hits if h[1] > 0]
        check(not clash, label,
              ', '.join(f'crosses {n} by {g:.2f} mm' for n, g in clash)
              if clash else 'sits on a solid stretch of wall')


def check_tab_wall_left():
    section('Shell wall left at each tab')
    slot = case.BASE_TAB_THICKNESS + case.BASE_TAB_CLEARANCE
    remaining = case.WALL - slot - case.BASE_TAB_BUMP
    check(remaining >= MIN_SKIN - EPS, 'wall behind the bump pocket',
          f'{remaining:.2f} mm, from {case.WALL:.1f} mm of wall less a '
          f'{slot:.1f} mm slot and a {case.BASE_TAB_BUMP:.1f} mm pocket')


def check_outside_stays_flat():
    """Nothing may stand outside the outer footprint.

    The joint has to fit inside the wall. Growing a boss outward to make room
    is the easy way out and it is not allowed here: it was a stated property
    of this case before the split, and relaxing it quietly is how a redesign
    loses the things that were already right.
    """
    section('Outside stays flat')
    outer_l = case.CASE_INNER_LENGTH + 2 * case.WALL
    outer_w = case.CASE_INNER_WIDTH + 2 * case.WALL

    rects = [('pad ' + name, rect)
             for name, rect, _z, _h in case.pi_pad_layout()]
    for index, tab in enumerate(case.base_tab_layout(), 1):
        for part in ('arm', 'bump', 'slot', 'pocket'):
            rects.append((f'tab {index} {part}', tab[part]))

    for label, (x, y, length, width) in rects:
        inside = (x >= -EPS and y >= -EPS
                  and x + length <= outer_l + EPS
                  and y + width <= outer_w + EPS)
        check(inside, label,
              f'x {x:.2f}..{x + length:.2f}, y {y:.2f}..{y + width:.2f} '
              f'within {outer_l:.1f} x {outer_w:.1f}')


def check_snap_strain():
    section('Snap strain (PETG yields near 5 per cent)')
    for label, thickness, deflection, free_length in (
        ('base snap tab', case.BASE_TAB_THICKNESS,
         case.BASE_TAB_BUMP, case.BASE_TAB_BUMP_CENTRE),
        ('lid latch', case.LID_RIM_THICKNESS,
         case.LID_LATCH_DEPTH, case.LID_RIM_HEIGHT - case.LID_LATCH_BELOW_TOP),
    ):
        strain = 1.5 * thickness * deflection / free_length ** 2
        check(strain < 0.05, label,
              f'{strain:.1%} at {deflection:.1f} mm on a '
              f'{free_length:.1f} mm arm')

    tip = case.BASE_TAB_HEIGHT - case.BASE_TAB_BUMP_CENTRE
    check(tip >= 0.5, 'bump sits near the tip of the tab',
          f'{tip:.1f} mm of arm beyond the bump')


def check_tabs_can_flex():
    """A tab bends toward the cavity, which above the parting plane is empty."""
    section('Room for the tabs to flex')
    pi = case.pi_layout()
    board = (pi['x'], pi['y'], case.PI_BOARD_LENGTH, case.PI_BOARD_WIDTH)
    for index, tab in enumerate(case.base_tab_layout(), 1):
        dx, dy = rect_overlap(tab['arm'], board)
        check(min(dx, dy) <= 0, f'tab {index} clears the board footprint',
              'the arm is in the wall, and above the parting plane the board '
              'is no longer in the way')


def check_sma_and_gps():
    section('GPS and antenna')
    outer_l = case.CASE_INNER_LENGTH + 2 * case.WALL
    outer_w = case.CASE_INNER_WIDTH + 2 * case.WALL
    outer_h = case.CASE_INNER_HEIGHT + case.FLOOR
    gps = case.gps_cradle_layout(outer_l, outer_w)
    sma_x = outer_l - gps['sma_center_x']
    half = case.SMA_RECESS_DIAMETER / 2

    check(case.SMA_HOLE_DIAMETER > case.SMA_THREAD_DIAMETER,
          'SMA hole clears the threaded section',
          f"{case.SMA_HOLE_DIAMETER:.1f} mm hole for a "
          f"{case.SMA_THREAD_DIAMETER:.1f} mm thread, "
          f"{case.SMA_HOLE_CLEARANCE:.1f} mm all round")
    check(case.SMA_LOCAL_WALL < case.WALL,
          'counterbore leaves the antenna room to tighten',
          f'wall reduced to {case.SMA_LOCAL_WALL:.1f} mm from '
          f'{case.WALL:.1f} mm around the connector')
    check(2 * case.GPS_FIT_CLEARANCE <= 0.5,
          'GPS cradle lateral play',
          f'{2 * case.GPS_FIT_CLEARANCE:.1f} mm total across the PCB')
    check(case.GPS_EDGE_SUPPORT_WIDTH
          <= case.GPS_COMPONENT_KEEPOUT_INSET,
          'GPS supports stay in the component-free perimeter',
          f'{case.GPS_EDGE_SUPPORT_WIDTH:.1f} mm supports inside a '
          f'{case.GPS_COMPONENT_KEEPOUT_INSET:.1f} mm edge keep-out')
    check(case.GPS_CLIP_OVERHANG
          < case.GPS_COMPONENT_KEEPOUT_INSET,
          'GPS clip lips avoid the component envelope',
          f'{case.GPS_CLIP_OVERHANG:.1f} mm overhang before components begin '
          f'at {case.GPS_COMPONENT_KEEPOUT_INSET:.1f} mm')
    rear_clip_end = (gps['rear_y'] - case.SMA_BASE_LENGTH
                     - case.GPS_FIT_CLEARANCE)
    check(rear_clip_end <= gps['rear_y'] - case.SMA_BASE_LENGTH,
          'rear GPS clips stop before the SMA base',
          f'{gps["rear_y"] - case.SMA_BASE_LENGTH - rear_clip_end:.1f} mm '
          'clearance before the base')

    # The SMA hole and the cradle that positions it must stay in one part.
    check(case.PARTING_Z < outer_h - case.LID_RIM_HEIGHT,
          'SMA hole is entirely in the shell',
          f'parting plane at z {case.PARTING_Z:.2f}, the hole sits just under '
          f'the lid at z {outer_h:.1f}')

    for index, tab in enumerate(case.base_tab_layout(), 1):
        if tab['wall'] != 'rear':
            continue
        arm = tab['arm']
        gap = -overlap_1d(arm[0] - 2.0, arm[0] + arm[2] + 2.0,
                          sma_x - half, sma_x + half)
        check(gap > 0, f'tab {index} versus the SMA counterbore',
              f'{gap:.2f} mm apart along the rear wall')


def check_standoffs():
    section('Standoffs and headroom')
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
    rim_bottom = case.FLOOR + case.CASE_INNER_HEIGHT - case.LID_RIM_HEIGHT
    opening_top = max(o['z'] + o['height'] for o in case.pi_io_openings())
    check(rim_bottom > opening_top,
          'lid rim clears the tallest opening',
          f'rim reaches z {rim_bottom:.1f}, openings stop at z '
          f'{opening_top:.1f}')


def check_lid_ventilation():
    section('Raspberry ventilation')
    outer_l = case.CASE_INNER_LENGTH + 2 * case.WALL
    outer_w = case.CASE_INNER_WIDTH + 2 * case.WALL
    berries, leaves, gps_keepout = case.raspberry_vent_layout(outer_l, outer_w)
    bridge = case.RASPBERRY_VENT_PITCH - case.RASPBERRY_VENT_DIAMETER
    check(len(berries) == 18 and len(leaves) == 6,
          'two complete raspberry motifs',
          f'{len(berries)} berry and {len(leaves)} leaf vents')
    check(bridge >= 2.0 - EPS,
          'printable bridges between berry vents',
          f'{bridge:.1f} mm minimum nominal bridge')
    radius = case.RASPBERRY_VENT_DIAMETER / 2
    clashes = [circle for circle in berries if case.rectangles_overlap(
        (circle[0] - radius, circle[1] - radius,
         2 * radius, 2 * radius), gps_keepout)]
    check(not clashes, 'berry vents clear the GPS carrier',
          'no overlap' if not clashes else f'{len(clashes)} overlap(s)')
    leaf_clashes = [leaf for leaf in leaves if case.rectangles_overlap(
        case.rotated_ellipse_bounds(leaf), gps_keepout)]
    check(not leaf_clashes, 'leaf vents clear the GPS carrier',
          'no overlap' if not leaf_clashes
          else f'{len(leaf_clashes)} overlap(s)')


def main():
    check_board_envelope()
    check_assembly_is_possible()
    check_connectors_sit_in_their_openings()
    check_pads_clear_components()
    check_pads_hold_the_board()
    check_tabs_clear_components()
    check_tabs_clear_openings()
    check_tabs_can_flex()
    check_tab_wall_left()
    check_outside_stays_flat()
    check_snap_strain()
    check_sma_and_gps()
    check_standoffs()
    check_lid_ventilation()

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

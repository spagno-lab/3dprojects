import adsk.core
import adsk.fusion
import math
import traceback


# ---------------------------------------------------------------------------
# Raspberry Pi 4 Model B, official mechanical drawing.
# Datum: PCB corner on the micro-USB-C side of the connector long edge.
# ---------------------------------------------------------------------------
# 1.0 mm per side. pkoehlers/rpi-case-openscad, the closest comparable design
# (Pi 4 with an external antenna), uses 1.2 mm; this pocket also sits the board
# on four standoffs, which centres it, so it can afford slightly less.
# The 0.4 mm it used to carry was below what FDM resolves on an 85 mm pocket.
PI_SIDE_CLEARANCE = 1.0
PI_STANDOFF_HEIGHT = 3.0
PI_STANDOFF_DIAMETER = 5.0

# ---------------------------------------------------------------------------
# Why the case is split in two at board level.
#
# The connectors stand outside the PCB outline: 2.81 mm on the USB and
# Ethernet edge. Whatever the retention, a board whose envelope is wider than
# its pocket cannot be pushed into a closed box, and openings that are closed
# above the connectors cannot be entered from inside either. Earlier revisions
# kept trying to hold a board that had no way of getting there.
#
# So the box parts along the top face of the PCB. The base carries the floor,
# the standoffs and the pocket that locates the board. The shell carries
# everything above it, and every I/O opening is open at its bottom edge: the
# shell comes down over the board and the connectors enter their openings from
# below. Nothing ever has to pass through material.
#
# This is what pkoehlers/rpi-case-openscad does (topSelector splits the case
# with "a small lip for the IO"), and it is why that model can be assembled.
# ---------------------------------------------------------------------------

# Pads on the underside of the shell that press the board onto the standoffs.
# They are rigid: nothing has to snap over the board any more, the shell simply
# traps it. Placement is the same problem as before, so they sit on the four
# free stretches of board edge, and fit_check.py still verifies every one.
PI_PAD_REACH = 1.2
PI_PAD_HEIGHT = 2.5
# The pads reach this far below the parting plane so the board is clamped
# rather than rattling between the standoffs and the shell. The PCB and the
# standoffs absorb it; it is far less than the thickness tolerance of the
# board itself.
PI_PAD_PRELOAD = 0.15
PI_PADS = (
    ('front', 61.0, 14.0),
    ('left', 6.0, 12.0),
    ('left', 38.0, 12.0),
    ('rear', 59.0, 14.0),
)

# Snap tabs that hold the shell down on the base. They rise from the base wall
# into slots in the shell wall and are the only flexing features left.
# One per corner: the corners are the only stretches of wall that no connector
# reaches on either side, so they are the same on every wall.
# Positions are absolute along the wall, because the tabs live in the wall
# rather than over the board.
# 0.8 mm, not 1.0: the whole joint has to fit inside the 2.5 mm wall, because
# the outside of this case stays flat. The budget is slot (thickness plus
# clearance) plus bump pocket plus at least two perimeters of skin behind it,
# which leaves 0.9 mm here. A thinner arm also bends more easily, so the
# strain drops to 2.0 per cent.
BASE_TAB_THICKNESS = 0.8
BASE_TAB_HEIGHT = 7.0
BASE_TAB_CLEARANCE = 0.2
BASE_TAB_BUMP = 0.6
BASE_TAB_BUMP_HEIGHT = 2.0
# Centre of the bump above the parting plane. Keeping it near the tip is what
# holds the bending strain down; see the table in the README.
BASE_TAB_BUMP_CENTRE = 6.0
BASE_TABS = (
    # Short, because the USB-C opening starts 8.4 mm along the front wall.
    ('front', 2.6, 5.4),
    ('front', 83.0, 6.0),
    ('left', 53.5, 6.0),
    ('rear', 83.0, 6.0),
)
# Gap left between the two printed faces so they meet on the wall, not on a
# high spot.
PARTING_CLEARANCE = 0.1
# Features that join to a wall are grown this far into it. A join across two
# exactly coincident faces is valid but brittle in Fusion: it survives the
# first rebuild and drops out after an edit.
JOIN_OVERLAP = 0.5

# ---------------------------------------------------------------------------
# GPS carrier, user-measured. The component/pin face points into the case, the
# u-blox shield faces the lid, the SMA sits in the top-right corner.
# ---------------------------------------------------------------------------
GPS_BOARD_LENGTH = 23.0
GPS_BOARD_WIDTH = 18.0
GPS_BOARD_THICKNESS = 1.6
GPS_MODULE_DEPTH = 8.0
GPS_BACK_COMPONENT_DEPTH = (GPS_MODULE_DEPTH - GPS_BOARD_THICKNESS) / 2
GPS_FRONT_COMPONENT_DEPTH = GPS_BACK_COMPONENT_DEPTH
# The first printed cradle could rock under pressure on the SMA. 0.2 mm per
# side still leaves a printable PETG sliding fit without the former 0.6 mm of
# total lateral play.
GPS_FIT_CLEARANCE = 0.2
GPS_PIN_COUNT = 5
GPS_PIN_FORWARD = 5.0
GPS_PIN_DROP = 8.0
GPS_PIN_PITCH = 2.54
GPS_PIN_WIDTH = 0.64
GPS_JOIN_OVERLAP = 0.2
SMA_BASE_LENGTH = 7.0
SMA_BASE_WIDTH = 7.0
SMA_BASE_DEPTH = 1.0
SMA_THREAD_DIAMETER = 5.0
SMA_PROJECTION = 8.0
SMA_CENTER_FROM_RIGHT = SMA_BASE_WIDTH / 2
# The printed 5.6 mm hole was too tight on the first print: the nut and the
# solder fillet at the base of the connector fouled the wall. Opened by 2 mm.
SMA_HOLE_CLEARANCE = 1.3
SMA_HOLE_DIAMETER = SMA_THREAD_DIAMETER + 2 * SMA_HOLE_CLEARANCE
SMA_LOCAL_WALL = 2.0
# The counterbore must stay wider than the enlarged through hole, otherwise it
# no longer thins the wall around the antenna nut.
SMA_RECESS_DIAMETER = SMA_HOLE_DIAMETER + 2.0
GPS_CLIP_THICKNESS = 2.0
GPS_CLIP_LENGTH = 5.0
GPS_CLIP_OVERHANG = 1.1
# The component keep-out starts 1.2 mm in from every edge, so the full safe
# perimeter can support the PCB without touching parts on its underside.
GPS_EDGE_SUPPORT_WIDTH = 1.2
GPS_COMPONENT_KEEPOUT_INSET = 1.2

# ---------------------------------------------------------------------------
# Case. The cavity now hugs the PCB so the connectors sit against their
# openings instead of floating 3 mm inboard.
PI_BOARD_LENGTH = 85.0
PI_BOARD_WIDTH = 56.0
PI_BOARD_THICKNESS = 1.6
PI_BOARD_EDGE_CLEARANCE = PI_SIDE_CLEARANCE
PI_MOUNT_X = 58.0
PI_MOUNT_Y = 49.0
PI_MOUNT_EDGE_OFFSET = 3.5
PI_MOUNT_HOLE_DIAMETER = 2.7
PI_IO_CLEARANCE = 0.8

# Connector envelopes in the public reference model's board coordinates.
# The Pi is assembled 180 degrees from that model in this case.
PI_FRONT_CONNECTORS = (
    ('USB-C opening', 67.1, 12.2, 4.5),
    ('Micro-HDMI 1 opening', 54.5, 8.5, 4.5),
    ('Micro-HDMI 2 opening', 40.7, 8.5, 4.5),
    ('Audio opening', 26.9, 8.5, 6.9),
)
PI_RIGHT_CONNECTORS = (
    ('USB 2 opening', 39.6, 14.7, 15.6),
    ('USB 3 opening', 22.6, 14.7, 15.6),
    ('Ethernet opening', 2.15, 17.9, 13.6),
)
# How far the connector bodies stand proud of the PCB edge. These are not
# reference-only decoration: they set the real envelope of the board, which is
# what the pocket has to clear.
#
# The in-plane table above was taken from pkoehlers/rpi-case-openscad, whose
# positions, widths and heights match this file exactly. That model places the
# USB and Ethernet solids at x = -2.81, i.e. 2.81 mm outside the board edge.
# The overhang did not come across with the rest of the table, and the pocket
# ended up sized to the bare PCB.
PI_CONNECTOR_PROUD_RIGHT = 2.81
# The USB-C, micro-HDMI and audio bodies on the connector long edge stand out
# less. 2.0 mm is the audio jack, the worst of them, in the saarbastler board
# model that txoof/pi4_case builds on.
PI_CONNECTOR_PROUD_FRONT = 2.0
# Kept as the larger of the two for anything that wants a single figure.
PI_CONNECTOR_PROUD = max(PI_CONNECTOR_PROUD_RIGHT, PI_CONNECTOR_PROUD_FRONT)
PI_GPIO_LENGTH = 50.8
PI_GPIO_WIDTH = 5.1
PI_GPIO_HEIGHT = 8.5
PI_GPIO_EDGE_OFFSET = 3.5
PI_GPIO_FIRST_PIN = 3.5
PI_MICROSD_Y = 22.4
PI_MICROSD_WIDTH = 11.11
PI_MICROSD_ACCESS_WIDTH = 18.0
PI_MICROSD_OPENING_HEIGHT = 8.0

# Two raspberry-shaped groups of round vents replace the anonymous square
# lattice. Individual holes keep printable bridges between them, while the
# narrow leaf rows fit beside the GPS keep-out.
RASPBERRY_VENT_DIAMETER = 6.5
RASPBERRY_VENT_PITCH = 8.5
RASPBERRY_VENT_EDGE_MARGIN = 6.0
RASPBERRY_VENT_GPS_MARGIN = 2.0


# ---------------------------------------------------------------------------
WALL = 2.5
FLOOR = 2.5
CASE_INNER_LENGTH = PI_BOARD_LENGTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_WIDTH = PI_BOARD_WIDTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_HEIGHT = 29.0
# The two printed parts meet on the top face of the PCB. Above this plane the
# board is gone and only its connectors remain, which is exactly what lets the
# I/O openings be open at the bottom.
PARTING_Z = FLOOR + PI_STANDOFF_HEIGHT + PI_BOARD_THICKNESS
LID_THICKNESS = 2.4

# Lid retention. The first print never snapped because the rim was 0.6 mm
# clear of the wall on each side and had no latch at all.
LID_RIM_HEIGHT = 7.0
LID_RIM_THICKNESS = 1.2
# PETG lays down slightly fatter than PLA and the rim is a long sliding fit,
# so it gets 0.25 mm instead of the 0.15 mm that works in PLA.
LID_RIM_CLEARANCE = 0.25
LID_LATCH_DEPTH = 0.6
LID_LATCH_LENGTH = 12.0
LID_LATCH_HEIGHT = 2.0
# Measured down from the rim tip. The rim is what flexes, so the latch sits
# far from its root: 5 mm of free rim keeps the strain near 4 per cent.
LID_LATCH_BELOW_TOP = 2.0
# The pocket is taller than the bump so the lid can seat fully.
LID_LATCH_LEAD_IN = 0.4

# Raspberry Pi 4 Model B mechanical datum. Board and mounting dimensions come
# from the official mechanical drawing. Connector envelopes are cross-checked
# against public Pi 4 enclosure models and receive one explicit print margin.
def cm(mm):
    return mm / 10.0


def value(mm):
    return adsk.core.ValueInput.createByString(f'{mm} mm')


def component(root, name, x_offset=0):
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(cm(x_offset), 0, 0)
    occurrence = root.occurrences.addNewComponent(matrix)
    occurrence.component.name = name
    return occurrence.component


def offset_plane(comp, z):
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(comp.xYConstructionPlane, value(z))
    return planes.add(plane_input)


def rectangle_feature(comp, name, x, y, z, length, width, height,
                      operation=adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                      participant_bodies=None):
    plane = comp.xYConstructionPlane if z == 0 else offset_plane(comp, z)
    sketch = comp.sketches.add(plane)
    sketch.name = name
    lines = sketch.sketchCurves.sketchLines
    lines.addTwoPointRectangle(
        adsk.core.Point3D.create(cm(x), cm(y), 0),
        adsk.core.Point3D.create(cm(x + length), cm(y + width), 0)
    )
    profile = sketch.profiles.item(0)
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    if participant_bodies:
        extrude_input.participantBodies = participant_bodies
    extrude_input.setDistanceExtent(False, value(height))
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def cylinder_feature(comp, name, center_x, center_y, z, diameter, height,
                     operation=adsk.fusion.FeatureOperations.JoinFeatureOperation,
                     participant_bodies=None):
    sketch = comp.sketches.add(offset_plane(comp, z))
    sketch.name = name
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(center_x), cm(center_y), 0), cm(diameter / 2))
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(sketch.profiles.item(0), operation)
    if participant_bodies:
        extrude_input.participantBodies = participant_bodies
    extrude_input.setDistanceExtent(False, value(height))
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def circle_vent_feature(comp, target_body, name, circles, height):
    """Cut a group of round vents in one sketch/extrude operation."""
    sketch = comp.sketches.add(comp.xYConstructionPlane)
    sketch.name = name
    for center_x, center_y, diameter in circles:
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(center_x), cm(center_y), 0),
            cm(diameter / 2),
        )

    profiles = adsk.core.ObjectCollection.create()
    for index in range(sketch.profiles.count):
        profiles.add(sketch.profiles.item(index))
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrude_input.participantBodies = [target_body]
    extrude_input.setDistanceExtent(False, value(height))
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def ellipse_vent_feature(comp, target_body, name, ellipses, height):
    """Cut rotated elliptical leaf vents in one sketch/extrude operation."""
    sketch = comp.sketches.add(comp.xYConstructionPlane)
    sketch.name = name
    for center_x, center_y, major_radius, minor_radius, angle_degrees in ellipses:
        angle = math.radians(angle_degrees)
        center = adsk.core.Point3D.create(cm(center_x), cm(center_y), 0)
        major = adsk.core.Point3D.create(
            cm(center_x + major_radius * math.cos(angle)),
            cm(center_y + major_radius * math.sin(angle)), 0)
        minor = adsk.core.Point3D.create(
            cm(center_x - minor_radius * math.sin(angle)),
            cm(center_y + minor_radius * math.cos(angle)), 0)
        sketch.sketchCurves.sketchEllipses.add(center, major, minor)

    profiles = adsk.core.ObjectCollection.create()
    for index in range(sketch.profiles.count):
        profiles.add(sketch.profiles.item(index))
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrude_input.participantBodies = [target_body]
    extrude_input.setDistanceExtent(False, value(height))
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def pi_layout():
    """Return the Pi board datum and mounting locations inside the case."""
    board_x = WALL + PI_BOARD_EDGE_CLEARANCE
    board_y = WALL + PI_BOARD_EDGE_CLEARANCE
    board_bottom_z = FLOOR + PI_STANDOFF_HEIGHT
    return {
        'x': board_x,
        'y': board_y,
        'bottom_z': board_bottom_z,
        'top_z': board_bottom_z + PI_BOARD_THICKNESS,
        'mount_x': board_x + PI_MOUNT_EDGE_OFFSET,
        'mount_y': board_y + PI_MOUNT_EDGE_OFFSET,
    }


def pi_io_openings():
    """Derive all Pi 4 wall apertures from the common assembled board datum.

    Every connector opening starts exactly at the parting plane and is open
    at its bottom edge. That is the whole point of splitting the box: the
    shell descends and the connectors, which stand up to 2.81 mm outside the
    PCB outline, enter their openings from below instead of having to be
    pushed through solid wall.
    """
    pi = pi_layout()
    opening_z = PARTING_Z
    openings = []

    for name, source_x, connector_width, connector_height in PI_FRONT_CONNECTORS:
        rotated_x = pi['x'] + PI_BOARD_LENGTH - source_x - connector_width
        openings.append({
            'name': name,
            'wall': 'front',
            'start': rotated_x - PI_IO_CLEARANCE,
            'span': connector_width + 2 * PI_IO_CLEARANCE,
            'z': opening_z,
            'height': connector_height + PI_IO_CLEARANCE,
            'open_bottom': True,
        })

    for name, source_y, connector_width, connector_height in PI_RIGHT_CONNECTORS:
        rotated_y = pi['y'] + PI_BOARD_WIDTH - source_y - connector_width
        openings.append({
            'name': name,
            'wall': 'right',
            'start': rotated_y - PI_IO_CLEARANCE,
            'span': connector_width + 2 * PI_IO_CLEARANCE,
            'z': opening_z,
            'height': connector_height + PI_IO_CLEARANCE,
            'open_bottom': True,
        })

    microsd_center_y = (
        pi['y'] + PI_BOARD_WIDTH
        - PI_MICROSD_Y - PI_MICROSD_WIDTH / 2
    )
    # The card sits under the board, so its slot belongs to the base and runs
    # up to the parting plane. Open at the top, which also means no bridging.
    microsd_z = pi['bottom_z'] - FLOOR
    openings.append({
        'name': 'MicroSD opening',
        'wall': 'left',
        'start': microsd_center_y - PI_MICROSD_ACCESS_WIDTH / 2,
        'span': PI_MICROSD_ACCESS_WIDTH,
        'z': microsd_z,
        'height': PARTING_Z - microsd_z,
        'open_bottom': False,
        'part': 'base',
    })
    for opening in openings:
        opening.setdefault('part', 'shell')
    return openings


def pi_component_footprints():
    """Return every Pi 4 component that stands above the PCB.

    One source of truth for two consumers: body 4 draws these, and
    fit_check.py tests the retention clips against them. The rear lip that
    broke assembly landed on the GPIO header precisely because the clip
    placement and the reference body were worked out separately.

    Each entry is (name, rect, height) with rect as (x, y, length, width) and
    height measured from the top face of the PCB.
    """
    pi = pi_layout()
    parts = []

    for name, source_x, width, height in PI_FRONT_CONNECTORS:
        x = pi['x'] + PI_BOARD_LENGTH - source_x - width
        parts.append((
            name.replace(' opening', ''),
            (x, pi['y'] - PI_CONNECTOR_PROUD_FRONT,
             width, PI_CONNECTOR_PROUD_FRONT + width / 3),
            height,
        ))

    for name, source_y, width, height in PI_RIGHT_CONNECTORS:
        y = pi['y'] + PI_BOARD_WIDTH - source_y - width
        depth = 21.0 if 'USB' in name else 21.3
        parts.append((
            name.replace(' opening', ''),
            (pi['x'] + PI_BOARD_LENGTH + PI_CONNECTOR_PROUD_RIGHT - depth, y,
             depth, width),
            height,
        ))

    parts.append((
        'GPIO header',
        (pi['x'] + PI_GPIO_FIRST_PIN,
         pi['y'] + PI_BOARD_WIDTH - PI_GPIO_EDGE_OFFSET - PI_GPIO_WIDTH / 2,
         PI_GPIO_LENGTH, PI_GPIO_WIDTH),
        PI_GPIO_HEIGHT,
    ))
    return parts


def rectangles_overlap(first, second):
    """Return whether two (x, y, length, width) rectangles overlap."""
    ax, ay, al, aw = first
    bx, by, bl, bw = second
    return not (
        ax + al <= bx or bx + bl <= ax
        or ay + aw <= by or by + bw <= ay
    )


def rotated_ellipse_bounds(ellipse):
    """Return an axis-aligned bounds rectangle for a rotated ellipse."""
    center_x, center_y, major, minor, angle_degrees = ellipse
    angle = math.radians(angle_degrees)
    radius_x = math.sqrt(
        (major * math.cos(angle)) ** 2 + (minor * math.sin(angle)) ** 2)
    radius_y = math.sqrt(
        (major * math.sin(angle)) ** 2 + (minor * math.cos(angle)) ** 2)
    return (center_x - radius_x, center_y - radius_y,
            2 * radius_x, 2 * radius_y)


def raspberry_vent_layout(outer_l, outer_w, x_offset=0):
    """Return two raspberry motifs made from separated berry and leaf vents.

    The four-three-two berry rows sit below the GPS carrier. Three narrower
    holes above each berry read as leaves and fit on either side of the carrier.
    The motif is intentionally geometric rather than a traced trademark.
    """
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    gps_keepout = (
        gps['x'] - GPS_FIT_CLEARANCE - GPS_CLIP_THICKNESS
        - RASPBERRY_VENT_GPS_MARGIN,
        gps['y'] - GPS_CLIP_THICKNESS - RASPBERRY_VENT_GPS_MARGIN,
        GPS_BOARD_WIDTH + 2 * (
            GPS_FIT_CLEARANCE + GPS_CLIP_THICKNESS
            + RASPBERRY_VENT_GPS_MARGIN),
        GPS_BOARD_LENGTH + GPS_CLIP_THICKNESS
        + 2 * RASPBERRY_VENT_GPS_MARGIN,
    )
    radius = RASPBERRY_VENT_DIAMETER / 2
    pitch = RASPBERRY_VENT_PITCH
    motif_center_y = RASPBERRY_VENT_EDGE_MARGIN + radius + pitch * 1.25
    motif_center_x = (
        RASPBERRY_VENT_EDGE_MARGIN + radius + pitch * 1.5
    )
    motif_centers = (
        x_offset + motif_center_x,
        x_offset + outer_l - motif_center_x,
    )

    # (horizontal pitch offset, vertical pitch offset). The fruit points
    # toward the front edge and the three-hole crown forms the leaves.
    berry = (
        (-1.5, 1.0), (-0.5, 1.0), (0.5, 1.0), (1.5, 1.0),
        (-1.0, 0.0), (0.0, 0.0), (1.0, 0.0),
        (-0.5, -1.0), (0.5, -1.0),
    )
    circles = []
    leaves = []
    for center_x in motif_centers:
        for dx, dy in berry:
            circle = (
                center_x + dx * pitch,
                motif_center_y + dy * pitch,
                RASPBERRY_VENT_DIAMETER,
            )
            bounds = (circle[0] - radius, circle[1] - radius,
                      2 * radius, 2 * radius)
            if not rectangles_overlap(bounds, gps_keepout):
                circles.append(circle)
        candidates = (
            (center_x - 0.55 * pitch, motif_center_y + 2.15 * pitch,
             4.0, 2.0, 55.0),
            (center_x + 0.55 * pitch, motif_center_y + 2.15 * pitch,
             4.0, 2.0, 125.0),
            (center_x, motif_center_y + 2.95 * pitch,
             4.0, 2.0, 90.0),
        )
        leaves.extend(leaf for leaf in candidates if not rectangles_overlap(
            rotated_ellipse_bounds(leaf), gps_keepout))
    return circles, leaves, gps_keepout


def rear_wall_hole(comp, target_body, name, center_x, center_z, wall_y,
                   diameter, depth):
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    # Fusion's positive offset from the XZ plane points toward negative Y.
    plane_input.setByOffset(comp.xZConstructionPlane, value(-wall_y))
    plane = planes.add(plane_input)
    sketch = comp.sketches.add(plane)
    sketch.name = name
    model_center = adsk.core.Point3D.create(
        cm(center_x), cm(wall_y), cm(center_z))
    sketch_center = sketch.modelToSketchSpace(model_center)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        sketch_center, cm(diameter / 2)
    )
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrude_input.participantBodies = [target_body]
    extrude_input.setSymmetricExtent(value(depth), False)
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def pi_pad_layout(x_offset=0):
    """Return the shell pads that press the board onto its standoffs.

    Each pad is (name, rect, z, height) with rect as (x, y, length, width).
    A pad spans the clearance gap and reaches PI_PAD_REACH over the PCB edge,
    on a stretch of edge that carries no connector.
    """
    pi = pi_layout()
    pads = []
    for wall, offset, length in PI_PADS:
        reach = PI_SIDE_CLEARANCE + PI_PAD_REACH + JOIN_OVERLAP
        if wall == 'front':
            rect = (x_offset + pi['x'] + offset, WALL - JOIN_OVERLAP,
                    length, reach)
        elif wall == 'rear':
            rect = (x_offset + pi['x'] + offset,
                    pi['y'] + PI_BOARD_WIDTH - PI_PAD_REACH, length, reach)
        else:
            rect = (x_offset + WALL - JOIN_OVERLAP, pi['y'] + offset,
                    reach, length)
        pads.append((
            f'Board press pad {wall} {offset:.0f}',
            rect,
            PARTING_Z - PI_PAD_PRELOAD,
            PI_PAD_HEIGHT + PI_PAD_PRELOAD,
        ))
    return pads


def base_tab_layout(x_offset=0):
    """Return the snap tabs that hold the shell down on the base.

    Each entry gives the tab arm, its bump, and the slot and bump pocket the
    shell needs, all as (x, y, length, width) rectangles. The tab is the inner
    slice of the base wall continued above the parting plane, so it is rooted
    in thick material and bends over its whole free length.
    """
    slot_depth = BASE_TAB_THICKNESS + BASE_TAB_CLEARANCE
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    tabs = []
    for wall, start, length in BASE_TABS:
        if wall in ('front', 'rear'):
            arm_l, arm_w = length, BASE_TAB_THICKNESS
            if wall == 'front':
                arm_y = WALL - BASE_TAB_THICKNESS
                slot_y, bump_y = WALL - slot_depth, WALL - slot_depth - BASE_TAB_BUMP
                bump_face_y = arm_y - BASE_TAB_BUMP
            else:
                arm_y = outer_w - WALL
                slot_y, bump_y = outer_w - WALL, outer_w - WALL + slot_depth
                bump_face_y = arm_y + BASE_TAB_THICKNESS - JOIN_OVERLAP
            arm = (x_offset + start, arm_y, arm_l, arm_w)
            bump = (x_offset + start, bump_face_y,
                    arm_l, BASE_TAB_BUMP + JOIN_OVERLAP)
            slot = (x_offset + start - BASE_TAB_CLEARANCE, slot_y,
                    arm_l + 2 * BASE_TAB_CLEARANCE, slot_depth)
            pocket = (x_offset + start - BASE_TAB_CLEARANCE, bump_y,
                      arm_l + 2 * BASE_TAB_CLEARANCE, BASE_TAB_BUMP)
        else:
            arm_l, arm_w = BASE_TAB_THICKNESS, length
            arm_x = WALL - BASE_TAB_THICKNESS
            arm = (x_offset + arm_x, start, arm_l, arm_w)
            bump = (x_offset + arm_x - BASE_TAB_BUMP, start,
                    BASE_TAB_BUMP + JOIN_OVERLAP, arm_w)
            slot = (x_offset + WALL - slot_depth, start - BASE_TAB_CLEARANCE,
                    slot_depth, arm_w + 2 * BASE_TAB_CLEARANCE)
            pocket = (x_offset + WALL - slot_depth - BASE_TAB_BUMP,
                      start - BASE_TAB_CLEARANCE, BASE_TAB_BUMP,
                      arm_w + 2 * BASE_TAB_CLEARANCE)
        tabs.append({
            'wall': wall,
            'start': start,
            'length': length,
            'arm': arm,
            'bump': bump,
            'slot': slot,
            'pocket': pocket,
        })
    return tabs


def tab_bump_z():
    """Z extent of a tab bump and of the pocket that receives it."""
    bump_z = PARTING_Z + BASE_TAB_BUMP_CENTRE - BASE_TAB_BUMP_HEIGHT / 2
    return {
        'bump_z': bump_z,
        'bump_height': BASE_TAB_BUMP_HEIGHT,
        'pocket_z': bump_z - BASE_TAB_CLEARANCE,
        'pocket_height': BASE_TAB_BUMP_HEIGHT + 2 * BASE_TAB_CLEARANCE,
        'slot_height': BASE_TAB_HEIGHT + 1.0,
    }


def lid_latch_positions(x_offset=0):
    """Latch pockets in the case walls and matching bumps on the lid rim."""
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    z = FLOOR + CASE_INNER_HEIGHT - LID_LATCH_BELOW_TOP
    first = x_offset + outer_l / 2 - 24.0 - LID_LATCH_LENGTH / 2
    second = x_offset + outer_l / 2 + 24.0 - LID_LATCH_LENGTH / 2
    return {'z': z, 'x_positions': (first, second)}


def gps_cradle_layout(outer_l, outer_w, x_offset=0):
    """Return the board envelope with the SMA base against the rear wall."""
    board_x = x_offset + (outer_l - GPS_BOARD_WIDTH) / 2
    board_rear_y = outer_w - WALL
    return {
        'x': board_x,
        'y': board_rear_y - GPS_BOARD_LENGTH,
        'rear_y': board_rear_y,
        'center_x': board_x + GPS_BOARD_WIDTH / 2,
        'sma_center_x': board_x + GPS_BOARD_WIDTH - SMA_CENTER_FROM_RIGHT,
        'sma_tip_y': board_rear_y + SMA_PROJECTION,
    }


def gps_sma_wall_features(comp, target_body, outer_l, outer_w, outer_h):
    """Cut the round SMA hole and its shallow external tightening recess."""
    gps = gps_cradle_layout(outer_l, outer_w)
    # The generated lid must be flipped 180 degrees around its front-rear axis
    # before assembly. Mirror its lateral coordinate, then place the SMA axis
    # below the lid's inner face. outer_h already locates that inner face, so
    # LID_THICKNESS must not be counted again in the vertical offset.
    sma_center_x = outer_l - gps['sma_center_x']
    axis_below_lid_inner_face = (
        GPS_BACK_COMPONENT_DEPTH + GPS_FIT_CLEARANCE
        + GPS_BOARD_THICKNESS / 2
    )
    sma_center_z = outer_h - axis_below_lid_inner_face
    rear_wall_hole(
        comp, target_body, 'GPS SMA hole', sma_center_x, sma_center_z,
        outer_w - WALL / 2, SMA_HOLE_DIAMETER, WALL + 2.0,
    )
    recess_depth = WALL - SMA_LOCAL_WALL
    rear_wall_hole(
        comp, target_body, 'GPS SMA outside recess',
        sma_center_x, sma_center_z,
        outer_w - recess_depth / 2, SMA_RECESS_DIAMETER,
        recess_depth + 0.2,
    )


def cut_opening(comp, target_body, opening, x_offset, z_floor, z_ceiling):
    """Cut one wall aperture into a part, clipped to that part's z range.

    An opening flagged open_bottom starts at the parting plane, which is the
    bottom face of the shell, so it is cut as a notch that reaches below the
    part and leaves nothing under the connector.
    """
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    z_start = opening['z']
    z_end = z_start + opening['height']
    if opening.get('open_bottom'):
        z_start -= 1.0
    z_start = max(z_start, z_floor - 1.0)
    z_end = min(z_end, z_ceiling + 1.0)
    if z_end <= z_start:
        return
    height = z_end - z_start

    if opening['wall'] == 'front':
        rect = (x_offset + opening['start'], -1.0, opening['span'], WALL + 2.0)
    elif opening['wall'] == 'right':
        rect = (x_offset + outer_l - WALL - 1.0, opening['start'],
                WALL + 2.0, opening['span'])
    elif opening['wall'] == 'rear':
        rect = (x_offset + opening['start'], outer_w - WALL - 1.0,
                opening['span'], WALL + 2.0)
    else:
        rect = (x_offset - 1.0, opening['start'], WALL + 2.0, opening['span'])

    rectangle_feature(
        comp, opening['name'], rect[0], rect[1], z_start,
        rect[2], rect[3], height,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
        [target_body],
    )


def base_plate(comp, x_offset=0):
    """Bottom part: floor, standoffs, the pocket that locates the board, and
    the four snap tabs that the shell latches onto.

    Its wall stops at the parting plane, which is the top face of the PCB, so
    no connector ever meets it.
    """
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL

    base_feature = rectangle_feature(
        comp, 'Base outer body', x_offset, 0, 0, outer_l, outer_w, PARTING_Z)
    base_body = base_feature.bodies.item(0)
    rectangle_feature(
        comp, 'Base pocket', x_offset + WALL, WALL, FLOOR,
        CASE_INNER_LENGTH, CASE_INNER_WIDTH, PARTING_Z - FLOOR + 1.0,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
        [base_body],
    )

    pi = pi_layout()
    holes = [
        (pi['mount_x'], pi['mount_y']),
        (pi['mount_x'] + PI_MOUNT_X, pi['mount_y']),
        (pi['mount_x'], pi['mount_y'] + PI_MOUNT_Y),
        (pi['mount_x'] + PI_MOUNT_X, pi['mount_y'] + PI_MOUNT_Y),
    ]
    for index, (x, y) in enumerate(holes, 1):
        cylinder_feature(comp, f'Pi standoff {index}', x_offset + x, y, FLOOR,
                         PI_STANDOFF_DIAMETER, PI_STANDOFF_HEIGHT)

    for opening in pi_io_openings():
        if opening.get('part') != 'base':
            continue
        cut_opening(comp, base_body, opening, x_offset, FLOOR, PARTING_Z)

    # Snap tabs. The arm is the inner slice of the wall carried above the
    # parting plane; the bump near its tip engages a pocket in the shell.
    z = tab_bump_z()
    for index, tab in enumerate(base_tab_layout(x_offset), 1):
        arm = tab['arm']
        rectangle_feature(
            comp, f"Base snap tab {index} {tab['wall']}",
            arm[0], arm[1], PARTING_Z - JOIN_OVERLAP, arm[2], arm[3],
            BASE_TAB_HEIGHT + JOIN_OVERLAP,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)
        bump = tab['bump']
        rectangle_feature(
            comp, f"Base snap tab {index} bump",
            bump[0], bump[1], z['bump_z'], bump[2], bump[3], z['bump_height'],
            adsk.fusion.FeatureOperations.JoinFeatureOperation)
    return base_body


def shell(comp, x_offset=0, height_limit=None):
    """Top part: everything above the top face of the PCB.

    Carries the I/O openings, which are open at the bottom so the connectors
    enter from below, the pads that press the board down, the slots for the
    base tabs, the lid seat and the SMA hole.

    height_limit truncates the part for a test print. Everything that decides
    whether the board fits lives in the bottom 16.4 mm; the lid seat and the
    SMA hole above it are geometry that a previous print already proved.
    """
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    outer_h = CASE_INNER_HEIGHT + FLOOR
    full_height = outer_h - PARTING_Z
    shell_height = full_height if height_limit is None else height_limit
    truncated = height_limit is not None

    outer_feature = rectangle_feature(
        comp, 'Shell outer body', x_offset, 0, PARTING_Z,
        outer_l, outer_w, shell_height)
    shell_body = outer_feature.bodies.item(0)

    rectangle_feature(
        comp, 'Shell cavity', x_offset + WALL, WALL, PARTING_Z,
        CASE_INNER_LENGTH, CASE_INNER_WIDTH, shell_height + 1.0,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
        [shell_body],
    )

    # Slots and bump pockets for the base tabs.
    z = tab_bump_z()
    for index, tab in enumerate(base_tab_layout(x_offset), 1):
        slot = tab['slot']
        rectangle_feature(
            comp, f'Shell tab slot {index}', slot[0], slot[1],
            PARTING_Z - 1.0, slot[2], slot[3], z['slot_height'] + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            [shell_body],
        )
        pocket = tab['pocket']
        rectangle_feature(
            comp, f'Shell tab pocket {index}', pocket[0], pocket[1],
            z['pocket_z'], pocket[2], pocket[3], z['pocket_height'],
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            [shell_body],
        )

    # Pads that trap the board against the standoffs.
    for name, rect, pad_z, pad_height in pi_pad_layout(x_offset):
        rectangle_feature(
            comp, name, rect[0], rect[1], pad_z, rect[2], rect[3], pad_height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Every connector opening, open at the bottom edge of this part.
    for opening in pi_io_openings():
        if opening.get('part') != 'shell':
            continue
        cut_opening(comp, shell_body, opening, x_offset, PARTING_Z, outer_h)

    if truncated:
        return shell_body

    # Latch pockets for the lid rim bumps. Without these the bumps would jam
    # against the wall and the lid could not close at all.
    latches = lid_latch_positions(x_offset)
    for x in latches['x_positions']:
        rectangle_feature(
            comp, 'Lid latch pocket front', x, WALL - LID_LATCH_DEPTH,
            latches['z'], LID_LATCH_LENGTH, LID_LATCH_DEPTH,
            LID_LATCH_HEIGHT + LID_LATCH_LEAD_IN,
            adsk.fusion.FeatureOperations.CutFeatureOperation)
        rectangle_feature(
            comp, 'Lid latch pocket rear', x, outer_w - WALL,
            latches['z'], LID_LATCH_LENGTH, LID_LATCH_DEPTH,
            LID_LATCH_HEIGHT + LID_LATCH_LEAD_IN,
            adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Round rear-wall hole aligned with the assembled SMA axis. A shallow
    # circular counterbore leaves 2 mm of local wall so an antenna that stops
    # 3 mm from the SMA base can still tighten completely.
    gps_sma_wall_features(comp, shell_body, outer_l, outer_w, outer_h)
    return shell_body


def lid(comp, x_offset=0):
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    lid_feature = rectangle_feature(
        comp, 'Lid', x_offset, 0, 0, outer_l, outer_w, LID_THICKNESS)
    lid_body = lid_feature.bodies.item(0)

    # Continuous locating rim. LID_RIM_CLEARANCE is the only gap to the cavity
    # wall, so the latch bumps actually engage instead of rattling.
    inset = WALL + LID_RIM_CLEARANCE
    rim_inner_l = CASE_INNER_LENGTH - 2 * LID_RIM_CLEARANCE
    rim_inner_w = CASE_INNER_WIDTH - 2 * LID_RIM_CLEARANCE
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    cradle_gap_start = gps['x'] - GPS_FIT_CLEARANCE - GPS_CLIP_THICKNESS - 1.0
    cradle_gap_end = (gps['x'] + GPS_BOARD_WIDTH + GPS_FIT_CLEARANCE
                      + GPS_CLIP_THICKNESS + 1.0)
    rear_y = outer_w - inset - LID_RIM_THICKNESS

    rectangle_feature(comp, 'Lid rim front', x_offset + inset, inset,
                      LID_THICKNESS, rim_inner_l, LID_RIM_THICKNESS,
                      LID_RIM_HEIGHT,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim rear left', x_offset + inset, rear_y,
                      LID_THICKNESS, cradle_gap_start - (x_offset + inset),
                      LID_RIM_THICKNESS, LID_RIM_HEIGHT,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim rear right', cradle_gap_end, rear_y,
                      LID_THICKNESS,
                      x_offset + inset + rim_inner_l - cradle_gap_end,
                      LID_RIM_THICKNESS, LID_RIM_HEIGHT,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim left', x_offset + inset, inset,
                      LID_THICKNESS, LID_RIM_THICKNESS, rim_inner_w,
                      LID_RIM_HEIGHT,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim right',
                      x_offset + inset + rim_inner_l - LID_RIM_THICKNESS, inset,
                      LID_THICKNESS, LID_RIM_THICKNESS, rim_inner_w,
                      LID_RIM_HEIGHT,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Latch bumps on the outer face of the rim. They ride over the wall and
    # drop into the pockets cut in the case.
    latch_z = LID_THICKNESS + LID_RIM_HEIGHT - LID_LATCH_BELOW_TOP
    for x in lid_latch_positions(x_offset)['x_positions']:
        rectangle_feature(
            comp, 'Lid latch bump front', x, inset - LID_LATCH_DEPTH, latch_z,
            LID_LATCH_LENGTH, LID_LATCH_DEPTH, LID_LATCH_HEIGHT,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)
        rectangle_feature(
            comp, 'Lid latch bump rear', x, rear_y + LID_RIM_THICKNESS,
            latch_z, LID_LATCH_LENGTH, LID_LATCH_DEPTH, LID_LATCH_HEIGHT,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # GPS cradle on the inside of the lid. The full component-free perimeter
    # supports the PCB, including a rear crossbar directly below the SMA load.
    # The five right-angle pins and their cable path remain open.
    gps_x = gps['x']
    gps_y = gps['y']
    board_z = LID_THICKNESS + GPS_BACK_COMPONENT_DEPTH + GPS_FIT_CLEARANCE
    rail_x_left = gps_x - GPS_FIT_CLEARANCE - GPS_CLIP_THICKNESS
    rail_x_right = gps_x + GPS_BOARD_WIDTH + GPS_FIT_CLEARANCE
    rail_y = gps_y + 1.0
    rail_length = GPS_BOARD_LENGTH - 2.0
    support_h = board_z - LID_THICKNESS
    rail_h = support_h + GPS_BOARD_THICKNESS + 0.8
    rectangle_feature(comp, 'GPS left edge support', gps_x, rail_y,
                      LID_THICKNESS, GPS_EDGE_SUPPORT_WIDTH, rail_length,
                      support_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS right edge support',
                      gps_x + GPS_BOARD_WIDTH - GPS_EDGE_SUPPORT_WIDTH, rail_y,
                      LID_THICKNESS, GPS_EDGE_SUPPORT_WIDTH, rail_length,
                      support_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS rear edge support', gps_x,
                      gps['rear_y'] - GPS_EDGE_SUPPORT_WIDTH, LID_THICKNESS,
                      GPS_BOARD_WIDTH, GPS_EDGE_SUPPORT_WIDTH, support_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS left rail', rail_x_left, rail_y, LID_THICKNESS,
                      GPS_CLIP_THICKNESS, rail_length, rail_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS right rail', rail_x_right, rail_y, LID_THICKNESS,
                      GPS_CLIP_THICKNESS, rail_length, rail_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Tiny corner latches stay outside the centred five-pin bank. The entire
    # front edge between them is open for the 8 mm pins and Dupont leads.
    stop_width = GPS_EDGE_SUPPORT_WIDTH
    stop_h = support_h + GPS_BOARD_THICKNESS + 0.5
    front_stop_y = gps_y - GPS_CLIP_THICKNESS
    rectangle_feature(comp, 'GPS front stop left', gps_x, front_stop_y,
                      LID_THICKNESS, stop_width, GPS_CLIP_THICKNESS, stop_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS front stop right',
                      gps_x + GPS_BOARD_WIDTH - stop_width, front_stop_y,
                      LID_THICKNESS, stop_width, GPS_CLIP_THICKNESS, stop_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # The rear lips clamp close to the loaded edge. The right lip stays ahead
    # of the 7 mm SMA base instead of overlapping it as the old one did.
    lip_z = board_z + GPS_BOARD_THICKNESS + GPS_FIT_CLEARANCE
    lip_width = GPS_CLIP_THICKNESS + GPS_FIT_CLEARANCE + GPS_CLIP_OVERHANG
    for position, clip_y in (('front', gps_y + 3.0),
                             ('rear', gps['rear_y'] - SMA_BASE_LENGTH
                              - GPS_FIT_CLEARANCE - GPS_CLIP_LENGTH)):
        rectangle_feature(comp, f'GPS {position} clip left', rail_x_left, clip_y,
                          lip_z, lip_width, GPS_CLIP_LENGTH, 1.0,
                          adsk.fusion.FeatureOperations.JoinFeatureOperation)
        rectangle_feature(comp, f'GPS {position} clip right',
                          gps_x + GPS_BOARD_WIDTH - GPS_CLIP_OVERHANG, clip_y,
                          lip_z, lip_width, GPS_CLIP_LENGTH, 1.0,
                          adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Raspberry-shaped ventilation. Two combined cuts keep Fusion rebuilds
    # fast and leave solid bridges between 18 berry and six leaf openings.
    vent_circles, vent_leaves, _ = raspberry_vent_layout(
        outer_l, outer_w, x_offset)
    circle_vent_feature(
        comp, lid_body, 'Raspberry berry vents', vent_circles,
        LID_THICKNESS + 1.0,
    )
    ellipse_vent_feature(
        comp, lid_body, 'Raspberry leaf vents', vent_leaves,
        LID_THICKNESS + 1.0,
    )


def gps_reference(comp, x_offset=0):
    """Add one removable GPS body with component, SMA, and bent-pin envelopes."""
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    board_z = LID_THICKNESS + GPS_BACK_COMPONENT_DEPTH + GPS_FIT_CLEARANCE

    pcb_feature = rectangle_feature(
        comp, 'GPS reference PCB', gps['x'], gps['y'], board_z,
        GPS_BOARD_WIDTH, GPS_BOARD_LENGTH, GPS_BOARD_THICKNESS,
    )
    gps_body = pcb_feature.bodies.item(0)
    gps_body.name = 'GPS module - removable fit reference'
    rectangle_feature(
        comp, 'GPS reference component keepout',
        gps['x'] + GPS_COMPONENT_KEEPOUT_INSET,
        gps['y'] + GPS_COMPONENT_KEEPOUT_INSET,
        board_z - GPS_BACK_COMPONENT_DEPTH,
        GPS_BOARD_WIDTH - 2 * GPS_COMPONENT_KEEPOUT_INSET,
        GPS_BOARD_LENGTH - 2 * GPS_COMPONENT_KEEPOUT_INSET,
        GPS_MODULE_DEPTH,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
        [gps_body],
    )
    rectangle_feature(
        comp, 'GPS reference SMA base', gps['x'] + GPS_BOARD_WIDTH - SMA_BASE_WIDTH,
        gps['rear_y'] - SMA_BASE_LENGTH, board_z + GPS_BOARD_THICKNESS,
        SMA_BASE_WIDTH, SMA_BASE_LENGTH, SMA_BASE_DEPTH,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
        [gps_body],
    )
    rectangle_feature(
        comp, 'GPS reference SMA thread',
        gps['sma_center_x'] - SMA_THREAD_DIAMETER / 2, gps['rear_y'],
        board_z + GPS_BOARD_THICKNESS / 2 - SMA_THREAD_DIAMETER / 2,
        SMA_THREAD_DIAMETER, SMA_PROJECTION, SMA_THREAD_DIAMETER,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
        [gps_body],
    )
    pin_bank_width = (GPS_PIN_COUNT - 1) * GPS_PIN_PITCH
    first_pin_x = gps['center_x'] - pin_bank_width / 2
    for index in range(GPS_PIN_COUNT):
        pin_x = first_pin_x + index * GPS_PIN_PITCH - GPS_PIN_WIDTH / 2
        # Each header pin first projects 5 mm away from the PCB face, then
        # bends 90 degrees and drops 8 mm beyond the front PCB edge.
        rectangle_feature(
            comp, f'GPS reference pin {index + 1} forward',
            pin_x, gps['y'] - GPS_PIN_WIDTH / 2,
            board_z + GPS_BOARD_THICKNESS - GPS_JOIN_OVERLAP,
            GPS_PIN_WIDTH, GPS_PIN_WIDTH,
            GPS_PIN_FORWARD + GPS_JOIN_OVERLAP,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            [gps_body],
        )
        rectangle_feature(
            comp, f'GPS reference pin {index + 1} drop',
            pin_x, gps['y'] - GPS_PIN_DROP,
            board_z + GPS_BOARD_THICKNESS + GPS_PIN_FORWARD - GPS_PIN_WIDTH,
            GPS_PIN_WIDTH, GPS_PIN_DROP + GPS_PIN_WIDTH / 2,
            GPS_PIN_WIDTH,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            [gps_body],
        )


def pi_reference(comp):
    """Add one removable Raspberry Pi 4 body to check fit inside the case.

    The board sits exactly where the standoffs and clips put it, and every
    connector is placed with the same rotation used for the wall openings, so
    if a connector does not line up here it will not line up in plastic. The
    GPIO header is a plain block: it exists to show the volume the ribbon and
    the GPS wiring have to share, not to model individual pins.
    """
    pi = pi_layout()
    board_feature = rectangle_feature(
        comp, 'Pi reference PCB', pi['x'], pi['y'], pi['bottom_z'],
        PI_BOARD_LENGTH, PI_BOARD_WIDTH, PI_BOARD_THICKNESS,
    )
    pi_body = board_feature.bodies.item(0)
    pi_body.name = 'Raspberry Pi 4 - removable fit reference'

    top = pi['bottom_z'] + PI_BOARD_THICKNESS

    for name, source_x, width, height in PI_FRONT_CONNECTORS:
        x = pi['x'] + PI_BOARD_LENGTH - source_x - width
        rectangle_feature(
            comp, f'Pi reference {name.replace(" opening", "")}',
            x, pi['y'] - PI_CONNECTOR_PROUD, top,
            width, PI_CONNECTOR_PROUD + width / 3, height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            [pi_body],
        )

    for name, source_y, width, height in PI_RIGHT_CONNECTORS:
        y = pi['y'] + PI_BOARD_WIDTH - source_y - width
        depth = 21.0 if 'USB' in name else 21.3
        rectangle_feature(
            comp, f'Pi reference {name.replace(" opening", "")}',
            pi['x'] + PI_BOARD_LENGTH + PI_CONNECTOR_PROUD - depth, y, top,
            depth, width, height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            [pi_body],
        )

    rectangle_feature(
        comp, 'Pi reference GPIO header',
        pi['x'] + PI_GPIO_FIRST_PIN,
        pi['y'] + PI_BOARD_WIDTH - PI_GPIO_EDGE_OFFSET - PI_GPIO_WIDTH / 2,
        top, PI_GPIO_LENGTH, PI_GPIO_WIDTH, PI_GPIO_HEIGHT,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
        [pi_body],
    )

    microsd_y = (pi['y'] + PI_BOARD_WIDTH - PI_MICROSD_Y
                 - PI_MICROSD_WIDTH)
    rectangle_feature(
        comp, 'Pi reference microSD card', pi['x'] - 4.0, microsd_y,
        pi['bottom_z'] - 1.2, 15.0, PI_MICROSD_WIDTH, 1.2,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
        [pi_body],
    )


def test_collar_height():
    """Shell height a test print needs to cover every opening and every tab."""
    opening_top = max(o['z'] + o['height'] for o in pi_io_openings())
    tab_top = PARTING_Z + tab_bump_z()['slot_height']
    return max(opening_top, tab_top) - PARTING_Z + 1.0


def test_print(root):
    """Base plus a truncated shell: the cheap way to find out whether the
    board actually goes in, before committing to the full part.

    Call this from run() instead of the real parts. It exercises the pocket,
    the standoffs, all four snap tabs, all four press pads and every connector
    opening, and leaves out only the lid seat and the SMA hole.
    """
    base_plate(root, 0.0)
    shell(root, 110.0, height_limit=test_collar_height())
    pi_reference(root)


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        if not isinstance(design, adsk.fusion.Design):
            ui.messageBox('Open or create a Fusion 360 Design before running the script.')
            return

        root = design.rootComponent
        # The shell must stay at the origin: the SMA hole is derived from the
        # unshifted cradle layout.
        shell(root)
        lid(root, 110.0)
        gps_reference(root, 110.0)
        base_plate(root, 230.0)
        pi_reference(root)
        app.activeViewport.fit()
        ui.messageBox('Case generated. Three printed parts: shell, lid and '
                      'base plate. Body 4 is the removable GPS reference and '
                      'body 5 the removable Raspberry Pi 4 reference. '
                      'Hide or delete either one to inspect the case.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

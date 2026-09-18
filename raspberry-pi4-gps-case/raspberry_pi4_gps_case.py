import adsk.core
import adsk.fusion
import traceback


# ---------------------------------------------------------------------------
# Raspberry Pi 4 Model B, official mechanical drawing.
# Datum: PCB corner on the micro-USB-C side of the connector long edge.
# ---------------------------------------------------------------------------
# 0.4 mm of side clearance locates the board laterally on its own, so no pegs
# are needed in the mounting holes.
PI_SIDE_CLEARANCE = 0.4
PI_STANDOFF_HEIGHT = 3.0
PI_STANDOFF_DIAMETER = 5.0

# Screwless PCB retention: the board drops straight down and snaps past four
# flexible clips, one per free stretch of board edge.
#
# The previous revision used two rigid lips on the rear wall and a tilt-in
# assembly. It could not work, for two independent reasons:
#   * the lips overhung the board by PI_LIP_OVERHANG = 1.2 mm, but the rear
#     clearance is only PI_SIDE_CLEARANCE = 0.4 mm, so the board could never
#     slide far enough back to get under them;
#   * the left lip sat at x 12..26 mm, straight on top of the 8.5 mm tall GPIO
#     header, which starts 0.95 mm in from the rear edge.
# Dropping the board in vertically removes the slide entirely, so no feature
# needs more lateral room than the printing clearance.
#
# The arm is recessed into the wall with a blind relief slot behind it, so the
# outside of the case stays flat. It is rooted at the floor rather than at
# board level: a 7 mm cantilever keeps the bending strain near 2 per cent,
# where a 4 mm one reached 10 and would crack even in PETG.
PI_CLIP_THICKNESS = 1.1
PI_CLIP_LENGTH = 14.0
PI_CLIP_RELIEF = 0.8
PI_CLIP_OVERHANG = 0.6
PI_CLIP_EDGE_GAP = 0.2
PI_CLIP_LEAD_IN = 1.2
PI_CLIP_POCKET_MARGIN = 1.0
# The lead-in is a 45 degree ramp above the retaining face, so the descending
# board pushes the clips aside on its own instead of needing a fingernail. It
# is printed as a short staircase: at 0.2 mm layers a real chamfer comes out as
# steps anyway, and a staircase needs no chamfer feature to survive a rebuild.
PI_CLIP_LEAD_IN_STEPS = 4

# Clip placement, as the offset of the arm's near end from the board corner
# along the wall it sits on. Every entry is checked by fit_check.py against the
# connector and header keep-outs; see PI_EDGE_KEEPOUTS.
PI_CLIPS = (
    ('front', 61.0),
    ('left', 3.0),
    ('left', 40.0),
    ('rear', 59.0),
)

# Strips of board edge that a clip hook must not overhang, as
# (wall, start, end) in millimetres from the board corner along that wall.
# Derived from the connector table below and from the GPIO header footprint;
# fit_check.py rebuilds them rather than trusting these numbers blindly.
PI_HOOK_EDGE_MARGIN = 1.0

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
GPS_FIT_CLEARANCE = 0.3
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
GPS_CLIP_THICKNESS = 1.6
GPS_CLIP_LENGTH = 5.0
GPS_CLIP_OVERHANG = 1.0
GPS_EDGE_SUPPORT_WIDTH = 0.8
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
# Connector bodies stand this far proud of the PCB edge, and the GPIO header
# is modelled as a plain 2x20 block. Reference geometry only.
PI_CONNECTOR_PROUD = 2.0
PI_GPIO_LENGTH = 50.8
PI_GPIO_WIDTH = 5.1
PI_GPIO_HEIGHT = 8.5
PI_GPIO_EDGE_OFFSET = 3.5
PI_GPIO_FIRST_PIN = 3.5
PI_MICROSD_Y = 22.4
PI_MICROSD_WIDTH = 11.11
PI_MICROSD_ACCESS_WIDTH = 18.0
PI_MICROSD_OPENING_HEIGHT = 8.0

# A square lattice gives the lid broad passive ventilation while keeping
# printable 2 mm ribs and a solid load path around the locating rim and GPS.
LID_MESH_EDGE_MARGIN = 6.0
LID_MESH_OPENING = 7.0
LID_MESH_PITCH = 9.0
LID_MESH_GPS_MARGIN = 2.0


# ---------------------------------------------------------------------------
WALL = 2.5
FLOOR = 2.5
CASE_INNER_LENGTH = PI_BOARD_LENGTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_WIDTH = PI_BOARD_WIDTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_HEIGHT = 29.0
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


def rectangle_mesh_feature(comp, target_body, name, rectangles, height):
    """Cut many rectangular mesh cells in one sketch/extrude operation."""
    sketch = comp.sketches.add(comp.xYConstructionPlane)
    sketch.name = name
    lines = sketch.sketchCurves.sketchLines
    for x, y, length, width in rectangles:
        lines.addTwoPointRectangle(
            adsk.core.Point3D.create(cm(x), cm(y), 0),
            adsk.core.Point3D.create(cm(x + length), cm(y + width), 0),
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
    """Derive all Pi 4 wall apertures from the common assembled board datum."""
    pi = pi_layout()
    opening_z = pi['top_z'] - PI_IO_CLEARANCE
    openings = []

    for name, source_x, connector_width, connector_height in PI_FRONT_CONNECTORS:
        rotated_x = pi['x'] + PI_BOARD_LENGTH - source_x - connector_width
        openings.append({
            'name': name,
            'wall': 'front',
            'start': rotated_x - PI_IO_CLEARANCE,
            'span': connector_width + 2 * PI_IO_CLEARANCE,
            'z': opening_z,
            'height': connector_height + 2 * PI_IO_CLEARANCE,
        })

    for name, source_y, connector_width, connector_height in PI_RIGHT_CONNECTORS:
        rotated_y = pi['y'] + PI_BOARD_WIDTH - source_y - connector_width
        openings.append({
            'name': name,
            'wall': 'right',
            'start': rotated_y - PI_IO_CLEARANCE,
            'span': connector_width + 2 * PI_IO_CLEARANCE,
            'z': opening_z,
            'height': connector_height + 2 * PI_IO_CLEARANCE,
        })

    microsd_center_y = (
        pi['y'] + PI_BOARD_WIDTH
        - PI_MICROSD_Y - PI_MICROSD_WIDTH / 2
    )
    openings.append({
        'name': 'MicroSD opening',
        'wall': 'left',
        'start': microsd_center_y - PI_MICROSD_ACCESS_WIDTH / 2,
        'span': PI_MICROSD_ACCESS_WIDTH,
        'z': pi['bottom_z'] - FLOOR,
        'height': PI_MICROSD_OPENING_HEIGHT,
    })
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
            (x, pi['y'] - PI_CONNECTOR_PROUD,
             width, PI_CONNECTOR_PROUD + width / 3),
            height,
        ))

    for name, source_y, width, height in PI_RIGHT_CONNECTORS:
        y = pi['y'] + PI_BOARD_WIDTH - source_y - width
        depth = 21.0 if 'USB' in name else 21.3
        parts.append((
            name.replace(' opening', ''),
            (pi['x'] + PI_BOARD_LENGTH + PI_CONNECTOR_PROUD - depth, y,
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


def lid_mesh_layout(outer_l, outer_w, x_offset=0):
    """Return printable square mesh cells, excluding the GPS cradle zone."""
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    gps_keepout = (
        gps['x'] - GPS_FIT_CLEARANCE - GPS_CLIP_THICKNESS
        - LID_MESH_GPS_MARGIN,
        gps['y'] - GPS_CLIP_THICKNESS - LID_MESH_GPS_MARGIN,
        GPS_BOARD_WIDTH + 2 * (
            GPS_FIT_CLEARANCE + GPS_CLIP_THICKNESS + LID_MESH_GPS_MARGIN),
        GPS_BOARD_LENGTH + GPS_CLIP_THICKNESS + 2 * LID_MESH_GPS_MARGIN,
    )
    cells = []
    y = LID_MESH_EDGE_MARGIN
    while y + LID_MESH_OPENING <= outer_w - LID_MESH_EDGE_MARGIN:
        x = x_offset + LID_MESH_EDGE_MARGIN
        while x + LID_MESH_OPENING <= x_offset + outer_l - LID_MESH_EDGE_MARGIN:
            cell = (x, y, LID_MESH_OPENING, LID_MESH_OPENING)
            if not rectangles_overlap(cell, gps_keepout):
                cells.append(cell)
            x += LID_MESH_PITCH
        y += LID_MESH_PITCH
    return cells, gps_keepout


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


def pi_clip_layout():
    """Return the relief, arm and hook rectangles of every retention clip.

    Pure geometry, no Fusion calls, so fit_check.py can audit the result
    against the connector and header keep-outs without opening Fusion.
    Rectangles are (x, y, length, width) in case coordinates.
    """
    pi = pi_layout()
    board_rear_y = pi['y'] + PI_BOARD_WIDTH
    front_arm_y = pi['y'] - PI_CLIP_EDGE_GAP - PI_CLIP_THICKNESS
    rear_arm_y = board_rear_y + PI_CLIP_EDGE_GAP
    left_arm_x = pi['x'] - PI_CLIP_EDGE_GAP - PI_CLIP_THICKNESS
    margin = PI_CLIP_POCKET_MARGIN
    reach = PI_CLIP_OVERHANG + PI_CLIP_EDGE_GAP

    clips = []
    for wall, offset in PI_CLIPS:
        if wall == 'front':
            start = pi['x'] + offset
            relief = (start - margin, front_arm_y - PI_CLIP_RELIEF,
                      PI_CLIP_LENGTH + 2 * margin, PI_CLIP_RELIEF)
            arm = (start, front_arm_y, PI_CLIP_LENGTH, PI_CLIP_THICKNESS)
            hook = (start, front_arm_y + PI_CLIP_THICKNESS,
                    PI_CLIP_LENGTH, reach)
        elif wall == 'rear':
            start = pi['x'] + offset
            relief = (start - margin, rear_arm_y + PI_CLIP_THICKNESS,
                      PI_CLIP_LENGTH + 2 * margin, PI_CLIP_RELIEF)
            arm = (start, rear_arm_y, PI_CLIP_LENGTH, PI_CLIP_THICKNESS)
            hook = (start, rear_arm_y - reach, PI_CLIP_LENGTH, reach)
        else:
            start = pi['y'] + offset
            relief = (left_arm_x - PI_CLIP_RELIEF, start - margin,
                      PI_CLIP_RELIEF, PI_CLIP_LENGTH + 2 * margin)
            arm = (left_arm_x, start, PI_CLIP_THICKNESS, PI_CLIP_LENGTH)
            hook = (left_arm_x + PI_CLIP_THICKNESS, start,
                    reach, PI_CLIP_LENGTH)
        clips.append({'wall': wall, 'offset': offset, 'start': start,
                      'relief': relief, 'arm': arm, 'hook': hook})
    return clips


def pi_clip_lead_in_slices(clip, board_top):
    """Stair-stepped 45 degree ramp sitting on top of one hook.

    Slice 0 is the full hook at board level, the last slice is nearly flush
    with the arm, so the board only ever meets sloped material on the way in.
    """
    x, y, length, width = clip['hook']
    reach = PI_CLIP_OVERHANG + PI_CLIP_EDGE_GAP
    step_height = PI_CLIP_LEAD_IN / PI_CLIP_LEAD_IN_STEPS
    slices = []
    for step in range(PI_CLIP_LEAD_IN_STEPS):
        depth = reach * (PI_CLIP_LEAD_IN_STEPS - step) / PI_CLIP_LEAD_IN_STEPS
        if clip['wall'] == 'front':
            rect = (x, y, length, depth)
        elif clip['wall'] == 'rear':
            rect = (x, y + width - depth, length, depth)
        else:
            rect = (x, y, depth, width)
        slices.append((rect, board_top + step * step_height, step_height))
    return slices


def pi_retention(comp):
    """Screwless retention: drop the board in, four clips snap over its edges.

    Assembly: lower the board onto the standoffs. Each clip is met by its
    45 degree lead-in, springs outward, and snaps back over the PCB.
    Removal: push the four clips outward and lift.

    The previous revision slid the GPIO edge under two rigid lips on the rear
    wall. That could not be assembled: the lips reached 1.2 mm over the board
    while the rear gap is only 0.4 mm, and the left lip landed on top of the
    8.5 mm GPIO header. Dropping the board in vertically removes the slide, so
    no feature needs more room than the printing clearance.

    Placement is forced by the I/O and by the header. Free stretches of board
    edge: the front wall past the audio jack, the left wall on either side of
    the microSD slot, and the rear wall past the end of the GPIO header. The
    right wall is solid USB and Ethernet and takes nothing. fit_check.py
    verifies all four against the keep-outs.

    Nothing sits in the mounting holes: pegs cannot deflect enough to let the
    board pass, and they would fight the clips.
    """
    pi = pi_layout()
    holes = [
        (pi['mount_x'], pi['mount_y']),
        (pi['mount_x'] + PI_MOUNT_X, pi['mount_y']),
        (pi['mount_x'], pi['mount_y'] + PI_MOUNT_Y),
        (pi['mount_x'] + PI_MOUNT_X, pi['mount_y'] + PI_MOUNT_Y),
    ]
    for index, (x, y) in enumerate(holes, 1):
        cylinder_feature(comp, f'Pi standoff {index}', x, y, FLOOR,
                         PI_STANDOFF_DIAMETER, PI_STANDOFF_HEIGHT)

    board_top = pi['bottom_z'] + PI_BOARD_THICKNESS

    # Rooted on the floor so the cantilever is long enough to bend safely.
    arm_height = (pi['bottom_z'] - FLOOR + PI_BOARD_THICKNESS
                  + PI_CLIP_LEAD_IN + 1.2)
    for index, clip in enumerate(pi_clip_layout(), 1):
        tag = f"{clip['wall']} {index}"
        relief, arm = clip['relief'], clip['arm']
        rectangle_feature(
            comp, f'Pi clip relief {tag}', relief[0], relief[1],
            FLOOR, relief[2], relief[3], arm_height + PI_CLIP_LEAD_IN,
            adsk.fusion.FeatureOperations.CutFeatureOperation)
        rectangle_feature(
            comp, f'Pi clip arm {tag}', arm[0], arm[1], FLOOR,
            arm[2], arm[3], arm_height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)
        for step, (rect, z, height) in enumerate(
                pi_clip_lead_in_slices(clip, board_top), 1):
            rectangle_feature(
                comp, f'Pi clip hook {tag} step {step}', rect[0], rect[1], z,
                rect[2], rect[3], height,
                adsk.fusion.FeatureOperations.JoinFeatureOperation)


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


def body_shell(comp):
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    outer_h = CASE_INNER_HEIGHT + FLOOR

    outer_feature = rectangle_feature(
        comp, 'Case outer body', 0, 0, 0, outer_l, outer_w, outer_h)
    case_body = outer_feature.bodies.item(0)
    rectangle_feature(
        comp, 'Case cavity', WALL, WALL, FLOOR,
        CASE_INNER_LENGTH, CASE_INNER_WIDTH, CASE_INNER_HEIGHT + 1,
        adsk.fusion.FeatureOperations.CutFeatureOperation
    )

    # Pi 4 mounting posts: official 58 x 49 mm pattern, with print clearance.
    pi_retention(comp)

    # Derive every wall opening from the same assembled Pi board datum.
    for opening in pi_io_openings():
        if opening['wall'] == 'front':
            rectangle_feature(
                comp, opening['name'], opening['start'], -1.0, opening['z'],
                opening['span'], WALL + 2.0, opening['height'],
                adsk.fusion.FeatureOperations.CutFeatureOperation,
                [case_body],
            )
        elif opening['wall'] == 'right':
            rectangle_feature(
                comp, opening['name'], outer_l - WALL - 1.0,
                opening['start'], opening['z'], WALL + 2.0,
                opening['span'], opening['height'],
                adsk.fusion.FeatureOperations.CutFeatureOperation,
                [case_body],
            )
        else:
            rectangle_feature(
                comp, opening['name'], -1.0, opening['start'], opening['z'],
                WALL + 2.0, opening['span'], opening['height'],
                adsk.fusion.FeatureOperations.CutFeatureOperation,
                [case_body],
            )

    # Latch pockets for the lid rim bumps. Without these the bumps would jam
    # against the wall and the lid could not close at all.
    latches = lid_latch_positions()
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
    gps_sma_wall_features(comp, case_body, outer_l, outer_w, outer_h)


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

    # GPS cradle on the inside of the lid. Narrow ledges support only the free
    # PCB edges and lift the shield clear of the lid. The five right-angle pins
    # and their cable path remain fully open toward the case interior.
    gps_x = gps['x']
    gps_y = gps['y']
    board_z = LID_THICKNESS + GPS_BACK_COMPONENT_DEPTH + GPS_FIT_CLEARANCE
    rail_x_left = gps_x - GPS_FIT_CLEARANCE - GPS_CLIP_THICKNESS
    rail_x_right = gps_x + GPS_BOARD_WIDTH + GPS_FIT_CLEARANCE
    rail_y = gps_y + 2.0
    rail_length = GPS_BOARD_LENGTH - 4.0
    support_h = board_z - LID_THICKNESS
    rail_h = support_h + GPS_BOARD_THICKNESS + 0.8
    rectangle_feature(comp, 'GPS left edge support', gps_x, rail_y,
                      LID_THICKNESS, GPS_EDGE_SUPPORT_WIDTH, rail_length,
                      support_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS right edge support',
                      gps_x + GPS_BOARD_WIDTH - GPS_EDGE_SUPPORT_WIDTH, rail_y,
                      LID_THICKNESS, GPS_EDGE_SUPPORT_WIDTH, rail_length,
                      support_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)
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

    # The rear PCB edge and SMA base sit directly against the inside wall, so
    # no printed rear stop is needed and no stop can collide with the SMA.
    lip_z = board_z + GPS_BOARD_THICKNESS + GPS_FIT_CLEARANCE
    lip_width = GPS_CLIP_THICKNESS + GPS_FIT_CLEARANCE + GPS_CLIP_OVERHANG
    for position, clip_y in (('front', gps_y + 4.0),
                             ('rear', gps['rear_y'] - 4.0 - GPS_CLIP_LENGTH)):
        rectangle_feature(comp, f'GPS {position} clip left', rail_x_left, clip_y,
                          lip_z, lip_width, GPS_CLIP_LENGTH, 1.0,
                          adsk.fusion.FeatureOperations.JoinFeatureOperation)
        rectangle_feature(comp, f'GPS {position} clip right',
                          gps_x + GPS_BOARD_WIDTH - GPS_CLIP_OVERHANG, clip_y,
                          lip_z, lip_width, GPS_CLIP_LENGTH, 1.0,
                          adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Broad square mesh above the Pi. One combined cut is considerably faster
    # in Fusion than creating a separate extrude feature for every mesh cell.
    mesh_cells, _ = lid_mesh_layout(outer_l, outer_w, x_offset)
    rectangle_mesh_feature(
        comp, lid_body, 'Lid ventilation mesh', mesh_cells,
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
        body_shell(root)
        lid(root, 110.0)
        gps_reference(root, 110.0)
        pi_reference(root)
        app.activeViewport.fit()
        ui.messageBox('Case generated. Body 3 is the removable GPS reference, '
                      'body 4 is the removable Raspberry Pi 4 reference. '
                      'Hide or delete either one to inspect the case.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

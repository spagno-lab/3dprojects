import adsk.core
import adsk.fusion
import traceback


# ---------------------------------------------------------------------------
# Raspberry Pi 4 Model B, official mechanical drawing.
# Datum: PCB corner on the micro-USB-C side of the connector long edge.
# ---------------------------------------------------------------------------
PI_LENGTH = 85.0
PI_WIDTH = 56.0
PI_THICKNESS = 1.4
PI_HOLE_INSET = 3.5
PI_HOLE_PITCH_X = 58.0
PI_HOLE_PITCH_Y = 49.0
PI_HOLE_DIAMETER = 2.7
PI_SIDE_CLEARANCE = 1.0
PI_STANDOFF_HEIGHT = 3.0
PI_STANDOFF_DIAMETER = 5.0
PI_PEG_DIAMETER = PI_HOLE_DIAMETER - 0.3
PI_PEG_HEIGHT = 1.6
PI_BOARD_KEEPOUT = 17.0

# Screwless PCB retention. Values follow the measured reference case:
# 2.2 mm arms, 12 mm long, 1.0 mm of latch interference.
PI_CLIP_THICKNESS = 2.2
PI_CLIP_LENGTH = 12.0
PI_CLIP_OVERHANG = 1.0
PI_CLIP_LEAD_IN = 1.0

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
# ---------------------------------------------------------------------------
WALL = 2.5
FLOOR = 2.5
CASE_INNER_LENGTH = PI_LENGTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_WIDTH = PI_WIDTH + 2 * PI_SIDE_CLEARANCE
CASE_INNER_HEIGHT = 29.0
LID_THICKNESS = 2.4

# Lid retention. The first print never snapped because the rim was 0.6 mm
# clear of the wall on each side and had no latch at all.
LID_RIM_HEIGHT = 6.0
LID_RIM_THICKNESS = 1.6
LID_RIM_CLEARANCE = 0.15
LID_LATCH_DEPTH = 1.0
LID_LATCH_LENGTH = 12.0
LID_LATCH_HEIGHT = 2.0
LID_LATCH_BELOW_TOP = 4.0


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


def pi_layout(x_offset=0):
    """PCB datum and derived heights for the Pi inside the cavity."""
    pcb_x = x_offset + WALL + PI_SIDE_CLEARANCE
    pcb_y = WALL + PI_SIDE_CLEARANCE
    board_z = FLOOR + PI_STANDOFF_HEIGHT
    return {
        'x': pcb_x,
        'y': pcb_y,
        'board_z': board_z,
        'top_z': board_z + PI_THICKNESS,
        'holes': [
            (pcb_x + PI_HOLE_INSET, pcb_y + PI_HOLE_INSET),
            (pcb_x + PI_HOLE_INSET + PI_HOLE_PITCH_X, pcb_y + PI_HOLE_INSET),
            (pcb_x + PI_HOLE_INSET, pcb_y + PI_HOLE_INSET + PI_HOLE_PITCH_Y),
            (pcb_x + PI_HOLE_INSET + PI_HOLE_PITCH_X,
             pcb_y + PI_HOLE_INSET + PI_HOLE_PITCH_Y),
        ],
    }


def pi_port_openings(x_offset=0):
    """Port cut-outs referenced to the PCB datum, not to the case shell.

    Connector centres come from the Raspberry Pi 4 Model B mechanical drawing.
    Each opening keeps 1 mm of margin around the connector body.
    """
    pi = pi_layout(x_offset)
    edge_z = pi['board_z'] - 1.0
    long_edge = [
        ('USB-C opening', 11.2, 13.0, 7.0),
        ('Micro-HDMI 1 opening', 26.0, 11.0, 7.0),
        ('Micro-HDMI 2 opening', 39.5, 11.0, 7.0),
        ('Audio opening', 54.0, 11.0, 9.0),
    ]
    short_edge = [
        ('USB pair 2 opening', 9.0, 17.5, 18.0),
        ('USB pair 1 opening', 27.0, 17.5, 18.0),
        ('Ethernet opening', 45.75, 18.0, 16.0),
    ]
    return {
        'edge_z': edge_z,
        'long_edge': [
            (name, pi['x'] + centre - width / 2, width, height)
            for name, centre, width, height in long_edge
        ],
        'short_edge': [
            (name, pi['y'] + centre - width / 2, width, height)
            for name, centre, width, height in short_edge
        ],
    }


def pi_retention(comp, x_offset=0):
    """Screwless retention: locating pegs plus four cantilever clips.

    The printed M2.5 posts were dropped. The board drops onto four standoffs
    whose small pegs enter the mounting holes, and four clips snap over the
    board edge. PI_CLIP_OVERHANG of material sits on top of the PCB.
    """
    pi = pi_layout(x_offset)
    for index, (x, y) in enumerate(pi['holes'], 1):
        cylinder_feature(comp, f'Pi standoff {index}', x, y, FLOOR,
                         PI_STANDOFF_DIAMETER, PI_STANDOFF_HEIGHT)
        cylinder_feature(comp, f'Pi locating peg {index}', x, y,
                         pi['board_z'], PI_PEG_DIAMETER, PI_PEG_HEIGHT)

    clip_z = pi['board_z']
    arm_height = PI_THICKNESS + PI_CLIP_LEAD_IN + 1.2
    left_x = pi['x'] - PI_SIDE_CLEARANCE - PI_CLIP_THICKNESS
    right_x = pi['x'] + PI_LENGTH + PI_SIDE_CLEARANCE
    clip_positions = (
        ('front left', left_x, pi['y'] + 14.0),
        ('rear left', left_x, pi['y'] + PI_WIDTH - 14.0 - PI_CLIP_LENGTH),
        ('front right', right_x, pi['y'] + 14.0),
        ('rear right', right_x, pi['y'] + PI_WIDTH - 14.0 - PI_CLIP_LENGTH),
    )
    for name, x, y in clip_positions:
        rectangle_feature(
            comp, f'Pi clip arm {name}', x, y, clip_z,
            PI_CLIP_THICKNESS, PI_CLIP_LENGTH, arm_height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation)
        hook_x = x + PI_CLIP_THICKNESS if x < pi['x'] else x - PI_CLIP_OVERHANG
        rectangle_feature(
            comp, f'Pi clip hook {name}', hook_x, y,
            clip_z + PI_THICKNESS, PI_CLIP_OVERHANG, PI_CLIP_LENGTH,
            PI_CLIP_LEAD_IN,
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

    pi_retention(comp)

    # Port openings. The upper edge of each cut stays open and is closed by
    # the lid, so no bridging is needed while printing.
    ports = pi_port_openings()
    for name, y, width, height in ports['short_edge']:
        rectangle_feature(comp, name, outer_l - WALL - 1, y, ports['edge_z'],
                          WALL + 2, width, height,
                          adsk.fusion.FeatureOperations.CutFeatureOperation)
    for name, x, width, height in ports['long_edge']:
        rectangle_feature(comp, name, x, -1.0, ports['edge_z'],
                          width, WALL + 2, height,
                          adsk.fusion.FeatureOperations.CutFeatureOperation)

    pi = pi_layout()
    rectangle_feature(comp, 'MicroSD opening', -1.0, pi['y'] + 19.0, 0.0,
                      WALL + 2, 14.0, pi['board_z'] + PI_THICKNESS + 1.0,
                      adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Latch pockets for the lid rim bumps.
    latches = lid_latch_positions()
    for x in latches['x_positions']:
        rectangle_feature(
            comp, 'Lid latch pocket front', x, WALL - LID_LATCH_DEPTH,
            latches['z'], LID_LATCH_LENGTH, LID_LATCH_DEPTH, LID_LATCH_HEIGHT,
            adsk.fusion.FeatureOperations.CutFeatureOperation)
        rectangle_feature(
            comp, 'Lid latch pocket rear', x, outer_w - WALL,
            latches['z'], LID_LATCH_LENGTH, LID_LATCH_DEPTH, LID_LATCH_HEIGHT,
            adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Round rear-wall hole aligned with the assembled SMA axis. A shallow
    # circular counterbore leaves 2 mm of local wall so an antenna that stops
    # 3 mm from the SMA base can still tighten completely.
    gps_sma_wall_features(comp, case_body, outer_l, outer_w, outer_h)


def lid(comp, x_offset=0):
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    rectangle_feature(comp, 'Lid', x_offset, 0, 0, outer_l, outer_w, LID_THICKNESS)

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

    # Ventilation slots above the Pi.
    slot_count = 6
    slot_width = 6.0
    slot_pitch = 11.0
    slots_width = slot_width + (slot_count - 1) * slot_pitch
    slots_x = x_offset + (outer_l - slots_width) / 2
    for i in range(slot_count):
        rectangle_feature(comp, f'Vent slot {i + 1}', slots_x + i * slot_pitch, 12, 0,
                          slot_width, 2.2, LID_THICKNESS + 1,
                          adsk.fusion.FeatureOperations.CutFeatureOperation)


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
        app.activeViewport.fit()
        ui.messageBox('Case generated. The Pi is held by pegs and four clips, '
                      'the lid snaps on four latches, and body 3 is the '
                      'removable GPS fit reference.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

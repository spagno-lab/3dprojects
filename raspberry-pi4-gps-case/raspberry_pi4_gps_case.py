import adsk.core
import adsk.fusion
import traceback


# User-measured dimensions in millimetres. Viewed from inside the case, the
# component/pin face points inward, the u-blox shield faces the lid, and the
# SMA occupies the top-right corner and points through the rear wall.
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
SMA_HOLE_DIAMETER = SMA_THREAD_DIAMETER + 2 * GPS_FIT_CLEARANCE
SMA_LOCAL_WALL = 2.0
SMA_RECESS_DIAMETER = SMA_BASE_WIDTH + 2 * GPS_FIT_CLEARANCE
GPS_CLIP_THICKNESS = 1.6
GPS_CLIP_LENGTH = 5.0
GPS_CLIP_OVERHANG = 1.0
GPS_EDGE_SUPPORT_WIDTH = 0.8
GPS_COMPONENT_KEEPOUT_INSET = 1.2

WALL = 2.4
FLOOR = 2.4
CLEARANCE = 0.6
CASE_INNER_LENGTH = 91.0
CASE_INNER_WIDTH = 62.0
CASE_INNER_HEIGHT = 29.0
LID_THICKNESS = 2.4

# Raspberry Pi 4 Model B mechanical datum. Board and mounting dimensions come
# from the official mechanical drawing. Connector envelopes are cross-checked
# against public Pi 4 enclosure models and receive one explicit print margin.
PI_BOARD_LENGTH = 85.0
PI_BOARD_WIDTH = 56.0
PI_BOARD_THICKNESS = 1.6
PI_BOARD_EDGE_CLEARANCE = 2.5
PI_MOUNT_X = 58.0
PI_MOUNT_Y = 49.0
PI_MOUNT_EDGE_OFFSET = 3.5
PI_MOUNT_HOLE_DIAMETER = 3.0
PI_POST_DIAMETER = 6.0
PI_POST_HEIGHT = 4.0
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
    board_bottom_z = FLOOR + PI_POST_HEIGHT
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
    pi = pi_layout()
    pi_x = pi['mount_x']
    pi_y = pi['mount_y']
    for index, (x, y) in enumerate(((pi_x, pi_y), (pi_x + PI_MOUNT_X, pi_y),
                                    (pi_x, pi_y + PI_MOUNT_Y),
                                    (pi_x + PI_MOUNT_X, pi_y + PI_MOUNT_Y)), 1):
        sketch = comp.sketches.add(offset_plane(comp, FLOOR))
        sketch.name = f'Pi post {index}'
        circles = sketch.sketchCurves.sketchCircles
        circles.addByCenterRadius(
            adsk.core.Point3D.create(cm(x), cm(y), 0),
            cm(PI_POST_DIAMETER / 2),
        )
        post = comp.features.extrudeFeatures.createInput(
            sketch.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation)
        post.setDistanceExtent(False, value(PI_POST_HEIGHT))
        comp.features.extrudeFeatures.add(post)

        hole_sketch = comp.sketches.add(offset_plane(comp, FLOOR))
        hole_sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(x), cm(y), 0),
            cm(PI_MOUNT_HOLE_DIAMETER / 2),
        )
        hole = comp.features.extrudeFeatures.createInput(
            hole_sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        hole.setDistanceExtent(False, value(PI_POST_HEIGHT + 1.0))
        comp.features.extrudeFeatures.add(hole)

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

    # Inner locating rim, discontinuous so it can flex when snapped into place.
    rim_h = 3.0
    rim_t = 1.2
    inset = WALL + CLEARANCE
    rectangle_feature(comp, 'Lid rim front', x_offset + inset + 8, inset, LID_THICKNESS,
                      CASE_INNER_LENGTH - 16, rim_t, rim_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    rear_rim_start = x_offset + inset + 8
    rear_rim_end = rear_rim_start + CASE_INNER_LENGTH - 16
    cradle_gap_start = gps['x'] - CLEARANCE - GPS_CLIP_THICKNESS - 1.0
    cradle_gap_end = gps['x'] + GPS_BOARD_WIDTH + CLEARANCE + GPS_CLIP_THICKNESS + 1.0
    rectangle_feature(comp, 'Lid rim rear left', rear_rim_start,
                      outer_w - inset - rim_t, LID_THICKNESS,
                      cradle_gap_start - rear_rim_start, rim_t, rim_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim rear right', cradle_gap_end,
                      outer_w - inset - rim_t, LID_THICKNESS,
                      rear_rim_end - cradle_gap_end, rim_t, rim_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim left', x_offset + inset, inset + 8, LID_THICKNESS,
                      rim_t, CASE_INNER_WIDTH - 16, rim_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'Lid rim right', x_offset + outer_l - inset - rim_t, inset + 8, LID_THICKNESS,
                      rim_t, CASE_INNER_WIDTH - 16, rim_h,
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
        ui.messageBox('Case generated. Body 3 is the removable GPS fit reference '
                      'with a round SMA hole and five right-angle pins.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

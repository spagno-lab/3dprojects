import adsk.core
import adsk.fusion
import traceback


# User-measured dimensions in millimetres. Viewed in its mounted orientation,
# the 18 mm edge is horizontal, the chip faces inward, and the SMA points
# outward from the rear/top edge. Its axis is 6 mm from the right PCB corner.
GPS_BOARD_LENGTH = 23.0
GPS_BOARD_WIDTH = 18.0
GPS_BOARD_THICKNESS = 1.6
GPS_MAX_COMPONENT_HEIGHT = 8.0
SMA_PROJECTION = 10.0
SMA_CENTER_FROM_RIGHT = 6.0
SMA_SLOT_WIDTH = 10.0
GPS_CLIP_THICKNESS = 1.6
GPS_CLIP_LENGTH = 5.0
GPS_CLIP_OVERHANG = 1.0
GPS_REFERENCE_GAP = 0.2

WALL = 2.4
FLOOR = 2.4
CLEARANCE = 0.6
CASE_INNER_LENGTH = 91.0
CASE_INNER_WIDTH = 62.0
CASE_INNER_HEIGHT = 29.0
LID_THICKNESS = 2.4


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
                      operation=adsk.fusion.FeatureOperations.NewBodyFeatureOperation):
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
    extrude_input.setDistanceExtent(False, value(height))
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def rear_wall_hole(comp, name, center_x, center_z, wall_y, diameter):
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    # Fusion's positive offset from the XZ plane points toward negative Y.
    plane_input.setByOffset(comp.xZConstructionPlane, value(-wall_y))
    plane = planes.add(plane_input)
    sketch = comp.sketches.add(plane)
    sketch.name = name
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(center_x), cm(center_z), 0), cm(diameter / 2)
    )
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrude_input.setSymmetricExtent(value(WALL + 2.0), False)
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def gps_cradle_layout(outer_l, outer_w, x_offset=0):
    """Return the board envelope with its offset SMA facing the rear wall."""
    board_x = x_offset + (outer_l - GPS_BOARD_WIDTH) / 2
    # Leave one clip thickness behind the PCB so the rear stops remain fully
    # inside the case wall. The SMA barrel bridges this small setback.
    board_rear_y = outer_w - WALL - GPS_CLIP_THICKNESS - CLEARANCE
    return {
        'x': board_x,
        'y': board_rear_y - GPS_BOARD_LENGTH,
        'rear_y': board_rear_y,
        'center_x': board_x + GPS_BOARD_WIDTH / 2,
        'sma_center_x': board_x + GPS_BOARD_WIDTH - SMA_CENTER_FROM_RIGHT,
        'sma_tip_y': board_rear_y + SMA_PROJECTION,
    }


def body_shell(comp):
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    outer_h = CASE_INNER_HEIGHT + FLOOR

    rectangle_feature(comp, 'Case outer body', 0, 0, 0, outer_l, outer_w, outer_h)
    rectangle_feature(
        comp, 'Case cavity', WALL, WALL, FLOOR,
        CASE_INNER_LENGTH, CASE_INNER_WIDTH, CASE_INNER_HEIGHT + 1,
        adsk.fusion.FeatureOperations.CutFeatureOperation
    )

    # Pi 4 mounting posts: standard 58 x 49 mm hole pattern, M2.5 clearance.
    pi_x = WALL + 3.5 + 2.5
    pi_y = WALL + 3.5 + 2.5
    for index, (x, y) in enumerate(((pi_x, pi_y), (pi_x + 58, pi_y),
                                    (pi_x, pi_y + 49), (pi_x + 58, pi_y + 49)), 1):
        sketch = comp.sketches.add(offset_plane(comp, FLOOR))
        sketch.name = f'Pi post {index}'
        circles = sketch.sketchCurves.sketchCircles
        circles.addByCenterRadius(adsk.core.Point3D.create(cm(x), cm(y), 0), cm(3.0))
        post = comp.features.extrudeFeatures.createInput(
            sketch.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation)
        post.setDistanceExtent(False, value(4.0))
        comp.features.extrudeFeatures.add(post)

        hole_sketch = comp.sketches.add(offset_plane(comp, FLOOR))
        hole_sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(x), cm(y), 0), cm(1.35))
        hole = comp.features.extrudeFeatures.createInput(
            hole_sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        hole.setDistanceExtent(False, value(5.0))
        comp.features.extrudeFeatures.add(hole)

    # Separate top-open Pi 4 port cut-outs. Their upper edge is closed by the lid.
    top = outer_h - 17.0
    rectangle_feature(comp, 'Ethernet opening', outer_l - WALL - 1, 6.0, top,
                      WALL + 2, 17.5, 18.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'USB pair 1 opening', outer_l - WALL - 1, 25.0, top,
                      WALL + 2, 15.5, 18.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'USB pair 2 opening', outer_l - WALL - 1, 42.0, top,
                      WALL + 2, 15.5, 18.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    rectangle_feature(comp, 'USB-C opening', 8.0, -1.0, top + 4.0,
                      11.0, WALL + 2, 14.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'Micro-HDMI 1 opening', 24.0, -1.0, top + 5.0,
                      9.0, WALL + 2, 13.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'Micro-HDMI 2 opening', 37.0, -1.0, top + 5.0,
                      9.0, WALL + 2, 13.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'Audio opening', 54.0, -1.0, top + 4.0,
                      10.0, WALL + 2, 14.0, adsk.fusion.FeatureOperations.CutFeatureOperation)
    rectangle_feature(comp, 'MicroSD opening', -1.0, 23.0, 4.0,
                      WALL + 2, 18.0, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Top-open slot: the lid-mounted board drops in with its SMA connector
    # already fitted. The connector is offset 6 mm from the board's right edge.
    gps = gps_cradle_layout(outer_l, outer_w)
    rectangle_feature(
        comp, 'GPS SMA opening', gps['sma_center_x'] - SMA_SLOT_WIDTH / 2,
        outer_w - WALL - 1, outer_h - 12.0,
        SMA_SLOT_WIDTH, WALL + 2, 13.0,
        adsk.fusion.FeatureOperations.CutFeatureOperation
    )


def lid(comp, x_offset=0):
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    rectangle_feature(comp, 'Lid', x_offset, 0, 0, outer_l, outer_w, LID_THICKNESS)

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

    # GPS cradle on the inside of the lid. Its long axis runs front-to-rear,
    # leaving the rear SMA connector and front Dupont header unobstructed.
    # Four short snap lips touch only the PCB side edges, away from components.
    gps_x = gps['x']
    gps_y = gps['y']
    rail_x_left = gps_x - CLEARANCE - GPS_CLIP_THICKNESS
    rail_x_right = gps_x + GPS_BOARD_WIDTH + CLEARANCE
    rail_y = gps_y + 2.0
    rail_length = GPS_BOARD_LENGTH - 4.0
    rail_h = GPS_BOARD_THICKNESS + 1.3
    rectangle_feature(comp, 'GPS left rail', rail_x_left, rail_y, LID_THICKNESS,
                      GPS_CLIP_THICKNESS, rail_length, rail_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS right rail', rail_x_right, rail_y, LID_THICKNESS,
                      GPS_CLIP_THICKNESS, rail_length, rail_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Corner stops prevent lengthwise movement while keeping the SMA and
    # four-wire Dupont connector paths clear.
    stop_width = 4.0
    stop_h = GPS_BOARD_THICKNESS + 0.5
    front_stop_y = gps_y - GPS_CLIP_THICKNESS
    rectangle_feature(comp, 'GPS front stop left', gps_x, front_stop_y,
                      LID_THICKNESS, stop_width, GPS_CLIP_THICKNESS, stop_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)
    rectangle_feature(comp, 'GPS front stop right',
                      gps_x + GPS_BOARD_WIDTH - stop_width, front_stop_y,
                      LID_THICKNESS, stop_width, GPS_CLIP_THICKNESS, stop_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # The SMA is close enough to the right corner that a right rear stop would
    # cross its 9 mm opening. A single left rear stop locates the PCB while the
    # full connector corridor remains unobstructed.
    rectangle_feature(comp, 'GPS rear stop left', gps_x,
                      gps['rear_y'] + CLEARANCE, LID_THICKNESS,
                      stop_width, GPS_CLIP_THICKNESS, stop_h,
                      adsk.fusion.FeatureOperations.JoinFeatureOperation)

    lip_z = LID_THICKNESS + GPS_BOARD_THICKNESS + 0.3
    lip_width = GPS_CLIP_THICKNESS + CLEARANCE + GPS_CLIP_OVERHANG
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
    """Add a third body representing the measured GPS PCB and SMA envelope."""
    outer_l = CASE_INNER_LENGTH + 2 * WALL
    outer_w = CASE_INNER_WIDTH + 2 * WALL
    gps = gps_cradle_layout(outer_l, outer_w, x_offset)
    reference_z = LID_THICKNESS + GPS_REFERENCE_GAP

    rectangle_feature(
        comp, 'GPS reference PCB', gps['x'], gps['y'], reference_z,
        GPS_BOARD_WIDTH, GPS_BOARD_LENGTH, GPS_BOARD_THICKNESS,
    )
    rectangle_feature(
        comp, 'GPS reference SMA', gps['sma_center_x'] - SMA_SLOT_WIDTH / 2,
        gps['rear_y'], reference_z, SMA_SLOT_WIDTH, SMA_PROJECTION,
        GPS_BOARD_THICKNESS,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
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
        ui.messageBox('Case generated. Body, lid, and GPS reference are three separate '
                      'bodies. The reference shows the measured PCB and SMA envelope.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

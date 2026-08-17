import adsk.core
import adsk.fusion
import traceback


BASE_WIDTH = 160.0
BASE_DEPTH = 95.0
BASE_HEIGHT = 10.0
POST_DIAMETER = 18.0
POST_FOOT_DIAMETER = 44.0
POST_FOOT_HEIGHT = 18.0
ASSEMBLED_BAR_BOTTOM_HEIGHT = 180.0
TENON_HEIGHT = 14.0
BAR_WIDTH = 230.0
BAR_DIAMETER = 24.0
SOCKET_BOSS_DIAMETER = 28.0
FIT_CLEARANCE = 0.35
PRINT_GAP = 15.0


def cm(mm):
    return mm / 10.0


def value(mm):
    return adsk.core.ValueInput.createByString(f'{mm} mm')


def offset_plane(comp, z):
    plane_input = comp.constructionPlanes.createInput()
    plane_input.setByOffset(comp.xYConstructionPlane, value(z))
    return comp.constructionPlanes.add(plane_input)


def box(comp, name, x, y, z, width, depth, height, operation,
        participant_bodies=None):
    plane = comp.xYConstructionPlane if z == 0 else offset_plane(comp, z)
    sketch = comp.sketches.add(plane)
    sketch.name = name
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(cm(x), cm(y), 0),
        adsk.core.Point3D.create(cm(x + width), cm(y + depth), 0),
    )
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(sketch.profiles.item(0), operation)
    extrude_input.setDistanceExtent(False, value(height))
    if participant_bodies:
        extrude_input.participantBodies = participant_bodies
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def vertical_cylinder(comp, name, center_x, center_y, z, diameter, height,
                      operation, participant_bodies=None):
    plane = comp.xYConstructionPlane if z == 0 else offset_plane(comp, z)
    sketch = comp.sketches.add(plane)
    sketch.name = name
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(center_x), cm(center_y), 0),
        cm(diameter / 2),
    )
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(sketch.profiles.item(0), operation)
    extrude_input.setDistanceExtent(False, value(height))
    if participant_bodies:
        extrude_input.participantBodies = participant_bodies
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def horizontal_cylinder(comp, name, center_y, center_z, length, diameter):
    sketch = comp.sketches.add(comp.yZConstructionPlane)
    sketch.name = name
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(center_y), cm(center_z), 0),
        cm(diameter / 2),
    )
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        sketch.profiles.item(0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )
    extrude_input.setSymmetricExtent(value(length / 2), False)
    feature = extrudes.add(extrude_input)
    feature.name = name
    return feature


def build_stand(comp):
    base = box(comp, 'Base', -BASE_WIDTH / 2, -BASE_DEPTH / 2, 0,
               BASE_WIDTH, BASE_DEPTH, BASE_HEIGHT,
               adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    stand_body = base.bodies.item(0)
    stand_body.name = 'Bracelet stand'
    post_height = ASSEMBLED_BAR_BOTTOM_HEIGHT + TENON_HEIGHT - BASE_HEIGHT
    vertical_cylinder(
        comp, 'Upright post', 0, 0, BASE_HEIGHT,
        POST_DIAMETER, post_height,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, [stand_body],
    )
    vertical_cylinder(
        comp, 'Post foot', 0, 0, BASE_HEIGHT,
        POST_FOOT_DIAMETER, POST_FOOT_HEIGHT,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, [stand_body],
    )


def build_bar(comp):
    bar_center_y = BASE_DEPTH / 2 + PRINT_GAP + BAR_DIAMETER / 2
    bar_center_z = TENON_HEIGHT

    bar = horizontal_cylinder(
        comp, 'Display bar', bar_center_y, bar_center_z,
        BAR_WIDTH, BAR_DIAMETER,
    )
    bar_body = bar.bodies.item(0)
    bar_body.name = 'Bracelet display bar'
    vertical_cylinder(
        comp, 'Socket boss', 0, bar_center_y, 0,
        SOCKET_BOSS_DIAMETER, TENON_HEIGHT,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, [bar_body],
    )
    vertical_cylinder(
        comp, 'Post socket', 0, bar_center_y, -0.1,
        POST_DIAMETER + 2 * FIT_CLEARANCE, TENON_HEIGHT + 0.2,
        adsk.fusion.FeatureOperations.CutFeatureOperation, [bar_body],
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
        build_stand(root)
        build_bar(root)
        app.activeViewport.fit()
        ui.messageBox('Stand generated as two separated bodies in print orientation.')
    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    pass

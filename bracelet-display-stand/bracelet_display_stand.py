import adsk.core
import adsk.fusion
import traceback


BASE_WIDTH = 160.0
BASE_DEPTH = 95.0
BASE_HEIGHT = 10.0
POST_WIDTH = 20.0
POST_DEPTH = 28.0
ASSEMBLED_BAR_BOTTOM_HEIGHT = 180.0
TENON_HEIGHT = 14.0
BAR_WIDTH = 230.0
BAR_DEPTH = 38.0
BAR_HEIGHT = 28.0
END_STOP_THICKNESS = 6.0
END_STOP_OVERHANG = 3.0
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


def build_stand(comp):
    base = box(comp, 'Base', -BASE_WIDTH / 2, -BASE_DEPTH / 2, 0,
               BASE_WIDTH, BASE_DEPTH, BASE_HEIGHT,
               adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    stand_body = base.bodies.item(0)
    stand_body.name = 'Bracelet stand'
    post_height = ASSEMBLED_BAR_BOTTOM_HEIGHT + TENON_HEIGHT - BASE_HEIGHT
    box(comp, 'Upright post', -POST_WIDTH / 2, -POST_DEPTH / 2, BASE_HEIGHT,
        POST_WIDTH, POST_DEPTH, post_height,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, [stand_body])
    box(comp, 'Post foot', -24, -(POST_DEPTH + 16) / 2, BASE_HEIGHT,
        48, POST_DEPTH + 16, 18,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, [stand_body])


def build_bar(comp):
    stop_depth = BAR_DEPTH + 2 * END_STOP_OVERHANG
    stop_height = BAR_HEIGHT + 2 * END_STOP_OVERHANG
    bar_center_y = BASE_DEPTH / 2 + PRINT_GAP + stop_depth / 2
    bar_bottom_z = END_STOP_OVERHANG

    bar = box(comp, 'Display bar', -BAR_WIDTH / 2,
              bar_center_y - BAR_DEPTH / 2, bar_bottom_z,
              BAR_WIDTH, BAR_DEPTH, BAR_HEIGHT,
              adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    bar_body = bar.bodies.item(0)
    bar_body.name = 'Bracelet display bar'
    for name, x in (('Left end stop', -BAR_WIDTH / 2),
                    ('Right end stop', BAR_WIDTH / 2 - END_STOP_THICKNESS)):
        box(comp, name, x, bar_center_y - stop_depth / 2, 0,
            END_STOP_THICKNESS, stop_depth, stop_height,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [bar_body])
    box(comp, 'Post socket', -POST_WIDTH / 2 - FIT_CLEARANCE,
        bar_center_y - POST_DEPTH / 2 - FIT_CLEARANCE,
        bar_bottom_z - 0.1,
        POST_WIDTH + 2 * FIT_CLEARANCE, POST_DEPTH + 2 * FIT_CLEARANCE,
        TENON_HEIGHT + 0.2,
        adsk.fusion.FeatureOperations.CutFeatureOperation, [bar_body])


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

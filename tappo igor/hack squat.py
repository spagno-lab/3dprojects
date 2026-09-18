import numpy as np
import trimesh

# Carica il file disegnato dall'utente (asse di rivoluzione = Y)
body = trimesh.load('/mnt/user-data/uploads/tappo_bilanciere.stl')
body.merge_vertices()
body.fix_normals()
print("Corpo caricato watertight:", body.is_watertight, "volume:", body.volume)

RING_R_OUT = 12.5     # raggio esterno degli anelli (misurato dal file)
RING1_Y0 = 10.0        # bordo inferiore anello 1
RING2_Y0 = 15.0        # bordo inferiore anello 2

STEP_FWD = 1.0         # gradino in avanti per non toccare il cilindro
TOOTH_R_IN = RING_R_OUT + STEP_FWD     # 13.5 - a filo, spostato in avanti di 1 mm
TOOTH_THICK = 1.5                      # spessore radiale del dente (assunzione)
TOOTH_R_OUT = TOOTH_R_IN + TOOTH_THICK

TOOTH_DROP = 2.0        # scende di 2 mm sotto l'anello
TOP_WIDTH = 4.0          # base lunga, in alto (assunzione)
BOTTOM_WIDTH = 1.5       # base corta, in basso (dato)

N_TEETH = 4
angle_step = 360.0 / N_TEETH


def make_tooth(theta_center_deg, y_top):
    theta_c = np.radians(theta_center_deg)
    y_bottom = y_top - TOOTH_DROP

    half_top = (TOP_WIDTH / 2.0) / TOOTH_R_IN
    half_bottom = (BOTTOM_WIDTH / 2.0) / TOOTH_R_IN

    def pt(r, dtheta, y):
        a = theta_c + dtheta
        return (r * np.cos(a), y, r * np.sin(a))

    pts = [
        pt(TOOTH_R_IN, -half_top, y_top),
        pt(TOOTH_R_IN, half_top, y_top),
        pt(TOOTH_R_IN, -half_bottom, y_bottom),
        pt(TOOTH_R_IN, half_bottom, y_bottom),
        pt(TOOTH_R_OUT, -half_top, y_top),
        pt(TOOTH_R_OUT, half_top, y_top),
        pt(TOOTH_R_OUT, -half_bottom, y_bottom),
        pt(TOOTH_R_OUT, half_bottom, y_bottom),
    ]
    pts = np.array(pts)
    return trimesh.Trimesh(vertices=pts).convex_hull


teeth = []
for k in range(N_TEETH):
    theta_deg = k * angle_step
    teeth.append(make_tooth(theta_deg, RING1_Y0))
    teeth.append(make_tooth(theta_deg, RING2_Y0))

final = trimesh.boolean.union([body] + teeth)
final.merge_vertices()
final.fix_normals()

print("Finale watertight:", final.is_watertight)
print("Volume mm^3:", final.volume)
print("Bounds:", final.bounds)

final.export("/mnt/user-data/outputs/tappo_bilanciere.stl")
print("saved")
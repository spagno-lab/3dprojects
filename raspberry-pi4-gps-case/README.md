# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
The script generates three separate bodies: case, lid, and a GPS reference
object used to check the cradle and SMA opening visually in Fusion 360.

## Raspberry Pi 4 fit and I/O

The Pi geometry uses a single assembled-board datum instead of independent
wall-opening coordinates. The board and mounting pattern follow Raspberry
Pi's official mechanical drawing:

- board: 85 × 56 × 1.6 mm;
- mounting-hole pattern: 58 × 49 mm;
- mounting-hole centres: 3.5 mm from the board edges;
- printed mounting holes: 3.0 mm diameter, enlarged from the nominal 2.7 mm
  PCB holes to allow for FDM printing and an M2.5 fastener.

USB-C, the two Micro-HDMI ports, audio, both USB stacks, Ethernet, and MicroSD
openings are derived from that same datum. Connector envelopes were
cross-checked against the detailed public
[`pkoehlers/rpi-case-openscad`](https://github.com/pkoehlers/rpi-case-openscad)
model and a second enclosure,
[`txoof/pi4_case`](https://github.com/txoof/pi4_case), then expanded by
0.8 mm on each mating edge for printing and plug access. The second project
also confirms that broader grouped port openings are a viable alternative,
but this design retains separate openings for better wall protection.

Primary references:

- [Raspberry Pi 4 Model B mechanical drawing](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf)
- [Raspberry Pi 4 Model B specifications](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/)

## Ventilated lid

The lid uses a broad 7 × 7 mm square mesh with 2 mm ribs. A 6 mm solid border
preserves stiffness and leaves the locating rim intact. Mesh cells that would
intersect the GPS cradle and its clips are automatically omitted, leaving a
solid load-bearing region around the removable module while opening most of
the area above the Raspberry Pi for passive airflow.

## Board retention

The board drops straight down onto the four standoffs and snaps past four
flexible clips, one on each free stretch of board edge. Nothing screws in and
nothing slides sideways.

| clip | wall | offset along the wall | what makes that stretch free |
|---|---|---|---|
| 1 | front | 61 mm | past the audio jack, which ends at 58.1 mm |
| 2 | left | 3 mm | front corner, before the microSD opening |
| 3 | left | 40 mm | behind the microSD opening, which ends at 37.1 mm |
| 4 | rear | 59 mm | past the GPIO header, which ends at 54.3 mm |

Each hook reaches 0.6 mm over the PCB and carries a 45 degree lead-in above
the retaining face, printed as a four-step staircase: at 0.2 mm layers a real
chamfer comes out as steps anyway, and a staircase survives every rebuild
without a chamfer feature to re-attach. The board pushes the clips aside on
the way down instead of needing a fingernail.

The right wall holds nothing: it is solid USB and Ethernet.

### The revision that would not assemble

The previous design slid the GPIO edge under two rigid lips on the rear wall
and then snapped the opposite edge down. It could not be assembled at all, for
two independent reasons, and neither is visible in Fusion:

- the lips reached `PI_LIP_OVERHANG` = 1.2 mm over the board, but the rear gap
  is `PI_SIDE_CLEARANCE` = 0.4 mm, so the board could never travel far enough
  back to get under them — 0.8 mm short;
- the left lip sat at x 12 to 26 mm, which is on top of the GPIO header. The
  header body runs from 0.95 to 6.05 mm in from the rear edge, so a lip
  reaching 1.2 mm in overlaps it by 0.25 mm, and the header stands 8.5 mm tall
  against a lip 1.4 mm above the PCB. The board hit it and stopped.

The root cause is that clip placement and the reference body were each worked
out from the drawing separately, so nothing compared them. They now share
`pi_component_footprints()`, and `fit_check.py` tests one against the other.

## Checking the fit

```
python3 fit_check.py
```

`fit_check.py` imports the script with a stub in place of the Fusion API and
audits the geometry: board clearance, every clip hook against every component
envelope, clip arms against the wall openings, that no feature needs a
sideways slide the pocket cannot give, lead-in direction, snap strain, wall
left behind each relief slot, the SMA counterbore against the rear clip, and
headroom under the lid. It exits non-zero on failure, so it works as a
pre-commit hook.

Fed the old lip geometry it reports exactly the two defects above, which is
the point: both were geometry that looked right on screen.

## Snap strain

Both snap features were checked against the standard cantilever formula,
`strain = 1.5 * t * deflection / L^2`, since PETG yields around 5 per cent:

| feature | thickness | deflection | free length | strain |
|---|---|---|---|---|
| PCB clip | 1.1 mm | 0.6 mm | 7.0 mm | 2.0 % |
| lid latch | 1.2 mm | 0.6 mm | 5.0 mm | 4.3 % |

Two earlier revisions failed this check badly: the clip arm was rooted at
board level, giving 4 mm of cantilever and 10 per cent strain, and the lid rim
was 1.6 mm thick with the latch only 2 mm from its root, which works out at
60 per cent. Both would have snapped off on first assembly. The fix is length,
not thickness: the clip arm now starts at the floor and the lid latch sits
near the tip of a taller rim.

Going from two clips to four multiplies the insertion force by two, not the
strain: each clip still deflects 0.6 mm on its own 7 mm arm. `fit_check.py`
re-runs this table from the constants.

## Reference bodies

The script emits two throwaway bodies so the fit can be checked on screen
before printing:

- **body 3**, `GPS module - removable fit reference`;
- **body 4**, `Raspberry Pi 4 - removable fit reference`: PCB, the four
  connectors on the front edge, the three on the port edge, the GPIO header as
  a plain 2x20 block, and the microSD card sticking out.

Body 4 is placed exactly where the standoffs and the clips put the real board,
and its connectors use the same rotation as the wall openings, so a mismatch on
screen is a mismatch in plastic. Hide or delete both bodies before exporting
the mesh. The GPIO block is a volume placeholder, not a pin-accurate model.

Measured clearances with both bodies in place: 0.8 mm around every connector,
8.8 mm between the tallest connector and the lid, and 2.9 mm between the Pi and
the GPS cradle hanging from the lid.

## GPS carrier reference

The cradle follows the supplied front, rear, and side photos and the measured
dimensions of the blue carrier:

- PCB envelope: 18 × 23 mm;
- complete component envelope across both PCB faces: 8 mm;
- five right-angle pins: 5 mm forward from the PCB face, then an 8 mm drop;
- SMA connector pointing toward the rear/top edge of the lid;
- SMA base: 7 × 7 × 1 mm, beginning at the top-right PCB corner when viewed
  from the component/pin side;
- SMA threaded section: 5 mm diameter and 8 mm projection from its base;
- the shield/chip face points toward the lid while the component and pin face
  points toward the case interior;
- the lid is flipped 180 degrees around its front-rear axis for assembly, so
  the SMA hole position is mirrored left-to-right on the case;
- the vertical SMA axis is measured down from the assembled lid's inner face;
  the lid plate itself is not part of that offset;
- the SMA passes through a circular 5.6 mm rear-wall hole aligned with its
  assembled axis;
- a circular external counterbore reduces the general 2.4 mm wall to 2 mm
  around the SMA, leaving about
  1 mm clearance before an attached antenna that stops 3 mm from the base;
- four short side clips grip the PCB edges without spanning the SMA or header;
- two 0.8 mm edge ledges lift the board clear of the lid-side shield;
- only the two extreme front corners are retained, leaving the pin bank and
  cable path open.

The PCB, overall module, pin, and SMA dimensions are user measurements. The
1.6 mm PCB thickness and the equal split of the remaining component depth
between the two PCB faces are modelling assumptions because only the complete
8 mm depth was measured. Adjust `GPS_BOARD_THICKNESS`,
`GPS_BACK_COMPONENT_DEPTH`, and `GPS_FRONT_COMPONENT_DEPTH` if separate face
measurements become available. A cradle-only test print is recommended before
printing the full case.

Body 3 is named `GPS module - removable fit reference` and remains a single
body, with every join explicitly limited to that body so Fusion cannot merge it
with the lid. It includes the PCB, an inset 8 mm component keep-out, the 7 mm
SMA base, the 5 × 8 mm threaded-section envelope, and the two legs of each bent
pin. It can be hidden or removed to inspect the cradle. The clips retain only
the PCB edges and do not press on the component keep-out.

## Slicing profile

`raspberry.3mf` carries the Bambu Studio project for an X2D with a 0.4 nozzle
and PETG. Settings that matter for this part:

| setting | value | why |
|---|---|---|
| wall generator | Arachne | the clip arm is 1.1 mm and the lid rim 1.2 mm, neither is a multiple of the 0.42 mm line, and the classic generator leaves them hollow |
| wall loops | 5 | 2.5 mm walls come out solid from perimeters alone |
| sparse infill | 5 % gyroid | nothing structural relies on infill |
| bottom shell layers | 5 | the floor carries the four standoffs that take the push when the board snaps in |
| outer wall speed | 120 mm/s | 200 rounds off the 0.6 mm latch features |
| fan max | 45 % | PETG layer adhesion at the clip root matters more than surface finish |
| elephant foot | 0.15 mm | protects the 0.25 mm rim and 0.4 mm board clearances |
| supports | off | the only overhangs are the 0.6 to 1.6 mm ledges, which print in air |

Both parts are placed unrotated: the case with its opening up and the lid with
its rim up, so the clips and the rim grow along Z and bend across layer lines.

### Loading it

Those values live inside the 3mf. Two things stopped them from showing up:

- importing the 3mf loads the geometry and drops the configuration, so use
  **File - Open Project**;
- the project still declared `print_settings_id: 0.20mm Standard @BBL X2D`,
  the name of a system preset. Bambu Studio resolves that name against its own
  preset and reloads the stock values, discarding what the file carries. The
  project now declares its own name, `0.20mm PETG snap-fit case @BBL X2D`,
  inheriting the standard one, so the dropdown shows that entry and the
  overrides survive.

If you prefer importing, install the standalone process preset instead:
`bambu-presets/0.20mm PETG snap-fit case @BBL X2D.json`, via Bambu Studio's
preset import. It inherits `0.20mm Standard @BBL X2D` and overrides only what
this part needs, so it stays selectable from the process dropdown no matter how
the geometry was loaded.

One setting cannot live in a process preset: part cooling. Cap the fan at
about 45 per cent in the PETG **filament** profile. It trades surface finish
for layer adhesion at the root of the clips, which is where they break.

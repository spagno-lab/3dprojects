# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
Three printed parts — shell, lid and base plate — plus two reference bodies
used to check the fit visually in Fusion 360.

Run `python3 fit_check.py` before printing anything.

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

## Three parts, split at board level

The box parts on the top face of the PCB. There are three printed pieces:

- **base** — floor, four standoffs, the pocket that locates the board, and the
  four snap tabs;
- **shell** — everything above the board: the I/O openings, the pads that hold
  the board down, the lid seat and the SMA hole;
- **lid** — vent mesh and the GPS cradle, unchanged.

### Why it has to be split

The Pi 4 is not 85 x 56 mm. That is the PCB. The connectors stand outside that
outline, and the USB and Ethernet stack stands **2.81 mm** outside it. So the
board's real envelope is 87.8 x 60 mm.

A box sized to the PCB therefore cannot be assembled at all, whatever holds the
board down:

- the connectors have to end up inside the wall, 1.8 mm past its inner face;
- so they have to enter the wall openings;
- so the openings must be open on the side the board arrives from.

Two revisions were spent designing retention for a board that had no way of
reaching the pocket. The first slid the board under rear lips that needed
1.2 mm of travel in a 0.4 mm gap, and put one of them on top of the GPIO
header. The second replaced them with snap clips, which fixed a real defect and
changed nothing about the board still not fitting.

Splitting at the top face of the PCB is what makes assembly possible: above
that plane the board is gone and only its connectors remain, so every opening
can be open at its bottom edge. The shell comes down over the board and the
connectors enter from below. Nothing ever passes through material.

This is what `pkoehlers/rpi-case-openscad` does — a Pi 4 case with an external
antenna, so the same problem — where `topSelector` splits the case "with a
small lip for the IO". That model's connector table is the same one this file
uses: same positions, same widths, same heights. Only the `-2.81` overhang and
the 1.2 mm clearance had not come across, which is precisely what broke.

### Clearance

1.0 mm per side, against 1.2 in the reference model. Slightly less because the
board here also sits on four standoffs, which centre it. The 0.4 mm it used to
have was below what FDM resolves across an 85 mm pocket.

### Holding the board

Four rigid pads on the underside of the shell press the PCB onto the
standoffs. They reach 1.2 mm over the edge and 0.15 mm below the parting
plane, so the board is clamped rather than free to rattle; the PCB and the
standoffs absorb the interference.

Nothing snaps over the board any more. The shell traps it.

| pad | wall | offset | what makes that stretch free |
|---|---|---|---|
| 1 | front | 61 mm | past the audio jack, which ends at 58.1 mm |
| 2 | left | 6 mm | front corner, before the microSD opening |
| 3 | left | 38 mm | behind the microSD opening |
| 4 | rear | 59 mm | past the GPIO header, which ends at 54.3 mm |

### Holding the shell

Four snap tabs, one per corner, rise from the base wall into slots in the
shell. The corners are the only stretches of wall that no connector reaches
from either side, which is why they are all in the same place on every wall.
The arm is the inner 1.0 mm slice of the base wall carried above the parting
plane, so it is rooted in thick material, and the bump sits near its tip.

The whole joint fits inside the 2.5 mm wall: a 1.0 mm slot, a 0.6 mm bump
pocket and 0.9 mm of skin behind it. Nothing is thickened outward — the
outside of this case is flat, and growing a boss to make room for the joint
was the wrong way round. That is what sets the arm at 0.8 mm rather than 1.0,
which also drops the bending strain to 2.0 per cent.

## Test print before the real one

```python
# in run(), instead of shell/lid/gps_reference:
test_print(root)
```

`test_print()` emits the base plus a shell truncated to 17.4 mm. That covers
the pocket, the four standoffs, all four snap tabs, all four press pads and
every connector opening — everything that decides whether the board goes in.
It leaves out only the lid seat and the SMA hole, which an earlier print
already proved.

Printing the base on its own is not worth much: the snap tabs have no
counterpart without the shell, and the pads and the openings are all in the
shell. The base alone only checks the pocket and the standoffs.

## Checking the fit

```
python3 fit_check.py
```

`fit_check.py` imports the script with a stub in place of the Fusion API and
audits the geometry outside Fusion. It exits non-zero on failure, so it works
as a pre-commit hook.

It checks that nothing stands outside the outer footprint, board clearance,
that the connector envelope really does need
open-bottomed openings and that it gets them, that the parting plane is the top
face of the PCB, every pad and tab against every component envelope and every
wall opening, room for the tabs to flex, wall left behind each bump pocket,
snap strain, the SMA hole and its counterbore, and the lid rim against the
tallest opening.

It exists because three separate defects shipped and all three were invisible
in Fusion: geometry that looks right on screen and cannot be assembled.

## Snap strain

Both snap features were checked against the standard cantilever formula,
`strain = 1.5 * t * deflection / L^2`, since PETG yields around 5 per cent:

| feature | thickness | deflection | free length | strain |
|---|---|---|---|---|
| base snap tab | 0.8 mm | 0.6 mm | 6.0 mm | 2.0 % |
| lid latch | 1.2 mm | 0.6 mm | 5.0 mm | 4.3 % |

Earlier revisions failed this check badly: a clip arm rooted at board level
gave 4 mm of cantilever and 10 per cent strain, and a 1.6 mm lid rim with the
latch 2 mm from its root worked out at 60 per cent. Both would have snapped off
on first assembly. The fix is length, not thickness. `fit_check.py` re-runs
this table from the constants.

The tab only has to deflect 0.4 mm in practice, not 0.6: the slot already
gives it 0.2 mm of clearance before the bump touches anything.

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
| bottom shell layers | 5 | the base floor carries the four standoffs the board is clamped onto |
| outer wall speed | 120 mm/s | 200 rounds off the 0.6 mm latch features |
| fan max | 45 % | PETG layer adhesion at the root of the snap tabs matters more than surface finish |
| elephant foot | 0.15 mm | protects the 0.25 mm lid rim clearance |
| supports | off | see the orientation below: nothing needs them |

### Orientation

| part | on the bed | why |
|---|---|---|
| base | floor down | standoffs and snap tabs grow along Z, and the tabs bend across layer lines |
| shell | parting face down | the press pads land on the first layer and the I/O openings are open at the bed, so nothing bridges |
| lid | rim up | unchanged |

The 3mf project still carries the old single-piece case. Its process settings
are still the right ones, but the geometry in it is stale: regenerate the
bodies from the script before slicing.

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

## Preview

```
python3 preview.py                          # base, shell, lid, assembly
python3 preview.py assembly --res 0.15      # finer
python3 preview.py assembly --azimuth -140  # look at the I/O wall
python3 preview.py testprint                # what the test print gives you
```

Writes `preview-<name>.png`. No Fusion, no mesh library: it imports the script
with the Fusion API stubbed, records the extrude calls the builders make, and
replays them onto a voxel grid in the same order. What you see is what the
script would build, and it cannot drift, because there is no second model.

`assembly` and `fit` draw the Pi reference body in green inside the case,
through one depth buffer, so the board is seen through the openings rather
than painted over them. That is the picture that would have made the original
defect obvious in a second: connectors buried in a solid wall.

0.2 mm voxels resolve every feature here; the thinnest is the 0.8 mm snap tab.

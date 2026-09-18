# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
The script generates three separate bodies: case, lid, and a GPS reference
object used to check the cradle and SMA opening visually in Fusion 360.

## Revision after the first physical print

The first printed revision had four defects. All four are addressed here, and
the fixes are cross-checked against a measured screwless reference case
(`raspberry-pi-4-case-remix.stl`, Printables model 296102) whose geometry was
extracted from the mesh rather than guessed:

1. **The M2.5 screw posts are gone.** The board now drops onto four 3 mm
   standoffs whose 2.4 mm pegs enter the mounting holes, and four 2.2 mm
   cantilever clips snap 1 mm over the PCB edge. Clip thickness, length, and
   interference follow the reference case.
2. **The lid now latches.** The old rim cleared the cavity wall by 0.6 mm per
   side and had no catch at all, so it could never click. The rim is now
   continuous with 0.15 mm clearance and carries four bumps that drop into
   pockets cut 4 mm below the case rim.
3. **The SMA hole is 2 mm wider** (5.6 mm to 7.6 mm). The external counterbore
   grew to 9.6 mm so it still thins the wall around the antenna nut.
4. **The Pi sits against its openings.** The cavity was 91 x 62 mm for an
   85 x 56 mm board, leaving the connectors about 3 mm inboard of the walls.
   It is now the PCB plus 1 mm per side, and every port cut-out is generated
   from the PCB datum using the official Raspberry Pi 4 connector centres.

The resulting outer footprint is 92 x 63 mm, identical to the reference case.

## Reference geometry taken from the mesh

Measured directly from the donor STL, since mesh files carry no parameters:

- wall thickness 2.5 mm, outer footprint 92 x 63 mm;
- Pi standoffs on a 58.3 x 49.2 mm pattern, 5 mm diameter;
- lid clips 2.2 mm thick, 12 mm long, latching over roughly 1 mm.

Print orientation matters for the clips: they must be printed so the layer
lines are not perpendicular to the bending direction, otherwise they shear off
on first assembly.

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

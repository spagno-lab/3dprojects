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

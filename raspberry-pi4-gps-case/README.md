# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
The script generates the case body and lid as separate bodies.

## GPS carrier reference

The cradle follows the supplied photo and the measured dimensions of the blue
carrier:

- PCB envelope: 18 × 23 mm;
- SMA connector pointing toward the rear/top edge of the lid;
- SMA projection beyond the PCB edge: 10 mm;
- SMA axis 6 mm from the left PCB edge in the model (or 6 mm from the right
  edge when the physical module is mirrored), exposed through a 9 mm top-open
  rear slot;
- four-pin Dupont header on the opposite short edge, with an unobstructed cable
  path toward the Raspberry Pi;
- component side facing the inside of the case;
- four short side clips grip the PCB edges without spanning the SMA or header.

The board envelope and SMA position are user measurements. PCB thickness and
component height remain estimates; adjust `GPS_BOARD_THICKNESS`,
`GPS_MAX_COMPONENT_HEIGHT`, and `CLEARANCE` if caliper measurements differ. A
small cradle-only test print is recommended before printing the full case.

`GPS_MAX_COMPONENT_HEIGHT` records an 8 mm component keep-out estimate from the
photo. It does not set the clip height: the clips retain the PCB itself so they
do not press on the module components.

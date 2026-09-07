# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
The script generates the case body and lid as separate bodies.

## GPS carrier reference

The cradle follows the supplied ruler photo of the blue carrier:

- PCB envelope: approximately 22 × 30 mm;
- SMA connector centred on one short edge and exposed through a 9 mm top-open
  rear slot;
- four-pin Dupont header on the opposite short edge, with an unobstructed cable
  path toward the Raspberry Pi;
- component side facing the inside of the case;
- four short side clips grip the PCB edges without spanning the SMA or header.

The dimensions are estimates from a perspective photo. Measure the physical
board with calipers and adjust `GPS_BOARD_WIDTH`, `GPS_BOARD_LENGTH`,
`GPS_BOARD_THICKNESS`, and `CLEARANCE` before a final print. A small cradle-only
test print is recommended before printing the full case.

`GPS_MAX_COMPONENT_HEIGHT` records an 8 mm component keep-out estimate from the
photo. It does not set the clip height: the clips retain the PCB itself so they
do not press on the module components.

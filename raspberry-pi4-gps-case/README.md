# Raspberry Pi 4 GPS case

Parametric case for a Raspberry Pi 4 Model B and a clip-in u-blox GPS carrier.
The script generates three separate bodies: case, lid, and a GPS reference
object used to check the cradle and SMA opening visually in Fusion 360.

## GPS carrier reference

The cradle follows the supplied photo and the measured dimensions of the blue
carrier:

- PCB envelope: 18 × 23 mm;
- SMA connector pointing toward the rear/top edge of the lid;
- SMA projection beyond the PCB edge: 10 mm;
- with the chip facing inward, SMA axis 6 mm from the right PCB corner,
  exposed through a 10 mm top-open rear slot aligned to the retaining cradle;
- four-pin Dupont header on the opposite short edge, with an unobstructed cable
  path toward the Raspberry Pi;
- component side facing the inside of the case;
- four short side clips grip the PCB edges without spanning the SMA or header;
- the rear-right corner stop is omitted so it cannot obstruct the offset SMA.

The board envelope and SMA position are user measurements. PCB thickness and
component height remain estimates; adjust `GPS_BOARD_THICKNESS`,
`GPS_MAX_COMPONENT_HEIGHT`, and `CLEARANCE` if caliper measurements differ. A
small cradle-only test print is recommended before printing the full case.

The third GPS reference object reproduces the measured top-view envelope as a
single body: an 18 × 23 × 1.6 mm PCB joined to a 10 × 10 mm SMA extension whose
axis is 6 mm from the PCB's right edge. It is positioned inside the lid cradle
with a 0.2 mm visual separation from the lid.

`GPS_MAX_COMPONENT_HEIGHT` records an 8 mm component keep-out estimate from the
photo. It does not set the clip height: the clips retain the PCB itself so they
do not press on the module components.

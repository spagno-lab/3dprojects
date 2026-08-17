# Bracelet display stand

Parametric T-shaped bracelet display stand. It generates a base with an upright
post and a removable display bar with a matching socket. The two-piece design
can be printed flat with minimal support.

Both printable parts are generated as separate bodies in the active root
component, so the script also works in Fusion part-design documents that allow
only one component. The display bar is placed flat behind the base with a
configurable `PRINT_GAP`, rather than overlapping the upright in its assembled
position.

The display bar is a 24 mm cylinder with a round socket boss underneath. The
bar, boss, and blind mounting socket are resolved as temporary BRep geometry
before the single finished body is added to the document. This avoids Fusion
part-document feature joins leaving the boss behind as a third body. The
upright is also cylindrical and uses a slimmer 18 mm diameter, with a wider
round foot where it meets the base. All diameters are configurable.

The cylindrical bar is generated horizontally and may require slicer supports
along its lower surface.

Adjust the dimensions and `FIT_CLEARANCE` at the beginning of the script for the
material and printer in use. Default assembled size: 230 × 95 × 206 mm.

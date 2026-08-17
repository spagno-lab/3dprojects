# 3D Projects

An experimental collection of parametric, 3D-printable designs created with
the help of large language models.

The goal of this repository is to explore how models such as **GPT-3.6 Sol**
can participate in a practical CAD workflow: turning a plain-language idea
into a configurable Python script, generating geometry inside Autodesk Fusion,
and iterating on the result until it is ready for a physical print.

This is not a gallery of one-click AI output. Each project is an experiment in
the full feedback loop between human intent, LLM-generated code, CAD validation,
real-world measurements, tolerances, slicing, printing, and physical testing.

## Why this repository exists

Most generative AI demonstrations stop at text or images. These experiments ask
a more concrete question: can an LLM help design an object that must exist in
the real world, fit other objects, survive assembly, and be manufactured on a
consumer 3D printer?

The scripts in this repository are used to explore:

- translating natural-language requirements into parametric geometry;
- generating and refining Autodesk Fusion scripts with an LLM;
- keeping important dimensions and print clearances easy to adjust;
- organizing reusable CAD experiments as normal source code;
- testing the gap between syntactically valid CAD automation and printable
  geometry;
- feeding Fusion errors and physical print results back into the next design
  iteration.

## Projects

### Raspberry Pi 4 GPS case

`raspberry-pi4-gps-case/`

A case for a Raspberry Pi 4 Model B with a clip-in u-blox NEO-M8N GPS carrier,
accessible Pi ports, ventilation, a removable lid, and an external antenna
opening. The carrier dimensions are deliberately parameterized because the
final geometry depends on physical measurements of the specific board.

### Bracelet display stand

`bracelet-display-stand/`

A two-piece T-shaped stand for displaying bracelets. The base and upright form
one printable body; the removable, rounded display bar uses a configurable
press-fit socket. Its overall size, bar dimensions, edge radius, post
dimensions, and fit clearance can all be changed at the top of the script.

## How the workflow works

1. Describe the object, its purpose, constraints, and approximate dimensions.
2. Use an LLM to turn those requirements into a parametric Fusion Python script.
3. Run the script in Fusion and inspect the generated components and bodies.
4. Report API errors, geometric failures, or awkward design choices back to the
   model.
5. Export the validated bodies, slice them, and print a prototype.
6. Measure the result and update dimensions, clearances, and geometry.

The Python files are the source of truth. Generated Fusion documents and mesh
exports can always be recreated after adjusting the parameters.

## Running a project

Requirements:

- Autodesk Fusion with the Design workspace available;
- a supported Python runtime provided by Fusion;
- a slicer and 3D printer for physical validation.

Copy the complete project directory into the Fusion Scripts folder. In Fusion,
open or create a Design, then select **Utilities → Add-Ins → Scripts and
Add-Ins** and run the project script.

Each directory contains:

- a Python script that generates the model;
- a Fusion `.manifest` file;
- a project README with design-specific notes.

Dimensions are expressed in millimetres and collected near the beginning of
each script.

## Experimental status

These designs are prototypes. Python syntax validation only proves that a file
can be parsed; it does not prove that every Fusion operation succeeds or that
the generated object is safe and printable. Always inspect the model, verify
critical dimensions, check wall thickness and clearances, and print a small
test piece before committing time and material to a full build.

The interesting part of this repository is precisely that boundary between
generated code and physical reality.

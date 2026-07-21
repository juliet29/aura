# aura

[![DOI](https://zenodo.org/badge/1291731033.svg)](https://doi.org/10.5281/zenodo.21466574)

This repository accompanies the paper "AURA: Automated Universal floor plan Replication for Airflow and thermal analysis". It transforms SVGs drawn on images of floorplans into EnergyPlus models, runs a sensitivity analysis, and validates the approach. [`svg2plan`](https://github.com/juliet29/sv2) transforms SVGs into vectorized data, while [`plan2eplus`](https://github.com/juliet29/plan2eplus) transforms vectorized data into energy models.

## Installation

Clone this repository. It temporarily relies on editable local versions of several dependencies, which must be cloned as sibling directories alongside `aura`.

The main dependencies:

- [`plan2eplus`](https://github.com/juliet29/plan2eplus)
- [`svg2plan` (`sv2`)](https://github.com/juliet29/sv2)

and their supporting libraries:

- [`polyfix`](https://github.com/juliet29/polyfix)
- [`plyze`](https://github.com/juliet29/plyze)
- [`utils4plans`](https://github.com/juliet29/utils4plans)

The project is managed with [`uv`](https://docs.astral.sh/uv/); run `uv sync` once the siblings are in place. `TEMP_PATH` is read from a `.env` file (default `static/4_temp`).

## Source Files

In `src/aura2`, the code is driven by three command-line entry points (`src/aura2/cli`):

- `au` generates and runs the sensitivity campaign through a Snakemake workflow, and collects the paper figures (`au collect`).
- `aus` runs the real-plan studies.
- `auv` runs the validation studies: `epc` compares a built model against an EnergyPlus reference case, and `rob` tests the robustness of the geometry alignment.

## Static Files

`static/1_inputs` holds the inputs (floor-plan SVGs, the reference IDF, and weather data). Intermediate data and working figures are written under `TEMP_PATH`; `static/5_figures` holds the figures selected for the paper.

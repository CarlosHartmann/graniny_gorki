
# graniny_gorki

## Setup

Ensure [Poetry](https://python-poetry.org/docs/#installation) and [Quarto](https://quarto.org/docs/get-started/) are installed, then run:

```bash
make setup
```

This installs all dependencies needed for analysis and Quarto execution.

If you do not have `make`, run this manually:

```bash
poetry install
```

Note: Poetry does not run project-defined post-install hooks, so automatic kernel registration is not reliable across machines. This repository therefore uses the standard `python3` kernel in QMD files and expects Quarto to be run from the Poetry environment.

## Usage

Render the main results notebook with:

```bash
poetry run quarto render notebooks/results.qmd
```

or preview it interactively:

```bash
poetry run quarto preview notebooks/results.qmd
```

The same pattern works for other QMD files, e.g.:

```bash
poetry run quarto render notebooks/discarded.qmd
poetry run quarto render cost/explanations.qmd
```
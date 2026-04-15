
# graniny_gorki

## Setup

Ensure [Poetry](https://python-poetry.org/docs/#installation) is installed, then run:

```bash
make setup
```

This installs all dependencies and registers the Jupyter kernel used by the Quarto notebooks.

If you do not have `make`, run the two steps manually:

```bash
poetry install
poetry run python -m ipykernel install --user --name graniny_gorki
```

## Usage

Render the main results notebook with:

```bash
quarto render notebooks/results.qmd
```

or preview it interactively:

```bash
quarto preview notebooks/results.qmd
```
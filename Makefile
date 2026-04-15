.PHONY: setup

setup:
	poetry install
	poetry run python -m ipykernel install --user --name graniny_gorki

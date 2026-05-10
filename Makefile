.PHONY: help install dev test lint clean uninstall

help:
	@echo "Targets:"
	@echo "  install    pipx install --force . + sudo absolute-path install"
	@echo "  dev        python -m pip install -e .[dev] inside a venv"
	@echo "  test       pytest"
	@echo "  lint       ruff check"
	@echo "  uninstall  sudo absolute-path uninstall + pipx uninstall"

install:
	pipx install --force .
	sudo "$$(command -v nv-fancurve)" install

dev:
	python -m pip install -e '.[dev]'

test:
	pytest -v

lint:
	ruff check .

uninstall:
	-sudo "$$(command -v nv-fancurve)" uninstall
	pipx uninstall nv-fancurve

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

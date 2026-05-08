.PHONY: help install dev test lint clean uninstall

help:
	@echo "Targets:"
	@echo "  install    pip install + sudo nv-fancurve install"
	@echo "  dev        pip install -e .[dev]"
	@echo "  test       pytest"
	@echo "  lint       ruff check"
	@echo "  uninstall  sudo nv-fancurve uninstall + pip uninstall"

install:
	pip install .
	sudo nv-fancurve install

dev:
	pip install -e .[dev]

test:
	pytest -v

lint:
	ruff check .

uninstall:
	-sudo nv-fancurve uninstall
	pip uninstall -y nv-fancurve

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

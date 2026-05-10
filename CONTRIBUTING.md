# Contributing

Thanks for helping improve `nv-fancurve`.

## Development Setup

```bash
git clone https://github.com/alicankiraz1/nv-fancurve.git
cd nv-fancurve
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Workflow

1. Fork the repository.
2. Create a branch from `main`.
3. Make the smallest focused change that solves the issue.
4. Run the checks before opening a pull request:

```bash
make test
make lint
```

## Pull Request Notes

Please include:

- What changed.
- Why the change is useful.
- How you tested it, including distro, driver version, and GPU model when hardware behavior is
  involved.

Hardware-specific reports are especially valuable because NVIDIA fan control behavior can vary by
driver, board firmware, and card family.

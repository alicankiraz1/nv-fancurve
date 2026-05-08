# Publishing Notes

## GitHub Repository

Suggested description:

```text
Temperature-based fan curve daemon for NVIDIA GPUs on headless Linux, built for sustained ML inference and training workloads.
```

Suggested topics:

```text
nvidia, gpu, fan-control, linux, headless, rtx, blackwell, thermal-management, systemd, ml-infrastructure
```

## First Publish

```bash
git init -b main
gh repo create alicankiraz1/nv-fancurve --public --source=. --remote=origin
git add .
git commit -m "feat: initial nv-fancurve release"
git tag -a v0.1.0 -m "v0.1.0"
git push -u origin main
git push origin v0.1.0
```

Use the `CHANGELOG.md` entry for `0.1.0` as the GitHub Release notes.

## LinkedIn Announcement Draft

Long-running inference loads expose a different thermal profile than short benchmark bursts.
I built `nv-fancurve`, a small open-source daemon for headless Linux machines with NVIDIA GPUs, after
seeing workstation cards sit hotter than I wanted during sustained LLM dataset generation. It runs
a tiny Xorg display, reads temperatures with `nvidia-smi`, and applies a TOML fan curve through
`nvidia-settings`.

The goal is boring, inspectable infrastructure: systemd-managed, configurable, and easy to revert.
On my RTX PRO 6000 setup, the curve reduced peak temperature from `<before C>` to `<after C>` during
`<workload>`. If you run RTX / Blackwell cards in headless ML rigs and have fought default fan
behavior, this may save you a little thermal anxiety.

# WebV Experiment

## Structure

`webv.md` is the bullet list of requirements for WebValidate - it was generated using Claude from <https://github.com/bartr/webvalidate>

`webv-prd.md` and `sessions.md` are generated from the docs directory

## Docs

`create-prd.mdc` and `prd-template.md` are used to go from `stream of conciousness md file` to PRD

`METHODOLOGY.md` is used on the PRD to plan 90-120 minute implementation sessions

## Python Bootstrap

Use the repo bootstrap script to set up a local virtual environment and install
Python dependencies without modifying system Python.

```bash
cd ~/webv
./bootstrap.sh
source .venv/bin/activate
```

If virtual environment creation fails on Debian/Ubuntu, install venv support:

```bash
sudo apt install python3-venv
```

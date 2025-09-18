# yourpkg

A tiny example package that imports **pandas** and exposes a CLI entry point `yourpkg-run`.

## Quickstart

```bash
python -m pip install --upgrade build
python -m build
# then install the wheel that appears in dist/
pip install dist/yourpkg-0.1.0-py3-none-any.whl

# run it
yourpkg-run
```

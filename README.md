# ReddYT
Semi-automatic pipeline for posting top Reddit posts/comments to YouTube shorts, with Discord integration for curation and eventual ML



## How to build PyInstaller executable
```
pip install google-cloud-core
PyInstaller --onefile --clean --collect-data pyshadow discord_main.py
```
That might fail with a 'lower' problem so add this to the spec:
```python
import os
import importlib
proot = os.path.dirname(importlib.import_module('asyncpraw').__file__)
datas = [(os.path.join(proot, 'praw.ini'), 'asyncpraw')]
```
and then run
```
PyInstaller --clean discord_main.spec
```
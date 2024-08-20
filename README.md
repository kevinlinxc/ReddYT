# ReddYT
Semi-automatic pipeline for posting top Reddit posts/comments to YouTube shorts, with Discord integration for curation.

Example of a video made automatically: https://www.youtube.com/shorts/aR66m36bFkg


## Introduction
This project took a bunch of Python libraries and smashed them together to make a marvel of human-computer interaction.

Basically, a Discord bot launches and then:
1. You run a command to get the top Reddit posts of the day using PRAW,
2. The bot shows the posts to you, you react to the message to select one
3. The bot fetches comments for the post you chose, you react to choose the funniest ones
4. The bot uses selenium to gather screenshots of the post and the comments you chose, Google API TTS to generate voiceover, then generates a video using moviepy
5. The bot shows you the final output once for curation, and upon confirmation, uploads it to YouTube using their (limited) API

I ended up shutting down this project after a few weeks because I felt bad for making slop, but the Reddit API pricing changes soon made it hard to justify anyway. 



## PyInstaller notes for myself
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

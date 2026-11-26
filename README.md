# The World in One Day — Thursday 26 November 2026

[![make.fun](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/bounty/news-image-20261126)
[![make.fun rank](https://make.fun/badge/news-image-20261126/haidildariell/news-image-20261126-v1/rank.svg)](https://make.fun/bounty/news-image-20261126)
[![make.fun reward](https://make.fun/badge/news-image-20261126/haidildariell/news-image-20261126-v1/reward.svg)](https://make.fun/bounty/news-image-20261126)

https://make.fun/bounty/news-image-20261126

A self-contained Python 3.13 program (standard library only) that draws one
1024x1024 PNG summing up the world's news of Thursday 26 November 2026:
34 stories across 6 continents — 3 hero stories, 10 illustrated cards,
a UTC timeline, a day-in-numbers strip, a world map with numbered story
locations, an "also on this day" list, and a date check in the footer.

Run: `MAKEFUN_OUTPUT_DIR=out python3 main.py` — writes `out/entry.png`.
The program reads no files and uses no network; two runs produce
byte-identical output. All text is rendered from a bitmap glyph atlas
embedded in `main.py`; all art is drawn with a small built-in 2D library
and the PNG is encoded with a built-in encoder.

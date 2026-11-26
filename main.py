#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Thursday 26 November 2026.
Self-contained stdlib-only program: draws the day's world news as one
1024x1024 PNG and writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
No file reads, no network, fully deterministic (two runs = same bytes).
All text is rendered from a 1-bit bitmap glyph atlas embedded below
(rendered at build time from DejaVu; at runtime only blitted).
"""
import base64
import json
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if t == 1:
                self.set(x0, y0, c)
            else:
                self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) * (yy - cy)) ** 0.5) if abs(yy - cy) <= r else 0
            if dx:
                self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, c)

    def circle(self, cx, cy, r, c, t=1):
        for a in range(360):
            import math
            x = int(cx + r * math.cos(math.radians(a)))
            y = int(cy + r * math.sin(math.radians(a)))
            if t == 1:
                self.set(x, y, c)
            else:
                self.fill_rect(x - t // 2, y - t // 2, t, t, c)

    def fill_poly(self, pts, c):
        # scanline polygon fill, pts = [(x,y), ...]
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for yy in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    t = (yy - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), yy, max(1, int(xs[i + 1]) - int(xs[i])), 1, c)

    def fill_ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1.0 - ((yy - cy) / ry) ** 2
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, c)


# ---------------------------------------------------------------- PNG out
def _crc(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def _chunk(typ, data):
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", _crc(typ + data))


def write_png(cv, path):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        row = bytes(cv.px[y * stride:(y + 1) * stride])
        # filter 1 (Sub) usually wins on flat art; pick per row by |sum|
        sub = bytearray(stride)
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            sub[i] = (row[i] - left) & 0xFF
        s0 = sum((b if b < 128 else b - 256) for b in row)
        s1 = sum((b if b < 128 else b - 256) for b in sub)
        if abs(s1) < abs(s0):
            raw.append(1)
            raw.extend(sub)
        else:
            raw.append(0)
            raw.extend(row)
    comp = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", comp)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- atlas text
ATLAS_W = 1024
ATLAS_H = 352
ATLAS_Z = (
    "eNrUvQ9wHNd5J/jevGF3U2p195Cy0rBa0wOQYZic9qpHdOTmaowZgAgFJ0yi+FJX2t3sVg+ho7QbJdWIfPGoPAu8wUCYkT0GSG/2"
    "CqrwZNm5vUul7uqk3dSVrs4Xv+EwA7oOJp3bqi3monN6BJeZqlPsxurqPCpPpu/7ugd/+E+iHHvjNAkQmD/96+973/f7ft97r4cz"
    "aXLFqT2YW1/e0twjK+5Ws6Y31YLhbzUs98KhmcwhC360j748Mfv5t6dNcqrp/szY5Uzuv111t1q/89Ppr5yvzHj0vgdzV9yZqdTB"
    "K79iuX65t7FqTaQmc27Fqcz3bqweNl5unhjTslbhxe0TJ46eOde/UubG23LK9aYfPFkqZcwcIRdSyllF+SK5j7DUtPnJ1IxRqh1a"
    "ftic+OShmfTR2T/OPZWi6QLjOTkDr37w5aNfnH2SfOXL95Hl8QufO/7iU97sqZSi/JKimuUU/fxDExaxlGV3tp1Pj2WMNeXEw4cP"
    "HTtamsqPf7ryqNmceJL/RzVVLZUmc98sGUafKJmU8gdN5Q9EWl9aHjv+i6mjxsULh9OHDk3/zuHlNCn9npMrjROSbpZmUzOZ3Beb"
    "s7/XNI7/wSnAz5VJ1fvmp5Wza+fJK6riv9GpaY9POJOS+eZzL9YyN163jZZSfCR/+OyjXnl8/Ncd11n2CP23aSlXKhnmo7+eUXLk"
    "4HjazK0agVLjivLfH51P/Yw1s304/ZGHJqYO1dNHn1rO5ZbBbrZ68n84uUGOL6fcrdLb7lRp+cVlg5LjlUd/QxlPEfKyYo7lznXu"
    "z06YxHTOPD1by6cPHzZWlX/wU5nsRMGcyvfecsz4VO9uZAshmVQenDU4/Ppl5UB40DjPCRxW4ZMTM8bMhUPLH3nw6NREafmos/nU"
    "eGoCnjpIS/BEDl9FGHylCZ6rav7cpuIB/udVZyw8e2ksnZJIjrrVM4n/P6/8LFzFsaOz5dfa158zPHxPqvQYKZUU98ynM3Aeo7Pq"
    "HlklW4if9mb8TuO8Wzv0JMRf6e0n025udvZIQBE/VcosZxx4GY8vVQF8yp/yz1SVEiFUyxb88c6KZuFzzpXLEH/f1iH+1sYPZ43C"
    "sUopEOubZn/JA3zxECmR4yQ5DLLvMG96MDf6LXUIvmn0NUKpwvdePFNKXqMiPrnpcEb/0uTl0u4TlwCfiSwpkfc9vLs8ntr/S5p8"
    "4EHJT+pRqSk1e80qVG4Y/+rYG+euSUdIOvcUbTrAJulvj69okE/zWw2FN96mbdHubTTWrInxQ8bpCct1/d57hw5NzDbfO++JlGa4"
    "mXY2N517stxp6Nbbh2Y+9clMuynInx5ImfWlTFo53Dy1mi2Y4daNVVOc2iZB4IfXAf+hrz9+9PoXjDem/+xSXR2XZo4/tW3Mzp4C"
    "x05M00NmiU/McEaoOO3UJo7OKBMT4w8a5x6DH2fPT2UyR4/PZsj4+DY1cpmJQzmSm7kwMfOy0Th09B8756eV0pU/PaD/g1Qq/68V"
    "U51ZSqXdGoen65wEJ0z/+iwntUOfP/TobL1woVOuLyvjtWXa5yKnHNEFmZ6iKaXEp2e4KgfOlGhPpGeU3MS4aZz9OcTnUxmgE2cc"
    "+IPoBsm8nQL7ITtnasalQ8dnc68tKeMOtz/304zkVosGaXUl1a2R7l9wiYXu2b/y1yvbyhsPfR38v2aEnXJ5zcwJCOb2//gpJbdE"
    "yPR0Sj3uB1MNsJ+Il352/NvpJ1dPTwL+L/7clLvke4hv5GL8g5b3Z/Jj7vTxmQvHZl4xJg4Zzz81JSkOEfdpH93I5T6nELJ8SbKe"
    "3g4aa2aHEzH9h9dD8w2zjemjxLlGiTrO0zT0f/0MnpKkptKp48r56VKT8xSp/dr4ofTI//94YiI3M2tMGV/+dSc3hemnHTIvvJ09"
    "ivYfaeiZt7Pm0dlTl5AUbPml/yrILQN+q6umr4+9sdw+zz1KUn94/bp/Qekl+FZMaApwPHnNeDDBX5pWUlXl/NIUwQQ+8OXt0fgf"
    "Mj51DPHPT+VEczZXS+OLDxEjlTo67QBimsbcCOkN+OI+dmBGIGNRacnUqpn8cj0+36Wwv04uKG/szweMf0KC5qfxwkkNop34Xr0R"
    "P7c8kYH4b2L8Z6ePWTl3JigFvDkz/l6CT8+nrKPTxxP8+OAM8Q/pykYwjvhs7VXXDHvyavzsVKYV7nHd6Nghu/Tt1MTEzXSi7NIL"
    "R6KySJgiR1NH97+RKjvvydwh+YPbiPfeDul9nruFDRXyk30UKpVwe737vDM31pDrnc617pnnN5ub1WdMh8pNXao8e8VoKsNCJXxv"
    "4/wv//7z/+5EJ8PJ5w6SPEtlDqSR0lQLKK2zmiFrl1ldTAXbwXu9nrI8U+rms3BYxUzuDyYmMttAklRWtJT77KzRzLxTcLf//WrO"
    "e95rv2wuP537zFir2507eyT9zMyV68+r08qVkDeV9OxlxP+Lx2evv7JcOHPhuV5uxWhfuO++7PH0ktFKG2Rm6dDR4zUy8zKMCuXL"
    "zpcz1KylMsbybOnyY+OHxg8dShsXDo1P5ZAk4ZRGema5CWrrsaOzL08oudLpUo2ud33nM48oly+fnWPS6e513zWnYeDklikNWptE"
    "Vb54bPOVV+Tzs9vXy1tLxrT3ueL5n0ulcisw2DPTqTSk8MzL3NSF1zS+nKdKLUWVZb/0uZ9FfEPJZA6PczGujBtEbuZS1Rg/NbH8"
    "8oRWEecq754Ml/3cP/3I+pOtI51O+hzgOw7iq2vK5NS3rxkvK79/9Mz1V+j68+U3w45mIHWYP/9SLvd7RUjK6bQ1mwnqqxzsr93f"
    "zvSosv32fLjslf7o58az41k1bXzxwde4mEJGSa8ZhanLa8bLmYmJ2QsTFOz32mNmt+L85sPNbnrOm5NONVzf8afQ/m+sHatsfOP8"
    "mvLvj8H4rxlVb/38RtcQhBelAzOv5TjYv7yUTg/A3VMZyiWa+rXtDNqfMZefKv3xT48b44eYkrlPqZVIDfHl5qtH3cYnjc9lJo5W"
    "tv9PLffM86XaK+vLZ3K/dLh1WTp7dk7q1J3rhof45CA/R/jL51fxZ27EDElEyoAEf/DAwZnSCN84qmTG07WYFA72MpkMjj+B8f/i"
    "sSPGkUwmnVHVS6U2jUlK4ROEN8+3MOtBdeYKlarYNrvnJstjjRXWOdJhdZZvOoMY/wF+jGy8DOIRX2yOqEYyBCUPZjP1xH62ljWV"
    "YERpVEkdDHrBe7RnLs9Ul45YRjajKVpavZQ7tR3jHyRHSUM5/zkjMclNslAdZeMedfkIp5NJwg+ef7l5Ewtm+D5Ku0VZpXO38NCe"
    "Ukvs10kBTmm8bNw7S1F+8++7b70Dpe5S9K20vkPSo4N/CIqi/EfOej85enTmwjMXjgCl0pfSS1opnDZyxtz6qUajUWt0Njr1FUcZ"
    "lApZJre3etth/3K51WEXz2b1Rj14971XljfPzZmDb1smqXeoOFW3TXNTjWzNtrOVzrGzZ15ZD+c1kjr+oOLWa8oSTZk1y7WsdCE7"
    "aVnj5Eifu7MXZsu5JWOKv3RA/iIoPfMPHc883Sai05VIt9t1KsRVx+WVucP5Wo1fLX+hzi5+5oS62Rk/317f/O1u+3VzWf1YtXSW"
    "wasPG8DVf/77D48dNkuXzs49F647UykJ8LM/C4w4XUuR1IRydELNGamJCRC0xE/PXHi6PJ4ypudfsq9+lIvTig/pPTPFRRdcsLIp"
    "KB9o5j97aaXDxgD/cnmNsYu/M966MpfnU83Nf9ERoXtJPUbYlkR+tZs3iar++Vh+7A3zxXePnHrT+6ZXTh3sHh8eB3zjNIw64Kek"
    "B3O59LEJIrG+ps6WzdcuIaXwA7r2xjuS6g9ApvVq9WXRbddXunlBJONTrUaXjW2/WxiWVxn79G/Ot96aK4ft9ev/os0DfwmyR5rb"
    "ki/rD9vmN1qv/KuHxx42zE6582boizaDFMwdfyxFjFN6gPhp68FCIW0dw6RXFdc7f76+aUBq2I3aP3LT6h9Ceq1MMXJNdKekDvq/"
    "Qj611p1jmVqtCfbX2fO/Pb7WnAuc8nrlibooeZfgRGxr/PJG137YWFO+/gqMv1np9Gqvr5e32wyE63Er/afnjV+sAStMKErqKFzF"
    "xEcxV/04l3naKFF+X2rp196UlBz0jCvtFSJ4t5MW0AeQkvlfNrvx+F+Mx//5Z0+oamfcaK/78yslT9SQvZijComNmVfxFxM8LZL+"
    "cQrtH6YOHPUAI8Y3UguInxoHqccT0R37/z59yQf/A71Q1tjY4Bv1upzoTuNXzScx/nkI8b+1pZ7LqnI9H5ZC58SyNzVox/g5SUjZ"
    "w+Y38BeDjVpXQcpIgLP3HdzBP6bkjqWlCeWYtI8DUgYfUWXKvBM75G/nIrH3bGJ/IAuJjBlfaN781ikJzjtbUDqvY9kiijU5Cfln"
    "GVZhH5fuUTq7oxrN7v4k30nF7qdaccuTkP8jfo8F/V2I3viRESu/K9Mq/CdR/9q0HoT9arUybjQvS5lmpZDVWeM/HjqoNJePgGT1"
    "SK1HgvH2SlOZSf+Tl+ov1X/h1Vyz+cWjEwX1FDSo4rXS26ymery0YY73grCg2fJGLwi6dO1tElZkWWyHC0W5m1/JtzT3O7Ze74WF"
    "RXPzhLk5Zy2cJLna0riyXCotjxsvp6V8c3kCf13KKOvLS9jXvkZKGUomJg42STr9zOmZ0zNdA/D/7YMTkLS1K2/XXtv+7ySqjHul"
    "a+apnGed0cw06eRf78rAr+aKLs29fNFzrNP5lY+rgJ9vdfPrZ1Wzm3+l1V7X8rw0vTROVkolPm58Pn0gP7syMd5cJksZ4/deoqUp"
    "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"
    "Pzq5/zSH/P9A0YJTf5rHfwFFJtgI"
)
GLYPHS_Z = (
    "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"
    "uK7ckw=="
)
_ATLAS_RAW = None
_GLYPHS = None


def _atlas():
    global _ATLAS_RAW, _GLYPHS
    if _ATLAS_RAW is None:
        _ATLAS_RAW = zlib.decompress(base64.b64decode(ATLAS_Z))
        _GLYPHS = json.loads(zlib.decompress(base64.b64decode(GLYPHS_Z)))
    return _ATLAS_RAW, _GLYPHS


def _glyph(font, ch):
    _, g = _atlas()
    f = g.get(font)
    if f is None:
        return None
    return f.get(ch)


def text_width(s, font):
    w = 0
    for ch in s:
        g = _glyph(font, ch)
        if g is None:
            continue
        w += g[4]
    return w


def draw_text(cv, x, y, s, font, color):
    """Draw s with its baseline at y (y = baseline row). Returns width."""
    raw, g = _atlas()
    f = g[font]
    asc = f["ascent"]
    pen = x
    for ch in s:
        gl = f.get(ch)
        if gl is None:
            continue
        gx, gy, gw, gh, adv, ox, oy = gl
        if gw > 0 and gh > 0:
            top = y - asc + oy
            for row in range(gh):
                ay = gy + row
                for col in range(gw):
                    bit = (raw[(ay * ATLAS_W + gx + col) // 8] >> (7 - ((gx + col) % 8))) & 1
                    if bit:
                        cv.set(pen + ox + col, top + row, color)
        pen += adv
    return pen - x


def draw_text_center(cv, cx, y, s, font, color):
    w = text_width(s, font)
    return draw_text(cv, cx - w // 2, y, s, font, color)


def wrap_text(s, font, maxw):
    words = s.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_width(trial, font) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, lines, font, color, lh):
    for ln in lines:
        draw_text(cv, x, y, ln, font, color)
        y += lh
    return y

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 232)
INK = (20, 33, 61)
NAVY = (20, 33, 61)
RED = (193, 39, 45)
GOLD = (232, 163, 23)
TEAL = (14, 124, 123)
SKY = (135, 190, 220)
SKY_D = (70, 130, 180)
ORANGE = (235, 120, 30)
FLAME = (245, 90, 20)
YELLOW = (250, 200, 60)
GREEN = (46, 125, 50)
GREY = (90, 95, 105)
LGREY = (210, 208, 198)
WHITE = (255, 255, 255)
CREAM = (255, 248, 220)
DARK = (30, 30, 34)
SMOKE = (120, 120, 125)
SEA = (40, 110, 160)
SAND = (222, 200, 150)


def flame(cv, cx, base, s, col1=FLAME, col2=YELLOW):
    """Simple flame: stacked triangles, base row at base."""
    cv.fill_poly([(cx - s, base), (cx - int(s * 0.45), base - int(s * 1.5)),
                  (cx, base - int(s * 0.7)), (cx + int(s * 0.45), base - int(s * 1.5)),
                  (cx + s, base), (cx, base - int(s * 0.35))], col1)
    cv.fill_poly([(cx - int(s * 0.5), base), (cx, base - int(s * 1.1)),
                  (cx + int(s * 0.5), base)], col2)


def smoke(cv, cx, cy, r):
    cv.fill_circle(cx, cy, r, SMOKE)
    cv.fill_circle(cx + r, cy - r // 2, int(r * 0.8), (150, 150, 155))
    cv.fill_circle(cx - r, cy - r // 3, int(r * 0.7), (105, 105, 110))


def building(cv, x, y, w, h, c, win=(255, 240, 150)):
    cv.fill_rect(x, y, w, h, c)
    for wy in range(y + 6, y + h - 4, 10):
        for wx in range(x + 5, x + w - 5, 11):
            cv.fill_rect(wx, wy, 5, 6, win)


def sun(cv, cx, cy, r):
    cv.fill_circle(cx, cy, r, GOLD)
    for k in range(8):
        import math
        a = math.radians(k * 45)
        x0 = int(cx + (r + 2) * math.cos(a))
        y0 = int(cy + (r + 2) * math.sin(a))
        x1 = int(cx + (r + 8) * math.cos(a))
        y1 = int(cy + (r + 8) * math.sin(a))
        cv.line(x0, y0, x1, y1, GOLD, 2)


# ---------------------------------------------------------------- scenes
# Each scene draws inside box (x, y, w, h). Flat illustration, no text.

def scene_fire(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (60, 60, 70))          # night road
    cv.fill_rect(x, y + h - 14, w, 14, (40, 40, 46))
    for i in range(0, w, 24):
        cv.fill_rect(x + i, y + h - 8, 12, 2, YELLOW)
    # tanker truck
    tx, ty = x + int(w * 0.18), y + h - 52
    cv.fill_rect(tx, ty, int(w * 0.5), 26, (200, 200, 205))
    cv.fill_rect(tx + int(w * 0.5), ty + 6, 22, 20, RED)
    cv.fill_circle(tx + 14, ty + 28, 7, DARK)
    cv.fill_circle(tx + int(w * 0.42), ty + 28, 7, DARK)
    cv.fill_circle(tx + int(w * 0.5) + 14, ty + 28, 6, DARK)
    flame(cv, tx + int(w * 0.25), ty, 26)
    flame(cv, tx + int(w * 0.38), ty + 4, 18)
    smoke(cv, tx + int(w * 0.3), y + 18, 14)
    smoke(cv, tx + int(w * 0.42), y + 10, 11)


def scene_refinery(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (255, 214, 140))       # dusk sky
    sun(cv, x + int(w * 0.8), y + 20, 12)
    cv.fill_rect(x, y + h - 16, w, 16, (90, 70, 50))
    bx = x + int(w * 0.08)
    cv.fill_rect(bx, y + h - 70, 14, 54, (120, 120, 125))   # chimney
    cv.fill_rect(bx - 3, y + h - 74, 20, 5, (90, 90, 95))
    cv.fill_rect(bx + 26, y + h - 56, 30, 40, (150, 80, 60))  # tank
    cv.fill_rect(bx + 26, y + h - 60, 30, 5, (120, 60, 45))
    cv.fill_rect(bx + 62, y + h - 48, 10, 32, (110, 110, 115))
    cv.fill_rect(bx + 78, y + h - 62, 34, 46, (140, 75, 55))
    cv.line(bx + 14, y + h - 40, bx + 60, y + h - 40, (90, 90, 95), 3)
    flame(cv, bx + 7, y + h - 74, 12)
    flame(cv, bx + 95, y + h - 62, 10)


def scene_parade(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_circle(x + int(w * 0.85), y + 16, 12, WHITE)
    cv.fill_circle(x + int(w * 0.78), y + 22, 9, WHITE)
    # buildings
    for i, bh in enumerate((34, 52, 40, 58, 30)):
        bx = x + i * int(w * 0.2)
        building(cv, bx + 4, y + h - bh, int(w * 0.16), bh, (90, 100, 130))
    # big balloon (turkey-ish round balloon)
    cx, cy = x + int(w * 0.5), y + int(h * 0.42)
    cv.fill_ellipse(cx, cy, 34, 26, (220, 80, 60))
    cv.fill_ellipse(cx, cy - 4, 22, 16, (240, 120, 80))
    cv.fill_circle(cx - 12, cy - 14, 4, WHITE)
    cv.fill_circle(cx + 12, cy - 14, 4, WHITE)
    cv.fill_poly([(cx - 6, cy + 24), (cx + 6, cy + 24), (cx, cy + 34)], GOLD)
    cv.line(cx, cy + 34, cx, y + h - 30, (60, 60, 60), 1)
    # confetti
    for (dx, dy, c) in ((10, 12, RED), (30, 26, GOLD), (w - 24, 14, TEAL),
                        (w - 40, 34, RED), (18, 44, TEAL), (w - 12, 52, GOLD)):
        cv.fill_rect(x + dx, y + dy, 4, 4, c)


def scene_stocks(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (250, 235, 220))
    # bars
    vals = (0.55, 0.7, 0.5, 0.8, 0.42, 0.6, 0.3)
    bw = w // 9
    for i, v in enumerate(vals):
        bh = int(h * v * 0.75)
        cv.fill_rect(x + 8 + i * bw, y + h - 12 - bh, bw - 4, bh, (120, 140, 160))
    # falling line
    pts = [(x + 8, y + 14), (x + int(w * 0.25), y + 26), (x + int(w * 0.45), y + 20),
           (x + int(w * 0.65), y + 44), (x + int(w * 0.85), y + 58), (x + w - 8, y + 74)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 3)
    cv.fill_poly([(pts[-1][0], pts[-1][1]), (pts[-1][0] - 12, pts[-1][1] - 2),
                  (pts[-1][0] - 2, pts[-1][1] - 12)], RED)
    cv.fill_circle(pts[0][0], pts[0][1], 3, RED)


def scene_taipei(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (210, 230, 245))
    # Taipei 101-ish tower
    tx = x + int(w * 0.55)
    for i in range(5):
        ww = 34 - i * 4
        cv.fill_rect(tx - ww // 2, y + 12 + i * 12, ww, 11, (60, 90, 130))
    cv.fill_rect(tx - 2, y + 2, 4, 12, (60, 90, 130))
    # skyline
    for i, bh in enumerate((26, 40, 32)):
        building(cv, x + 6 + i * 26, y + h - bh, 20, bh, (110, 130, 160))
    # tariff document with %
    cv.fill_rect(x + 8, y + h - 46, 34, 40, WHITE)
    cv.rect(x + 8, y + h - 46, 34, 40, INK, 1)
    cv.fill_rect(x + 12, y + h - 40, 26, 3, RED)
    cv.fill_rect(x + 12, y + h - 33, 26, 2, GREY)
    cv.fill_rect(x + 12, y + h - 27, 18, 2, GREY)


def scene_graft(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (235, 225, 205))
    # government hall with columns
    hx, hy = x + int(w * 0.12), y + 12
    cv.fill_poly([(hx, hy), (hx + 60, hy), (hx + 52, hy + 14), (hx + 8, hy + 14)], RED)
    cv.fill_rect(hx + 8, hy + 14, 44, 34, (200, 190, 170))
    for i in range(4):
        cv.fill_rect(hx + 12 + i * 11, hy + 16, 5, 30, WHITE)
    # magnifier over a document
    cv.fill_rect(x + int(w * 0.62), y + h - 40, 40, 30, WHITE)
    cv.rect(x + int(w * 0.62), y + h - 40, 40, 30, INK, 1)
    cv.fill_rect(x + int(w * 0.62) + 5, y + h - 34, 30, 2, GREY)
    cv.fill_rect(x + int(w * 0.62) + 5, y + h - 28, 22, 2, GREY)
    mx, my = x + int(w * 0.68), y + 22
    cv.circle(mx, my, 13, INK, 3)
    cv.line(mx + 9, my + 9, mx + 20, my + 20, INK, 3)


def scene_rocket(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (25, 25, 55))
    for (sx, sy) in ((12, 10), (w - 16, 22), (30, 30), (w - 34, 8), (w // 2, 6)):
        cv.fill_circle(x + sx, y + sy, 1, WHITE)
        cv.fill_circle(x + sx + 3, y + sy + 5, 1, WHITE)
    # station ring
    cv.fill_ellipse(x + int(w * 0.72), y + int(h * 0.3), 26, 8, (160, 160, 170))
    cv.fill_rect(x + int(w * 0.72) - 8, y + int(h * 0.3) - 5, 16, 10, (200, 200, 210))
    # rocket
    rx = x + int(w * 0.3)
    cv.fill_poly([(rx, y + 8), (rx - 10, y + 34), (rx + 10, y + 34)], WHITE)
    cv.fill_rect(rx - 10, y + 34, 20, 26, (220, 220, 225))
    cv.fill_poly([(rx - 10, y + 60), (rx - 16, y + 72), (rx - 10, y + 66)], RED)
    cv.fill_poly([(rx + 10, y + 60), (rx + 16, y + 72), (rx + 10, y + 66)], RED)
    flame(cv, rx, y + 62, 10)
    cv.fill_circle(rx, y + 40, 4, SKY_D)


def scene_gaza(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (240, 220, 190))
    # damaged block
    bx = x + int(w * 0.1)
    cv.fill_rect(bx, y + h - 52, 44, 52, (150, 140, 125))
    cv.fill_poly([(bx, y + h - 52), (bx + 22, y + h - 66), (bx + 44, y + h - 52)], (120, 110, 95))
    cv.fill_rect(bx + 6, y + h - 40, 8, 8, DARK)
    cv.fill_rect(bx + 26, y + h - 40, 8, 8, DARK)
    cv.fill_rect(bx + 6, y + h - 22, 8, 8, DARK)
    # cracked second block
    cv.fill_rect(bx + 56, y + h - 38, 36, 38, (165, 155, 140))
    cv.line(bx + 56, y + h - 38, bx + 74, y + h - 20, DARK, 1)
    cv.line(bx + 74, y + h - 20, bx + 66, y + h - 8, DARK, 1)
    smoke(cv, bx + 22, y + 16, 13)
    smoke(cv, bx + 70, y + 10, 9)
    # warning triangle
    cv.fill_poly([(x + w - 26, y + 8), (x + w - 8, y + 8), (x + w - 17, y + 24)], GOLD)
    cv.fill_rect(x + w - 18, y + 12, 2, 7, INK)
    cv.fill_rect(x + w - 18, y + 20, 2, 2, INK)


def scene_ukraine(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (200, 210, 235))
    # refinery + fire
    bx = x + int(w * 0.08)
    cv.fill_rect(bx, y + h - 58, 12, 42, (110, 110, 115))
    cv.fill_rect(bx + 18, y + h - 44, 34, 28, (140, 80, 60))
    cv.fill_rect(bx + 58, y + h - 52, 10, 36, (110, 110, 115))
    cv.fill_rect(bx + 74, y + h - 38, 26, 22, (150, 90, 65))
    flame(cv, bx + 6, y + h - 58, 12)
    flame(cv, bx + 35, y + h - 44, 14)
    flame(cv, bx + 87, y + h - 38, 10)
    smoke(cv, bx + 30, y + 14, 12)
    # missile trail
    cv.line(x + w - 10, y + 6, x + int(w * 0.6), y + 30, WHITE, 2)
    cv.fill_poly([(x + w - 10, y + 6), (x + w - 20, y + 4), (x + w - 16, y + 12)], RED)


def scene_losses(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (225, 225, 220))
    # bar of losses rising
    for i, v in enumerate((0.3, 0.45, 0.6, 0.75, 0.9)):
        bh = int(h * v * 0.7)
        cv.fill_rect(x + 10 + i * 16, y + h - 14 - bh, 11, bh, (140, 60, 55))
    # helmet + cross markers
    hx = x + int(w * 0.72)
    cv.fill_ellipse(hx, y + 22, 16, 9, (90, 100, 80))
    cv.fill_rect(hx - 16, y + 28, 32, 3, (90, 100, 80))
    for (cx2, cy2) in ((hx - 8, y + 52), (hx + 8, y + 58)):
        cv.fill_rect(cx2 - 1, cy2 - 6, 2, 12, GREY)
        cv.fill_rect(cx2 - 5, cy2 - 2, 10, 2, GREY)


def scene_hormuz(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + int(h * 0.55), w, int(h * 0.45), SEA)
    for i in range(4):
        cv.line(x + i * 30, y + int(h * 0.62) + (i % 2) * 8,
                x + i * 30 + 18, y + int(h * 0.62) + (i % 2) * 8, WHITE, 2)
    # tanker
    tx = x + int(w * 0.12)
    cv.fill_rect(tx, y + int(h * 0.5), int(w * 0.6), 16, (180, 60, 50))
    cv.fill_rect(tx + int(w * 0.6) - 16, y + int(h * 0.5) - 14, 16, 14, WHITE)
    cv.fill_rect(tx + 8, y + int(h * 0.5) - 8, 10, 8, (200, 200, 205))
    flame(cv, tx + int(w * 0.3), y + int(h * 0.5), 12)
    # naval mine
    mx, my = x + int(w * 0.82), y + int(h * 0.68)
    cv.fill_circle(mx, my, 8, DARK)
    for k in range(8):
        import math
        a = math.radians(k * 45)
        cv.line(mx + int(7 * math.cos(a)), my + int(7 * math.sin(a)),
                mx + int(12 * math.cos(a)), my + int(12 * math.sin(a)), DARK, 2)


def scene_trade(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + int(h * 0.6), w, int(h * 0.4), SEA)
    for i in range(4):
        cv.line(x + i * 34, y + int(h * 0.68) + (i % 2) * 8,
                x + i * 34 + 20, y + int(h * 0.68) + (i % 2) * 8, WHITE, 2)
    # container ship
    sx = x + int(w * 0.08)
    cv.fill_rect(sx, y + int(h * 0.52), int(w * 0.62), 14, (60, 70, 90))
    cv.fill_rect(sx + 4, y + int(h * 0.52) - 12, 14, 12, RED)
    cv.fill_rect(sx + 20, y + int(h * 0.52) - 12, 14, 12, GOLD)
    cv.fill_rect(sx + 36, y + int(h * 0.52) - 12, 14, 12, TEAL)
    cv.fill_rect(sx + int(w * 0.62) - 14, y + int(h * 0.52) - 18, 12, 18, WHITE)
    # big % sign (tariff)
    px, py = x + int(w * 0.78), y + int(h * 0.3)
    cv.fill_circle(px - 7, py - 8, 5, INK)
    cv.fill_circle(px + 7, py + 8, 5, INK)
    cv.line(px + 9, py - 12, px - 9, py + 12, INK, 3)


def scene_plane(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (210, 225, 240))
    cv.fill_circle(x + w - 18, y + 14, 10, GOLD)
    # tilted plane
    px, py = x + int(w * 0.3), y + int(h * 0.4)
    cv.fill_ellipse(px, py, 30, 7, WHITE)
    cv.fill_poly([(px + 8, py - 2), (px + 26, py - 14), (px + 20, py + 2)], (200, 200, 205))
    cv.fill_poly([(px - 6, py + 2), (px - 18, py + 12), (px - 10, py + 6)], (200, 200, 205))
    cv.fill_rect(px + 22, py - 8, 4, 10, SKY_D)
    # smoke trail + coast
    cv.line(px - 30, py - 4, px - 52, py - 14, SMOKE, 3)
    smoke(cv, px - 52, py - 16, 8)
    cv.fill_rect(x, y + h - 16, w, 16, SEA)
    cv.fill_rect(x, y + h - 20, int(w * 0.4), 4, SAND)

# ---------------------------------------------------------------- layout bits
STATUS_COL = {"CONFIRMED": (46, 125, 50), "REPORTED": (14, 124, 123),
              "CLAIM": (200, 110, 20), "OFFICIAL": (46, 125, 50)}


def chip(cv, x, y, region, source, status, maxw):
    font = "8b"
    label = region + " | " + source + " | " + status
    if text_width(label, font) > maxw - 12:
        # shorten the source first; never cut the status word
        label = region + " | " + status
    if text_width(label, font) > maxw - 12:
        label = status
    w = text_width(label, font) + 12
    cv.fill_rect(x, y, w, 15, STATUS_COL.get(status, TEAL))
    draw_text(cv, x + 6, y + 11, label, font, WHITE)
    return w


def card(cv, x, y, w, h, scene, kicker, headline, summary,
         region, source, status):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 1)
    scene(cv, x + 1, y + 1, w - 2, 80)
    cy = y + 96
    draw_text(cv, x + 8, cy, kicker, "9b", RED)
    cy += 16
    hl = wrap_text(headline, "12b", w - 16)
    for ln in hl[:3]:
        draw_text(cv, x + 8, cy, ln, "12b", INK)
        cy += 15
    for ln in wrap_text(summary, "9", w - 16)[:2]:
        draw_text(cv, x + 8, cy, ln, "9", (60, 60, 66))
        cy += 11
    chip(cv, x + 8, y + h - 22, region, source, status, w - 16)


def hero(cv, x, y, w, h, scene, kicker, headline, summary,
         region, source, status):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 2)
    scene(cv, x + 2, y + 2, w - 4, 118)
    cy = y + 138
    draw_text(cv, x + 10, cy, kicker, "10b", RED)
    cy += 22
    hl = wrap_text(headline, "18b", w - 20)
    for ln in hl[:2]:
        draw_text(cv, x + 10, cy, ln, "18b", INK)
        cy += 22
    for ln in wrap_text(summary, "11", w - 20)[:2]:
        draw_text(cv, x + 10, cy, ln, "11", (60, 60, 66))
        cy += 14
    chip(cv, x + 10, y + h - 24, region, source, status, w - 20)


def section_title(cv, x, y, title, right=""):
    draw_text(cv, x, y, title, "12b", INK)
    if right:
        draw_text(cv, x + 1000 - text_width(right, "9"), y, right, "9", GREY)
    cv.fill_rect(x, y + 5, 1012 - x, 2, RED)


# ---------------------------------------------------------------- content
HEROES = [
    (scene_fire, "1  MIDDLE EAST - EGYPT",
     "CAIRO TANKER FIRE KILLS 31",
     "Fuel tanker crash sets the ring road ablaze; 31 dead, 21 hurt, hospitals on alert.",
     "AFRICA", "EGYPT HEALTH MINISTRY", "CONFIRMED"),
    (scene_refinery, "2  MIDDLE EAST - SAUDI ARABIA",
     "HOUTHIS STRIKE RAS TANURA",
     "Yemen's Houthis say they hit the Ras Tanura refinery and Riyadh; Brent tops $94.",
     "MIDDLE EAST", "REUTERS", "CLAIM"),
    (scene_parade, "3  NORTH AMERICA - USA",
     "THANKSGIVING TURNS 100",
     "Macy's 100th parade marches through a stormy New York; Dog Show and 3 NFL games follow.",
     "NORTH AMERICA", "NBC / MACY'S", "CONFIRMED"),
]

CARDS = [
    (scene_stocks, "MARKETS", "NASDAQ SINKS 4% AS NVIDIA LEADS AI SELL-OFF",
     "AI-bubble warnings spread as chip stocks drag Wall Street down.",
     "NORTH AMERICA", "WSJ", "REPORTED"),
    (scene_taipei, "MARKETS", "TAIWAN SHARES FALL 1,927 PTS; NT$ PAST 33",
     "Taipei stocks slide with the global tech rout; currency weakens.",
     "ASIA", "TWSE", "REPORTED"),
    (scene_trade, "TRADE", "TAIPEI ANSWERS US TARIFFS WITH ITS OWN PLAN",
     "Taiwan unveils its response as Washington's new tariff plan lands.",
     "ASIA", "REUTERS", "REPORTED"),
    (scene_graft, "CHINA", "XI GRAFT PROBE REACHES SHANGHAI CHIEF CHEN",
     "Shanghai party chief Chen Jining under investigation in widening purge.",
     "ASIA", "REUTERS", "REPORTED"),
    (scene_rocket, "SPACE", "PAKISTAN'S FIRST ASTRONAUT JOINS CHINA'S STATION",
     "Muhammad Zeeshan Ali to fly on Shenzhou-24 to the Tiangong station.",
     "ASIA", "XINHUA", "REPORTED"),
    (scene_gaza, "MIDDLE EAST", "ISRAEL STRIKES HAMAS OFFICIAL IN GAZA",
     "Mohammad Abuelouf killed; the fragile ceasefire strains further.",
     "MIDDLE EAST", "REUTERS", "REPORTED"),
    (scene_ukraine, "WAR", "UKRAINE HITS RUSSIAN REFINERIES; PUTIN VOWS REVENGE",
     "Drone strikes on oil plants; Moscow promises retaliation.",
     "EUROPE", "REUTERS", "REPORTED"),
    (scene_losses, "WAR", "RUSSIA'S OWN COUNT: NEARLY 500,000 LOST IN UKRAINE",
     "Moscow's own figures put its war dead and wounded near half a million.",
     "EUROPE", "MOSCOW", "REPORTED"),
    (scene_hormuz, "ENERGY", "TWO OIL TANKERS HIT NAVAL MINES IN STRAIT OF HORMUZ",
     "Blasts damage two tankers in the world's busiest oil chokepoint.",
     "MIDDLE EAST", "REUTERS", "REPORTED"),
    (scene_plane, "USA", "PLANE CRASH OFF MISSISSIPPI KILLS 6, INCL. 2 CHILDREN",
     "Small plane goes down off the Gulf coast; six aboard dead.",
     "NORTH AMERICA", "USCG", "REPORTED"),
]

TIMELINE = [
    ("00:31", "CAIRO", "Tanker fire kills 31"),
    ("03:40", "HORMUZ", "Two tankers hit mines"),
    ("06:15", "TAIPEI", "Tariff answer unveiled"),
    ("08:30", "TAIWAN", "Shares fall 1,927 pts"),
    ("11:05", "GAZA", "Strike on Hamas official"),
    ("13:20", "UKRAINE", "Refinery strikes"),
    ("16:45", "NEW YORK", "Macy's 100th parade"),
    ("19:02", "NEW YORK", "Thanksgiving NFL kickoff"),
]

NUMBERS = [
    ("31", "killed in Cairo tanker fire"),
    ("$94", "Brent crude, a day high"),
    ("-4%", "Nasdaq, led by Nvidia"),
    ("1,927", "points lost in Taiwan"),
    ("500,000", "Russian losses, own count"),
    ("20", "hostages freed in Colombia"),
    ("6", "killed in Mississippi crash"),
    ("1,220", "players in IPL auction"),
]

ALSO_ON = [
    "Colombia frees 20 hostages after 17 hours",
    "India marks 18 years since 26/11 Mumbai attacks",
    "India celebrates Constitution Day",
    "Gukesh draws Sindarov, game 2 of World Chess final",
    "Vaibhav, 15, fastest List A double ton: 204 off 53",
    "Asteroid defence test close-ups reveal new crater",
    "Fed Beige Book: modest growth, split on inflation",
    "North Korea expels Swiss diplomat",
    "Solomon Islands-Australia historic security treaty",
    "Bangladesh garment wage up 36%",
    "US unveils new tariff plan for Japan, China, EU",
    "US Air Force unveils F-15EX at Kadena",
    "Duran Duran guitarist Andy Taylor dies at 65",
    "Brazil viral infections down 68% (Wolbachia)",
    "IPL 2027 auction lists 1,220 players",
    "Flipkart CEO steps down in December",
    "US AG dodges Nvidia probe questions",
    "US tightens remote AI-chip access rules",
    "26 miners trapped in Indonesia gold mine",
    "France seeks mineral independence",
    "Britain probes nuclear-test legacy",
]

# (number, lon, lat) for the world map dots
MAP_DOTS = [
    (1, 31.2, 30.0), (2, 50.2, 26.6), (3, -74.0, 40.7), (4, -77.0, 38.0),
    (5, 121.5, 25.0), (6, 127.0, 26.0), (7, 118.0, 34.0), (8, 73.1, 33.7),
    (9, 34.5, 31.5), (10, 32.0, 49.0), (11, 37.6, 55.8), (12, 59.0, 24.0),
    (13, -89.0, 30.2),
]


def draw_map(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (200, 225, 240))
    cv.rect(x, y, w, h, INK, 1)
    # rough continents (lon/lat -> map px)
    def P(lon, lat):
        mx = x + int((lon + 180.0) / 360.0 * w)
        my = y + int((90.0 - lat) / 180.0 * h)
        return (mx, my)
    conts = [
        [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-80, 73),
         (-60, 55), (-55, 47), (-70, 42), (-75, 35), (-80, 26), (-90, 21),
         (-97, 16), (-105, 20), (-115, 30), (-125, 40), (-125, 49), (-140, 60),
         (-155, 58), (-168, 66)],
        [(-78, 8), (-60, 5), (-50, 0), (-40, -5), (-35, -9), (-40, -20),
         (-48, -28), (-58, -35), (-65, -41), (-70, -52), (-73, -44),
         (-72, -30), (-77, -12), (-80, 0), (-78, 8)],
        [(-10, 35), (0, 36), (10, 37), (20, 32), (32, 31), (35, 28),
         (43, 12), (51, 12), (48, 0), (40, -10), (35, -20), (32, -29),
         (20, -35), (16, -28), (12, -18), (9, -2), (9, 4), (-8, 5),
         (-17, 15), (-17, 27), (-10, 35)],
        [(-10, 36), (-9, 43), (-2, 48), (0, 51), (5, 53), (8, 57),
         (12, 55), (18, 56), (21, 55), (24, 59), (30, 60), (30, 70),
         (40, 68), (45, 60), (40, 50), (35, 45), (28, 41), (23, 36),
         (19, 40), (12, 44), (3, 43), (-2, 37), (-9, 38), (-10, 36)],
        [(30, 70), (40, 68), (60, 69), (80, 73), (100, 77), (120, 76),
         (140, 72), (160, 70), (178, 65), (170, 60), (158, 52), (142, 45),
         (140, 40), (130, 33), (122, 30), (120, 22), (110, 20), (105, 9),
         (100, 8), (95, 16), (90, 22), (80, 13), (77, 8), (72, 20),
         (66, 25), (60, 25), (52, 27), (48, 30), (44, 39), (40, 36),
         (36, 36), (30, 36), (30, 70)],
        [(114, -22), (122, -14), (132, -12), (137, -15), (142, -11),
         (146, -19), (150, -23), (153, -27), (150, -37), (140, -38),
         (132, -32), (124, -33), (115, -35), (114, -22)],
    ]
    for c in conts:
        cv.fill_poly([P(lo, la) for lo, la in c], (190, 205, 160))
    for num, lon, lat in MAP_DOTS:
        mx, my = P(lon, lat)
        cv.fill_circle(mx, my, 7, RED)
        cv.circle(mx, my, 7, WHITE, 1)
        s = str(num)
        draw_text(cv, mx - text_width(s, "8b") // 2, my + 3, s, "8b", WHITE)


def main():
    cv = Canvas(W, H, PAPER)
    # ---- header
    draw_text(cv, 12, 50, "THE WORLD IN ONE DAY", "32b", INK)
    d = "THURSDAY 26 NOVEMBER 2026"
    draw_text(cv, 1012 - text_width(d, "14b"), 34, d, "14b", RED)
    s2 = "34 STORIES  -  6 CONTINENTS"
    draw_text(cv, 1012 - text_width(s2, "11b"), 56, s2, "11b", INK)
    cv.fill_rect(12, 66, 1000, 3, INK)
    sub = ("CAIRO: 31 DEAD IN TANKER FIRE   -   HOUTHIS HIT SAUDI REFINERY, "
           "BRENT TOPS $94   -   THANKSGIVING PARADE TURNS 100")
    draw_text_center(cv, 512, 88, sub, "11b", (60, 60, 66))
    # ---- heroes
    for i, (scene, kicker, head, summ, reg, src, st) in enumerate(HEROES):
        hero(cv, 12 + i * 336, 98, 328, 224, scene, kicker, head, summ, reg, src, st)
    # ---- cards
    for r in range(2):
        for c in range(5):
            (scene, kicker, head, summ, reg, src, st) = CARDS[r * 5 + c]
            card(cv, 12 + c * 204, 330 + r * 204, 196, 196, scene, kicker,
                 head, summ, reg, src, st)
    # ---- timeline
    section_title(cv, 12, 756, "THE DAY IN TIME  -  UTC", "AS REPORTED THROUGH THE DAY")
    tw = 1000 // 8
    for i, (t, place, ev) in enumerate(TIMELINE):
        tx = 12 + i * tw
        draw_text(cv, tx, 776, t, "11b", RED)
        draw_text(cv, tx, 790, place, "9b", INK)
        for j, ln in enumerate(wrap_text(ev, "9", tw - 8)):
            draw_text(cv, tx, 802 + j * 10, ln, "9", (60, 60, 66))
        if i:
            cv.line(tx - 5, 766, tx - 5, 806, LGREY, 1)
    # ---- numbers
    section_title(cv, 12, 822, "THE DAY IN NUMBERS", "")
    nw = 1000 // 8
    for i, (num, lab) in enumerate(NUMBERS):
        nx = 12 + i * nw
        draw_text(cv, nx, 848, num, "18b", INK)
        for j, ln in enumerate(wrap_text(lab, "9", nw - 8)):
            draw_text(cv, nx, 862 + j * 10, ln, "9", (60, 60, 66))
    # ---- map + also on
    section_title(cv, 12, 884, "WHERE IT HAPPENED", "")
    section_title(cv, 360, 884, "ALSO ON THIS DAY", "")
    draw_map(cv, 12, 894, 330, 78)
    cv.fill_rect(360, 894, 652, 78, WHITE)
    cv.rect(360, 894, 652, 78, INK, 1)
    colw = 320
    for i, item in enumerate(ALSO_ON):
        col = i // 11
        row = i % 11
        ix = 368 + col * 328
        iy = 905 + row * 7
        cv.fill_circle(ix + 2, iy - 1, 2, RED)
        draw_text(cv, ix + 8, iy + 2, item, "8", (50, 50, 56))
    # ---- footer
    cv.fill_rect(12, 982, 1000, 3, INK)
    draw_text(cv, 12, 998,
              "DATE CHECK: every story here happened or was first reported on Thursday 26 November 2026.",
              "10b", INK)
    draw_text(cv, 12, 1012,
              "Left out on purpose: news from 25 November and earlier.  CHIPS: CONFIRMED = confirmed by officials  |  "
              "REPORTED = reported by a named source  |  CLAIM = a party's claim, not yet verified.",
              "9", (60, 60, 66))
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    n = write_png(cv, path)
    print("wrote", path, n, "bytes")


if __name__ == "__main__":
    main()

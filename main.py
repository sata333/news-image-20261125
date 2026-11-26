#!/usr/bin/env python3
"""news-image-20261125: one image summing up Wednesday 25 November 2026.

Standard library only. Deterministic: two runs write byte-identical PNGs.
Draws a newspaper front page: masthead with the full date, a UTC timeline,
a world map with flashpoint markers, and 40 sourced stories in region
sections, plus a footer with the story count, sources and a date check.
"""

import binascii
import os
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (253, 253, 248)
INK = (20, 20, 31)
RED = (163, 18, 32)
NAVY = (20, 33, 61)
GREY = (90, 90, 102)
RULE = (201, 201, 194)
SEA = (215, 229, 239)
SEA_DOT = (178, 198, 214)
LAND = (51, 82, 107)
MARKER = (196, 18, 32)
WHITE = (255, 255, 255)
GOLD = (176, 124, 22)

# ------------------------------------------------------------- bitmap font
# 5x7 glyphs, '#' = on, '.' = off. Rendered text is upper-cased.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "\u2022": ("00000", "01110", "11111", "11111", "11111", "01110", "00000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
}

# Normalise curly punctuation and dashes to the glyphs we carry.
_NORMALISE = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u00b7": "\u2022", "\u00d7": "X",
    "\u2212": "-", "\u2011": "-",
}


def norm(text):
    out = []
    for ch in text.upper():
        out.append(_NORMALISE.get(ch, ch))
    return "".join(out)


def glyph(ch):
    return FONT.get(ch, FONT["?"])


def text_width(text, scale):
    return len(norm(text)) * 6 * scale - scale


def wrap(text, max_width_px, scale):
    """Word-wrap normalised text to lines fitting max_width_px."""
    words = norm(text).split(" ")
    lines, cur = [], ""
    limit = max_width_px // (6 * scale)
    for word in words:
        trial = word if not cur else cur + " " + word
        if len(trial) <= limit:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            base = (yy * self.w + x) * 3
            for xx in range(w):
                i = base + xx * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def hline(self, x, y, w, color):
        self.rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.rect(x, y, 1, h, color)

    def disc(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    self.set(cx + dx, cy + dy, color)

    def line(self, x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def text(self, s, x, y, scale, color):
        s = norm(s)
        cx = x
        for ch in s:
            g = glyph(ch)
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_centred(self, s, cx, y, scale, color):
        w = text_width(s, scale)
        return self.text(s, cx - w // 2, y, scale, color)


# --------------------------------------------------------------------- png
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    Path(path).write_bytes(png)
    return len(png)


# ------------------------------------------------------------------ content
# 40 stories, each first reported on Wednesday 25 November 2026 (UTC).
# Every story is kept to at most 76 characters so it fits two lines.
SECTIONS_LEFT = [
    ("AMERICAS", [
        "US proposes new tariffs on 14 trading partners. (Reuters)",
        "Nasdaq falls 2%, nearing bear market, as tariff fears hit. (Reuters)",
        "US October inflation data released; Fed rise priced in. (Reuters)",
        "Trump awards Rudy Giuliani the top US civilian honour. (SCMP)",
        "Unclassified CIA computer system breached, officials say. (SCMP)",
        "US soldier admits selling military secrets to Chinese buyers. (SCMP)",
        "Top Senate Democrat presses Nvidia over Huang's return. (Reuters)",
        "Police free hostages in Cartagena supermarket raid. (SCMP)",
        "Six killed, two of them children, in Mississippi plane crash. (JPost)",
    ]),
    ("EUROPE", [
        "Ukrainian drones hit two Rosneft refineries in Samara. (AP)",
        "Russian strike on Odesa kills two; Kyiv flats hit. (Just Security)",
        "Putin: Ukraine still hitting Russian refineries. (Just Security)",
        "Poland seeks permanent US military presence. (AP)",
        "Pope Leo XIV calls COP31 failure 'troubling'. (Reuters)",
        "Met Police still institutionally racist, report finds. (SCMP)",
        "Denmark bans headscarves for prosecutors. (SCMP)",
        "Burnham vows to end NDAs shielding abusers. (SCMP)",
        "Ex-Mossad chief Barnea addresses German parliament. (JPost)",
    ]),
    ("MIDDLE EAST", [
        "Two tankers hit naval mines and burn in Strait of Hormuz. (Just Security)",
        "Houthis say they hit Saudi Arabia's Ras Tanura refinery. (Just Security)",
        "Houthi strike hits Riyadh's tallest tower again; 11 hurt. (SCMP)",
        "Israeli strike kills Hamas security chief and family in Gaza. (SCMP)",
        "Fuel tanker fire on Cairo ring road kills at least 30. (Al Jazeera)",
        "Two Libyan officers die in Ukraine drone hit at Benghazi. (Just Security)",
    ]),
]

SECTIONS_RIGHT = [
    ("AFRICA", [
        "Sudan RSF drone strikes kill 19 civilians. (Just Security)",
        "Saudi national kidnapped by suspected IS militants in Niger. (Reuters)",
    ]),
    ("ASIA-PACIFIC", [
        "Shenzhou-24 lifts off with first foreign astronaut. (Xinhua)",
        "Australia, Solomons sign pact barring foreign bases. (Just Security)",
        "Asian stocks tumble: KOSPI plunges 6.2%, Nikkei falls 2.8%. (AP)",
        "Duran Duran guitarist Andy Taylor dies aged 65. (SCMP)",
        "Nvidia's Huang says he is in therapy as rally fades. (SCMP)",
        "US finds no evidence China told Alice Huang to spy on Nvidia chief. (SCMP)",
    ]),
    ("BUSINESS", [
        "US jury convicts Huawei on 10 of 12 counts, incl. bank fraud. (JPost)",
        "Dell reports record quarter: revenue $54.9bn, AI servers $22bn. (AP)",
        "Anthropic shares fall below $83 IPO price days after listing. (Reuters)",
        "CrowdStrike buys Zscaler in $44bn cybersecurity deal. (Reuters)",
    ]),
    ("TECH & SCIENCE", [
        "Microsoft declares 'Code Red' after historic outage. (Reuters)",
        "Retailers face rising AI cyberattack threat before Black Friday. (Reuters)",
    ]),
    ("SPORT", [
        "Champions League: PSG held 2-2 by Roma; Bayern lose at Lille. (AP)",
        "Barcelona win 4-1 at Sabah; Liverpool cruise 3-0 at Club Brugge. (UEFA)",
    ]),
]

TIMELINE = [
    ("00:18", "SHENZHOU-24 LIFTS OFF"),
    ("03:56", "SHENZHOU DOCKS"),
    ("13:15", "US PROPOSES NEW TARIFFS"),
    ("13:30", "US INFLATION DATA OUT"),
    ("~17:00", "CAIRO FIRE KILLS 30+"),
    ("21:00", "PSG HELD, BAYERN LOSE"),
]

# (name, latitude, longitude). Plotted with col=floor((lon+180)*0.3),
# row=floor((90-lat)*0.3) over the 108x45 land grid, rendered at 3px pitch.
MARKERS = [
    ("WASHINGTON", 38.9, -77.0),
    ("CARTAGENA", 10.4, -75.5),
    ("LONDON", 51.5, -0.1),
    ("PARIS", 48.9, 2.3),
    ("ROME", 41.9, 12.5),
    ("KYIV", 50.5, 30.5),
    ("GAZA", 31.5, 34.5),
    ("CAIRO", 30.0, 31.2),
    ("KHARTOUM", 15.6, 32.5),
    ("SAMARA", 53.2, 50.2),
    ("RIYADH", 24.7, 46.7),
    ("HORMUZ", 26.5, 56.3),
    ("JIUQUAN", 39.8, 98.5),
    ("SOLOMONS", -9.6, 160.2),
]
# Ras Tanura sits one grid cell from Riyadh, so its badge goes offshore
# in the Arabian Sea with a leader line back to its true position.
RAS_TANURA = (26.6, 50.2)
RAS_BADGE = (72, 21)  # grid col, row in open sea

MAP_PITCH = 3


def load_map():
    rows = (HERE / "worldmap.txt").read_text().splitlines()
    rows = [r for r in rows if r.strip()]
    assert len(rows) == 45, f"map rows: {len(rows)}"
    assert all(len(r) == 108 for r in rows), "map row width"
    return rows


def grid_xy(lat, lon):
    import math
    return math.floor((lon + 180) * 0.3), math.floor((90 - lat) * 0.3)


def draw_map(cv, x0, y0, rows):
    cv.rect(x0 - 2, y0 - 2, 108 * MAP_PITCH + 4, 45 * MAP_PITCH + 4, RULE)
    cv.rect(x0, y0, 108 * MAP_PITCH, 45 * MAP_PITCH, SEA)
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            px, py = x0 + c * MAP_PITCH, y0 + r * MAP_PITCH
            if ch == "#":
                cv.rect(px, py, 2, 2, LAND)
            else:
                cv.set(px + 1, py + 1, SEA_DOT)
    for name, lat, lon in MARKERS:
        c, r = grid_xy(lat, lon)
        cx, cy = x0 + c * MAP_PITCH + 1, y0 + r * MAP_PITCH + 1
        cv.disc(cx, cy, 3, WHITE)
        cv.disc(cx, cy, 2, MARKER)
    # Ras Tanura: offshore badge + leader line to its true grid cell.
    c, r = grid_xy(*RAS_TANURA)
    tx, ty = x0 + c * MAP_PITCH + 1, y0 + r * MAP_PITCH + 1
    bc, br = RAS_BADGE
    bx, by = x0 + bc * MAP_PITCH + 1, y0 + br * MAP_PITCH + 1
    cv.line(tx, ty, bx, by, MARKER)
    cv.disc(bx, by, 3, WHITE)
    cv.disc(bx, by, 2, MARKER)
    cv.disc(tx, ty, 1, MARKER)


def section_header(cv, x, y, w, title, count):
    cv.rect(x, y, w, 20, NAVY)
    cv.text(title, x + 8, y + 3, 2, WHITE)
    cv.text(str(count) + " STORIES", x + w - 8 - text_width(str(count) + " STORIES", 1),
            y + 6, 1, (200, 205, 220))
    return y + 20


def draw_stories(cv, x, y, w, sections):
    """Draw sections; returns the y just below the last story."""
    for title, stories in sections:
        y = section_header(cv, x, y, w, title, len(stories))
        y += 3
        for story in stories:
            lines = wrap(story, w - 16, 2)
            assert len(lines) <= 2, f"story wraps to {len(lines)} lines: {story}"
            cv.disc(x + 6, y + 6, 3, RED)
            ly = y
            for ln in lines:
                cv.text(ln, x + 16, ly, 2, INK)
                ly += 14
            y = ly + 1
        y += 4
    return y


def build():
    rows = load_map()
    cv = Canvas(W, H, PAPER)

    # ---------------------------------------------------------- masthead
    cv.text("THE WORLD TODAY", 24, 12, 5, INK)
    cv.text("WEDNESDAY 25 NOVEMBER 2026", 24, 54, 3, RED)
    cv.text("HORMUZ TANKERS HIT  \u2022  US TARIFFS  \u2022  SHENZHOU-24 IN ORBIT",
            24, 80, 2, GREY)
    cv.rect(24, 100, 976, 4, RED)
    cv.hline(24, 106, 976, INK)

    # ---------------------------------------------------------- timeline
    tl_y = 114
    cv.text("UTC TIMELINE", 24, tl_y, 1, GREY)
    slot_w = 976 // 6
    for i, (t, label) in enumerate(TIMELINE):
        sx = 24 + i * slot_w
        if i:
            cv.vline(sx - 8, tl_y + 10, 34, RULE)
        cv.text(t, sx, tl_y + 10, 2, RED)
        cv.text(label, sx, tl_y + 28, 1, INK)
    cv.hline(24, 160, 976, INK)

    # ---------------------------------------------------------- story grid
    col_w = 476
    left_x, right_x = 24, 524
    grid_top = 170
    left_end = draw_stories(cv, left_x, grid_top, col_w, SECTIONS_LEFT)
    assert left_end <= 962, f"left column overflows: {left_end}"

    # Right column: map box first, then sections.
    map_x = right_x + (col_w - 108 * MAP_PITCH) // 2
    map_y = grid_top + 24
    cv.text("THE WORLD AT A GLANCE", right_x, grid_top + 4, 2, NAVY)
    draw_map(cv, map_x, map_y, rows)
    cap_y = map_y + 45 * MAP_PITCH + 8
    cv.text_centred("RED DOTS MARK THE DAY'S FLASHPOINTS",
                    right_x + col_w // 2, cap_y, 1, GREY)
    right_end = draw_stories(cv, right_x, cap_y + 18, col_w, SECTIONS_RIGHT)
    assert right_end <= 962, f"right column overflows: {right_end}"

    # ------------------------------------------------------------- footer
    cv.hline(24, 968, 976, INK)
    cv.text("40 SOURCED STORIES  \u2022  DATE CHECKED: ALL FIRST REPORTED "
            "25 NOVEMBER 2026 (UTC)", 24, 976, 2, INK)
    cv.text("SOURCES: AP, REUTERS, SCMP, XINHUA, JERUSALEM POST, "
            "JUST SECURITY, AL JAZEERA, UEFA", 24, 994, 1, GREY)
    cv.text("ONE DAY'S NEWS IN ONE IMAGE - MAKE.FUN NEWS-IMAGE-20261125",
            24, 1004, 1, GREY)
    return cv


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    cv = build()
    size = write_png(cv, out_dir / "entry.png")
    total = sum(len(ss) for _, ss in SECTIONS_LEFT + SECTIONS_RIGHT)
    print(f"stories={total} size={size} bytes")


if __name__ == "__main__":
    main()

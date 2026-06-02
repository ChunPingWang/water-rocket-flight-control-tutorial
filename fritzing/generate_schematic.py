"""
Generate a clean circuit schematic SVG for the Water Rocket Flight Computer.
Components: Pi Pico, BNO055, BMP390, MicroSD, 4x SG90, 2x LED, 2x resistor, switch.
"""

import svgwrite
from svgwrite import cm, mm

W, H = 1400, 900

dwg = svgwrite.Drawing(
    "water_rocket_schematic.svg",
    size=(f"{W}px", f"{H}px"),
    viewBox=f"0 0 {W} {H}",
)

BG = "#1a1a2e"
PANEL = "#16213e"
BORDER = "#0f3460"
BLUE = "#533483"
GREEN = "#4ecca3"
YELLOW = "#e2b96f"
RED = "#e94560"
WHITE = "#e0e0e0"
GRAY = "#888"
ORANGE = "#f5a623"
PURPLE = "#9b59b6"
CYAN = "#00d2ff"

# Background
dwg.add(dwg.rect(insert=(0, 0), size=(W, H), fill=BG))

# Title bar
dwg.add(dwg.rect(insert=(0, 0), size=(W, 38), fill=BORDER, rx=0))
dwg.add(dwg.text(
    "水火箭飛行控制電腦  電路接線圖  Water Rocket Flight Computer — Circuit Schematic",
    insert=(W // 2, 24),
    text_anchor="middle", font_size=15, fill=WHITE,
    font_family="monospace", font_weight="bold"
))

# ── Helper functions ─────────────────────────────────────────────────────────

def box(x, y, w, h, label, color=BLUE, label_color=WHITE, sub=""):
    g = dwg.g()
    g.add(dwg.rect(insert=(x, y), size=(w, h),
                   fill=PANEL, stroke=color, stroke_width=2, rx=6))
    g.add(dwg.text(label, insert=(x + w // 2, y + 22),
                   text_anchor="middle", font_size=13,
                   fill=label_color, font_family="monospace", font_weight="bold"))
    if sub:
        g.add(dwg.text(sub, insert=(x + w // 2, y + 37),
                       text_anchor="middle", font_size=10,
                       fill=GRAY, font_family="monospace"))
    dwg.add(g)

def pin(x, y, label, side="left", color=GREEN):
    if side == "left":
        dwg.add(dwg.line(start=(x - 18, y), end=(x, y),
                         stroke=color, stroke_width=1.5))
        dwg.add(dwg.text(label, insert=(x - 22, y + 4),
                         text_anchor="end", font_size=9,
                         fill=color, font_family="monospace"))
    else:
        dwg.add(dwg.line(start=(x, y), end=(x + 18, y),
                         stroke=color, stroke_width=1.5))
        dwg.add(dwg.text(label, insert=(x + 22, y + 4),
                         text_anchor="start", font_size=9,
                         fill=color, font_family="monospace"))

def wire(x1, y1, x2, y2, color=GREEN, dashed=False):
    opts = {"stroke": color, "stroke_width": 1.8, "fill": "none"}
    if dashed:
        opts["stroke_dasharray"] = "6,4"
    # L-shaped wire
    if x1 != x2 and y1 != y2:
        dwg.add(dwg.polyline(
            points=[(x1, y1), (x1, y2), (x2, y2)], **opts))
    else:
        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), **opts))

def dot(x, y, color=GREEN):
    dwg.add(dwg.circle(center=(x, y), r=4, fill=color))

def label_wire(x, y, text, color=GRAY):
    dwg.add(dwg.text(text, insert=(x, y), font_size=9,
                     fill=color, font_family="monospace"))

# ── Raspberry Pi Pico ────────────────────────────────────────────────────────
PX, PY, PW, PH = 530, 80, 340, 680
box(PX, PY, PW, PH, "Raspberry Pi Pico", color=GREEN, label_color=GREEN,
    sub="RP2040 | 133MHz dual-core")

# Left pins (odd pins: 1,3,5,...) → GPIO on left side
LEFT_PINS = [
    ("GP0",    "#888"),
    ("GP1",    RED,   "Rec SW"),
    ("GND",    GRAY),
    ("GP2",    ORANGE,"Srv X1"),
    ("GP3",    ORANGE,"Srv X2"),
    ("GP4",    ORANGE,"Srv Y1"),
    ("GP5",    ORANGE,"Srv Y2"),
    ("GND",    GRAY),
    ("GP6",    RED,   "Rec LED"),
    ("GP7",    YELLOW,"Sta LED"),
    ("GP8",    "#888","GPS TX"),
    ("GP9",    "#888","GPS RX"),
    ("GND",    GRAY),
    ("GP10",   CYAN,  "SD SCK"),
    ("GP11",   CYAN,  "SD MOSI"),
    ("GP12",   CYAN,  "SD MISO"),
    ("GP13",   CYAN,  "SD CS"),
    ("GND",    GRAY),
    ("GP14",   BLUE,  "I2C SDA"),
    ("GP15",   BLUE,  "I2C SCL"),
]

RIGHT_PINS = [
    ("VBUS",   "#888","USB 5V"),
    ("VSYS",   RED,   "→Servo"),
    ("GND",    GRAY),
    ("3V3_EN", "#888"),
    ("3V3OUT", GREEN, "→Sensors"),
    ("ADC_REF","#888"),
    ("GP28",   "#888"),
    ("GND",    GRAY),
    ("GP27",   "#888"),
    ("GP26",   "#888"),
    ("RUN",    "#888"),
    ("GP22",   "#888"),
    ("GND",    GRAY),
    ("GP21",   "#888"),
    ("GP20",   "#888"),
    ("GP19",   "#888"),
    ("GP18",   "#888"),
    ("GND",    GRAY),
    ("GP17",   "#888"),
    ("GP16",   "#888"),
]

PIN_START_Y = PY + 55
PIN_STEP = 28

for i, entry in enumerate(LEFT_PINS):
    name = entry[0]
    color = entry[1] if len(entry) > 1 else GREEN
    desc = entry[2] if len(entry) > 2 else ""
    py = PIN_START_Y + i * PIN_STEP
    dwg.add(dwg.circle(center=(PX, py), r=3, fill=color))
    dwg.add(dwg.text(name, insert=(PX + 8, py + 4),
                     font_size=9, fill=color, font_family="monospace"))
    if desc:
        dwg.add(dwg.text(desc, insert=(PX + 70, py + 4),
                         font_size=8, fill=GRAY, font_family="monospace"))

for i, entry in enumerate(RIGHT_PINS):
    name = entry[0]
    color = entry[1] if len(entry) > 1 else GREEN
    desc = entry[2] if len(entry) > 2 else ""
    py = PIN_START_Y + i * PIN_STEP
    dwg.add(dwg.circle(center=(PX + PW, py), r=3, fill=color))
    dwg.add(dwg.text(name, insert=(PX + PW - 8, py + 4),
                     text_anchor="end", font_size=9, fill=color,
                     font_family="monospace"))
    if desc:
        dwg.add(dwg.text(desc, insert=(PX + PW - 70, py + 4),
                         text_anchor="end", font_size=8, fill=GRAY,
                         font_family="monospace"))

# ── BNO055 IMU ───────────────────────────────────────────────────────────────
BX, BY = 80, 120
box(BX, BY, 140, 90, "BNO055", color=BLUE, label_color=BLUE, sub="9-DOF IMU")
for r, (lbl, col) in enumerate([("VCC", GREEN), ("GND", GRAY),
                                  ("SDA", BLUE), ("SCL", BLUE), ("ADR→GND", GRAY)]):
    ry = BY + 30 + r * 14
    dwg.add(dwg.text(lbl, insert=(BX + 135, ry + 4),
                     text_anchor="end", font_size=9, fill=col,
                     font_family="monospace"))
    dwg.add(dwg.circle(center=(BX + 140, ry), r=3, fill=col))

# BNO055 wires
SDA_Y = PIN_START_Y + 18 * PIN_STEP  # GP14
SCL_Y = PIN_START_Y + 19 * PIN_STEP  # GP15
VCC_Y_BNO = BY + 30
GND_Y_BNO = BY + 44
BNO_SDA_Y = BY + 58
BNO_SCL_Y = BY + 72

wire(PX, SDA_Y, BX + 140, BNO_SDA_Y, color=BLUE)
wire(PX, SCL_Y, BX + 140 - 6, BNO_SCL_Y, color=BLUE)
dot(PX, SDA_Y, BLUE)

# ── BMP390 ───────────────────────────────────────────────────────────────────
MPX, MPY = 80, 260
box(MPX, MPY, 140, 75, "BMP390", color=PURPLE, label_color=PURPLE, sub="Barometer")
for r, (lbl, col) in enumerate([("VCC", GREEN), ("GND", GRAY),
                                  ("SDA", BLUE), ("SCL", BLUE)]):
    ry = MPY + 30 + r * 14
    dwg.add(dwg.text(lbl, insert=(MPX + 135, ry + 4),
                     text_anchor="end", font_size=9, fill=col,
                     font_family="monospace"))
    dwg.add(dwg.circle(center=(MPX + 140, ry), r=3, fill=col))

wire(PX, SDA_Y, MPX + 140, MPY + 58, color=BLUE)
wire(PX, SCL_Y, MPX + 134, MPY + 72, color=BLUE)

# I2C bus label
dwg.add(dwg.text("I2C (400kHz)", insert=(230, SDA_Y - 6),
                  font_size=8, fill=BLUE, font_family="monospace"))

# ── MicroSD ──────────────────────────────────────────────────────────────────
SDX, SDY = 80, 390
box(SDX, SDY, 140, 100, "MicroSD", color=CYAN, label_color=CYAN, sub="SPI @ 41.7MHz")
for r, (lbl, col) in enumerate([("VCC", GREEN), ("GND", GRAY),
                                  ("CLK", CYAN), ("MOSI", CYAN),
                                  ("MISO", CYAN), ("CS", CYAN)]):
    ry = SDY + 28 + r * 13
    dwg.add(dwg.text(lbl, insert=(SDX + 135, ry + 4),
                     text_anchor="end", font_size=9, fill=col,
                     font_family="monospace"))
    dwg.add(dwg.circle(center=(SDX + 140, ry), r=3, fill=col))

spi_pins = [13, 14, 15, 16]  # GP10-13
for i, pi in enumerate(spi_pins):
    pico_y = PIN_START_Y + pi * PIN_STEP
    sd_y = SDY + 54 + i * 13
    wire(PX, pico_y, SDX + 140, sd_y, color=CYAN)
    dot(PX, pico_y, CYAN)

# ── 4× SG90 Servo ────────────────────────────────────────────────────────────
SVX = 960
for si, (sname, spy) in enumerate([("Servo X1\nGP2", 120),
                                     ("Servo X2\nGP3", 220),
                                     ("Servo Y1\nGP4", 320),
                                     ("Servo Y2\nGP5", 420)]):
    box(SVX, spy, 120, 60, f"SG90 {sname.split()[0]}", color=ORANGE, label_color=ORANGE,
        sub=sname.split()[1])
    for r, (lbl, col) in enumerate([("VCC", RED), ("GND", GRAY), ("SIG", ORANGE)]):
        ry = spy + 22 + r * 13
        dwg.add(dwg.circle(center=(SVX, ry), r=3, fill=col))
        dwg.add(dwg.text(lbl, insert=(SVX + 5, ry + 4),
                         font_size=9, fill=col, font_family="monospace"))

    # Signal wire from Pico GP(2+si)
    pico_y = PIN_START_Y + (3 + si) * PIN_STEP  # GP2=index3, GP3=4, GP4=5, GP5=6
    sig_y = spy + 48
    wire(PX + PW, pico_y, SVX, sig_y, color=ORANGE)

# VSYS → servo VCC bus
VSYS_Y = PIN_START_Y + 1 * PIN_STEP  # RIGHT pin index 1 = VSYS
vsys_x = PX + PW
# vertical bus line on right side for servo power
dwg.add(dwg.line(start=(vsys_x + 40, VSYS_Y),
                 end=(vsys_x + 40, 420 + 35),
                 stroke=RED, stroke_width=2))
dwg.add(dwg.text("VSYS", insert=(vsys_x + 44, VSYS_Y - 4),
                  font_size=9, fill=RED, font_family="monospace"))
for si, spy in enumerate([120, 220, 320, 420]):
    vcc_y = spy + 22
    dwg.add(dwg.line(start=(vsys_x + 40, vcc_y), end=(SVX, vcc_y),
                     stroke=RED, stroke_width=1.5))
    dot(vsys_x + 40, vcc_y, RED)
wire(PX + PW, VSYS_Y, vsys_x + 40, VSYS_Y, color=RED)
dot(PX + PW, VSYS_Y, RED)

# ── LED + Resistors ──────────────────────────────────────────────────────────
LX = 80

# Red LED (GP6 = index 8)
RD_Y = 540
box(LX, RD_Y, 140, 55, "LED 🔴 錄製", color=RED, label_color=RED, sub="GP6 → 330Ω → LED")
pico_gp6_y = PIN_START_Y + 8 * PIN_STEP
wire(PX, pico_gp6_y, LX + 140, RD_Y + 22, color=RED)
dot(PX, pico_gp6_y, RED)

# Yellow LED (GP7 = index 9)
YL_Y = 620
box(LX, YL_Y, 140, 55, "LED 🟡 狀態", color=YELLOW, label_color=YELLOW, sub="GP7 → 330Ω → LED")
pico_gp7_y = PIN_START_Y + 9 * PIN_STEP
wire(PX, pico_gp7_y, LX + 140, YL_Y + 22, color=YELLOW)
dot(PX, pico_gp7_y, YELLOW)

# Recording switch (GP1 = index 1)
SW_Y = 700
box(LX, SW_Y, 140, 55, "錄製開關", color=WHITE, label_color=WHITE, sub="GP1 (pull-up → GND)")
pico_gp1_y = PIN_START_Y + 1 * PIN_STEP
wire(PX, pico_gp1_y, LX + 140, SW_Y + 22, color=WHITE)
dot(PX, pico_gp1_y, WHITE)

# ── 3V3 power bus ────────────────────────────────────────────────────────────
V33_Y = PIN_START_Y + 4 * PIN_STEP  # RIGHT pin index 4 = 3V3OUT
wire(PX + PW, V33_Y, PX + PW + 20, V33_Y, color=GREEN)
dot(PX + PW, V33_Y, GREEN)
# vertical line
dwg.add(dwg.line(start=(PX + PW + 20, V33_Y),
                 end=(PX + PW + 20, 390 + 28),
                 stroke=GREEN, stroke_width=1.5))
# to BNO055 VCC
wire(PX + PW + 20, BY + 30, BX + 140, BY + 30, color=GREEN)
dot(PX + PW + 20, BY + 30, GREEN)
# to BMP390 VCC
wire(PX + PW + 20, MPY + 30, BX + 140, MPY + 30, color=GREEN)
dot(PX + PW + 20, MPY + 30, GREEN)
# to MicroSD VCC
wire(PX + PW + 20, SDY + 28, SDX + 140, SDY + 28, color=GREEN)
dot(PX + PW + 20, SDY + 28, GREEN)
dwg.add(dwg.text("3V3OUT", insert=(PX + PW + 22, V33_Y - 5),
                  font_size=9, fill=GREEN, font_family="monospace"))

# ── GPS (disabled) ───────────────────────────────────────────────────────────
GPX, GPY = 960, 530
box(GPX, GPY, 120, 75, "PA1616D", color=GRAY, label_color=GRAY, sub="GPS (停用)")
for r, lbl in enumerate(["VCC", "GND", "TX→GP9", "RX←GP8"]):
    ry = GPY + 28 + r * 13
    dwg.add(dwg.circle(center=(GPX, ry), r=2, fill=GRAY))
    dwg.add(dwg.text(lbl, insert=(GPX + 5, ry + 4),
                     font_size=8, fill=GRAY, font_family="monospace"))

# Dashed lines for GPS (disabled)
gp8_y = PIN_START_Y + 10 * PIN_STEP
gp9_y = PIN_START_Y + 11 * PIN_STEP
wire(PX + PW, gp8_y, GPX, GPY + 67, color=GRAY, dashed=True)
wire(PX + PW, gp9_y, GPX - 5, GPY + 54, color=GRAY, dashed=True)

# ── Legend ───────────────────────────────────────────────────────────────────
LGX, LGY = 960, 650
dwg.add(dwg.rect(insert=(LGX, LGY), size=(200, 140),
                 fill=PANEL, stroke=BORDER, stroke_width=1, rx=4))
dwg.add(dwg.text("圖例 / Legend", insert=(LGX + 100, LGY + 18),
                  text_anchor="middle", font_size=11, fill=WHITE,
                  font_family="monospace", font_weight="bold"))

legend_items = [
    (GREEN, "I2C 匯流排 (SDA/SCL)"),
    (CYAN,  "SPI 匯流排 (SD卡)"),
    (ORANGE,"PIO PWM 伺服訊號"),
    (RED,   "VSYS 電源 / LED"),
    (GREEN, "3V3OUT 感測器電源"),
    (GRAY,  "GPS（虛線=停用）"),
]
for i, (col, desc) in enumerate(legend_items):
    ly = LGY + 35 + i * 18
    dwg.add(dwg.line(start=(LGX + 12, ly), end=(LGX + 30, ly),
                     stroke=col, stroke_width=2))
    dwg.add(dwg.text(desc, insert=(LGX + 36, ly + 4),
                     font_size=9, fill=col, font_family="monospace"))

# ── Footer ───────────────────────────────────────────────────────────────────
dwg.add(dwg.text(
    "github.com/ChunPingWang/water-rocket-flight-control-tutorial  |  2026-06-03",
    insert=(W // 2, H - 6),
    text_anchor="middle", font_size=9, fill=GRAY, font_family="monospace"
))

dwg.save()
print("Saved: water_rocket_schematic.svg")

#!/usr/bin/env python3
"""
Build water_rocket_flight_computer.fzz for the water rocket flight control tutorial.
This script creates a complete Fritzing sketch (.fzz = ZIP) containing:
  - The main breadboard sketch XML (water_rocket_bb.fz)
  - The Raspberry Pi Pico part description (rpi_pico-tht_1.fzp)
  - The Pico breadboard SVG
"""

import zipfile
import os
import uuid

FRITZING_DIR = "/home/rexwang/workspace/water-rocket-flight-control-tutorial/fritzing"
OUTPUT_FZZ = os.path.join(FRITZING_DIR, "water_rocket_flight_computer.fzz")
PICO_FZP = os.path.join(FRITZING_DIR, "rpi_pico-tht_1.fzp")
PICO_BB_SVG = os.path.join(FRITZING_DIR, "rpi_pico-tht_1_breadboard.svg")

# ---------------------------------------------------------------------------
# Sketch UUID
# ---------------------------------------------------------------------------
SKETCH_UUID = "d3e7a1f0-7c2b-4e5a-9f3d-2b8c6e1a4f7d"

# ---------------------------------------------------------------------------
# Helper: generate a simple SVG for a generic SIP header module
# pins: list of (connector_id, label)
# ---------------------------------------------------------------------------
def make_sip_svg(module_id, pins, title):
    pin_h = 18   # px per pin row
    width = 80
    height = max(60, len(pins) * pin_h + 20)
    rects = []
    circles = []
    labels = []
    for i, (cid, label) in enumerate(pins):
        y = 10 + i * pin_h
        circles.append(
            f'  <circle id="{cid}pin" cx="10" cy="{y+9}" r="4" '
            f'fill="#cccccc" stroke="#888888" stroke-width="1"/>'
        )
        labels.append(
            f'  <text x="20" y="{y+13}" font-size="8" fill="#333333">{label}</text>'
        )
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
     x="0" y="0" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}">
  <title>{title}</title>
  <rect x="0" y="0" width="{width}" height="{height}"
        fill="#d4a843" stroke="#888800" stroke-width="2" rx="4"/>
  <text x="{width//2}" y="9" font-size="7" fill="#000000"
        text-anchor="middle">{title}</text>
{''.join(circles)}
{''.join(labels)}
</svg>"""
    return svg

# ---------------------------------------------------------------------------
# Helper: generate a minimal FZP for a generic SIP header
# ---------------------------------------------------------------------------
def make_sip_fzp(module_id, title, pins, family="SIP header"):
    """
    pins: list of (connector_id, name, description)
    """
    connectors_xml = ""
    for cid, name, desc in pins:
        connectors_xml += f"""    <connector id="{cid}" type="male" name="{name}">
      <description>{desc}</description>
      <views>
        <breadboardView>
          <p svgId="{cid}pin" layer="breadboard"/>
        </breadboardView>
        <schematicView>
          <p svgId="{cid}pin" layer="schematic"/>
        </schematicView>
      </views>
    </connector>
"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<module moduleId="{module_id}" fritzingVersion="0.9.4">
  <version>1</version>
  <author>Generated</author>
  <title>{title}</title>
  <label>U</label>
  <date>2024-01-01</date>
  <properties>
    <property name="family">{family}</property>
  </properties>
  <views>
    <breadboardView>
      <layers image="breadboard/{module_id}_breadboard.svg">
        <layer layerId="breadboard"/>
      </layers>
    </breadboardView>
    <schematicView>
      <layers image="schematic/{module_id}_breadboard.svg">
        <layer layerId="schematic"/>
      </layers>
    </schematicView>
  </views>
  <connectors>
{connectors_xml}  </connectors>
</module>
"""

# ---------------------------------------------------------------------------
# Part definitions
# ---------------------------------------------------------------------------

# BNO055 IMU — 8-pin SIP (VIN, GND, SDA, SCL, INT, ADR, RST, NC)
BNO055_ID = "bno055_imu_custom_1"
BNO055_PINS_FZP = [
    ("connector0", "VIN",  "Power 3.3V"),
    ("connector1", "GND",  "Ground"),
    ("connector2", "SDA",  "I2C SDA"),
    ("connector3", "SCL",  "I2C SCL"),
    ("connector4", "INT",  "Interrupt"),
    ("connector5", "ADR",  "I2C Address select"),
    ("connector6", "RST",  "Reset"),
    ("connector7", "NC",   "Not connected"),
]
BNO055_PINS_SVG = [(c, n) for c, n, _ in BNO055_PINS_FZP]

# BMP390 Barometer — 6-pin SIP (VIN, GND, SDA, SCL, SDO, CSB)
BMP390_ID = "bmp390_baro_custom_1"
BMP390_PINS_FZP = [
    ("connector0", "VIN",  "Power 3.3V"),
    ("connector1", "GND",  "Ground"),
    ("connector2", "SDA",  "I2C SDA"),
    ("connector3", "SCL",  "I2C SCL"),
    ("connector4", "SDO",  "SDO / Address select"),
    ("connector5", "CSB",  "Chip select bar"),
]
BMP390_PINS_SVG = [(c, n) for c, n, _ in BMP390_PINS_FZP]

# MicroSD module — 6-pin SIP (VCC, GND, MISO, MOSI, SCK, CS)
SD_ID = "microsd_module_custom_1"
SD_PINS_FZP = [
    ("connector0", "VCC",  "Power 3.3V"),
    ("connector1", "GND",  "Ground"),
    ("connector2", "MISO", "SPI MISO"),
    ("connector3", "MOSI", "SPI MOSI"),
    ("connector4", "SCK",  "SPI Clock"),
    ("connector5", "CS",   "Chip Select"),
]
SD_PINS_SVG = [(c, n) for c, n, _ in SD_PINS_FZP]

# SG90 Servo — 3-pin SIP (VCC, GND, SIG)
def servo_id(axis): return f"sg90_servo_{axis.lower()}_custom_1"
SERVO_PINS_FZP = [
    ("connector0", "SIG", "PWM Signal"),
    ("connector1", "VCC", "Power (5V / VSYS)"),
    ("connector2", "GND", "Ground"),
]
SERVO_PINS_SVG = [(c, n) for c, n, _ in SERVO_PINS_FZP]
SERVO_AXES = ["X1", "X2", "Y1", "Y2"]

# ---------------------------------------------------------------------------
# Build all SIP SVG and FZP content strings
# ---------------------------------------------------------------------------
sip_parts = {}  # module_id -> {"fzp": str, "svg": str, "title": str}

sip_parts[BNO055_ID] = {
    "title": "BNO055 IMU",
    "fzp": make_sip_fzp(BNO055_ID, "BNO055 IMU", BNO055_PINS_FZP),
    "svg": make_sip_svg(BNO055_ID, BNO055_PINS_SVG, "BNO055 IMU"),
}
sip_parts[BMP390_ID] = {
    "title": "BMP390 Baro",
    "fzp": make_sip_fzp(BMP390_ID, "BMP390 Baro", BMP390_PINS_FZP),
    "svg": make_sip_svg(BMP390_ID, BMP390_PINS_SVG, "BMP390 Baro"),
}
sip_parts[SD_ID] = {
    "title": "MicroSD",
    "fzp": make_sip_fzp(SD_ID, "MicroSD Module", SD_PINS_FZP),
    "svg": make_sip_svg(SD_ID, SD_PINS_SVG, "MicroSD"),
}
for axis in SERVO_AXES:
    sid = servo_id(axis)
    sip_parts[sid] = {
        "title": f"SG90 Servo {axis}",
        "fzp": make_sip_fzp(sid, f"SG90 Servo {axis}", SERVO_PINS_FZP),
        "svg": make_sip_svg(sid, SERVO_PINS_SVG, f"Servo {axis}"),
    }

# ---------------------------------------------------------------------------
# Sketch XML  (water_rocket_bb.fz)
# Model indices:
#   1  = Pico
#   2  = BNO055
#   3  = BMP390
#   4  = MicroSD
#   5  = Servo X1
#   6  = Servo X2
#   7  = Servo Y1
#   8  = Servo Y2
#   9  = LED red (recording LED, GP6)
#   10 = LED yellow (status LED, GP7)
#   11 = Resistor R1 (for Red LED)
#   12 = Resistor R2 (for Yellow LED)
#   13 = Switch (recording switch, GP1)
# ---------------------------------------------------------------------------

def instance_xml(module_id, model_index, title, x, y,
                 connector_ids, z="0.5",
                 extra_props=""):
    """Build a breadboardView instance element."""
    conn_xml = ""
    for cid in connector_ids:
        conn_xml += f'            <connector id="{cid}" layer="breadboardbreadboard"/>\n'

    return f"""    <instance moduleIdRef="{module_id}" modelIndex="{model_index}" path="">
      <title>{title}</title>
      <text/>
      <views>
        <breadboardView>
          <geometry x="{x}" y="{y}" z="{z}" xFlip="false" yFlip="false"/>
          <connectors>
{conn_xml}          </connectors>
        </breadboardView>
      </views>
    </instance>
"""

def connection_xml(conn_id, model_index, connects):
    """
    connects: list of (target_conn_id, target_model_index)
    """
    connects_xml = ""
    for tc, tm in connects:
        connects_xml += f'        <connect connectorId="{tc}" modelIndex="{tm}" layer="breadboardbreadboard"/>\n'
    return f"""    <connection>
      <connects>
        <connect connectorId="{conn_id}" modelIndex="{model_index}" layer="breadboardbreadboard"/>
{connects_xml}      </connects>
    </connection>
"""

# --- Pico connectors used ---
PICO_CONNECTORS = [
    "connector1",   # GP1  -> switch
    "connector3",   # GP2  -> Servo X1
    "connector4",   # GP3  -> Servo X2
    "connector5",   # GP4  -> Servo Y1
    "connector6",   # GP5  -> Servo Y2
    "connector8",   # GP6  -> Red LED (recording)
    "connector9",   # GP7  -> Yellow LED (status)
    "connector13",  # GP10 -> SD SCK
    "connector14",  # GP11 -> SD MOSI
    "connector15",  # GP12 -> SD MISO
    "connector16",  # GP13 -> SD CS
    "connector18",  # GP14 -> I2C SDA
    "connector19",  # GP15 -> I2C SCL
    "connector35",  # 3V3OUT
    "connector37",  # GND
    "connector38",  # VSYS
]

instances = []
connections = []

# Pico (model 1)
instances.append(instance_xml(
    "rpi_pico-tht_1", 1, "U1", 300, 200,
    PICO_CONNECTORS
))

# BNO055 (model 2)
instances.append(instance_xml(
    BNO055_ID, 2, "BNO055 IMU", 600, 80,
    [c for c, n, _ in BNO055_PINS_FZP]
))

# BMP390 (model 3)
instances.append(instance_xml(
    BMP390_ID, 3, "BMP390 Baro", 600, 220,
    [c for c, n, _ in BMP390_PINS_FZP]
))

# MicroSD (model 4)
instances.append(instance_xml(
    SD_ID, 4, "MicroSD", 600, 340,
    [c for c, n, _ in SD_PINS_FZP]
))

# Servos (models 5..8)
servo_positions = [(50, 80), (50, 180), (50, 280), (50, 380)]
for i, axis in enumerate(SERVO_AXES):
    mi = 5 + i
    x, y = servo_positions[i]
    instances.append(instance_xml(
        servo_id(axis), mi, f"Servo {axis}", x, y,
        [c for c, n, _ in SERVO_PINS_FZP]
    ))

# Red LED (model 9) — moduleId: 5mmColorLEDModuleID
# connector0=cathode, connector1=anode
instances.append(instance_xml(
    "5mmColorLEDModuleID", 9, "LED1 (Red)", 550, 480,
    ["connector0", "connector1"]
))

# Yellow LED (model 10)
instances.append(instance_xml(
    "5mmColorLEDModuleID", 10, "LED2 (Yellow)", 550, 530,
    ["connector0", "connector1"]
))

# Resistor R1 for Red LED (model 11)
instances.append(instance_xml(
    "ResistorModuleID", 11, "R1 330ohm", 480, 480,
    ["connector0", "connector1"]
))

# Resistor R2 for Yellow LED (model 12)
instances.append(instance_xml(
    "ResistorModuleID", 12, "R2 330ohm", 480, 530,
    ["connector0", "connector1"]
))

# Switch (model 13) — moduleId: 33b94ebdb1ef4e7cf0f8425956cfca60
# connector0=leg0, connector1=leg1
instances.append(instance_xml(
    "33b94ebdb1ef4e7cf0f8425956cfca60", 13, "SW1 Record", 200, 500,
    ["connector0", "connector1"]
))

# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
# I2C SDA: Pico conn18 <-> BNO055 conn2 <-> BMP390 conn2
connections.append(connection_xml("connector18", 1, [("connector2", 2), ("connector2", 3)]))

# I2C SCL: Pico conn19 <-> BNO055 conn3 <-> BMP390 conn3
connections.append(connection_xml("connector19", 1, [("connector3", 2), ("connector3", 3)]))

# SD SPI
# GP10 SCK -> SD SCK (conn4)
connections.append(connection_xml("connector13", 1, [("connector4", 4)]))
# GP11 MOSI -> SD MOSI (conn3)
connections.append(connection_xml("connector14", 1, [("connector3", 4)]))
# GP12 MISO -> SD MISO (conn2)
connections.append(connection_xml("connector15", 1, [("connector2", 4)]))
# GP13 CS -> SD CS (conn5)
connections.append(connection_xml("connector16", 1, [("connector5", 4)]))

# Servo signals
# GP2 -> Servo X1 SIG (conn0, model5)
connections.append(connection_xml("connector3", 1, [("connector0", 5)]))
# GP3 -> Servo X2 SIG (conn0, model6)
connections.append(connection_xml("connector4", 1, [("connector0", 6)]))
# GP4 -> Servo Y1 SIG (conn0, model7)
connections.append(connection_xml("connector5", 1, [("connector0", 7)]))
# GP5 -> Servo Y2 SIG (conn0, model8)
connections.append(connection_xml("connector6", 1, [("connector0", 8)]))

# Red LED chain: Pico GP6(conn8) -> R1 conn0, R1 conn1 -> LED1 anode(conn1)
connections.append(connection_xml("connector8", 1, [("connector0", 11)]))    # GP6 -> R1 in
connections.append(connection_xml("connector1", 11, [("connector1", 9)]))    # R1 out -> LED1 anode
# LED1 cathode (conn0) -> GND bus represented by Pico conn37
connections.append(connection_xml("connector0", 9, [("connector37", 1)]))

# Yellow LED chain: Pico GP7(conn9) -> R2 conn0, R2 conn1 -> LED2 anode(conn1)
connections.append(connection_xml("connector9", 1, [("connector0", 12)]))    # GP7 -> R2 in
connections.append(connection_xml("connector1", 12, [("connector1", 10)]))   # R2 out -> LED2 anode
# LED2 cathode (conn0) -> GND bus
connections.append(connection_xml("connector0", 10, [("connector37", 1)]))

# Switch: Pico GP1(conn1) -> SW1 leg0(conn0), SW1 leg1(conn1) -> GND
connections.append(connection_xml("connector1", 1, [("connector0", 13)]))
connections.append(connection_xml("connector1", 13, [("connector37", 1)]))

# Power rails
# 3V3OUT -> BNO055 VIN (conn0), BMP390 VIN (conn0), SD VCC (conn0)
connections.append(connection_xml("connector35", 1, [
    ("connector0", 2),
    ("connector0", 3),
    ("connector0", 4),
]))

# VSYS -> Servo X1/X2/Y1/Y2 VCC (conn1)
connections.append(connection_xml("connector38", 1, [
    ("connector1", 5),
    ("connector1", 6),
    ("connector1", 7),
    ("connector1", 8),
]))

# GND bus: Pico conn37 -> BNO055 GND, BMP390 GND, SD GND, Servo GNDs
connections.append(connection_xml("connector37", 1, [
    ("connector1", 2),   # BNO055 GND
    ("connector1", 3),   # BMP390 GND
    ("connector1", 4),   # SD GND
    ("connector2", 5),   # Servo X1 GND
    ("connector2", 6),   # Servo X2 GND
    ("connector2", 7),   # Servo Y1 GND
    ("connector2", 8),   # Servo Y2 GND
]))

# ---------------------------------------------------------------------------
# Assemble sketch XML
# ---------------------------------------------------------------------------
instances_str = "".join(instances)
connections_str = "".join(connections)

sketch_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<module fritzingVersion="0.9.10" moduleId="{SKETCH_UUID}">
  <title>Water Rocket Flight Computer</title>
  <date>2024-01-01</date>
  <author>Water Rocket Tutorial</author>
  <description>Water Rocket RP2040 flight computer breadboard circuit.
Sensors: BNO055 IMU (I2C), BMP390 barometer (I2C).
Storage: MicroSD (SPI).
Actuators: 4x SG90 servo (PWM).
UI: record switch (GP1), record LED red (GP6), status LED yellow (GP7).</description>
  <instances>
{instances_str}  </instances>
  <connections>
{connections_str}  </connections>
</module>
"""

# ---------------------------------------------------------------------------
# Pack into .fzz (ZIP)
# ---------------------------------------------------------------------------
with zipfile.ZipFile(OUTPUT_FZZ, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    # Main sketch
    zf.writestr("water_rocket_bb.fz", sketch_xml)

    # Pi Pico part files
    with open(PICO_FZP, "r", encoding="utf-8") as f:
        pico_fzp_content = f.read()
    zf.writestr("parts/user/rpi_pico-tht_1.fzp", pico_fzp_content)

    # Pi Pico breadboard SVG
    with open(PICO_BB_SVG, "rb") as f:
        pico_svg_content = f.read()
    zf.writestr("parts/svg/breadboard/rpi_pico-tht_1_breadboard.svg", pico_svg_content)

    # Generic SIP parts
    for mod_id, data in sip_parts.items():
        zf.writestr(f"parts/user/{mod_id}.fzp", data["fzp"])
        zf.writestr(f"parts/svg/breadboard/{mod_id}_breadboard.svg", data["svg"])

print(f"Created: {OUTPUT_FZZ}")
print(f"Size: {os.path.getsize(OUTPUT_FZZ):,} bytes")
print()

# Verify ZIP contents
print("ZIP contents:")
with zipfile.ZipFile(OUTPUT_FZZ, "r") as zf:
    for info in zf.infolist():
        print(f"  {info.filename}  ({info.file_size:,} bytes)")

print()
print("Done — water_rocket_flight_computer.fzz is ready.")

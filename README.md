# 水火箭飛行控制電腦教學

基於 [SandwichRising/model-rocket-flight-computer](https://github.com/SandwichRising/model-rocket-flight-computer) 移植與改編，針對水火箭應用場景的完整教學。

---

## 目錄

1. [專案概述](#1-專案概述)
2. [系統架構](#2-系統架構)
3. [程式碼深度解析](#3-程式碼深度解析)
   - [PIO 狀態機：LED 控制](#31-pio-狀態機led-控制-blinkpio)
   - [PIO 狀態機：伺服機控制](#32-pio-狀態機伺服機控制-servopio)
   - [主程式：感測器讀取](#33-主程式感測器讀取-bno055-imu)
   - [主程式：轉向演算法](#34-主程式轉向演算法)
   - [主程式：SD 卡記錄](#35-主程式sd-卡資料記錄)
   - [硬體設定：SPI 介面](#36-硬體設定spi-介面-hw_configc)
   - [建置系統：CMakeLists](#37-建置系統cmakeliststxt)
4. [GPIO 接腳配置](#4-gpio-接腳配置)
5. [開發環境建置](#5-開發環境建置)
6. [逐步實作教程](#6-逐步實作教程)
7. [飛行資料分析](#7-飛行資料分析)
8. [常見問題排查](#8-常見問題排查)
9. [水火箭移植指南](#9-水火箭移植指南)

---

## 1. 專案概述

本專案實作一套搭載**主動穩定控制**的火箭飛行電腦，核心功能：

- **主動垂直飛行**：透過 IMU 重力向量即時調整伺服翼片，讓火箭保持垂直飛行
- **飛行資料記錄**：將加速度、重力向量、方向角、溫度等數據以 10Hz 寫入 SD 卡
- **PIO 精確控制**：使用 RP2040 的可程式 I/O 獨立控制伺服機脈衝，不依賴主程式計時

```
飛行電腦工作流程：
                    ┌─────────────┐
  [IMU] ──I2C──▶   │  RP2040     │ ──PIO──▶ [伺服 X1/X2/Y1/Y2]
  [GPS] ──UART──▶  │  主控制器   │ ──SPI──▶ [SD 卡記錄]
  [氣壓計]──I2C──▶ │             │ ──PIO──▶ [狀態 LED / 錄製 LED]
                    └─────────────┘
```

---

## 2. 系統架構

### 軟體層次

```
┌────────────────────────────────────────────────────────┐
│                     應用層 (C)                          │
│  Rocket_Computer.c                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ IMU讀取  │ │ 伺服控制 │ │ SD記錄   │ │ GPS解析  │  │
│  │ 100Hz    │ │ 100Hz    │ │ 10Hz     │ │ (停用)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├────────────────────────────────────────────────────────┤
│                    驅動層 (SDK)                          │
│  hardware_i2c  hardware_spi  hardware_pio  hardware_uart│
│  no-OS-FatFS-SD-SDIO-SPI-RPi-Pico (carlk3)            │
├────────────────────────────────────────────────────────┤
│                    PIO 硬體層                            │
│  pio0 SM0: 狀態 LED    pio1 SM0: 伺服 X1               │
│  pio0 SM1: 錄製 LED    pio1 SM1: 伺服 X2               │
│                        pio1 SM2: 伺服 Y1               │
│                        pio1 SM3: 伺服 Y2               │
└────────────────────────────────────────────────────────┘
```

### 主迴圈計時設計（輪詢式）

V1 採用**輪詢計時器**（polling-based timer）設計，非中斷驅動。所有任務共用同一個主迴圈，各自維護上次執行時間：

```
主迴圈每次迭代：
  currentTime = 現在的毫秒數

  if (currentTime - uartTimer  >= 5ms)  → GPS 讀取（停用）
  if (currentTime - accelTimer >= 10ms) → IMU 讀取 + 伺服更新觸發
  if (currentTime - recordTimer>= 100ms)→ SD 卡寫入（巢狀於 IMU 內）
  if (currentTime - baroTimer  >= 10ms) → 氣壓計讀取（停用）
  if (currentTime - servoTimer >= 10ms) → 伺服位置更新
```

**設計取捨**：輪詢式簡單但有競爭：若 IMU I2C 傳輸慢，伺服更新就延遲。V2 改用中斷驅動解決此問題。

---

## 3. 程式碼深度解析

### 3.1 PIO 狀態機：LED 控制 (`blink.pio`)

```pio
.program blink
.wrap_target
    pull noblock       ; 從 TX FIFO 取值（非阻塞；FIFO 空時保留舊值）
    out y, 32          ; 將 32-bit 值輸出到 Y 暫存器（計時用）
    mov x, y
    jmp !y lp1         ; 若 Y=0 → 跳到 lp1，LED 保持熄滅
    set pins, 1        ; LED 亮
lp1:
    jmp x-- lp1        ; 倒數 x 個時脈週期（ON 時間）
    mov x, y
    set pins, 0        ; LED 滅
lp2:
    jmp x-- lp2        ; 倒數相同週期（OFF 時間）
    mov x, y
.wrap
```

**控制方式**：向對應 SM 的 TX FIFO 寫入一個 32-bit 延遲值：

```c
// 計算公式：delay = (125_000_000 / (2 * freq)) - 3
// freq = 期望閃爍頻率（Hz），125MHz 為系統時脈

// 慢速閃爍（3Hz）：初始化中
pio0->txf[0] = (125000000 / (2 * 3)) - 3;   // 狀態 LED
pio0->txf[1] = (125000000 / (2 * 3)) - 3;   // 錄製 LED

// 關閉 LED：送入 0
pio0->txf[1] = 0;
```

**關鍵特性**：`pull noblock` 使狀態機在 FIFO 空時保留上一個值繼續執行，不會因等待資料而停止。

---

### 3.2 PIO 狀態機：伺服機控制 (`servo.pio`)

```pio
.program servo
.wrap_target
    pull noblock       ; 從 TX FIFO 取新的脈衝寬度值
    out y, 32
    mov x, y
    set pins, 1        ; 脈衝 HIGH（伺服機量測此持續時間）
lp1:
    jmp x-- lp1        ; 倒數 → 決定脈衝寬度（1ms ~ 2ms）
    mov x, y
    set pins, 0        ; 脈衝 LOW
lp2:
    nop [5]            ; 延長 OFF 時間（產生 50~100Hz 週期）
    jmp x-- lp2
    mov x, y
.wrap
```

**伺服機脈衝時序原理**：

```
標準伺服機控制訊號（PWM）：
  ┌────┐                              ┌────
  │    │                              │
──┘    └──────────────────────────────┘

  ← 1ms →← ──── 約 19ms OFF ──────────→   ← 全左（-90°）
  ←  1.5ms  →←  約 18.5ms OFF ──────→     ← 中間（0°）
  ←   2ms    →← 約 18ms OFF ──────────→   ← 全右（+90°）

125MHz 時脈下：
  1ms  = 125,000 ticks   → finPos 最小值
  1.5ms = 187,500 ticks  → SERVO_MIDPOINT（中點）
  2ms  = 250,000 ticks   → finPos 最大值
```

**主程式中的伺服初始化**（注意：實際使用 `blink_program_init`，兩者組合語言邏輯等效）：

```c
PIO pioServo = pio1;
uint offset = pio_add_program(pioServo, &blink_program);

// 初始化 4 個伺服機 SM，全部設定為中點
servo(pioServo, 0, offset, SERVO_X1_PIN, 3);  // SM0 → GPIO2 → X軸伺服1
servo(pioServo, 1, offset, SERVO_X2_PIN, 3);  // SM1 → GPIO3 → X軸伺服2
servo(pioServo, 2, offset, SERVO_Y1_PIN, 3);  // SM2 → GPIO4 → Y軸伺服1
servo(pioServo, 3, offset, SERVO_Y2_PIN, 3);  // SM3 → GPIO5 → Y軸伺服2

// servo() 函式本質上是：
void servo(PIO pio, uint sm, uint offset, uint pin, uint freq) {
    blink_program_init(pio, sm, offset, pin);
    pio_sm_set_enabled(pio, sm, true);
    pio->txf[sm] = SERVO_MIDPOINT;   // 187500 ticks = 1.5ms
}
```

---

### 3.3 主程式：感測器讀取（BNO055 IMU）

#### 初始化流程

```c
void bno055_init(void) {
    sleep_ms(1000);               // 等待感測器穩定

    // 1. 驗證 Chip ID（應為 0xA0）
    uint8_t IDreg = 0x00;
    uint8_t chipID[1];
    i2c_write_blocking(I2C_PORT, BN0_ADDY, &IDreg, 1, true);
    i2c_read_blocking(I2C_PORT, BN0_ADDY, chipID, 1, false);
    // chipID[0] != 0xA0 → 無限迴圈報錯

    // 2. 使用外部振盪器並重置中斷
    // 暫存器 0x3F (SYS_TRIGGER) = 0x40 → 外部振盪器
    // 暫存器 0x3F (SYS_TRIGGER) = 0x01 → 重置中斷

    // 3. 軸配置
    // 暫存器 0x41 (AXIS_MAP_CONFIG) = 0x24 → 預設軸配置
    // 暫存器 0x42 (AXIS_MAP_SIGN)   = 0x00 → 所有軸正方向

    // 4. 單位設定（暫存器 0x3B = 0x00）
    // Windows 方向、°F、m/s²、度/秒、公尺

    // 5. 設定操作模式為 NDOF（暫存器 0x3D = 0x0C）
    // NDOF = 9-DOF 感測器融合：加速計 + 陀螺儀 + 磁力計 → 卡爾曼濾波
    sleep_ms(100);   // 模式切換後需等待
}
```

#### 主迴圈中的 IMU 讀取

```c
// 每 10ms 讀取一次（100Hz）
if (GET_IMU && (accelTimer + IMU_DELAY <= currentTime)) {

    // 線性加速度（暫存器 0x08~0x0D，6 bytes）
    // 格式：little-endian 16-bit signed，單位：1/100 m/s²
    uint8_t accelRegStart = 0x08;
    i2c_write_blocking(I2C_PORT, BN0_ADDY, &accelRegStart, 1, true);
    i2c_read_blocking(I2C_PORT, BN0_ADDY, accel, 6, false);
    
    accelX = (accel[1] << 8) | accel[0];   // 合併高低位元組
    f_accelX = accelX / 100.0;              // 轉換為 m/s²

    // 重力向量（暫存器 0x2E~0x33，6 bytes）
    // 理想垂直飛行：gravX=0, gravY=0, gravZ=9.8
    uint8_t gravRegStart = 0x2E;
    i2c_write_blocking(I2C_PORT, BN0_ADDY, &gravRegStart, 1, true);
    i2c_read_blocking(I2C_PORT, BN0_ADDY, grav, 6, false);
    
    gravX = (grav[1] << 8) | grav[0];
    f_gravX = gravX / 100.0;               // 轉換為 m/s²

    // 方向角（暫存器 0x1A~0x1B，2 bytes）
    // 單位：1/16 度
    uint8_t headRegStart = 0x1A;
    heading = (head[1] << 8) | head[0];
    f_heading = heading / 16.0;            // 轉換為度數

    // 溫度（暫存器 0x34，1 byte，單位：°C）
    f_temperatureIMU = (temperatureIMU * 9.0/5.0) + 32;  // 轉換為 °F

    accelTimer = currentTime;
}
```

**BNO055 關鍵暫存器速查表**：

| 暫存器 | 名稱 | 說明 |
|--------|------|------|
| 0x00 | CHIP_ID | 固定值 0xA0，用於驗證連線 |
| 0x3B | UNIT_SEL | 單位選擇（加速度、角度、溫度格式）|
| 0x3D | OPR_MODE | 操作模式（0x0C = NDOF 融合模式）|
| 0x3F | SYS_TRIGGER | 系統觸發（振盪器選擇、重置）|
| 0x41 | AXIS_MAP_CONFIG | 軸映射配置 |
| 0x08 | ACC_DATA_X_LSB | 加速度 X 軸低位元組（起始）|
| 0x2E | GRV_DATA_X_LSB | 重力向量 X 軸低位元組（起始）|
| 0x1A | EUL_HEADING_LSB | 歐拉角方向（heading）|
| 0x34 | TEMP | 溫度 |

---

### 3.4 主程式：轉向演算法

這是整個系統最核心的部分：**比例控制器（P-Controller）**。

```c
// 每 10ms 執行一次
if (SET_SERVOS && (servoTimer + SERVO_DELAY <= currentTime)) {

    int32_t finPos[4];

    // X 軸修正（gravX 偏離 0 → 調整 X 方向翼片）
    if (f_gravX >= -9.8 && f_gravX <= 9.8) {
        // X1 和 X2 翼片反向偏轉（差動控制）
        finPos[0] = (f_gravX * SERVO_STEP) + SERVO_MIDPOINT + SERVO_X1_OFFSET;
        finPos[1] = (f_gravX * SERVO_STEP * -1) + SERVO_MIDPOINT + SERVO_X2_OFFSET;
        pio1->txf[0] = finPos[0];   // 直接寫入 PIO TX FIFO
        pio1->txf[1] = finPos[1];
    }

    // Y 軸修正（同理）
    if (f_gravY >= -9.8 && f_gravY <= 9.8) {
        finPos[2] = (f_gravY * SERVO_STEP) + SERVO_MIDPOINT + SERVO_Y1_OFFSET;
        finPos[3] = (f_gravY * SERVO_STEP * -1) + SERVO_MIDPOINT + SERVO_Y2_OFFSET;
        pio1->txf[2] = finPos[2];
        pio1->txf[3] = finPos[3];
    }

    servoTimer = currentTime;
}
```

**控制邏輯視覺化**：

```
重力向量與翼片偏轉的關係：

火箭向右傾斜：                火箭垂直飛行：
  gravX = +3.0 m/s²             gravX = 0
  gravY = 0                     gravY = 0

  X1 翼片 = 3.0×7000 + 187500 = 208500 ticks (向右偏)
  X2 翼片 = -3.0×7000 + 187500 = 166500 ticks (向左偏)
  → 差動偏轉產生修正力矩 ←

計算公式：
  伺服位置（ticks）= gravX × SERVO_STEP + SERVO_MIDPOINT
  
  SERVO_STEP = 7000 ticks/（m/s²）
  SERVO_MIDPOINT = 187500 ticks（= 1.5ms 脈衝，對應中點）
  
  最大修正量（gravX = ±9.8）：
    ± 9.8 × 7000 = ±68,600 ticks → ±0.549ms
    範圍：118,900 ~ 256,100 ticks = 0.951ms ~ 2.049ms ✓
```

**控制參數調整**：

```c
// 在 Rocket_Computer.c 頂部修改
#define SERVO_MIDPOINT 187500  // 伺服中點（勿隨意更動）
#define SERVO_STEP 7000        // 增益：值越大 → 修正越激烈
                               // 第1-2次飛行用 4000，後改為 7000
#define SERVO_X1_OFFSET 0      // 個別伺服機的機械偏移校正
#define SERVO_X2_OFFSET 0      // 若翼片安裝時有偏斜則在此補正
#define SERVO_Y1_OFFSET 0
#define SERVO_Y2_OFFSET 0
```

---

### 3.5 主程式：SD 卡資料記錄

```c
// 錄製邏輯：由 GPIO1 開關控制（低電平有效）
recording = !gpio_get(RECORDING_PIN);

// 開始錄製時：建立新檔案
if (recording && !recordingWasOn) {
    // 自動遞增檔名：IMU_1.csv, IMU_2.csv, ...
    sprintf(num, "%d", fileIncrement);
    strcpy(buf, "IMU_");
    strcat(buf, num);
    strcat(buf, ".csv");

    // 若檔案不存在 → 建立並寫入 CSV 標頭
    fr = f_open(&fil, buf, FA_OPEN_EXISTING);
    if (fr == FR_NO_FILE) {
        f_open(&fil, buf, FA_WRITE | FA_CREATE_NEW);
        f_printf(&fil, "Time(ms), AccelX, AccelY, AccelZ, "
                       "GravX, GravY, GravZ, Heading, Temp (*C)\r\n");
    }
}

// 每 100ms 寫入一筆資料（10Hz）
if (recording && (recordTimer + RECORD_DELAY <= currentTime)) {
    f_open(&fil, buf, FA_WRITE);
    f_lseek(&fil, f_size(&fil));   // 追加到檔案末尾
    f_printf(&fil, "%lu, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %d\r\n",
        currentTime,       // 時間戳（毫秒）
        f_accelX, f_accelY, f_accelZ,  // 線性加速度 (m/s²)
        f_gravX, f_gravY, f_gravZ,     // 重力向量 (m/s²)
        f_heading,                     // 方向角 (度)
        temperatureIMU);               // 溫度 (°C)
    f_close(&fil);
    recordTimer = currentTime;
}
```

**SD 卡輸出格式**（`IMU_1.csv`）：
```
Time(ms), AccelX, AccelY, AccelZ, GravX, GravY, GravZ, Heading, Temp (*C)
1234,  0.12, -0.05,  9.82,  0.08, -0.03,  9.79, 180.25, 28
1334,  0.15, -0.02,  9.81,  0.09, -0.04,  9.78, 180.30, 28
...
```

---

### 3.6 硬體設定：SPI 介面 (`hw_config.c`)

```c
// SPI1 設定（連接 SD 卡）
static spi_t spi = {
    .hw_inst  = spi1,
    .sck_gpio  = 10,      // GPIO10 = SPI 時脈
    .mosi_gpio = 11,      // GPIO11 = 主機發送
    .miso_gpio = 12,      // GPIO12 = 主機接收
    .baud_rate = 125000000 / 3   // ≈ 41.7 MHz（SD 卡最高速）
};

static sd_spi_if_t spi_if = {
    .spi = &spi,
    .ss_gpio = 13         // GPIO13 = 片選（Chip Select）
};
```

**SPI 速率選擇**：`baud_rate` 可試不同除數，SD 卡品質越好可用越高速率。若讀寫錯誤頻繁，改用 `/6` 或 `/8`。

---

### 3.7 建置系統：`CMakeLists.txt`

```cmake
# 關鍵設定：
pico_generate_pio_header(Rocket_Computer blink.pio)   # 自動生成 blink.pio.h
pico_generate_pio_header(Rocket_Computer servo.pio)   # 自動生成 servo.pio.h

target_link_libraries(Rocket_Computer
    pico_stdlib
    no-OS-FatFS-SD-SDIO-SPI-RPi-Pico   # SD 卡函式庫（carlk3）
    hardware_i2c                          # I2C（BNO055/BMP390）
    hardware_pio                          # PIO（伺服機/LED）
    hardware_dma                          # DMA（SD 卡傳輸加速）
    hardware_spi                          # SPI（SD 卡）
)

# 除錯輸出透過 USB（不用 UART，避免干擾 GPS）
pico_enable_stdio_uart(Rocket_Computer 0)
pico_enable_stdio_usb(Rocket_Computer 1)
```

---

## 4. GPIO 接腳配置

| GPIO | Pi Pico 腳位 | 功能 | 介面 | 說明 |
|------|-------------|------|------|------|
| 1 | Pin 2 | 錄製開關 | GPIO IN | 低電平啟動錄製（pull-up）|
| 2 | Pin 4 | 伺服 X1 | PIO1 SM0 | X 軸翼片 1 |
| 3 | Pin 5 | 伺服 X2 | PIO1 SM1 | X 軸翼片 2（反向）|
| 4 | Pin 6 | 伺服 Y1 | PIO1 SM2 | Y 軸翼片 1 |
| 5 | Pin 7 | 伺服 Y2 | PIO1 SM3 | Y 軸翼片 2（反向）|
| 6 | Pin 9 | 錄製 LED | PIO0 SM1 | 紅色 LED |
| 7 | Pin 10 | 狀態 LED | PIO0 SM0 | 黃色 LED |
| 8 | Pin 11 | GPS TX | UART1 TX | → GPS 模組 RX |
| 9 | Pin 12 | GPS RX | UART1 RX | ← GPS 模組 TX |
| 10 | Pin 14 | SD SCK | SPI1 CLK | SD 卡時脈 |
| 11 | Pin 15 | SD MOSI | SPI1 TX | SD 卡寫入 |
| 12 | Pin 16 | SD MISO | SPI1 RX | SD 卡讀取 |
| 13 | Pin 17 | SD CS | SPI1 CS | SD 卡片選 |
| 14 | Pin 19 | I2C SDA | I2C1 | BNO055 / BMP390 資料 |
| 15 | Pin 20 | I2C SCL | I2C1 | BNO055 / BMP390 時脈 |

**接線示意圖（麵包板）**：

```
Pi Pico                    BNO055
─────────                  ──────
3.3V (Pin 36) ──────────▶ VCC
GND  (Pin 38) ──────────▶ GND
GPIO14 (Pin 19) ────────▶ SDA
GPIO15 (Pin 20) ────────▶ SCL

Pi Pico                    MicroSD 模組（SPI）
─────────                  ────────────────────
3.3V  ──────────────────▶ VCC
GND   ──────────────────▶ GND
GPIO10 (Pin 14) ────────▶ CLK
GPIO11 (Pin 15) ────────▶ MOSI
GPIO12 (Pin 16) ────────▶ MISO
GPIO13 (Pin 17) ────────▶ CS

Pi Pico                    SG90 伺服機（×4）
─────────                  ──────────────────
5V (Pin 40) ────────────▶ 紅線（VCC）[所有伺服共用]
GND ────────────────────▶ 棕線（GND）[所有伺服共用]
GPIO2 ──────────────────▶ 橘線（訊號）X1
GPIO3 ──────────────────▶ 橘線（訊號）X2
GPIO4 ──────────────────▶ 橘線（訊號）Y1
GPIO5 ──────────────────▶ 橘線（訊號）Y2
```

> **注意**：伺服機使用 5V 供電（Pi Pico VSYS/VBUS），但訊號線為 3.3V，SG90 可直接接受。

---

## 5. 開發環境建置

### 5.1 安裝 Pico SDK（Linux / macOS）

```bash
# 安裝依賴
sudo apt install cmake gcc-arm-none-eabi libnewlib-arm-none-eabi \
                 libstdc++-arm-none-eabi-newlib git python3

# 下載 Pico SDK
git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk && git submodule update --init

# 設定環境變數
export PICO_SDK_PATH=$HOME/pico-sdk

# 加入 ~/.bashrc 永久生效
echo 'export PICO_SDK_PATH=$HOME/pico-sdk' >> ~/.bashrc
```

### 5.2 下載並建置專案

```bash
# Clone 專案
git clone https://github.com/SandwichRising/model-rocket-flight-computer.git
cd model-rocket-flight-computer/src/v1.0

# 下載 SD 卡函式庫（carlk3）
mkdir lib && cd lib
git clone https://github.com/carlk3/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico.git
cd ..

# 建置
mkdir build && cd build
cmake .. -DPICO_SDK_PATH=$PICO_SDK_PATH
make -j4
```

### 5.3 燒錄韌體

```bash
# 按住 Pi Pico 的 BOOTSEL 按鈕，同時接上 USB
# Pico 會掛載為 USB 磁碟（RPI-RP2）

# 複製 .uf2 檔案到磁碟
cp Rocket_Computer.uf2 /media/$USER/RPI-RP2/

# Pico 自動重啟並執行
```

### 5.4 啟用除錯模式

在 `Rocket_Computer.c` 頂部取消注解以啟用除錯輸出：

```c
#define DEBUG_MODE     // 顯示每秒迴圈次數（CPS）
#define DEBUG_PRINTS   // 啟用所有 printf 輸出
#define PRINT_IMU true // 顯示 IMU 數值
```

使用 `minicom` 或 `screen` 觀看 USB 串列輸出：
```bash
# 找到 Pico 的 USB 串列埠
ls /dev/ttyACM*

# 開啟串列監視器（115200 baud）
screen /dev/ttyACM0 115200
```

---

## 6. 逐步實作教程

### 階段一：驗證感測器（不需火箭）

**目標**：確認 BNO055 正常回傳資料。

```c
// 臨時修改 main() 最前面，只測試 IMU
#define SET_SERVOS false
#define RECORD_IMU false
#define PRINT_IMU true
#define DEBUG_PRINTS  // 取消注解
```

預期串列輸出：
```
BNO055 Initialized.
X:   0.12    Y:  -0.05    Z:   0.03
GrX:  0.08   GrY:  -0.03   GrZ:  9.79
Heading: 180.25    Temp: 28*C / 82*F  Mag: 1234
```

若 IMU 無回應：
- 確認 SDA/SCL 接線（GPIO14/15）
- 確認 I2C 位址（預設 0x28，ADR 腳位接 GND）
- 使用 I2C 掃描程式確認裝置可見

### 階段二：驗證伺服機控制

**目標**：確認 4 個伺服機可受 PIO 精確控制。

```c
// 在 main() 的主迴圈前測試
// 手動傳送不同脈衝寬度
pio1->txf[0] = 125000;   // 1ms → 全左
sleep_ms(1000);
pio1->txf[0] = 187500;   // 1.5ms → 中點
sleep_ms(1000);
pio1->txf[0] = 250000;   // 2ms → 全右
sleep_ms(1000);
```

確認每個伺服機行程範圍，記錄各伺服機的機械中點，計算並設定 `SERVO_Xn_OFFSET` 補正值。

### 階段三：閉迴路轉向測試（桌面）

**目標**：手持飛行電腦傾斜，觀察翼片跟隨轉向。

```c
// 確保以下均開啟
#define SET_SERVOS true
#define GET_IMU true
#define SERVO_STEP 7000  // 先從低值開始（4000）
```

測試方法：
1. 將飛行電腦夾在固定架上，讓翼片可自由活動
2. 傾斜飛行電腦，觀察翼片是否向反方向偏轉（修正方向）
3. 若翼片方向錯誤，在對應軸加上 `-1` 乘數

### 階段四：SD 卡記錄驗證

**目標**：確認錄製開關與資料寫入正常。

1. 格式化 MicroSD 卡（FAT32）
2. 插入卡，接通電源
3. 撥動錄製開關（GPIO1）→ 紅色 LED 慢速閃爍表示正在錄製
4. 傾斜感測器 30 秒後關閉開關
5. 取出 SD 卡，用電腦確認 `IMU_1.csv` 存在且資料筆數正確（應有約 300 筆）

### 階段五：增益調整（在飛行後分析）

根據錄製的飛行資料調整 `SERVO_STEP`：

| 飛行表現 | 調整方向 |
|----------|----------|
| 修正力道不足，火箭仍大幅偏斜 | 增加 SERVO_STEP |
| 修正過激，火箭來回振盪（震盪） | 減少 SERVO_STEP |
| 初期穩定但高空偏斜（高G失準）| 考慮加入 D 項或換用高G IMU |

---

## 7. 飛行資料分析

### 7.1 Python 快速分析腳本

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 讀取飛行資料
df = pd.read_csv('IMU_1.csv', skipinitialspace=True)
df.columns = ['time', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'heading', 'temp']
df['time'] = df['time'] / 1000.0  # 轉換為秒

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('飛行資料分析', fontsize=14)

# 線性加速度
axes[0, 0].plot(df['time'], df['ax'], label='X')
axes[0, 0].plot(df['time'], df['ay'], label='Y')
axes[0, 0].plot(df['time'], df['az'], label='Z')
axes[0, 0].set_title('線性加速度 (m/s²)')
axes[0, 0].legend()
axes[0, 0].set_xlabel('時間 (s)')

# 重力向量（偏斜指標）
axes[0, 1].plot(df['time'], df['gx'], label='gravX', color='red')
axes[0, 1].plot(df['time'], df['gy'], label='gravY', color='blue')
axes[0, 1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[0, 1].set_title('重力向量 (m/s²) — 0 表示完美垂直')
axes[0, 1].legend()
axes[0, 1].set_xlabel('時間 (s)')

# 高度重建（積分加速度）
dt = df['time'].diff().fillna(0)
# 去除重力分量，只保留線性加速度的 Z 軸（垂直方向）
net_az = df['az'] - 9.8  # 扣除靜止重力
net_az[net_az < -9.0] = 0  # 過濾靜止期雜訊

vz = np.cumsum(net_az * dt)       # 積分 → 速度
z = np.cumsum(vz * dt)            # 積分 → 位置（高度）

axes[1, 0].plot(df['time'], z, color='green')
axes[1, 0].set_title('重建高度 (m)（近似值）')
axes[1, 0].set_xlabel('時間 (s)')
axes[1, 0].set_ylabel('高度 (m)')

# 方向角
axes[1, 1].plot(df['time'], df['heading'], color='purple')
axes[1, 1].set_title('方向角 (度)')
axes[1, 1].set_xlabel('時間 (s)')

plt.tight_layout()
plt.savefig('flight_analysis.png', dpi=150)
plt.show()

# 統計摘要
print(f"飛行時長：{df['time'].max():.1f} 秒")
print(f"峰值加速度：{df['az'].max():.2f} m/s²（Z 軸）")
print(f"最大 gravX 偏斜：{df['gx'].abs().max():.2f} m/s²")
print(f"最大 gravY 偏斜：{df['gy'].abs().max():.2f} m/s²")
print(f"平均溫度：{df['temp'].mean():.1f} °C")
```

### 7.2 判讀飛行品質

```
良好飛行（主動控制有效）：
  gravX ≈ 0 ± 0.5 m/s²（推力期間）
  gravY ≈ 0 ± 0.5 m/s²
  az 出現明顯峰值（引擎推力段）後迅速歸零

控制失效指標：
  gravX 或 gravY 持續偏離 ±2 m/s² 以上 → SERVO_STEP 需增加
  gravX/Y 高頻振盪（蝴蝶效應）→ SERVO_STEP 需減少
  az 出現高頻雜訊 → 可能機身共振或感測器未固定
```

---

## 8. 常見問題排查

| 問題 | 可能原因 | 解決方式 |
|------|----------|----------|
| BNO055 無法初始化 | 接線錯誤或位址錯誤 | 確認 SDA/SCL 接 GPIO14/15，ADR 腳位接 GND |
| SD 卡 mount 失敗 | 格式問題或接線 | 確認 FAT32 格式，檢查 SPI 接線和 CS（GPIO13）|
| 伺服機不動 | PIO 未啟動或 5V 不足 | 確認伺服電源接 5V，確認 PIO 初始化成功 |
| 翼片方向相反 | 軸映射問題 | 調整 `SERVO_Xn_OFFSET` 或在 finPos 計算加 `-1` |
| SD 錄製時伺服抖動 | SPI 阻塞主迴圈 | 降低 SD baud rate，或等待 V2 中斷驅動方案 |
| GPS 啟用後伺服抖動 | UART 解析太慢 | 保持 `GET_GPS false`，這是 V1 已知限制 |
| BMP390 初始化卡住 | 過採樣設定問題 | 保持 `GET_BARO false`，設定 no oversample |
| 飛行中 IMU 資料突變 | 高G造成感測器融合失準 | 這是 BNO055 已知限制，高G環境需換用其他方案 |

---

## 9. 水火箭移植指南

### 9.1 主要修改項目

相較於模型火箭，移植到水火箭需調整以下部分：

**1. 降落傘展開機構**（最重要）

水火箭沒有引擎彈射藥，需用氣壓計偵測頂點後由伺服機觸發：

```c
// 在 GET_BARO 區塊中加入頂點偵測
static float prev_altitude = 0;
static bool apogee_detected = false;
static int descending_count = 0;

if (!apogee_detected) {
    if (f_altitudeData < prev_altitude - 0.5) {
        descending_count++;
        if (descending_count >= 3) {   // 連續 3 次下降才確認頂點
            apogee_detected = true;
            // 觸發降落傘伺服機
            pio1->txf[PARACHUTE_SM] = PARACHUTE_OPEN_TICKS;
        }
    } else {
        descending_count = 0;
    }
}
prev_altitude = f_altitudeData;
```

**2. 感測器高G補償**

水火箭初始加速度可達 20-50g，BNO055 重力向量在此期間不可靠：

```c
// 推力期間忽略重力向量，改用純加速度積分（陀螺儀）
// 判斷推力期：az 超過閾值
bool is_thrusting = (f_accelZ > THRUST_THRESHOLD);  // 例如 20 m/s²

if (!is_thrusting && SET_SERVOS) {
    // 正常重力向量控制
    finPos[0] = (f_gravX * SERVO_STEP) + SERVO_MIDPOINT;
    // ...
}
// 推力期 → 伺服保持中點，避免錯誤修正
```

**3. 機身適配（2L 寶特瓶 ≈ 110mm 直徑）**

需重新設計伺服外殼適配較大直徑，其餘電子部分完全相容。

### 9.2 水火箭簡化版架構

若以學習為主，可先用此最小配置：

```c
// 水火箭最小飛行電腦設定
#define SET_SERVOS  true   // 主動穩定（可選）
#define GET_IMU     true   // 姿態與加速度記錄
#define RECORD_IMU  true   // SD 卡記錄（最重要）
#define GET_GPS     false  // 暫不使用
#define GET_BARO    true   // 頂點偵測用（BMP390 需先修好初始化）
```

### 9.3 水火箭飛行電腦 vs 模型火箭對比

| 功能 | 模型火箭（V1） | 水火箭移植 |
|------|---------------|-----------|
| IMU 讀取 | ✅ 相同 | ✅ 相同 |
| 伺服控制 | ✅ 相同 | ✅ 相同（需重新校正增益）|
| SD 記錄 | ✅ 相同 | ✅ 相同 |
| 降落傘觸發 | 引擎彈射藥自動 | 需氣壓計 + 伺服觸發 |
| 高G處理 | 最高 ~7.5g | 需加高G補償邏輯 |
| 每次費用 | 引擎費用 | 幾乎零耗材 |
| 適合場景 | 精確飛行測試 | 快速迭代電子系統 |

---

## 參考資料

- [SandwichRising/model-rocket-flight-computer](https://github.com/SandwichRising/model-rocket-flight-computer) — 原始專案
- [RP2040 資料手冊](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) — PIO 章節（第 3 章）
- [BNO055 資料手冊](https://www.bosch-sensortec.com/products/smart-sensor-systems/bno055/) — 暫存器定義
- [carlk3/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico](https://github.com/carlk3/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico) — SD 卡函式庫
- [Raspberry Pi Pico SDK](https://github.com/raspberrypi/pico-sdk) — 官方 SDK 文件
- [OpenRocket](https://openrocket.info/) — 火箭飛行模擬軟體
- [IEEE UEMCON 2025 論文](https://ieeexplore.ieee.org/document/11267717) — V1 工程論文

---

*文件版本：1.0 | 更新日期：2026-06-02*

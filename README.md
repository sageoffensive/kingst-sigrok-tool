# Kingst LA Series — sigrok Firmware Tool

Use your **Kingst logic analyzer** with **sigrok**, **sigrok-cli**, **PulseView**, and **AI assistants** on Linux.

Includes an **MCP server** so AI tools (Windsurf, Claude Desktop, Cursor) can directly trigger captures, decode protocols, and analyze logic signals.

Supports the full Kingst LA lineup: LA1010, LA1010A, LA1016, LA2016, LA5016, LA5032, and MS6218.

Kingst devices require proprietary firmware to be uploaded on each connection. This tool extracts that firmware from the free KingstVIS application so sigrok can load it automatically.

---

## Quick Start (Linux)

```bash
# 1. Clone this repo
git clone https://github.com/sageoffensive/kingst-sigrok-tool.git
cd kingst-sigrok-tool

# 2. Build and install the official sigrok libsigrok
bash install_sigrok_driver.sh

# 3. Download KingstVIS for Linux and extract firmware
curl -L -o /tmp/KingstVIS_linux.tar.gz https://www.qdkingst.com/download/vis_linux
tar -xzf /tmp/KingstVIS_linux.tar.gz -C /tmp
python3 extract_firmware.py /tmp/KingstVIS/KingstVIS

# 4. Plug in your device and test
sigrok-cli --driver kingst-la2016 --scan
```

Expected output:
```
The following devices were found:
kingst-la2016:conn=1.14 - Kingst LA1010 with 18 channels: CH0 CH1 ... CH15 PWM1 PWM2
```

---

## Requirements

- **Linux** (Debian/Ubuntu/Kali or Fedora/RHEL)
- Python 3.9+
- Build tools: `git`, `autoconf`, `automake`, `libtool`
- Libraries: `libusb-1.0`, `libglib2.0`, `libzip`, `libserialport`

### KingstVIS (for firmware extraction)

The firmware files inside KingstVIS are proprietary to Kingst Electronics and **cannot be redistributed**. You must download KingstVIS yourself — it is free:

```bash
# Download the Linux version (recommended)
curl -L -o /tmp/KingstVIS_linux.tar.gz https://www.qdkingst.com/download/vis_linux
tar -xzf /tmp/KingstVIS_linux.tar.gz -C /tmp

# Extract firmware
python3 extract_firmware.py /tmp/KingstVIS/KingstVIS
```

The script extracts all firmware to:
```
~/.local/share/sigrok-firmware/
```

---

## What Gets Extracted

### MCU (Cypress FX2) Firmware

Uploaded to the device's USB microcontroller on first connect. Named for the official sigrok driver.

| File | Device |
|------|--------|
| `kingst-la-01a2.fw` | LA1010 / LA1010A (DFU PID 01A2) |
| `kingst-la-01a3.fw` | LA1010 rev A3 (DFU PID 01A3) |
| `kingst-la-01a4.fw` | LA1010 rev A4 (DFU PID 01A4) |
| `kingst-la-03a1.fw` | LA1016 / LA2016 / LA5016 / LA5032 (DFU PID 03A1) |

### FPGA Bitstreams

Configure the on-board FPGA after MCU firmware loads. Auto-selected by the driver based on device EEPROM.

| File | Device |
|------|--------|
| `kingst-la1010a0-fpga.bitstream` | LA1010A rev 0 |
| `kingst-la1010a1-fpga.bitstream` | LA1010A rev 1 |
| `kingst-la1010a2-fpga.bitstream` | LA1010A rev 2 |
| `kingst-la1016-fpga.bitstream` | LA1016 |
| `kingst-la1016a1-fpga.bitstream` | LA1016A rev 1 |
| `kingst-la2016-fpga.bitstream` | LA2016 |
| `kingst-la2016a1-fpga.bitstream` | LA2016A rev 1 |
| `kingst-la2016a2-fpga.bitstream` | LA2016A rev 2 |
| `kingst-la5016-fpga.bitstream` | LA5016 |
| `kingst-la5016a1-fpga.bitstream` | LA5016A rev 1 |
| `kingst-la5016a2-fpga.bitstream` | LA5016A rev 2 |
| `kingst-la5032a0-fpga.bitstream` | LA5032A rev 0 |
| `kingst-ms6218-fpga.bitstream` | MS6218 |

---

## Detailed Steps

### Step 1 — Install libsigrok

The official `libsigrok` includes the `kingst-la2016` driver which supports all Kingst LA devices.

```bash
bash install_sigrok_driver.sh
```

This will:
- Install build dependencies via apt/dnf
- Clone and build [sigrokproject/libsigrok](https://github.com/sigrokproject/libsigrok)
- Install to `/usr` and run `ldconfig`
- Install udev rules for USB access

### Step 2 — Extract firmware

```bash
python3 extract_firmware.py /tmp/KingstVIS/KingstVIS
```

Or specify a custom output directory:
```bash
python3 extract_firmware.py /tmp/KingstVIS/KingstVIS /custom/firmware/dir
```

The macOS KingstVIS binary is also supported as a fallback, but the Linux binary is required for correct firmware (the macOS version ships different MCU firmware that is incompatible with the official driver).

### Step 3 — Capture signals

Use the provided `kingst-cli` wrapper (hardcodes the driver for you):

```bash
# Scan for device (plug in first)
./kingst-cli --scan

# Capture 1 second at 10MHz on channels CH0 and CH1
./kingst-cli --config samplerate=10m \
           --channels CH0,CH1 --time 1s -o capture.sr

# Decode UART at 115200 baud
./kingst-cli --config samplerate=1m \
           --channels CH0 --time 5s \
           --protocol-decoder uart:rx=CH0:baudrate=115200
```

Or use `sigrok-cli` directly with `--driver kingst-la2016`:

```bash
# Scan for device (plug in first)
sigrok-cli --driver kingst-la2016 --scan

# Capture 1 second at 10MHz on channels CH0 and CH1
sigrok-cli --driver kingst-la2016 --config samplerate=10m \
           --channels CH0,CH1 --time 1s -o capture.sr

# Decode UART at 115200 baud
sigrok-cli --driver kingst-la2016 --config samplerate=1m \
           --channels CH0 --time 5s \
           --protocol-decoder uart:rx=CH0:baudrate=115200

# Open in PulseView GUI
pulseview
```

---

## How the Firmware Extractor Works

### Linux ELF mode (recommended)
KingstVIS for Linux embeds all firmware as Qt resource symbols in the ELF binary. The extractor:
1. Parses the ELF symbol table to find `_ZL16qt_resource_struct`, `_ZL16qt_resource_name`, `_ZL16qt_resource_data`
2. Walks the Qt resource tree to find the `fwusb` (MCU firmware) and `fwfpga` (FPGA bitstreams) directories
3. Converts Intel HEX firmware to raw binary blobs
4. Writes files with names the official `kingst-la2016` driver expects

### macOS Mach-O mode (fallback)
The macOS binary is also supported via `__TEXT __const` section parsing. However, the macOS KingstVIS ships MCU firmware that changes the device PID and is incompatible with the official sigrok driver. Use the Linux binary for production.

---

## Troubleshooting

**`Driver kingst-la2016 not found`**
- Run `bash install_sigrok_driver.sh` to build the official libsigrok from source

**`Device failed to re-enumerate`**
- Firmware file is wrong or missing. Re-run `python3 extract_firmware.py` using the **Linux** KingstVIS binary

**`Failed to open resource 'kingst-la-01a2.fw'`**
- Firmware files are missing. Run `python3 extract_firmware.py`
- Check: `ls ~/.local/share/sigrok-firmware/kingst-la-*.fw`

**Device not found / scan returns nothing**
- Unplug and replug the USB cable (full power cycle needed between runs)
- Check USB permissions: `lsusb | grep 77a1` — if it shows, run `sudo sigrok-cli ...` to confirm it's a permissions issue
- Reinstall udev rules: re-run `bash install_sigrok_driver.sh`

**`Unexpected run state` warning**
- This is normal on first use after device enumeration. The device still works.

---

## Supported Devices

| Device | DFU VID:PID | MCU Firmware | FPGA Bitstream |
|--------|-------------|--------------|----------------|
| Kingst LA1010 (rev A2) | 77A1:01A2 | kingst-la-01a2.fw | kingst-la1010a0/a1/a2-fpga.bitstream |
| Kingst LA1010 (rev A3) | 77A1:01A3 | kingst-la-01a3.fw | kingst-la1010a0/a1/a2-fpga.bitstream |
| Kingst LA1010 (rev A4) | 77A1:01A4 | kingst-la-01a4.fw | kingst-la1010a0/a1/a2-fpga.bitstream |
| Kingst LA1016 | 77A1:03A1 | kingst-la-03a1.fw | kingst-la1016-fpga.bitstream |
| Kingst LA1016A (rev 1) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la1016a1-fpga.bitstream |
| Kingst LA2016 | 77A1:03A1 | kingst-la-03a1.fw | kingst-la2016-fpga.bitstream |
| Kingst LA2016A (rev 1) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la2016a1-fpga.bitstream |
| Kingst LA2016A (rev 2) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la2016a2-fpga.bitstream |
| Kingst LA5016 | 77A1:03A1 | kingst-la-03a1.fw | kingst-la5016-fpga.bitstream |
| Kingst LA5016A (rev 1) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la5016a1-fpga.bitstream |
| Kingst LA5016A (rev 2) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la5016a2-fpga.bitstream |
| Kingst LA5032A (rev 0) | 77A1:03A1 | kingst-la-03a1.fw | kingst-la5032a0-fpga.bitstream |
| Kingst MS6218 | 77A1:03A1 | kingst-la-03a1.fw | kingst-ms6218-fpga.bitstream |

Driver: official [sigrokproject/libsigrok](https://github.com/sigrokproject/libsigrok) `kingst-la2016`.

---

## MCP Server (AI Assistant Integration)

`mcp_server.py` exposes the logic analyzer as an MCP tool server, letting AI assistants (Windsurf, Claude Desktop, Cursor) directly trigger captures and decode protocols.

### Available Tools

| Tool | Description |
|------|-------------|
| `scan_device` | Scan for connected Kingst device |
| `capture` | Capture logic signals, returns `.sr` file |
| `decode_uart` | Capture + decode UART, returns ASCII text |
| `decode_protocol` | Capture + run any sigrok protocol decoder |
| `save_capture` | Save a capture to a named file |
| `list_decoders` | List all available sigrok decoders |

### Setup

**1. On the Linux machine (where the analyzer is connected):**
```bash
# No extra dependencies — uses only Python stdlib
chmod +x mcp_server.py
```

**2. In your AI tool's MCP config** (e.g. `~/.config/windsurf/mcp_settings.json` or `claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "kingst-la": {
      "command": "ssh",
      "args": [
        "user@your-linux-host",
        "python3",
        "/home/user/kingst-sigrok-tool/mcp_server.py"
      ]
    }
  }
}
```

See `mcp_config_example.json` for a ready-to-edit template.

### Example AI Prompts

Once connected, you can ask your AI assistant things like:

- *"Scan for the logic analyzer and tell me what's connected"*
- *"Capture 10 seconds of UART on CH1 at 115200 baud and show me the output"*
- *"Decode the SPI traffic on CH0 (CLK), CH1 (MOSI), CH2 (MISO), CH3 (CS)"*
- *"Save a 30 second capture to /tmp/boot.sr then decode the UART on CH0"*

---

## License

The extractor script (`extract_firmware.py`) and installer (`install_sigrok_driver.sh`) are MIT licensed.

The **firmware files themselves** are proprietary to Kingst Electronics Co., Ltd. and are **not included** in this repository. You extract them from KingstVIS which you download directly from Kingst.

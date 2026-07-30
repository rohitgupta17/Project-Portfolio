# Smart Sprinkler System for Wildfire Defense

A prototype wildfire-defense sprinkler system that monitors local environmental conditions, evaluates fire risk, and automatically activates a water pump when a camera-based classifier detects fire. The project integrates an STM32 sensor/camera node with a Raspberry Pi 4 central controller over Bluetooth serial communication.

> **Prototype notice:** This is an academic proof of concept, not a certified fire-protection product. Do not rely on it for life safety, property protection, or emergency response.

## Overview

The system combines two complementary functions:

- **Active fire response:** An OV7670 camera captures an image that is classified by a TensorFlow model. A positive fire prediction turns on the sprinkler pump.
- **Fire-risk awareness:** Temperature, humidity, gas readings, and forecast weather data are combined into a normalized risk score. The Raspberry Pi shows sensor values and a low/medium/high risk indicator on an SH1106 OLED display.

The sprinkler can also be activated manually with a button connected to the Raspberry Pi.

## System architecture

```text
OV7670 camera ─┐
DHT11 sensor ─┼─> STM32 ── Bluetooth UART (9600 baud) ──> Raspberry Pi 4
MQ135 sensor ─┘                                           │
                                                          ├─ TensorFlow fire classifier
Weather forecast API ─────────────────────────────────────┤
                                                          ├─ SH1106 OLED risk display
Manual button ────────────────────────────────────────────┤
                                                          └─ GPIO-controlled pump / sprinkler
```

The STM32 captures a 160 x 120 RGB565 image and periodically sends sensor readings alongside the image stream. The Raspberry Pi reconstructs the RGB image, retrieves weather data for Seattle, updates the risk display, and controls the sprinkler relay/pump.

## Key features

- Fire/no-fire image classification with a TensorFlow CNN.
- Automatic sprinkler activation when fire is detected.
- Manual sprinkler override via a GPIO button.
- Temperature and humidity monitoring with a DHT11.
- Gas-sensor readings via an MQ135-style analog sensor.
- Weather-aware fire-risk calculation using precipitation, dry chance, wind, and thunder chance.
- Live SH1106 OLED display of sensor values and low/medium/high fire risk.
- Bluetooth serial link between the STM32 and Raspberry Pi.

## Hardware

| Component | Role |
| --- | --- |
| Raspberry Pi 4 | Central controller, ML inference, weather lookup, OLED and pump control |
| STM32F4 | Camera capture, sensor acquisition, and UART transmission |
| OV7670 camera | Captures 160 x 120 RGB565 images |
| HC-06 Bluetooth module | Serial link between the STM32 and Raspberry Pi |
| DHT11 | Temperature and relative-humidity sensing |
| MQ135 gas sensor | Analog gas/air-quality reading |
| SH1106 OLED (I2C, `0x3C`) | Displays readings and fire-risk level |
| 12 V pump, sprinkler, relay/MOSFET | Water delivery and switching |
| Push button | Manual sprinkler activation |

## Repository contents

```text
final.py        Raspberry Pi application: serial receive, risk scoring, OLED, ML inference, pump control
model.py        CNN training script
resizeImage.py  Dataset image-resizing utility
main.c          STM32 firmware application code
```

`main.c` is intended to live in an STM32CubeIDE project that supplies generated files such as `main.h`, `usb_host.h`, camera drivers, HAL configuration, and startup code.

## Software requirements

### Raspberry Pi

- Raspberry Pi OS with Python 3
- A paired HC-06 device exposed as `/dev/rfcomm0`
- Python packages:

```bash
python3 -m pip install pyserial RPi.GPIO Pillow luma.oled python-weather numpy matplotlib opencv-python tensorflow
```

The hardware-facing libraries (`RPi.GPIO`, `luma.oled`) must be installed and run on the Raspberry Pi. TensorFlow must be installed in a version compatible with the Pi and its operating system.

### Model training workstation

```bash
python3 -m pip install numpy Pillow opencv-python tensorflow scikit-learn
```

The training script expects this dataset layout:

```text
archive/
└── fire_dataset/
    ├── fire_images/
    └── non_fire_images/
```

The source dataset is credited in the project report to Ahmed Saied, Ahmed Gamaleldin, Ahmed Atef, Heba Saker, and Ahmed Shaheen.

## Setup

1. Create and configure the STM32CubeIDE project for the camera, DCMI, DMA, UART, ADC, I2C, timer, and GPIO peripherals. Add `main.c` and the OV7670 support files used by the firmware.
2. Wire the sensors, camera, Bluetooth module, relay/pump driver, and OLED. Confirm the pump power circuit is safely isolated from the Pi GPIO.
3. Pair the HC-06 to the Raspberry Pi and create the RFCOMM serial device expected by `final.py`:

   ```bash
   sudo rfcomm bind 0 <HC-06-BLUETOOTH-MAC> 1
   ```

4. Train the classifier or copy a compatible trained model to the Pi:

   ```bash
   python3 model.py
   ```

5. Point `final.py` at the exported model. The included training script writes `my_model.keras`, while the runtime currently loads `fire_detection_model.h5`; make the filename and format consistent before running.
6. Place `riskGraphic.png` in the same directory as `final.py`.
7. Review the hardware-specific constants in `final.py`, including the serial port, GPIO pin numbers, I2C address, model filename, and weather location.
8. Run on the Raspberry Pi:

   ```bash
   sudo python3 final.py
   ```

## How it works

1. The Raspberry Pi sends `I` over Bluetooth to request a new image.
2. The STM32 captures an OV7670 snapshot and sends each pixel as `x`, `y`, and two RGB565 bytes. It also sends sensor data every tenth image row.
3. The Raspberry Pi converts RGB565 pixels to RGB, rebuilds the image, and evaluates it with the TensorFlow classifier.
4. A positive prediction activates the sprinkler output; a negative prediction turns it off.
5. In parallel, the Pi fetches forecast data and combines it with sensor data for an OLED fire-risk indicator.

## Fire-risk scoring

The implementation computes a normalized risk score from temperature, humidity, gas concentration, predicted precipitation, remaining-dry chance, wind speed, and thunder chance. The score is displayed as:

| Score | OLED level |
| --- | --- |
| `<= 0.2` | Low |
| `> 0.2` and `<= 0.5` | Medium |
| `> 0.5` | High |

This score is an experimental heuristic for awareness only. The automatic pump decision is based on the computer-vision model, rather than the risk score.

## Testing and results

The prototype was evaluated with controlled sensor conditions and images of fires shown to the camera, rather than live wildfire testing. The project report records successful manual activation, risk-level updates under controlled conditions, and correct classification across dozens of test images. It also notes occasional false positives and image-transfer response times that can approach one minute over the 9600-baud Bluetooth link.

## Limitations and future work

- Bluetooth throughput limits image transfer speed and response time.
- The model needs more diverse real-world validation to reduce false positives.
- The system is a small-scale prototype; full-property coverage would require higher-capacity pumping and multiple or longer-range sprinkler units.
- Weather data is currently requested for a hard-coded location (`Seattle`).
- The risk formula is a heuristic and has not been validated for operational fire-safety use.
- External services and hardware failures need stronger fault handling for a field deployment.

## Team

Rohit Gupta, Christopher Andrade, Lynden Huang, Garrett Lee, and Lincoln Lewis
Department of Electrical and Computer Engineering, University of Washington

## Acknowledgments

Weather inputs are retrieved through the `python-weather` wrapper, which uses World Weather Online data. The training dataset is credited above. Hardware and lab resources were provided through the University of Washington course environment.

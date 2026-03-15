🧓 STM32-Based Elderly Fall Detection and Health Monitoring System
📌 Project Overview

This project implements a remote elderly health monitoring and fall detection system based on the STM32F103C8T6 microcontroller.

The system integrates multiple sensors to monitor the physiological condition and motion state of elderly users in real time. When abnormal events occur, such as falls or abnormal vital signs, the device automatically triggers an alarm and sends an SMS alert containing GPS location information.

The project aims to provide a portable and low-cost safety monitoring solution for elderly care.

📷 System Prototype

![Device](docs/images/Photograph of the device.jpg)

⚙️ System Features

🚶 Fall detection using ADXL345

❤️ Heart rate monitoring (MAX30102)

🫁 Blood oxygen monitoring (SpO₂)

🌡 Body temperature monitoring (DS18B20)

📍 GPS positioning

📩 SMS alarm notification (SIM800 GSM module)

📟 OLED real-time display

⚠️ Threshold configuration

🆘 Emergency help button

🏗 System Architecture
Sensors → STM32 → Data Processing
             ↓
         OLED Display
             ↓
         Buzzer Alarm
             ↓
        GSM SMS Alert
             ↓
        GPS Location

The STM32 processes sensor data and determines whether abnormal conditions occur.

🧪 Experimental Results
System Operation

![Normal State](docs/images/Normal working state diagram.jpg)

Proteus Simulation

![Proteus](docs/images/Proteus simulation.png)

Fall Detection Experiment

![Fall](docs/images/Real-life image of an elderly person falling and standing up.png)

The ADXL345 accelerometer is used to detect motion changes and determine whether a fall occurs.

Heart Rate Sensor Test

![Heart Sensor](docs/images/Red LED indicator when the heart rate sensor is active.jpg)

The red LED indicates that the MAX30102 sensor is actively detecting heart rate and blood oxygen signals.

SMS Alert Example

![SMS](docs/images/SMS received after the elderly person fall.png)

When abnormal conditions occur, the system sends an SMS alert containing health data and location information.

GPS Positioning Test

![GPS](docs/images/Figure X. Experimental results of the GPS module in indoor and open outdoor environments (latitude and longitude can be clearly observed only in outdoor conditions).png)

⚠️ Important Note

The GPS module requires satellite signals.

Indoor: satellite signals cannot be received, therefore latitude and longitude cannot be displayed.

Outdoor: when satellite signals are available, accurate GPS coordinates can be obtained.

🎥 Demonstration Videos

Two demonstration videos are included:

Hardware demonstration:

docs/video/Hardware_Demonstration_Video.mp4

System simulation:

docs/video/System_Simulation_Demonstration.mp4
📂 Repository Structure
Fall-Detection-System-STM32
│
├── bom
│   └── list.xlsx
│
├── docs
│   ├── images
│   ├── video
│   └── Final report PDF
│
├── hardware
│   Reference hardware design files
│
├── src
│   STM32 firmware source code
│
└── README.md
⚠️ Hardware Files Notice

The hardware folder contains schematic and PCB design files created during development.

These files represent design drafts and intermediate versions, and may not correspond exactly to the final hardware implementation used in the experiments.

They are provided for reference purposes only.

📦 Bill of Materials

Component list:

bom/list.xlsx
📄 Project Report

Full dissertation:

docs/U2180177 Li Fengzhe Final report.pdf
👨‍💻 Author

Li Fengzhe

Final Year Project

Remote Elderly Live Alarm and Positioning Management System
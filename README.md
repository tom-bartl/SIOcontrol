# SIOcontrol - Shake-it-off Device Control

A Raspberry Pi-based control system for automated sample preparation with cryogenic spray and plunge mechanisms.

## Overview

**Shake-it-off** is the PyQt GUI application for controlling the SIO (Sample Injection & Orientation) device—an automated system designed for rapid sample preparation in laboratory environments. The device combines piezo spray, pneumatic plunging, and temperature monitoring to deliver reproducible, high-speed samples for analysis.

### Key Capabilities
- **Automated spray and plunge** control with configurable timing
- **Cryogenic safety interlock** monitoring (temperature-sensitive)
- **Plunger position sensing** via IR proximity detection
- **System cleaning cycles** with multi-pulse spray control
- **Touch-friendly GUI** with debounce for resistive screens
- **Real-time status monitoring** and logging

## Hardware Components

### Main Actuators
- **Plunger Solenoid** (GPIO 20): Engages sample holder
- **Retract Solenoid** (GPIO 21): Retracts plunger mechanism
- **Piezo Spray System** (GPIO 13, MOSFET-controlled): Controls spray using pneumatic pressure
- **Spray Control Lines**: Pulsed control for start/stop spray sequences

### Sensors & Safety
- **Plunger IR Proximity Sensor** (GPIO 12): Detects plunger position (READY/PLUNGED)
- **Cryostat Interlock** (GPIO 6, Reed Switch): Safety cutoff if cryogenic chamber is not at temperature
- **Sensor Power Control** (GPIO 26): Powers sensor circuits on demand

### Electronics
- Raspberry Pi GPIO control (BCM mode)
- MOSFET drivers for high-current loads
- Pull-up configured interlock reed switch
- PCB schematics in `PCB/` directory

## System Requirements

### Hardware
- **Raspberry Pi** 3B, 3B+, 4, or 5
- **GPIO Pin Compatibility**: Standard 40-pin header
- **Power Supply**: 5V USB-C (Pi) + 24V source for solenoids/spray system
- **Assembly**: See [Assembly Instructions](#assembly-instructions)

### Software
- **OS**: Raspberry Pi OS (Bullseye or later recommended)
- **Python**: 3.7 or later
- **PyQt**: 5.x or 6.x
  - On Raspberry Pi OS (preferred): `sudo apt install python3-pyqt5`
  - Via pip (other systems): `pip install PyQt6>=6.6`
- **GPIO Control**: RPi.GPIO library (included with Raspberry Pi OS)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/SIOcontrol.git
   cd SIOcontrol
   ```

2. **Install dependencies** (Raspberry Pi OS):
   ```bash
   sudo apt update
   sudo apt install python3-pyqt5 python3-pip
   ```
   
   Or for other systems:
   ```bash
   pip install -r requirements-pyqt-poc.txt
   ```

3. **(Optional) Install desktop launcher**:
   ```bash
   ./install_linux_launcher.sh
   ```
   This creates:
   - Application launcher in `~/.local/share/applications/`
   - Desktop shortcut (if `~/Desktop` exists)
   - Trusted execution flags
   - Auto-start from project directory

## Usage

### GUI Application

**Launch the application**:
```bash
python3 SIOgui.py
```

Or via desktop launcher after running `install_linux_launcher.sh`.

### Main Controls

**Control Panel**:
- **Spray Time (ms)**: Duration of piezo spray pulse (default: 5 ms, adjustable with +/- buttons)
- **Plunge Delay (ms)**: Delay from spray start to plunger engagement (default: 5 ms)
- **Do Not Plunge**: Checkbox to skip the plunge phase (spray-only mode)
- **Spray & Plunge Button**: Initiates the complete sequence (red, disabled until armed)

**Status Indicators**:
- **Plunger Position**: Colored dot showing status
  - 🟢 **READY**: Plunger retracted, ready to plunge
  - 🔴 **PLUNGED**: Plunger engaged with sample
  - ⚫ **N/A**: Sensor not ready
- **System Status**: Real-time log of operations and errors

**Safety Controls**:
- **Arm/Disarm Button**: Arms the system for spray/plunge operations
- **Cryostat Interlock**: Safety check for cryogenic chamber status
  - System will not operate if interlock is not satisfied (e.g., cryostat not cold)

### Command-Line Utilities

**Apply & Spray**:
```bash
python3 SIOapplyandplunge.py --stime 0.5 --sdelay 0.1
```
- `--stime`: Spray pulse duration (seconds)
- `--sdelay`: Delay before spray starts (seconds)

**Cleaning Cycle**:
```bash
python3 SIOclean.py --stime 0.2 --cycles 10
```
- `--stime`: Duration of each spray pulse (seconds, default: 0.2)
- `--cycles`: Number of cleaning pulses (default: 5)

**Power Control**:
```bash
python3 SIOpowerupdown.py --updown up    # Arm spray system
python3 SIOpowerupdown.py --updown down  # Disarm spray system
```

## Hardware Schematics

**Note**: Hardware schematics and detailed CAD designs are placeholders and will be updated. Current design files are in:
- **3D CAD Models**: `CAD_files/` (Fusion 360 .f3d and STEP formats)
  - Connector assemblies
  - Plunging solenoid holder
  - Small solenoid base
  - Piezo mount
  - Cryogenic container
- **PCB Designs**: `PCB/` (Altium/Eagle formats)
  - Schematic (`shake-it-off-v1-main.sch`)
  - PCB layout (`shake-it-off-v1-main.PCB`)

*Complete hardware documentation with pinout diagrams and electrical schematics coming soon.*

## Assembly Instructions

### Overview
Assembly involves three main stages:
1. **Mechanical assembly** of actuators and sensors (2-3 hours)
2. **Electrical integration** of solenoids, sensors, and control circuits (1-2 hours)
3. **Software setup** and calibration (30-45 minutes)

**Difficulty Level**: Intermediate - requires soldering, mechanical alignment, and GPIO understanding

### Mechanical Assembly (Placeholder)

See `CAD_files/` for 3D models. General steps:
1. Mount solenoid base on frame
2. Attach plunging solenoid and retract mechanism
3. Install plunger tip and sample holder
4. Mount IR proximity sensor parallel to plunger travel
5. Install cryostat detection mechanism (reed switch)
6. Mount piezo spray system with tubing

*Detailed assembly guide with photos coming soon.*

### Electrical Assembly (Placeholder)

1. **Solenoid wiring** to MOSFET drivers on control PCB
2. **Sensor connections**:
   - Plunger IR sensor → GPIO 12
   - Cryostat reed switch → GPIO 6 (with pull-up)
3. **Spray control** (MOSFET gate) → GPIO 13
4. **Power distribution**:
   - Solenoid power (24V) through current-limiting
   - Sensor power switched via GPIO 26
5. **Pi connection**: 40-pin header to control PCB

*Wiring diagram and PCB assembly guide coming soon.*

### Software Setup

1. **Clone repository** (see [Installation](#installation))
2. **Install dependencies**: `sudo apt install python3-pyqt5`
3. **Verify GPIO access**: User must be in `gpio` group
   ```bash
   sudo usermod -a -G gpio $USER
   # Log out and back in for group change to take effect
   ```
4. **Test hardware**:
   ```bash
   python3 SIOpowerupdown.py --updown up    # Should initialize spray
   python3 SIOpowerupdown.py --updown down  # Should disarm
   ```
5. **Launch GUI**: `python3 SIOgui.py`
6. **Calibrate timing**: Adjust spray time and plunge delay for your setup

## Code Structure

| File | Purpose |
|------|---------|
| `SIOgui.py` | Main PyQt GUI application (742 lines) |
| `SIOapplyandplunge.py` | Spray & plunge operation script |
| `SIOclean.py` | System cleaning cycle script |
| `SIOpowerupdown.py` | Spray system arm/disarm control |
| `SIOpinlist.py` | GPIO pin definitions (BCM numbering) |
| `sio_widgets.py` | Custom PyQt widgets (touch-optimized) |

## GPIO Pin Mapping (BCM)

| GPIO | Direction | Function | RPi Pin |
|------|-----------|----------|---------|
| 20 | OUT | Plunger solenoid | 38 |
| 21 | OUT | Retract solenoid | 40 |
| 26 | OUT | Sensor power control | 37 |
| 13 | OUT | Spray control (MOSFET) | 33 |
| 12 | IN | Plunger IR sensor signal | 32 |
| 6 | IN | Cryostat interlock (pullup) | 31 |

**Hardware Changes** (from original SIO design):
- Plunger IR sensor now always enabled (legacy enable pin retained for compatibility)
- Spray control pin added (MOSFET controls power to piezo spray)
- Cryostat sensor changed to simple reed switch with pull-up (switch normally open, closes to pull pin to ground)

## Known Issues & Troubleshooting

### GUI &amp; Operation
- **Button presses not registering**: Touch screens may need debounce adjustment in `SIOgui.py` (default: 0.22s)
- **Plunger status shows N/A**: Check IR sensor power and GPIO 12 wiring
- **Spray & Plunge button disabled**: Verify arm button is pressed and cryostat interlock is satisfied

### Hardware
- **Solenoids not firing**: Check 24V power supply and MOSFET driver connection
- **IR sensor not detecting**: Verify sensor alignment and lens clarity
- **Cryostat interlock stuck**: Check reed switch and GPIO 6 pull-up resistor

### Software
- **ImportError: No module named 'RPi.GPIO'**: Install `python3-dev` and `python3-rpi.gpio`
  ```bash
  sudo apt install python3-dev python3-rpi.gpio
  ```
- **Permission denied on GPIO**: Add user to `gpio` group (see [Software Setup](#software-setup))
- **PyQt import errors**: Install PyQt5 via apt (preferred on Pi OS)
  ```bash
  sudo apt install python3-pyqt5
  ```

## Development & Customization

### Modifying Timing
Edit control parameters in the GUI or command-line scripts:
- `spray_time`: Piezo spray duration (milliseconds)
- `plunge_delay`: Time from spray start to plunger engagement (milliseconds)
- Cleaning: `--stime` and `--cycles` for spray pulse duration and repetition

### Extending Functionality
- Custom GPIO control: Modify `SIOpinlist.py` and sensor/actuator code
- UI changes: Edit `SIOgui.py` (uses PyQt layout system)
- New operation scripts: Follow the pattern of `SIOapplyandplunge.py`

## License & Attribution

**Original Project**: [johnrubinstein/SIOcontrol](https://github.com/johnrubinstein/SIOcontrol)
- Author: John Rubinstein and contributors

**This Fork**: [Your Name/Organization]
- Hardware refinements and PyQt6 compatibility
- Extended documentation and assembly guides

*License details: [To be specified]*

## References

- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.com/documentation/computers/os.html#gpio-and-the-40-pin-header)
- [RPi.GPIO Python Library](https://pypi.org/project/RPi.GPIO/)
- [PyQt5 Documentation](https://pypi.org/project/PyQt5/)
- [Original SIOcontrol Repository](https://github.com/johnrubinstein/SIOcontrol)

## Support & Contributing

For issues, questions, or contributions:
- Check [Known Issues](#known-issues--troubleshooting)
- Review the code comments in `SIOgui.py`
- Open an issue on GitHub

---

**Last Updated**: April 2026  
**Tested On**: Raspberry Pi OS (Bullseye), PyQt5, Python 3.9+

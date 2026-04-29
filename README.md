# SIOcontrol - Shake-it-off Device Control

A Raspberry Pi-based control system for automated sample preparation with piezo spray and plunge freezing mechanisms.

## Overview

**Shake-it-off** is the Python GUI application for controlling the SIO (Shake-it-off) device - an automated system designed for spraying the sample onto the grid and automaticly plunge freezing them.

### Key Capabilities
- **Automated spray and plunge** control with configurable timing
- **Cryostat safety interlock** prevents operation without the vitrification dewar
- **Plunger position sensing** via IR proximity detection
- **Sprayer cleaning** with multi-pulse spray control
- **Touch-friendly GUI**
- **Real-time status monitoring** and logging

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
- **Plunge Delay (ms)**: Delay from spray start to plunger engagement (default: 5 ms), the retract solenoid activates in the middle of the delay
- **Do Not Plunge**: Checkbox to skip the plunge phase (spray-only mode)
- **Spray & Plunge Button**: Initiates the complete sequence (disabled until armed)

**Status Indicators**:
- **Plunger Position**:
  - 🟢 **READY**: Plunger armed, ready to plunge
  - 🔴 **PLUNGED**: Plunger unpowere in lower position (if tweezer is attached, the grid should be submerged in ethane at this point)
- **Cryostat interlock**:
  - 🟢 **OK**: Cryostat present, normal operation
  - 🔴 **EMPTY**: Cryostat not prosent or not placed correcectly, all opration disabled except cleaning.

### Operation
1. Power up the control computer and plug the SIO power source.
2. Connect all the connectors and press the turn-on switch on the front (starts glowing green).
3. Launch SIO Control.
4. Verify functionality of the sensors - plunger sensor and cryostat interlock.
5. Place the vitrification dewar in its place. The "Cryostat Interlock" should turn green.
6. Pull the spray plate to the forward position (or rather push it from behind).
7. Set your parameters.
8. Press the "READY" button.
9. Push the plunger to the upper position; it should stay there and the plunger indicator status should change to green.
10. If you wish to abort, press the "ABORT" button and manually pull the plunger back to the lower position.
11. Place the tweezer with a grid attached to the plunger.
12. Align the spray disc with the grid (the distance can be adjusted by loosening the 4 screws on top, rotating the adjustment screw to move it closer or further, and tightening the 4 screws again).
13. Apply sample with a pipette to the centre of the spray disc.
14. Make sure everything is aligned and free to move.
15. Press the "APPLY and PLUNGE" button (alternatively check the "do not plunge" checkbox).
16. Remove the tweezer from the plunger and transfer the grid into the grid box.

## Hardware Components

### Main Actuators
- **Plunger Solenoid** (GPIO 20): Plunges the grid into the vitrification dewar
- **Retract Solenoid** (GPIO 21): Retracts the spray mechanism to free space for the plunger
- **Piezo Spray System** (GPIO 13): Controls piezo spray module (the pin signal emulates a button press, taking the module input pin to GND for shot pulse. The module detects 3 different button presses - 1. start spraying, 2. spray for 5 hours, 3. stop spraying. So the control sends two singals at the start of the spraying and for the module to be ready to stop it and than the third signal at end of the reqired spray period.)

### Sensors & Safety
- **Plunger IR Proximity Sensor** (GPIO 12): Detects plunger position (READY/PLUNGED)
- **Cryostat Interlock** (GPIO 6): Safety cutoff if vitrifaction dewar is not present

### Electronics
- Raspberry Pi GPIO control
- Solidstate DC/DC realay modules (to prevent sparking in cobustible enviroment)
- Electronic schematics in `PCB/` directory

## System Requirements

### Hardware
- **Raspberry Pi** 3B, 3B+, 4, or 5
- **GPIO Pin Compatibility**: Standard 40-pin header
- **Power Supply**: 5V USB-C (Pi) + 24V source for solenoids + 5V for sensors and piezo spray module

### Software
- **OS**: Raspberry Pi OS
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

## Code Structure

| File | Purpose |
|------|---------|
| `SIOgui.py` | Main PyQt GUI application |
| `SIOapplyandplunge.py` | Spray & plunge operation script |
| `SIOclean.py` | System cleaning cycle script |
| `SIOpowerupdown.py` | Spray system arm/disarm control |
| `SIOpinlist.py` | GPIO pin definitions (BCM numbering) |
| `sio_widgets.py` | Custom PyQt widgets (touch-optimized) |

## GPIO Pin Mapping

| GPIO | Direction | Function | RPi Pin |
|------|-----------|----------|---------|
| 20 | OUT | Plunger solenoid | 38 |
| 21 | OUT | Retract solenoid | 40 |
| 26 | OUT | Sensor power control | 37 |
| 13 | OUT | Spray control | 33 |
| 12 | IN | Plunger IR sensor signal | 32 |
| 6 | IN | Cryostat interlock (pullup) | 31 |

**Hardware Changes** (from original SIO design):
- Plunger IR sensor now always enabled (legacy enable pin retained for compatibility)
- Spray control pin added (MOSFET controls power to piezo spray)
- Cryostat sensor changed to simple reed switch with pull-up (switch normally open, closes to pull pin to ground)

## Possible Issues & Troubleshooting

### GUI &amp; Operation
- **Button presses not registering**: Touch screens may need debounce adjustment in `SIOgui.py` (default: 0.22s)
- **Plunger status shows N/A**: Check IR sensor power and GPIO 12 wiring
- **Spray & Plunge button disabled**: Verify arm button is pressed and cryostat interlock is satisfied

### Hardware
- **Solenoids not firing**: Check 24V power supply and relays connection
- **IR sensor not detecting**: Verify sensor alignment

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

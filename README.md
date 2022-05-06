# Parallel Spatial Domain Thermoreflectance Sensor - Server

Current features:
- Control the DMD rgb and laser projectors, the helicam lock-in camera, and the CMOS camera
- Virtually align camera and projector surfaces
- Send trajectory patterns to the projectors

| Set trajectories in projectors (edit) | Set waveform generator settings (edit) |
| --- | --- |
| ![projectors-tab](/resources/dmd-projector-v2.gif) | ![signal-generator-tab](/resources/signal-generator-v1.gif) |

### Installation instructions
##### Download this repo:
- Download the files directly or clone the repo using git (you can download git for Windows from [here](https://git-scm.com/download/win))
##### Python requirements:
- Install Python 3.9 (https://www.python.org/downloads/release/python-399/)
- Run `pip install -r requirements.txt`
##### Projector driver:
- Download Zadig from [here](http://zadig.akeo.ie/)
- Connect the projector
- Go to 'Options' -> 'List All Devices'
- Look for 'DLCP900 (Interface 0)
- Replace WinUSB driver with libusb-win32 driver
- _NOTE: TI GUI will stop working once you replace the driver. If you want to restore the WinUSB driver, go to Device Manager, search for the libusb-win32 driver, uninstall and check 'Delete the driver software for this device'_
##### Lock-in camera driver:
- Download and install the SDK from [here](https://github.com/byutemplab/helicam-sdk)
##### CMOS Camera driver:
- Download native driver from [here](https://astronomy-imaging-camera.com/software-drivers)

### Running the GUI
- Open the terminal from the src folder
- Run `python main.py`

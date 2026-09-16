# HRMS Biometric Bridge

For the office fingerprint scanner (old firmware, no internet route to the
cloud API). Run this on any PC in the office LAN that can reach the device.

## Setup (one-time)

1. Install Python 3 if the PC doesn't have it: https://www.python.org/downloads/
   (tick "Add python.exe to PATH" during install)
2. Open Command Prompt and install the two dependencies:
   ```
   pip install pyzk requests
   ```
3. Copy `hrms_bridge.py` to a folder on the PC, e.g. `C:\HRMS-Bridge\`

## Run it

```
python hrms_bridge.py
```

Leave the window open — it checks the device every 2 minutes and pushes any
new punches. First run may take a few seconds longer while it reads the
device's full log; after that it only sends what's new.

## Run it automatically at startup (optional)

Windows Task Scheduler → Create Task → Trigger: "At log on" → Action:
`pythonw.exe C:\HRMS-Bridge\hrms_bridge.py` (pythonw avoids a console window).

## If it can't connect

- Make sure the PC and the device are on the same network and the PC can
  ping `192.168.0.201`.
- The device's IP can change if your router reassigns it — check
  Menu → Comm → Ethernet on the device if the bridge stops connecting, and
  update `DEVICE_IP` in `hrms_bridge.py` if it changed.
- Logs print to the console with timestamps; errors show what failed.

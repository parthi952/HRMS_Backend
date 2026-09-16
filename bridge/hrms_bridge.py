"""
HRMS Biometric Bridge

Runs on a PC in the office LAN that can reach the fingerprint terminal.
Reads punches off the device locally (it can't push to the cloud itself)
and forwards them to the HRMS backend over the internet.

Setup:
    pip install pyzk requests
    python hrms_bridge.py

Leave it running (or set it up in Windows Task Scheduler to start at
login, using pythonw.exe if you don't want a console window).
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests
from zk import ZK

# ── Configuration ──────────────────────────────────────────────────────────
DEVICE_IP = "192.168.0.201"
DEVICE_PORT = 4370
DEVICE_SERIAL = "OIN6080056071801007"
BACKEND_URL = "https://hrm-api.tibostech.in/iclock/bridge-push"
POLL_INTERVAL_SECONDS = 120  # how often to check the device for new punches

STATE_FILE = Path(__file__).parent / "bridge_state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hrms-bridge")


def load_last_synced() -> datetime | None:
    if STATE_FILE.exists():
        raw = json.loads(STATE_FILE.read_text()).get("last_synced")
        if raw:
            return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    return None


def save_last_synced(ts: datetime) -> None:
    STATE_FILE.write_text(json.dumps({"last_synced": ts.strftime("%Y-%m-%d %H:%M:%S")}))


def fetch_punches_from_device() -> list:
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=10, password=0, force_udp=False, ommit_ping=False)
    conn = zk.connect()
    try:
        conn.disable_device()
        return list(conn.get_attendance())
    finally:
        try:
            conn.enable_device()
        except Exception:
            pass
        conn.disconnect()


def sync_once() -> None:
    attendances = fetch_punches_from_device()
    last_synced = load_last_synced()

    new_punches = []
    latest_ts = last_synced
    for att in attendances:
        if last_synced and att.timestamp <= last_synced:
            continue
        new_punches.append({
            "pin": str(att.user_id),
            "timestamp": att.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if latest_ts is None or att.timestamp > latest_ts:
            latest_ts = att.timestamp

    if not new_punches:
        logger.info("No new punches (%d total on device).", len(attendances))
        return

    logger.info("Pushing %d new punch(es) to HRMS...", len(new_punches))
    resp = requests.post(
        BACKEND_URL,
        json={"device_serial": DEVICE_SERIAL, "punches": new_punches},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info("Server processed=%s skipped=%s", result.get("processed"), result.get("skipped"))

    if latest_ts:
        save_last_synced(latest_ts)


def main():
    logger.info("HRMS Biometric Bridge starting. %s:%s -> %s", DEVICE_IP, DEVICE_PORT, BACKEND_URL)
    while True:
        try:
            sync_once()
        except Exception:
            logger.exception("Sync cycle failed, will retry in %ds.", POLL_INTERVAL_SECONDS)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

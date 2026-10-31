import serial
import threading
import time
import re

SERIAL_PORT = "COM3"  # Change to your actual COM port
BAUD_RATE = 115200

# Thread-safe buffer for latest readings keyed by node string (e.g. "N01")
LATEST_SERIAL_DATA = {}
_lock = threading.Lock()

def _read_serial_loop():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[OK] Connected to ESP32 on {SERIAL_PORT}")
        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Could not open serial port {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            # Example output format:
            # [GREEN_STABLE] NODE:1 | STAGE:0 (STABLE) | CONF:98.5% | TILT:0.45° | PRED_30S:0.45° | RSSI:-65 dBm
            match = re.search(r'\[(\w+)\].*?NODE:(\d+).*?STAGE:(\d+)\s*\(([^)]+)\).*?'r'CONF:([\d\.]+)%.*?TILT:([\d\.]+)°.*?PRED_30S:([\d\.]+)°',line)
            if match:
                alert_level  = match.group(1)
                node_num     = int(match.group(2))
                node_id      = f"N{node_num:02d}"
                stage        = int(match.group(3))
                stage_label  = match.group(4)
                confidence   = float(match.group(5))
                tilt         = float(match.group(6))
                pred_tilt    = float(match.group(7))

                with _lock:
                    LATEST_SERIAL_DATA[node_id] = {
                        "tilt": tilt,
                        "pred_tilt": pred_tilt,
                        "confidence": confidence,
                        "stage": stage,
                        "stage_label": stage_label,
                        "alert_level": alert_level,
                        "last_update": time.time()
                    }
        except Exception as err:
            pass

def start_serial_listener():
    t = threading.Thread(target=_read_serial_loop, daemon=True)
    t.start()

def get_latest_node_data(node_id):
    with _lock:
        return LATEST_SERIAL_DATA.get(node_id, None)

# Auto-start thread when imported
start_serial_listener()
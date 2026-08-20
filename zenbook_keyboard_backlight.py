#!/usr/bin/env python3
import os, sys, fcntl, argparse, time
try:
    from evdev import UInput, ecodes as e
except ImportError:
    print("Please install evdev: sudo apt install python3-evdev")
    sys.exit(1)

# --- 1. Find the correct hidraw device ---
hid_id = '0B05:0220'
hidraw = 0
device = None

while os.path.exists(f'/dev/hidraw{hidraw}'):
    try:
        with open(f'/sys/class/hidraw/hidraw{hidraw}/device/uevent') as f:
            if hid_id in f.read():
                device = f'/dev/hidraw{hidraw}'
                break
    except FileNotFoundError:
        pass
    hidraw += 1

if not device:
    print(f"Error: Could not find Asus EC device ({hid_id})")
    sys.exit(1)

# --- 2. Setup Command Line Arguments ---
parser = argparse.ArgumentParser(description="Asus Zenbook 14 Snapdragon EC Control")
parser.add_argument("command", choices=["daemon", "backlight"], help="Run in background (daemon) or set backlight manually")
parser.add_argument("value", nargs="?", help="Backlight level (0-3) if using manual mode")
args = parser.parse_args()

HIDIOCSFEATURE_64 = 0xC0404806

def send_feature_report(fd, data_bytes, description):
    buf = bytearray(64)
    for i, b in enumerate(data_bytes):
        buf[i] = b
    try:
        fcntl.ioctl(fd, HIDIOCSFEATURE_64, buf)
        print(f"[OK] {description}")
    except OSError as ex:
        print(f"[ERROR] Failed to send {description}: {ex}")

# --- 3. Execute ---
try:
    # Notice we use os.open to allow simultaneous blocking reads and ioctl writes
    fd = os.open(device, os.O_RDWR)
    print(f"Connected to {hid_id} at {device}")
    
    # Init handshake
    send_feature_report(fd, [0x5A, 0x05, 0x20, 0x31, 0x00, 0x08], "Init Sequence 1")
    send_feature_report(fd, [0x5A, 0xD0, 0x8F, 0x01], "Init Sequence 2")
    
    if args.command == "backlight" and args.value is not None:
        level = int(args.value)
        send_feature_report(fd, [0x5A, 0xBA, 0xC5, 0xC4, level], f"Backlight Level {level}")
        sys.exit(0)
        
    elif args.command == "daemon":
        print("-" * 40)
        print("Starting ASUS EC Daemon. Listening for Fn hotkeys... (Press Ctrl+C to stop)")
        ui = UInput()
        current_bl = 3  # Assume max brightness on start
        
        while True:
            # Block and wait for a 64-byte Input Report from the keyboard
            data = os.read(fd, 64)
            
            if data and data[0] == 0x5A and len(data) >= 2:
                usage = data[1]
                
                # --- The Asus Hotkey Mappings ---
                if usage == 0xC7:   # Fn+F4 (Backlight Toggle)
                    current_bl = (current_bl + 1) % 4
                    send_feature_report(fd, [0x5A, 0xBA, 0xC5, 0xC4, current_bl], f"Backlight cycled to {current_bl}")
                    
                elif usage == 0x9D: # Fn+F (Fan Profile Cycle)
                    print("[EVENT] Fn+F pressed! (Fan profile cycle triggered)")
                    
                elif usage == 0x10: # Fn+F5 (Brightness Down)
                    ui.write(e.EV_KEY, e.KEY_BRIGHTNESSDOWN, 1)
                    ui.write(e.EV_KEY, e.KEY_BRIGHTNESSDOWN, 0)
                    ui.syn()
                    
                elif usage == 0x20: # Fn+F6 (Brightness Up)
                    ui.write(e.EV_KEY, e.KEY_BRIGHTNESSUP, 1)
                    ui.write(e.EV_KEY, e.KEY_BRIGHTNESSUP, 0)
                    ui.syn()
                    
                elif usage == 0x7C: # Fn+F9 (Mic Mute)
                    ui.write(e.EV_KEY, e.KEY_MICMUTE, 1)
                    ui.write(e.EV_KEY, e.KEY_MICMUTE, 0)
                    ui.syn()
                    
                elif usage == 0x6B: # Fn+F11 (Touchpad Toggle)
                    # Note: You might need to map this to a custom script depending on your DE
                    print("[EVENT] Touchpad toggle pressed")
                    
except PermissionError:
    print("Permission denied: You must run this script with sudo.")
except Exception as e:
    print(f"Fatal error: {e}")

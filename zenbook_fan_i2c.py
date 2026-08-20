#!/usr/bin/env python3
import sys
import time
import argparse
try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("Please install smbus2: sudo apt install python3-smbus2")
    sys.exit(1)

EC_I2C_ADDR = 0x5b
ADDR_PORT = 0x10
DATA_PORT = 0x11

def ecrb(bus, arg0, arg1):
    """Read a byte from Asus EC Memory (ACPI ECRB)"""
    # 1. Write [Bank, Register] to the Address Port
    msg_addr = i2c_msg.write(EC_I2C_ADDR, [ADDR_PORT, arg0, arg1])
    bus.i2c_rdwr(msg_addr)
    
    # 2. Read 1 byte from the Data Port
    msg_cmd = i2c_msg.write(EC_I2C_ADDR, [DATA_PORT])
    msg_read = i2c_msg.read(EC_I2C_ADDR, 1)
    bus.i2c_rdwr(msg_cmd, msg_read)
    
    return list(msg_read)[0]

def ecwb(bus, arg0, arg1, arg2):
    """Write a byte to Asus EC Memory (ACPI ECWB)"""
    # 1. Write [Bank, Register] to the Address Port
    msg_addr = i2c_msg.write(EC_I2C_ADDR, [ADDR_PORT, arg0, arg1])
    bus.i2c_rdwr(msg_addr)
    
    # 2. Write Payload to the Data Port
    msg_data = i2c_msg.write(EC_I2C_ADDR, [DATA_PORT, arg2])
    bus.i2c_rdwr(msg_data)

def eccw(bus, arg0, arg1, arg2):
    """Asus EC Wakeup/Command Protocol"""
    timeout = 5
    while timeout > 0:
        if ecrb(bus, 0xC4, 0x30) == 0:
            ecwb(bus, 0xC4, 0x31, arg1)
            ecwb(bus, 0xC4, 0x32, arg2)
            ecwb(bus, 0xC4, 0x30, arg0)
            
            wait = 5
            while wait > 0:
                if ecrb(bus, 0xC4, 0x30) == 0:
                    return True
                wait -= 1
                time.sleep(0.01)
            break
        timeout -= 1
        time.sleep(0.01)
    return False

def test_ec(bus_num):
    """Diagnose the EC Connection"""
    try:
        bus = SMBus(bus_num)
        print(f"Testing I2C Bus {bus_num} at Address 0x{EC_I2C_ADDR:02X}...\n")
        
        status = ecrb(bus, 0xC9, 0x6F)
        print(f"Mailbox Status Register (0xC9, 0x6F): 0x{status:02X}")
        
        q_event = ecrb(bus, 0xC4, 0x4F)
        print(f"Q-Event Register (0xC4, 0x4F):        0x{q_event:02X}")
        
        if status == 0x00:
            print("\n[OK] The EC is IDLE and ready to receive commands!")
        elif status == 0xC9:
            print("\n[ERROR] Still echoing the address byte. Protocol mismatch.")
        else:
            print("\n[OK] The EC responded!")
            
    except Exception as e:
        print(f"[ERROR] Communication failed: {e}")
    finally:
        if 'bus' in locals():
            bus.close()

def webc_ec_write(bus_num, command, data_bytes):
    """Replicates the WEBC Mailbox sequence"""
    try:
        bus = SMBus(bus_num)
    except Exception as e:
        print(f"[ERROR] Failed to open I2C bus {bus_num}: {e}")
        return False

    try:
        # 1. Wait for EC to be ready (BMCR & BMTR Loop)
        timeout = 200
        while timeout > 0:
            bmcr = ecrb(bus, 0xC9, 0x6F)
            if bmcr == 0:
                break
            time.sleep(0.001)
            timeout -= 1
            
        if timeout == 0:
            print("[ERROR] EC is busy. Returning non-zero status.")
            return False
            
        # 2. Write data buffer to registers 0x40+
        for i, b in enumerate(data_bytes):
            ecwb(bus, 0xC9, 0x40 + i, b)
            
        # 3. Set Bit 7 on Status Register (BMCR |= 0x80)
        bmcr = ecrb(bus, 0xC9, 0x6F)
        ecwb(bus, 0xC9, 0x6F, bmcr | 0x80)
        
        # 4. Write the Command Register (Arg0 to 0x6E)
        ecwb(bus, 0xC9, 0x6E, command)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] I2C transaction failed: {e}")
        return False
    finally:
        bus.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asus Snapdragon Native I2C Fan Control")
    parser.add_argument("-b", "--bus", type=int, default=6, help="The I2C bus number (default: 6)")
    parser.add_argument("profile", choices=["test", "standard", "whisper", "performance", "full"], help="Profile or Test")
    args = parser.parse_args()

    if args.profile == "test":
        test_ec(args.bus)
        sys.exit(0)

    profiles = {
        "standard":    [0x01],
        "whisper":     [0x02],
        "performance": [0x04],
        "full":        [0x10]
    }

    print(f"Setting fan profile to: {args.profile.capitalize()}...")
    success = webc_ec_write(args.bus, 0x11, profiles[args.profile])
    
    if success:
        print("[OK] Fan command sent successfully directly to EC memory!")

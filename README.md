# zenbook-a14-ubuntu-fixes
Setup Ubuntu 26.04 on Asus Zenbook a14 snapdragon UX3407RA x1e78100, including fan control and keyboard backlight and hotkeys

## Initial preparation
1. Resize the Windows partition, and disable Windows fastboot so the NTFS partition is properly closed at shutdown.
2. Download the Ubuntu 26.04 Concept for Snapdragon ISO.

## Installation
The ubuntu installer is easy to navigate, select custom installation to choose the free space on the disk that was created
during resizing of the Windows partition.

## Post installation
The wrong DTB is used at boot, and a couple qualcomm blobs have to be retrieved from the Windows partition.

### Fix DTB
Copy `x1e80100-asus-zenbook-a14.dtb` from `/usr/lib/firmware/<kernel-version>/device-tree/qcom/` to `/boot/`,
run `sudo update-initramfs -u`, add `devicetree /boot/x1e80100-asus-zenbook-a14.dtb` to the current default `menuentry`
in `/boot.grub/grub./cfg` below the `initrd /boot/initrd.img-<kernel-version>` line, run `sudo update-grub` and reboot the laptop.

### Retrieve qcom blobs
The Ubuntu release comes with a script to automate this: `qcom-firmware-extract`.

## Keyboard backlight and fan control
Use the scripts from this repo to tell the not-yet-supprted EC to turn of keyboard backlight and select a fan curve:
```bash
sudo ./zenbook_keyboard_backlight.py backlight 0
sudo ./zenbook_fan_i2c.py whisper
```

# import os
import select
import subprocess
import sys
import time

from evdev import InputDevice, ecodes, list_devices

# =========================
# Configuration
# =========================

IDLE_SECONDS = 180  # 3 minutes
SCAN_INTERVAL = 3.0  # scan input devices every 3 seconds
CHECK_TARGET_INTERVAL = 5.0  # check service.target every 5 secondS


# =========================
# Brightness
# =========================


def get_brightness():
    """
    Get current raw brightness value.
    """
    result = subprocess.run(
        ["brightnessctl", "get"], capture_output=True, text=True, check=True
    )

    return int(result.stdout.strip())


def set_brightness(value: int):
    """
    Set raw brightness value.
    """
    subprocess.run(
        ["brightnessctl", "set", str(value)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def max_brightness():
    """
    Get maximum raw brightness value.
    """
    result = subprocess.run(
        ["brightnessctl", "max"], capture_output=True, text=True, check=True
    )

    return int(result.stdout.strip())


def is_screen_off():
    return get_brightness() == 0


def set_screen_off() -> bool:
    i = 0
    while i < 3:
        set_brightness(0)
        if not is_screen_off():
            i += 1
            time.sleep(0.1)
        else:
            return True
    return False


def reset_screen_on(value: int | None) -> bool:
    i = 0
    if not value:
        value = max_brightness()
    while i < 3:
        set_brightness(value)
        if get_brightness() != value:
            i += 1
            time.sleep(0.1)
        else:
            return True
    return False


# =========================
# Input device detection
# =========================


def is_keyboard(caps):
    """
    Detect a real keyboard.
    """

    if ecodes.EV_KEY not in caps:
        return False

    keys = set(caps[ecodes.EV_KEY])

    keyboard_keys = {
        ecodes.KEY_A,
        ecodes.KEY_B,
        ecodes.KEY_C,
        ecodes.KEY_Z,
        ecodes.KEY_0,
        ecodes.KEY_1,
        ecodes.KEY_9,
        ecodes.KEY_ENTER,
        ecodes.KEY_ESC,
        ecodes.KEY_SPACE,
        ecodes.KEY_BACKSPACE,
        ecodes.KEY_TAB,
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_RIGHTCTRL,
        ecodes.KEY_LEFTSHIFT,
        ecodes.KEY_RIGHTSHIFT,
        ecodes.KEY_LEFTALT,
        ecodes.KEY_RIGHTALT,
        ecodes.KEY_UP,
        ecodes.KEY_DOWN,
        ecodes.KEY_LEFT,
        ecodes.KEY_RIGHT,
    }

    return bool(keys & keyboard_keys)


def is_mouse(caps):
    """
    Detect a normal mouse.
    """

    if ecodes.EV_REL in caps:
        rel = set(caps[ecodes.EV_REL])

        if ecodes.REL_X in rel or ecodes.REL_Y in rel:
            return True

    if ecodes.EV_KEY in caps:
        keys = set(caps[ecodes.EV_KEY])

        mouse_buttons = {
            ecodes.BTN_LEFT,
            ecodes.BTN_RIGHT,
            ecodes.BTN_MIDDLE,
            ecodes.BTN_SIDE,
            ecodes.BTN_EXTRA,
        }

        if keys & mouse_buttons:
            return True

    return False


def is_touchpad(caps):
    """
    Detect a touchpad.

    Modern touchpads normally use EV_ABS instead of EV_REL.
    """

    if ecodes.EV_ABS not in caps:
        return False

    abs_codes = set(caps[ecodes.EV_ABS])

    touchpad_axes = {
        ecodes.ABS_X,
        ecodes.ABS_Y,
        ecodes.ABS_MT_POSITION_X,
        ecodes.ABS_MT_POSITION_Y,
    }

    return bool(abs_codes & touchpad_axes)


def is_input_device(device):
    """
    Determine whether this event device should count as
    keyboard/mouse/touchpad input.
    """

    try:
        caps = device.capabilities()

        return is_keyboard(caps) or is_mouse(caps) or is_touchpad(caps)

    except Exception:  # noqa: BLE001
        return False


# =========================
# Device manager
# =========================


class InputManager:
    def __init__(self):
        self.devices = {}
        self.poller = select.poll()

    def add_device(self, path: str):
        if path in self.devices:
            return

        try:
            device = InputDevice(path)

            if not is_input_device(device):
                device.close()
                return

            self.devices[path] = device

            self.poller.register(
                device.fd, select.POLLIN | select.POLLERR | select.POLLHUP
            )

            print(f"Added input device: {path} - {device.name}", flush=True)

        except (PermissionError, OSError):
            pass

    def remove_device(self, path):
        device = self.devices.pop(path, None)

        if device is None:
            return

        try:
            self.poller.unregister(device.fd)
        except Exception:  # noqa: BLE001 S110
            pass

        try:
            device.close()
        except Exception:  # noqa: BLE001, S110
            pass

        print(f"Removed input device: {path}", flush=True)

    def scan(self):
        """
        Detect newly connected keyboards/mice/touchpads.
        """

        current = set(list_devices())

        # Add new devices
        for path in current:
            self.add_device(path)

        # Remove disconnected devices
        for path in list(self.devices):
            if path not in current:
                self.remove_device(path)

    def read_events(self):
        """
        Return True when user input is detected.
        """

        activity = False

        events = self.poller.poll(0)

        for fd, mask in events:
            device = None

            for d in self.devices.values():
                if d.fd == fd:
                    device = d
                    break

            if device is None:
                continue

            # Device disappeared
            if mask & (select.POLLERR | select.POLLHUP):
                self.remove_device(device.path)
                continue

            try:
                for event in device.read():
                    if event.type in (
                        ecodes.EV_KEY,
                        ecodes.EV_REL,
                        ecodes.EV_ABS,
                    ):
                        activity = True

            except (OSError, BlockingIOError):
                pass

        return activity


# =========================
# target
# =========================


def is_active(target: str) -> bool:
    return (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", target],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def get_target():
    if is_active("graphical.target"):
        # print("graphical.target")
        return 2
    elif is_active("multi-user.target"):
        # print("multi-user.target")
        return 1
    else:
        print("unknown / systemd not running")
        return 0


# =========================
# Main
# =========================


def main():

    manager = InputManager()

    print("Starting idle backlight monitor...", flush=True)

    manager.scan()

    if not manager.devices:
        print("No keyboard/mouse/touchpad detected yet.", flush=True)

    last_input = time.monotonic()

    screen_off = False
    saved_brightness = None

    target = get_target()
    next_target = time.monotonic() + CHECK_TARGET_INTERVAL

    next_scan = time.monotonic() + SCAN_INTERVAL

    while True:
        now = time.monotonic()

        # -------------------------
        # Check current target
        # -------------------------

        if target == 1:
            pass
        else:
            screen_off = is_screen_off()
            if now >= next_target:
                target = get_target()
            continue

        # -------------------------
        # Detect hot-plug devices
        # -------------------------

        if now >= next_scan:
            manager.scan()
            next_scan = now + SCAN_INTERVAL

        # -------------------------
        # Detect user input
        # -------------------------

        if manager.read_events():
            last_input = time.monotonic()

            if screen_off:
                print("User input detected, restoring brightness.", flush=True)

                if reset_screen_on(saved_brightness):
                    print(f"Brightness 0 -> {saved_brightness} ", flush=True)
                else:
                    print("Failed to restore brightness.", flush=True)

        # -------------------------
        # Check idle time
        # -------------------------

        if not screen_off:
            idle_time = time.monotonic() - last_input

            if idle_time >= IDLE_SECONDS:
                try:
                    if current := get_brightness() > 0:
                        saved_brightness = current

                        print(
                            f"No input for "
                            f"{IDLE_SECONDS} seconds. "
                            f"Brightness {current} -> 0",
                            flush=True,
                        )

                        screen_off = set_screen_off() and is_screen_off()
                    else:
                        screen_off = True

                    if screen_off:
                        print("Screen is off.", flush=True)

                except Exception as e:  # noqa: BLE001
                    print(f"Brightness error: {e}", flush=True)
        # else:
        #     screen_off = is_screen_off()

        time.sleep(0.05)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

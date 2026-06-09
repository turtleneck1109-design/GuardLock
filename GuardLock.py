import argparse
import ctypes
import logging
from pathlib import Path
import time
from datetime import datetime


APP_NAME = "GuardLock"
LOG_PATH = Path(__file__).with_name("GuardLock.log")
CAPTURE_DIR = Path(__file__).with_name("GuardLock_captures")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32


def get_last_input_tick() -> int:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError()
    return int(info.dwTime)


def lock_workstation() -> None:
    if not user32.LockWorkStation():
        raise ctypes.WinError()


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_ulong),
        ("dwStateMask", ctypes.c_ulong),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_ulong),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", ctypes.c_void_p),
    ]


class TrayIcon:
    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    IDI_SHIELD = 32518
    IDI_APPLICATION = 32512

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.hwnd = kernel32.GetConsoleWindow()
        self.icon_id = 1
        self.hicon = None
        self.added = False

        if not self.enabled or not self.hwnd:
            self.enabled = False
            return

        self.hicon = user32.LoadIconW(None, ctypes.c_void_p(self.IDI_SHIELD))
        if not self.hicon:
            self.hicon = user32.LoadIconW(None, ctypes.c_void_p(self.IDI_APPLICATION))

    def _data(self, tip: str) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = self.icon_id
        data.uFlags = self.NIF_ICON | self.NIF_TIP
        data.hIcon = self.hicon
        data.szTip = tip[:127]
        return data

    def set_status(self, status: str) -> None:
        if not self.enabled:
            return

        data = self._data(f"{APP_NAME}: {status}")
        action = self.NIM_MODIFY if self.added else self.NIM_ADD
        if shell32.Shell_NotifyIconW(action, ctypes.byref(data)):
            self.added = True

    def close(self) -> None:
        if not self.enabled or not self.added:
            return

        data = self._data(APP_NAME)
        shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(data))
        self.added = False


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def log_and_print(message: str) -> None:
    print(message)
    logging.info(message)


def countdown(seconds: float, tray: TrayIcon) -> None:
    if seconds <= 0:
        return

    end_time = time.monotonic() + seconds
    last_remaining = None

    while True:
        remaining = max(0, int(end_time - time.monotonic() + 0.999))
        if remaining != last_remaining:
            message = f"Arming in {remaining} seconds. Leave the computer now."
            print(message)
            tray.set_status(f"arming in {remaining}s")
            last_remaining = remaining
        if remaining <= 0:
            break
        time.sleep(0.1)


def capture_photo(
    camera_index: int,
    output_dir: Path,
    width: int,
    height: int,
    warmup_seconds: float,
    burst_count: int,
    burst_interval: float,
) -> Path | None:
    try:
        import cv2
    except ImportError:
        logging.warning("Photo capture skipped: opencv-python is not installed.")
        return None

    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"trigger_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    try:
        if not camera.isOpened():
            logging.warning("Photo capture skipped: camera %s could not be opened.", camera_index)
            return None

        if width > 0:
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height > 0:
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        warmup_until = time.monotonic() + max(warmup_seconds, 0)
        while time.monotonic() < warmup_until:
            camera.read()
            time.sleep(0.05)

        best_frame = None
        best_score = -1.0
        attempts = max(burst_count, 1)
        for index in range(attempts):
            ok, frame = camera.read()
            if not ok:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if score > best_score:
                best_score = score
                best_frame = frame

            if index < attempts - 1:
                time.sleep(max(burst_interval, 0))

        if best_frame is None:
            logging.warning("Photo capture skipped: camera frame could not be read.")
            return None

        ok, encoded = cv2.imencode(".jpg", best_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            logging.warning("Photo capture skipped: image could not be encoded.")
            return None

        output_path.write_bytes(encoded.tobytes())

        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logging.info(
            "Photo captured: %s (%sx%s, sharpness %.2f)",
            output_path,
            actual_width,
            actual_height,
            best_score,
        )
        return output_path
    finally:
        camera.release()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GuardLock locks this Windows workstation as soon as keyboard or mouse input is detected."
    )
    parser.add_argument(
        "--grace",
        type=float,
        default=5.0,
        help="Seconds to wait before arming, so you can walk away. Default: 5.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.05,
        help="Polling interval in seconds. Default: 0.05.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=LOG_PATH,
        help="Log file path. Default: GuardLock.log next to the script.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Camera index for trigger photos. Default: 0.",
    )
    parser.add_argument(
        "--camera-width",
        type=int,
        default=1280,
        help="Requested camera photo width. Default: 1280.",
    )
    parser.add_argument(
        "--camera-height",
        type=int,
        default=720,
        help="Requested camera photo height. Default: 720.",
    )
    parser.add_argument(
        "--photo-warmup",
        type=float,
        default=1.0,
        help="Seconds to warm up the camera before capture. Default: 1.0.",
    )
    parser.add_argument(
        "--photo-burst",
        type=int,
        default=3,
        help="Number of photos to sample and choose the sharpest from. Default: 3.",
    )
    parser.add_argument(
        "--photo-burst-interval",
        type=float,
        default=0.2,
        help="Seconds between burst samples. Default: 0.2.",
    )
    parser.add_argument(
        "--no-photo",
        action="store_true",
        help="Do not try to capture a photo before locking.",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable the Windows tray status icon.",
    )
    args = parser.parse_args()

    setup_logging(args.log)
    tray = TrayIcon(enabled=not args.no_tray)
    tray.set_status("starting")

    logging.info("GuardLock started.")
    countdown(args.grace, tray)

    baseline = get_last_input_tick()
    log_and_print("Armed. Any keyboard or mouse input will lock this computer.")
    tray.set_status("armed")

    try:
        while True:
            current = get_last_input_tick()
            if current != baseline:
                log_and_print("Input detected.")
                tray.set_status("triggered")

                if not args.no_photo:
                    photo_path = capture_photo(
                        args.camera_index,
                        CAPTURE_DIR,
                        args.camera_width,
                        args.camera_height,
                        args.photo_warmup,
                        args.photo_burst,
                        args.photo_burst_interval,
                    )
                    if photo_path:
                        log_and_print(f"Photo captured: {photo_path}")

                log_and_print("Locking workstation.")
                lock_workstation()
                return
            time.sleep(max(args.poll, 0.01))
    finally:
        tray.close()


if __name__ == "__main__":
    main()

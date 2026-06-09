import argparse
import configparser
import ctypes
import logging
from pathlib import Path
import time
from datetime import datetime


APP_NAME = "GuardLock"
LOG_PATH = Path(__file__).with_name("GuardLock.log")
CAPTURE_DIR = Path(__file__).with_name("GuardLock_captures")
CONFIG_PATH = Path(__file__).with_name("config.ini")


DEFAULT_CONFIG = {
    "guard": {
        "grace_seconds": "5.0",
        "poll_seconds": "0.05",
        "enable_photo": "true",
        "enable_tray": "true",
        "log_path": "GuardLock.log",
    },
    "camera": {
        "index": "0",
        "width": "1280",
        "height": "720",
        "warmup_seconds": "1.0",
        "burst_count": "3",
        "burst_interval_seconds": "0.2",
    },
}


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


def config_path_value(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(__file__).with_name(value)


def load_config(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read_dict(DEFAULT_CONFIG)

    if config_path.exists():
        config.read(config_path, encoding="utf-8")

    return config


def add_optional_bool_argument(
    parser: argparse.ArgumentParser,
    name: str,
    destination: str,
    enable_help: str,
    disable_help: str,
) -> None:
    parser.add_argument(
        name,
        dest=destination,
        action="store_true",
        default=None,
        help=enable_help,
    )
    parser.add_argument(
        f"--no-{name[2:]}",
        dest=destination,
        action="store_false",
        default=None,
        help=disable_help,
    )


def build_settings(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    guard = config["guard"]
    camera = config["camera"]

    enable_photo = guard.getboolean("enable_photo")
    enable_tray = guard.getboolean("enable_tray")

    if args.photo is not None:
        enable_photo = args.photo
    if args.tray is not None:
        enable_tray = args.tray

    return {
        "grace": args.grace if args.grace is not None else guard.getfloat("grace_seconds"),
        "poll": args.poll if args.poll is not None else guard.getfloat("poll_seconds"),
        "log": args.log if args.log is not None else config_path_value(guard.get("log_path")),
        "camera_index": args.camera_index if args.camera_index is not None else camera.getint("index"),
        "camera_width": args.camera_width if args.camera_width is not None else camera.getint("width"),
        "camera_height": args.camera_height if args.camera_height is not None else camera.getint("height"),
        "photo_warmup": args.photo_warmup
        if args.photo_warmup is not None
        else camera.getfloat("warmup_seconds"),
        "photo_burst": args.photo_burst if args.photo_burst is not None else camera.getint("burst_count"),
        "photo_burst_interval": args.photo_burst_interval
        if args.photo_burst_interval is not None
        else camera.getfloat("burst_interval_seconds"),
        "enable_photo": enable_photo,
        "enable_tray": enable_tray,
    }


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
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Config file path. Default: config.ini next to the script.",
    )
    parser.add_argument(
        "--grace",
        type=float,
        default=None,
        help="Seconds to wait before arming. Overrides config.ini.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=None,
        help="Polling interval in seconds. Overrides config.ini.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Log file path. Overrides config.ini.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=None,
        help="Camera index for trigger photos. Overrides config.ini.",
    )
    parser.add_argument(
        "--camera-width",
        type=int,
        default=None,
        help="Requested camera photo width. Overrides config.ini.",
    )
    parser.add_argument(
        "--camera-height",
        type=int,
        default=None,
        help="Requested camera photo height. Overrides config.ini.",
    )
    parser.add_argument(
        "--photo-warmup",
        type=float,
        default=None,
        help="Seconds to warm up the camera before capture. Overrides config.ini.",
    )
    parser.add_argument(
        "--photo-burst",
        type=int,
        default=None,
        help="Number of photos to sample and choose the sharpest from. Overrides config.ini.",
    )
    parser.add_argument(
        "--photo-burst-interval",
        type=float,
        default=None,
        help="Seconds between burst samples. Overrides config.ini.",
    )
    add_optional_bool_argument(
        parser,
        "--photo",
        "photo",
        "Enable trigger photo capture.",
        "Disable trigger photo capture.",
    )
    add_optional_bool_argument(
        parser,
        "--tray",
        "tray",
        "Enable the Windows tray status icon.",
        "Disable the Windows tray status icon.",
    )
    args = parser.parse_args()
    settings = build_settings(args)

    setup_logging(settings["log"])
    tray = TrayIcon(enabled=settings["enable_tray"])
    tray.set_status("starting")

    logging.info("GuardLock started.")
    logging.info("Config loaded: %s", args.config)
    countdown(settings["grace"], tray)

    baseline = get_last_input_tick()
    log_and_print("Armed. Any keyboard or mouse input will lock this computer.")
    tray.set_status("armed")

    try:
        while True:
            current = get_last_input_tick()
            if current != baseline:
                log_and_print("Input detected.")
                tray.set_status("triggered")

                if settings["enable_photo"]:
                    photo_path = capture_photo(
                        settings["camera_index"],
                        CAPTURE_DIR,
                        settings["camera_width"],
                        settings["camera_height"],
                        settings["photo_warmup"],
                        settings["photo_burst"],
                        settings["photo_burst_interval"],
                    )
                    if photo_path:
                        log_and_print(f"Photo captured: {photo_path}")

                log_and_print("Locking workstation.")
                lock_workstation()
                return
            time.sleep(max(settings["poll"], 0.01))
    finally:
        tray.close()


if __name__ == "__main__":
    main()

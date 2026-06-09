# GuardLock

GuardLock is a small Windows tool that locks the workstation as soon as keyboard or mouse input is detected after it is armed.

## Features

- Countdown before arming.
- Windows tray status icon.
- Trigger and status logs.
- Optional trigger photo capture before locking.

## Usage

Double-click `Start-GuardLock.bat`.

GuardLock reads its default settings from `config.ini`.

You can also run it from PowerShell:

```powershell
python GuardLock.py
```

Command-line options still work as temporary overrides.

## Configuration

Edit `config.ini` to change the default behavior:

```ini
[guard]
grace_seconds = 5.0
poll_seconds = 0.05
enable_photo = true
enable_tray = true
log_path = GuardLock.log

[camera]
index = 0
width = 1280
height = 720
warmup_seconds = 1.0
burst_count = 3
burst_interval_seconds = 0.2
```

## Options

```powershell
python GuardLock.py --config config.ini
python GuardLock.py --grace 10
python GuardLock.py --grace 5 --camera-index 0 --camera-width 1280 --camera-height 720
python GuardLock.py --photo-warmup 1.5 --photo-burst 5
python GuardLock.py --no-photo
python GuardLock.py --no-tray
```

Command-line values override `config.ini` for that run only.

Photo quality options:

- `--camera-width` and `--camera-height` request a higher camera resolution.
- `--photo-warmup` gives the camera time to adjust focus and exposure.
- `--photo-burst` captures multiple frames and saves the sharpest one.
- `--photo-burst-interval` controls the delay between burst samples.

## Output

- Logs are written to `GuardLock.log`.
- Trigger photos are saved in `GuardLock_captures`.

## Notes

- Locking Windows does not stop most running programs.
- GuardLock cannot prevent shutdown, restart, power button actions, or physical access attacks.
- For long-running tasks, make sure Windows sleep is disabled or delayed.

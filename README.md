# GuardLock

GuardLock is a small Windows tool that locks the workstation as soon as keyboard or mouse input is detected after it is armed.

## Features

- Countdown before arming.
- Windows tray status icon.
- Trigger and status logs.
- Optional trigger photo capture before locking.

## Usage

Double-click `Start-GuardLock.bat`.

By default, GuardLock waits 5 seconds before arming, so you have time to leave the computer.

You can also run it from PowerShell:

```powershell
python GuardLock.py --grace 10
```

`--grace 10` means GuardLock starts monitoring after 10 seconds.

## Options

```powershell
python GuardLock.py --grace 5 --camera-index 0 --camera-width 1280 --camera-height 720
python GuardLock.py --photo-warmup 1.5 --photo-burst 5
python GuardLock.py --no-photo
python GuardLock.py --no-tray
```

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

@echo off
cd /d "%~dp0"
python GuardLock.py --grace 5 --camera-width 1280 --camera-height 720 --photo-warmup 1.0 --photo-burst 3

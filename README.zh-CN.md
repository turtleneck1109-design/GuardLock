# GuardLock

GuardLock 是一个 Windows 离席防护小工具。启动并布防后，只要检测到键盘或鼠标输入，就会立即锁定电脑。

## 功能

- ⏳ 布防前倒计时，方便你离开电脑。
- 🛡️ Windows 托盘状态图标。
- 📝 记录启动、布防、触发和锁屏日志。
- 📷 触发后、锁屏前自动尝试拍照。

## 使用方法

🚀 双击 `Start-GuardLock.bat`。

默认会等待 5 秒后开始布防。

也可以在 PowerShell 中运行：

```powershell
python GuardLock.py --grace 10
```

`--grace 10` 表示 10 秒后开始监控。

## 常用参数

```powershell
python GuardLock.py --grace 5 --camera-index 0 --camera-width 1280 --camera-height 720
python GuardLock.py --photo-warmup 1.5 --photo-burst 5
python GuardLock.py --no-photo
python GuardLock.py --no-tray
```

- ⏱️ `--grace`：布防前等待秒数。
- 🔁 `--poll`：检测间隔秒数，默认 `0.05`。
- 📝 `--log`：日志文件路径。
- 📷 `--camera-index`：摄像头编号，默认 `0`。
- 🖼️ `--camera-width` / `--camera-height`：请求摄像头分辨率，默认 `1280x720`。
- 🌤️ `--photo-warmup`：拍照前预热时间，让摄像头自动曝光和对焦更稳定。
- 🎞️ `--photo-burst`：连拍张数，会自动保存最清晰的一张。
- ⏲️ `--photo-burst-interval`：连拍间隔秒数。
- 🚫 `--no-photo`：触发时不拍照。
- 🧩 `--no-tray`：不显示托盘图标。

## 输出文件

- 📝 日志保存到 `GuardLock.log`。
- 📷 触发照片保存到 `GuardLock_captures` 文件夹。

## 依赖

拍照功能需要安装 `opencv-python`：

```powershell
python -m pip install -r requirements.txt
```

如果没有安装该依赖，GuardLock 仍然会正常锁屏，只是会跳过拍照并把原因写入日志。

## 注意事项

- ✅ Windows 锁屏通常不会停止正在运行的程序。
- ⚠️ GuardLock 不能防止关机、重启、按电源键、拔电源或物理拆机等操作。
- 🔋 如果要长时间运行程序，请确认 Windows 不会自动睡眠。

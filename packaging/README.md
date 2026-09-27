# 打包说明 / Packaging

使用 [PyInstaller](https://pyinstaller.org/) 把 `run.py` 打包成单文件、无控制台窗口的
可执行程序 `stock-client`。

## 环境准备

```bash
cd stock-client
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pyinstaller      # 仅构建时需要，运行不需要
```

## 构建

```bash
packaging/build.sh            # 产出 dist/stock-client
packaging/build.sh --clean    # 先清理 build/ 与 dist/ 再构建
```

也可以直接调用 PyInstaller：

```bash
pyinstaller packaging/stockclient.spec --noconfirm
```

## 产物

- `dist/stock-client` — 单文件可执行程序（Windows 下为 `stock-client.exe`）。
- `build/` — 中间产物，可安全删除。

## 说明

- `stockclient.spec` 以 `../run.py` 为入口，`console=False`（windowed，不弹控制台），
  名称固定为 `stock-client`。
- PySide6 自带 PyInstaller hooks，无需额外配置；pyqtgraph 的 graphics items 是运行时
  按名字动态导入的，已在 spec 的 `hiddenimports` 中显式列出，避免打包后图表空白。
- 打包后的程序首次运行会解压到临时目录（`--onefile` 的固有行为），启动稍慢属正常。
- 建议在与目标用户相同的操作系统上构建（Windows 程序在 Windows 上构建）。
- 构建产物体积较大（含 Qt 运行库），属正常现象。

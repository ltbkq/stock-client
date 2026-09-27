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

## 生成安装包

在 `dist/stock-client` 已构建的前提下（Linux）：

```bash
packaging/make-packages.sh 0.4.2      # 版本号可省略，默认取最近 tag
```

产出到 `dist/packages/`：

| 文件 | 类型 | 工具 |
|---|---|---|
| `stock-client_<ver>_linux_<arch>.tar.gz` | 便携压缩包 | `tar` |
| `stock-client_<ver>_amd64.deb` | Debian/Ubuntu 安装包 | `dpkg-deb` |
| `stock-client_<ver>-1.<arch>.rpm` | Fedora/RHEL 安装包 | `rpmbuild`（`apt install rpm`） |

`.deb` / `.rpm` 会安装：

- `/usr/bin/stock-client`
- `/usr/share/applications/stock-client.desktop`（菜单入口）
- `/usr/share/icons/hicolor/256x256/apps/stock-client.png`（图标）

依赖（Qt 运行库）：Debian 系 `libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1`；
RPM 系 `mesa-libEGL mesa-libGL libxkbcommon dbus-libs fontconfig`。

安装/卸载：

```bash
sudo dpkg -i dist/packages/stock-client_0.4.2_amd64.deb   # 或 sudo apt install ./*.deb
sudo rpm  -i dist/packages/stock-client-0.4.2-1.x86_64.rpm
sudo apt remove stock-client   # 卸载
```

## 自动发布（CI）

`.github/workflows/release.yml` 在推送 `v*` tag 或手动触发时，于
ubuntu / windows / macos 上构建，并把安装包附加到对应 Release：

- Linux：`.tar.gz` + `.deb` + `.rpm`
- Windows：`*.zip`（便携 exe）
- macOS：`*.zip`（app / 可执行）

## 说明

- `stockclient.spec` 以仓库根的 `run.py` 为入口，`console=False`（windowed），
  名称固定 `stock-client`；`data_sources.json` 会一并打入包内。
- PySide6 自带 PyInstaller hooks，无需额外配置；pyqtgraph 的 graphics items 是运行时
  按名字动态导入的，已在 spec 的 `hiddenimports` 中显式列出，避免打包后图表空白。
- 打包后的程序首次运行会解压到临时目录（`--onefile` 的固有行为），启动稍慢属正常。
- PyInstaller 需要 **带共享库（`--enable-shared`）的 Python**；部分自编译 Python
  会报 `Python was built without a shared library`，改用发行版自带 Python 即可。
- 建议在与目标用户相同的操作系统上构建（Windows 程序在 Windows 上构建）。

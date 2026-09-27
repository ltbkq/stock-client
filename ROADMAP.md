# 开发路线（Roadmap）

按「可独立交付」拆分任务，便于并行开发、流水集成。每条任务标注涉及文件，
互不冲突；集成顺序见「流水集成」。

## 任务清单

### T1 · 分时图独立渲染
- 目标：分时周期单独绘制「走势线 + 均价线 + 分钟成交量」，不复用 K 线蜡烛。
- 涉及：`stockclient/ui/chart.py`（新增分时渲染分支）、`stockclient/indicators.py`（均价线）
- 验收：`--demo` 下选择「分时」能看到走势线与均价线；`scripts/smoke.py` 通过。

### T2 · 预警全类型 + 管理界面
- 目标：支持 价格上穿/下破、涨幅/跌幅超过 四类规则；新增预警管理对话框
  （列表/启停/删除/添加），不止价格上穿。
- 涉及：`stockclient/alerts.py`、`stockclient/ui/alerts_dialog.py`（新）、
  `stockclient/ui/main_window.py`（接入对话框）、`tests/test_alerts.py`
- 验收：单元测试覆盖四类规则与启停；`[预警]` 按钮可打开管理窗口。

### T3 · 数据层增强 + 测试
- 目标：新增 `clist` 批量自选股行情（自选股面板一次拉全，减少请求）；
  补齐 `trends2` 分时解析；增加搜索建议接口；扩充单元测试。
- 涉及：`stockclient/eastmoney.py`、`tests/test_eastmoney.py`、`tests/test_indicators.py`（新）
- 验收：批量接口解析测试通过；自选股 9 只一次请求返回。

### T4 · 打包 + CI + 文档
- 目标：PyInstaller 打包配置；GitHub Actions（单元测试 + 冒烟测试）；
  CONTRIBUTING、CHANGELOG、发布说明。
- 涉及：`packaging/`（新）、`.github/workflows/`（新）、`CONTRIBUTING.md`（新）、
  `CHANGELOG.md`（新）、`README.md`
- 验收：CI 在 push 时通过测试；`packaging/build.sh` 产出可执行文件。

### T5 · 数据源独立配置文件
- 目标：接口地址/参数/字段映射/周期复权码表/限频全部移入
  `stockclient/data_sources.json`，支持用户覆盖层，改接口不改代码。
- 涉及：`stockclient/data_sources.json`（新）、`stockclient/datasource.py`（新）、
  `stockclient/eastmoney.py`、`tests/test_datasource.py`（新）、README。
- 验收：`load_source` 深合并用户覆盖；`eastmoney` 常量来自配置；测试通过。

### T6 · 发行安装包（deb / rpm / zip）
- 目标：产出常规安装包并随 Release 发布：Linux `.deb`（dpkg-deb）、`.rpm`
  （rpmbuild）、`.tar.gz`；Windows/macOS `.zip`。
- 涉及：`packaging/make-packages.sh`、`packaging/linux/`（desktop/图标/rpm spec）、
  `.github/workflows/release.yml`。
- 验收：本地产出并通过 `dpkg-deb -I/-c` 校验；CI 在 ubuntu/windows/macos 构建并
  附加到 Release。

## 流水集成顺序

1. **基线**：合并 T1–T4 前，先推送当前可用版本（v0.3.0）。
2. **并行开发**：T1/T2/T3/T4 互不重叠文件，可同时进行。
3. **集成**：依次合入 → 跑 `unittest` + `smoke.py` → 修回归 → 提交推送。
4. **发布**：打 tag `v0.3.0`，CI 自动跑测试。

## 当前状态

- [x] 基线可用（demo 模式端到端通过）
- [x] T1 分时图（走势线 + 均价线 + 分钟量）
- [x] T2 预警（四类规则 + 管理窗口）
- [x] T3 数据层（clist 批量 / trends2 / suggest / 指标测试）
- [x] T4 打包 + CI + 文档
- [x] T5 数据源独立配置文件（可用户覆盖）
- [x] T6 发行安装包（deb/rpm/tar.gz/zip）

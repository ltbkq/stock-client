# 更新日志 / Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- **分时图独立渲染**：走势线 + 均价线（`indicators.avg_price`）+ 分钟成交量，
  不再复用 K 线蜡烛（`ui/chart.py::set_intraday`）。
- **预警全类型 + 管理窗口**：四类规则（价格上穿/下破、涨幅/跌幅超过）+
  `ui/alerts_dialog.py`（列表 / 添加 / 删除 / 启停）。
- **数据层增强**：`clist` 批量自选股行情（一次请求）、`trends2` 分时解析、
  `suggest` 搜索联想。
- **数据源独立配置文件**：`stockclient/data_sources.json` +
  `stockclient/datasource.py`，接口地址/参数/字段映射/码表/限频外置，
  支持用户覆盖层（`~/.config/stock-client/data_sources.json`）——改接口不改代码。
- **指标单元测试**（`tests/test_indicators.py`）与数据源配置测试
  （`tests/test_datasource.py`）。
- PyInstaller 打包配置（`packaging/stockclient.spec` + `packaging/build.sh`），
  可产出单文件、无控制台窗口的 `stock-client` 可执行程序。
- GitHub Actions CI（`.github/workflows/ci.yml`）：push / PR 时运行单元测试
  与无头冒烟测试。
- `CONTRIBUTING.md`：开发环境、测试、代码风格与 PR 流程说明。
- `CHANGELOG.md`：本文件。

## [0.3.0] - 2026-09-27

基线版本：`deepseek.txt` v3.0 设计文档的可运行参考实现。

### Added

- **设计文档 v3.0**（`deepseek.txt`）：固定 80 列线框，覆盖 9 个界面区域、
  交互状态、东方财富数据接入方案与非功能需求。
- **9 区域 UI**（`stockclient/ui/`）：
  - 顶部工具栏：搜索 / 周期 / 复权 / 五档 / 预警 / 刷新；
  - 左侧自选股面板（分组树 + 可排序列表，`QDockWidget`）；
  - K 线主图（自绘 `CandlestickItem` + MA/BOLL）；
  - 成交量副图（VOL + MAVOL）；
  - 指标副图（MACD / KDJ / RSI）；
  - 盘口五档（布局 A/B 切换，QSettings 记忆）；
  - 分时图（复用 K 线渲染）；
  - 底部工具条（导出 PNG / 全屏）；
  - 状态栏（数据源 / 更新时间 / 连接状态 / 刷新频率 / 预警数）。
- **东方财富客户端**（`stockclient/eastmoney.py`）：实时快照、K 线、分时、
  五档解析（纯函数 `parse_*`），含节流与指数退避。
- **预警引擎**（`stockclient/alerts.py`）：价格上穿规则（边沿触发）+
  托盘通知。
- **演示模式**（`run.py --demo`）：完全离线的确定性样例数据
  （`stockclient/sample.py`），无需网络即可运行与测试。
- **数据层**：SQLite（可降级内存）K 线缓存 + LRU 快照缓存
  （`stockclient/cache.py`）、`QThreadPool` 轮询（`stockclient/workers.py`）。
- **测试**：解析器与预警单元测试（`tests/`）、无头端到端冒烟测试
  （`scripts/smoke.py`）。

[Unreleased]: https://github.com/ltbkq/stock-client/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ltbkq/stock-client/releases/tag/v0.3.0

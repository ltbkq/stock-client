# 自选股行情分析客户端

`deepseek.txt`（v3.0 设计文档）的可运行参考实现：桌面原生 **PySide6/Qt**，
行情源为 **东方财富** 公开接口，另带完全离线的演示模式。

- 设计文档：[`deepseek.txt`](deepseek.txt)（80 列线框 + 区域/交互/数据/技术方案）
- 许可：[MIT](LICENSE) · 仓库：https://github.com/ltbkq/stock-client

## 与设计文档的对应

| 设计文档 | 实现 |
|---|---|
| 布局 A / B（五档收起 / 展开） | 右侧 `QDockWidget`，工具栏 `[五档]` 切换，状态写入配置 |
| 1 顶部工具栏（搜索/周期/复权/五档/预警/刷新/设置） | `ui/main_window.py::_build_toolbar` |
| 2 左侧自选股面板 | `ui/watchlist.py` |
| 3 K 线主图（蜡烛+均线/BOLL） | `ui/chart.py::CandlestickItem` + `indicators` |
| 4 成交量副图 | `chart.py::_draw_volume` |
| 5 指标副图（MACD/KDJ/RSI） | `chart.py::_draw_indicator` |
| 6 盘口五档 | `ui/orderbook.py` |
| 7 分时图 | 周期下拉选「分时」(`trends2` / 离线生成) |
| 8 底部工具条 + 导出/全屏 | `main_window.py::_build_bottom_bar`、`_export`、`_toggle_fullscreen` |
| 9 状态栏 | `main_window.py::_build_status_bar` |
| 预警提醒 | `alerts.py`（边沿触发规则引擎）+ 托盘通知 |
| 数据 / 缓存 / 线程 | `eastmoney.py` / `cache.py` / `workers.py` |

## 安装与运行

```bash
cd stock-client
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python run.py --demo      # 离线演示（确定性样例数据，无需网络）
.venv/bin/python run.py             # 实时行情
.venv/bin/python run.py --no-proxy  # 实时，忽略系统代理
```

依赖检测到本机 Python 可能缺少 `_sqlite3`，`cache.py` 会在缺失时自动降级为
内存缓存，不影响运行（状态见 `BarCache.backend`）。

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -t .   # 单元测试
.venv/bin/python scripts/smoke.py                     # 无头端到端冒烟测试
```

`scripts/smoke.py` 在 `QT_QPA_PLATFORM=offscreen` 下构造完整窗口、跑轮询、
断言自选股 / K 线 / 盘口均收到数据，并把图表导出为 PNG。

## 目录结构

```
stock-client/
├── run.py                     # 入口（--demo / --no-proxy）
├── requirements.txt
├── scripts/smoke.py           # 无头冒烟测试
├── stockclient/
│   ├── config.py              # JSON 配置（分组/周期/复权/主题/布局）
│   ├── models.py              # Quote / Bar / OrderBook / Alert
│   ├── eastmoney.py           # 东方财富客户端 + 纯函数解析器
│   ├── cache.py               # SQLite（或内存）K 线缓存 + LRU
│   ├── indicators.py          # MA/EMA/MACD/KDJ/RSI/BOLL
│   ├── sample.py              # 离线确定性样例数据
│   ├── alerts.py              # 预警规则引擎（边沿触发）
│   ├── workers.py             # DataService + QThreadPool 轮询
│   └── ui/                    # main_window / chart / watchlist / orderbook / style
└── tests/                     # 解析器与预警单元测试
```

## 数据源说明与注意事项

- 东方财富为非官方公开接口，`eastmoney.py` 中的字段号（`f43` 最新价、
  `f59` 小数位、`f11..f40` 五档等）按公开惯用映射实现，**上线前请用
  `tests/test_eastmoney.py` 或真实响应回归验证**。解析器对缺失字段、
  停牌、`"-"` 均做了容错。
- `secid` 规则：`1.` 沪市（6/5/9 开头），`0.` 深市与北交所。
- 请求已做节流（默认 200ms/次）与指数退避（最多 3 次）；请勿提高频率。
- 仅供学习研究，注意数据版权与使用条款，勿用于商业分发。

## 已知限制

- 分时图当前复用 K 线渲染，未单独绘制均价线；预警暂只支持价格上穿。
- 网络在后端代理波动时会重试；极端情况下降级到缓存并在状态栏标红。
- 线框图（`deepseek.txt`）固定 80 列，仅约束文档，不影响窗口布局。

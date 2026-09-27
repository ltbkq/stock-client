# 贡献指南 / Contributing

感谢参与本项目！本项目是 `deepseek.txt`（v3.0 设计文档）的可运行参考实现，
欢迎按 [ROADMAP.md](ROADMAP.md) 中的任务拆分提交改进。

## 开发环境

```bash
cd stock-client
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

- Python >= 3.11（CI 使用 3.11）。
- 依赖：PySide6-Essentials、pyqtgraph、numpy、requests（见 `requirements.txt`）。
- 无头环境（如 CI、远程服务器）下运行 GUI 相关命令时，请先设置
  `export QT_QPA_PLATFORM=offscreen`。

## 运行测试

```bash
# 单元测试（解析器 / 预警引擎等纯逻辑）
.venv/bin/python -m unittest discover -s tests -t .

# 无头端到端冒烟测试（构造完整窗口、跑轮询、导出 PNG）
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/smoke.py
```

- 新增纯逻辑（解析、指标计算等）时，请在 `tests/` 下补充单元测试。
- 改动 UI 或数据流后，务必跑一次冒烟测试确认端到端无回归。
- 提交前应保证两条命令均通过。

## 代码风格

- **类型注解**：公开函数/方法签名使用类型注解（`from __future__ import annotations`
  已启用，可直接写 `list[str]`、`X | None` 等）。
- **文档字符串**：模块、类、公开函数使用 docstring，风格与现有代码一致
  （中文描述，说明用途与关键参数/返回值）。
- **注释**：沿用代码库的中文注释习惯；解释「为什么」而非「做了什么」，
  行宽参考设计文档的 80 列线框。
- **命名**：模块/函数/变量用英文小写蛇形（`snake_case`），类用 `PascalCase`，
  常量用大写；UI 控件成员沿用现有 `lbl_` / `btn_` 等前缀风格。
- **线程**：网络请求放 `workers.py` 的 `QThreadPool`，通过信号回主线程，
  不要在子线程直接操作 UI。
- **数据解析**：东方财富字段解析保持纯函数（`eastmoney.py` 中的 `parse_*`），
  便于单元测试；对缺失字段、停牌、`"-"` 保持容错。

## 提交与 PR 流程

1. 从 `main` 拉取新分支，分支名体现任务（如 `feat/intraday-chart`、
   `fix/orderbook-parse`）。
2. 按 ROADMAP 的任务边界提交，保持改动聚焦；提交信息用中文或英文均可，
   说明「改了什么、为什么」。
3. 推送分支并开启 PR，描述中列出：改动摘要、涉及文件、测试结果
   （`unittest` 与 `smoke.py` 的输出）。
4. CI（GitHub Actions）会在 push / PR 时自动运行单元测试与冒烟测试，
   请确保两项均通过后再请求 review。
5. Review 意见处理完毕后由维护者合并；合并前请保持分支与 `main` 同步。

## 打包

可执行文件打包配置见 [packaging/README.md](packaging/README.md)。

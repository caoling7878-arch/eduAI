# Vendored: edulab

| 字段 | 值 |
|------|-----|
| 上游 | https://github.com/wy51ai/edulab |
| 版本 | 克隆自 `master`（集成时约 v0.1.8，见 package.json） |
| 许可证 | Apache-2.0（见 LICENSE / NOTICE） |
| 用途 | 为 eduAI 提供立体几何 / 解析几何 / 化学反应交互课页生成能力 |

本目录为源码 vendoring（已去除嵌套 `.git`）。升级方式：

```bash
rm -rf vendor/edulab
git clone --depth 1 https://github.com/wy51ai/edulab.git vendor/edulab
rm -rf vendor/edulab/.git
```

平台侧封装见 `tools/geometry-lab/`。

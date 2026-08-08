# 几何动图教学（edulab 集成）

上游开源：[wy51ai/edulab](https://github.com/wy51ai/edulab)（Apache-2.0）  
本地路径：`vendor/edulab`  
统一入口：`tools/geometry-lab/generate.py`  
产出目录：`content/geometry-lab/`

## 能力概览

| 技能 | 渲染 | 用途 |
|------|------|------|
| `edu-solid-geometry` | Three.js + MathJax | 立体几何：线面角、体积等，分步高亮 |
| `edu-analytic-geometry` | Canvas + KaTeX | 圆锥曲线：滑块驱动派生构造与读数 |
| `edu-chem-reaction` | Three.js + KaTeX | 化学微观动图（可选扩展） |

计算核心均为 **sympy 精确求解**，答案卡、步骤数值与交互控件同源，避免「讲错几何」。

## 安装依赖

```bash
python3 -m pip install -r tools/geometry-lab/requirements.txt
```

## 生成演示集

```bash
python3 tools/geometry-lab/generate.py demos
python3 -m http.server 8765 --directory content/geometry-lab
# 浏览器打开 http://127.0.0.1:8765/
```

## 常用命令

```bash
python3 tools/geometry-lab/generate.py list
python3 tools/geometry-lab/generate.py solid cube
python3 tools/geometry-lab/generate.py solid random 7
python3 tools/geometry-lab/generate.py analytic ellipse_dot_range
python3 tools/geometry-lab/generate.py analytic all
python3 tools/geometry-lab/generate.py chem combustion_ch4
```

## 与平台对接（规划）

1. **课时类型** `interactive_lab`：课时内容指向已生成 HTML（MinIO / 静态目录）。
2. **异步生成任务**：API `POST /api/v1/geometry-lab/jobs` → Worker 调用本脚本 → 回写 URL。
3. **学员端**：课程学习页用 iframe / 新开页打开；记录停留时长计入学习行为。
4. **管理端**：侧栏「几何动图实验室」：选题型、预览、挂课。

详见 `PRD.md` §17。

## 许可证注意

二次分发须保留 `vendor/edulab/LICENSE`、`NOTICE`，并在产品致谢中标明上游项目。

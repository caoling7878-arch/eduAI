#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eduAI × edulab 统一生成入口：立体几何 / 解析几何 / 化学反应交互课页。

上游仓库（Apache-2.0）：vendor/edulab ← https://github.com/wy51ai/edulab

用法:
  python3 tools/geometry-lab/generate.py list
  python3 tools/geometry-lab/generate.py solid cube
  python3 tools/geometry-lab/generate.py solid random 7
  python3 tools/geometry-lab/generate.py analytic ellipse_dot_range
  python3 tools/geometry-lab/generate.py analytic all
  python3 tools/geometry-lab/generate.py chem combustion_ch4
  python3 tools/geometry-lab/generate.py demos          # 一键产出演示集
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "edulab"
OUT_ROOT = ROOT / "content" / "geometry-lab"

SKILLS = {
    "solid": VENDOR / "skills" / "edu-solid-geometry" / "scripts" / "generate.py",
    "analytic": VENDOR / "skills" / "edu-analytic-geometry" / "scripts" / "generate.py",
    "chem": VENDOR / "skills" / "edu-chem-reaction" / "scripts" / "generate.py",
}

SOLID_KEYS = ("cube", "box", "pyramid", "random")
# analytic / chem 的完整列表由上游 generate.py list 给出


def _ensure_vendor() -> None:
    if not VENDOR.is_dir():
        raise SystemExit(
            f"未找到 vendor/edulab。请先克隆：\n"
            f"  git clone https://github.com/wy51ai/edulab.git vendor/edulab"
        )
    for name, script in SKILLS.items():
        if not script.is_file():
            raise SystemExit(f"缺少上游脚本 ({name}): {script}")


def _run(script: Path, args: list[str]) -> None:
    cmd = [sys.executable, str(script), *args]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(script.parent))


def cmd_list(_: argparse.Namespace) -> None:
    _ensure_vendor()
    print("=== solid（立体几何）===")
    print("  " + ", ".join(SOLID_KEYS))
    print("\n=== analytic（解析几何）===")
    _run(SKILLS["analytic"], ["list"])
    print("\n=== chem（化学反应，可选扩展）===")
    _run(SKILLS["chem"], ["list"])


def cmd_solid(ns: argparse.Namespace) -> None:
    _ensure_vendor()
    out_dir = OUT_ROOT / "solid"
    out_dir.mkdir(parents=True, exist_ok=True)
    key = ns.key
    if key == "random":
        out = out_dir / f"random-{ns.seed}.html"
        _run(SKILLS["solid"], ["random", str(ns.seed), str(out)])
    else:
        out = out_dir / f"{key}.html"
        _run(SKILLS["solid"], [key, str(out)])
    print(f"→ {out}")


def cmd_analytic(ns: argparse.Namespace) -> None:
    _ensure_vendor()
    out_dir = OUT_ROOT / "analytic"
    out_dir.mkdir(parents=True, exist_ok=True)
    if ns.key == "all":
        _run(SKILLS["analytic"], ["all", str(out_dir)])
    else:
        out = out_dir / f"{ns.key}.html"
        _run(SKILLS["analytic"], [ns.key, str(out)])
        print(f"→ {out}")


def cmd_chem(ns: argparse.Namespace) -> None:
    _ensure_vendor()
    out_dir = OUT_ROOT / "chem"
    out_dir.mkdir(parents=True, exist_ok=True)
    if ns.key == "random":
        out = out_dir / f"random-{ns.seed}.html"
        _run(SKILLS["chem"], ["random", str(ns.seed), str(out)])
    else:
        out = out_dir / f"{ns.key}.html"
        _run(SKILLS["chem"], [ns.key, str(out)])
    print(f"→ {out}")


def cmd_demos(_: argparse.Namespace) -> None:
    """生成平台演示用的几何动图教学课页集合，并刷新索引页。"""
    _ensure_vendor()
    if OUT_ROOT.exists():
        # 保留 index.html 模板逻辑：整目录重建更干净
        for sub in ("solid", "analytic", "chem"):
            p = OUT_ROOT / sub
            if p.exists():
                shutil.rmtree(p)

    # 立体几何旗舰样例
    for key in ("cube", "box", "pyramid"):
        ns = argparse.Namespace(key=key, seed=0)
        cmd_solid(ns)
    cmd_solid(argparse.Namespace(key="random", seed=7))

    # 解析几何：全部已注册题型
    cmd_analytic(argparse.Namespace(key="all"))

    # 化学（可选能力，一并演示）
    for key in ("combustion_ch4", "esterification"):
        try:
            cmd_chem(argparse.Namespace(key=key, seed=0))
        except subprocess.CalledProcessError as e:
            print(f"[warn] chem {key} 生成失败: {e}", file=sys.stderr)

    _write_index()
    print(f"\n演示集已就绪: {OUT_ROOT}")
    print("本地预览: python3 -m http.server 8765 --directory content/geometry-lab")


def _write_index() -> None:
    """写入简易画廊首页（品牌色对齐 PRD：青松 + 琥珀）。"""
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    def links(subdir: str) -> str:
        d = OUT_ROOT / subdir
        if not d.is_dir():
            return "<li class='empty'>暂无</li>"
        items = sorted(d.glob("*.html"))
        if not items:
            return "<li class='empty'>暂无</li>"
        return "\n".join(
            f'<li><a href="{subdir}/{p.name}">{p.stem.replace("_", " ")}</a></li>'
            for p in items
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>几何动图实验室 · eduAI</title>
  <style>
    :root {{
      --brand: #0F6B5C;
      --accent: #E8A317;
      --ink: #14212B;
      --muted: #5C6B73;
      --surface: #F3F6F4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "Source Han Sans SC", "IBM Plex Sans", "PingFang SC", sans-serif;
      color: var(--ink); background: linear-gradient(160deg, #F3F6F4 0%, #E7EEF5 100%);
      min-height: 100vh;
    }}
    header {{
      padding: 48px 24px 24px; max-width: 920px; margin: 0 auto;
    }}
    .brand {{
      font-family: "Source Han Serif SC", "Songti SC", serif;
      font-size: clamp(2rem, 4vw, 2.75rem); font-weight: 700; color: var(--brand);
      letter-spacing: 0.02em; margin: 0 0 8px;
    }}
    .lead {{ color: var(--muted); font-size: 1.05rem; max-width: 36em; line-height: 1.6; }}
    main {{
      max-width: 920px; margin: 0 auto; padding: 8px 24px 64px;
      display: grid; gap: 28px;
    }}
    section {{
      background: rgba(255,255,255,0.72); border: 1px solid rgba(15,107,92,0.12);
      border-radius: 16px; padding: 24px 28px;
    }}
    h2 {{
      margin: 0 0 6px; font-size: 1.2rem; color: var(--brand);
    }}
    .tag {{
      display: inline-block; font-size: 0.75rem; color: var(--ink);
      background: color-mix(in srgb, var(--accent) 28%, white);
      padding: 2px 8px; border-radius: 4px; margin-bottom: 12px;
    }}
    ul {{ margin: 0; padding-left: 1.2em; line-height: 1.9; }}
    a {{ color: var(--brand); text-decoration: none; border-bottom: 1px solid transparent; }}
    a:hover {{ border-bottom-color: var(--accent); }}
    footer {{
      max-width: 920px; margin: 0 auto; padding: 0 24px 48px;
      font-size: 0.85rem; color: var(--muted);
    }}
    .empty {{ color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <p class="brand">eduAI 几何动图实验室</p>
    <p class="lead">基于开源项目 <strong>edulab</strong>：用 sympy 精确求解，生成可交互的立体几何（Three.js）与解析几何（Canvas）教学页，把「算对」和「看懂」合在同一屏。</p>
  </header>
  <main>
    <section>
      <span class="tag">立体几何 · 3D</span>
      <h2>edu-solid-geometry</h2>
      <ul>{links("solid")}</ul>
    </section>
    <section>
      <span class="tag">解析几何 · 2D</span>
      <h2>edu-analytic-geometry</h2>
      <ul>{links("analytic")}</ul>
    </section>
    <section>
      <span class="tag">可选扩展 · 化学微观</span>
      <h2>edu-chem-reaction</h2>
      <ul>{links("chem")}</ul>
    </section>
  </main>
  <footer>
    上游：<a href="https://github.com/wy51ai/edulab">wy51ai/edulab</a>（Apache-2.0）·
    本地路径 <code>vendor/edulab</code> ·
    重新生成 <code>python3 tools/geometry-lab/generate.py demos</code>
  </footer>
</body>
</html>
"""
    (OUT_ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"→ {OUT_ROOT / 'index.html'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="eduAI 几何动图课页生成器（edulab）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出可用题型")
    p_list.set_defaults(func=cmd_list)

    p_solid = sub.add_parser("solid", help="生成立体几何课页")
    p_solid.add_argument("key", choices=SOLID_KEYS)
    p_solid.add_argument("seed", nargs="?", type=int, default=0, help="random 模式种子")
    p_solid.set_defaults(func=cmd_solid)

    p_an = sub.add_parser("analytic", help="生成解析几何课页")
    p_an.add_argument("key", help="题型 key，或 all")
    p_an.set_defaults(func=cmd_analytic)

    p_chem = sub.add_parser("chem", help="生成化学反应微观演示")
    p_chem.add_argument("key")
    p_chem.add_argument("seed", nargs="?", type=int, default=0)
    p_chem.set_defaults(func=cmd_chem)

    p_demos = sub.add_parser("demos", help="一键生成演示集 + 索引页")
    p_demos.set_defaults(func=cmd_demos)

    p_index = sub.add_parser("index", help="仅刷新画廊索引")
    p_index.set_defaults(func=lambda _ns: _write_index())

    ns = parser.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()

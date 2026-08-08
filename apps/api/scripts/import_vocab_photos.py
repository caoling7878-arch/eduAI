#!/usr/bin/env python3
"""从「中学生必背英语单词800词_带配图.docx」提取单词配图。

用法（仓库根目录）:
  python3 apps/api/scripts/import_vocab_photos.py
  python3 apps/api/scripts/import_vocab_photos.py --docx path/to/file.docx
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import OrderedDict
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _cell_text(cell: ET.Element) -> str:
    return "".join(t.text or "" for t in cell.findall(".//w:t", NS)).strip()


def _cell_rids(cell: ET.Element) -> list[str]:
    out = []
    for b in cell.findall(".//a:blip", NS):
        rid = b.attrib.get("{%s}embed" % NS["r"])
        if rid:
            out.append(rid)
    return out


def import_photos(docx: Path, out_dir: Path, map_path: Path) -> int:
    z = zipfile.ZipFile(docx)
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    rid_to_media = {}
    for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels):
        rid_to_media[m.group(1)] = "word/" + m.group(2).lstrip("/")

    root = ET.fromstring(z.read("word/document.xml"))
    word_to_rid: OrderedDict[str, str] = OrderedDict()
    for tbl in root.findall(".//w:tbl", NS):
        for row in tbl.findall("w:tr", NS):
            cells = row.findall("w:tc", NS)
            if len(cells) < 2:
                continue
            rids = _cell_rids(cells[0])
            text = _cell_text(cells[1])
            m = re.match(r"^([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*)*)\s+", text)
            if not m or not rids:
                continue
            word = m.group(1).strip().lower()
            if word not in word_to_rid:
                word_to_rid[word] = rids[0]

    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*"):
        if f.is_file():
            f.unlink()

    mapping: dict[str, str] = {}
    for word, rid in word_to_rid.items():
        media = rid_to_media.get(rid)
        if not media or media not in z.namelist():
            continue
        ext = Path(media).suffix.lower() or ".jpg"
        fname = re.sub(r"[^a-z0-9\-]+", "_", word) + ext
        (out_dir / fname).write_bytes(z.read(media))
        mapping[word] = fname

    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(mapping)


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--docx",
        type=Path,
        default=root / "中学生必背英语单词800词_带配图.docx",
    )
    args = parser.parse_args()
    api_app = Path(__file__).resolve().parents[1]
    n = import_photos(
        args.docx,
        api_app / "static" / "vocab",
        api_app / "data" / "vocab_image_map.json",
    )
    # 清缓存（若同进程）
    try:
        from app.services.vocab_images import clear_photo_cache

        clear_photo_cache()
    except Exception:
        pass
    print(f"imported {n} vocab photos from {args.docx.name}")


if __name__ == "__main__":
    main()

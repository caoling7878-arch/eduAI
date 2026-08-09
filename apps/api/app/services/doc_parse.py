from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Tuple
from xml.etree import ElementTree as ET


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB
MAX_TEXT_CHARS = 400_000


def detect_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in {".md", ".markdown"}:
        return "md"
    if ext == ".docx":
        return "docx"
    if ext == ".txt":
        return "txt"
    return "text"


def parse_upload(filename: str, data: bytes) -> Tuple[str, str]:
    """返回 (source_type, plain_text)。"""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"文件过大（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）")
    stype = detect_type(filename)
    if stype == "pdf":
        text = _parse_pdf(data)
    elif stype == "docx":
        text = _parse_docx(data)
    elif stype in {"md", "txt", "text"}:
        text = _parse_text(data)
    else:
        raise ValueError("暂不支持该格式，请上传 PDF / Markdown / TXT / DOCX")
    text = _normalize(text)
    if not text.strip():
        raise ValueError("未能从文件中提取到有效文本（可能是扫描件图片 PDF）")
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n\n…（正文已截断）"
    return stype, text


def _normalize(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ValueError("服务端未安装 pymupdf，无法解析 PDF") from e
    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    try:
        for page in doc:
            parts.append(page.get_text("text") or "")
    finally:
        doc.close()
    return "\n".join(parts)


def _parse_docx(data: bytes) -> str:
    # 优先 python-docx；失败则用 OOXML 简易抽取
    try:
        from docx import Document  # type: ignore

        d = Document(io.BytesIO(data))
        paras = [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()]
        if paras:
            return "\n".join(paras)
    except Exception:
        pass
    return _parse_docx_xml(data)


def _parse_docx_xml(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml")
    except Exception as e:
        raise ValueError("DOCX 解析失败，请另存为 PDF/TXT 后重试") from e
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts: list[str] = []
    for p in root.findall(".//w:p", ns):
        bits = [t.text or "" for t in p.findall(".//w:t", ns)]
        line = "".join(bits).strip()
        if line:
            texts.append(line)
    return "\n".join(texts)

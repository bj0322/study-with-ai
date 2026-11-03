"""Extract study materials into numbered units (page / slide / section).

Usage:
    python extract.py <file> [<file> ...] --out <work_dir> [--low-text-chars 80]

Writes:
    <work_dir>/units.json    list of {id, source, locator, title, text, low_text, images}
    <work_dir>/extracted.md  human-readable dump, one "## Unit N" block per unit
    <work_dir>/images/       rendered PDF pages (low-text pages) / pictures pulled from PPTX
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def need(module, pip_name):
    try:
        return __import__(module)
    except ImportError:
        sys.exit(f"Missing package: pip install {pip_name}")


def first_line(text, limit=80):
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:limit]
    return ""


def extract_pdf(path, img_dir, low_chars, render_all):
    fitz = need("fitz", "pymupdf")
    units = []
    doc = fitz.open(path)
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        has_images = bool(page.get_images(full=True)) or bool(page.get_drawings())
        low = len(text) < low_chars
        images = []
        if low or render_all or has_images:
            out = img_dir / f"{path.stem}_p{i:03d}.png"
            page.get_pixmap(dpi=110).save(out)
            images.append(str(out))
        units.append({
            "source": path.name, "locator": f"p.{i}", "title": first_line(text),
            "text": text, "low_text": low, "has_visuals": has_images, "images": images,
        })
    return units


def extract_pptx(path, img_dir, low_chars, render_all):
    pptx = need("pptx", "python-pptx")
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = pptx.Presentation(path)
    units = []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(sh.shapes)
            else:
                yield sh

    for i, slide in enumerate(prs.slides, start=1):
        parts, images, title = [], [], ""
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            title = slide.shapes.title.text_frame.text.strip()
        for n, sh in enumerate(walk(slide.shapes)):
            if sh.has_text_frame:
                for para in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in para.runs).strip()
                    if t:
                        parts.append("  " * para.level + "- " + t)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    parts.append("| " + " | ".join(c.text.strip() for c in row.cells) + " |")
            if getattr(sh, "has_chart", False) and sh.has_chart:
                parts.append("[chart: " + (sh.chart.chart_title.text_frame.text
                             if sh.chart.has_title else "untitled") + "]")
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                img = sh.image
                out = img_dir / f"{path.stem}_s{i:03d}_{n}.{img.ext}"
                out.write_bytes(img.blob)
                images.append(str(out))
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        text = "\n".join(parts)
        if notes:
            text += "\n\n[speaker notes]\n" + notes
        units.append({
            "source": path.name, "locator": f"slide {i}", "title": title or first_line(text),
            "text": text, "low_text": len(text) < low_chars,
            "has_visuals": bool(images), "images": images,
        })
    return units


def split_sections(text, max_chars=2500):
    """Split plain/markdown text by headings; fall back to paragraph groups."""
    blocks = re.split(r"(?m)^(?=#{1,3} )", text)
    blocks = [b.strip() for b in blocks if b.strip()]
    if len(blocks) <= 1:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        blocks, cur = [], ""
        for p in paras:
            if cur and len(cur) + len(p) > max_chars:
                blocks.append(cur)
                cur = ""
            cur = (cur + "\n\n" + p).strip()
        if cur:
            blocks.append(cur)
    return blocks


def extract_text_like(path, text, low_chars):
    units = []
    for i, block in enumerate(split_sections(text), start=1):
        units.append({
            "source": path.name, "locator": f"section {i}",
            "title": first_line(block).lstrip("# "), "text": block,
            "low_text": len(block) < low_chars, "has_visuals": False, "images": [],
        })
    return units


def extract_docx(path, low_chars):
    docx = need("docx", "python-docx")
    d = docx.Document(path)
    lines = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            lines.append("")
            continue
        style = (p.style.name or "").lower()
        m = re.match(r"heading (\d)", style)
        if m and int(m.group(1)) <= 3:
            lines += ["", "#" * int(m.group(1)) + " " + t]
        else:
            lines.append(t)
    for table in d.tables:
        lines.append("")
        for row in table.rows:
            lines.append("| " + " | ".join(c.text.strip() for c in row.cells) + " |")
    return extract_text_like(path, "\n".join(lines), low_chars)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--low-text-chars", type=int, default=80)
    ap.add_argument("--render-all", action="store_true", help="render every PDF page to PNG")
    args = ap.parse_args()

    out = Path(args.out)
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    units = []
    for f in args.files:
        path = Path(f)
        ext = path.suffix.lower()
        if ext == ".pdf":
            units += extract_pdf(path, img_dir, args.low_text_chars, args.render_all)
        elif ext == ".pptx":
            units += extract_pptx(path, img_dir, args.low_text_chars, args.render_all)
        elif ext == ".docx":
            units += extract_docx(path, args.low_text_chars)
        elif ext in (".md", ".txt", ".markdown"):
            units += extract_text_like(path, path.read_text(encoding="utf-8", errors="replace"),
                                       args.low_text_chars)
        else:
            sys.exit(f"Unsupported file type: {path.name} (pdf, pptx, docx, md, txt)")

    for n, u in enumerate(units, start=1):
        u["id"] = n
        units[n - 1] = {"id": n, **{k: v for k, v in u.items() if k != "id"}}

    (out / "units.json").write_text(json.dumps(units, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out / "extracted.md", "w", encoding="utf-8") as fh:
        for u in units:
            flags = []
            if u["low_text"]:
                flags.append("LOW TEXT - view image" if u["images"] else "LOW TEXT")
            if u["images"]:
                flags.append("images: " + ", ".join(Path(p).name for p in u["images"]))
            fh.write(f"## Unit {u['id']} — {u['source']} {u['locator']}\n")
            if flags:
                fh.write(f"_({'; '.join(flags)})_\n")
            fh.write("\n" + (u["text"] or "(no text)") + "\n\n")

    low = [u["id"] for u in units if u["low_text"]]
    print(f"Extracted {len(units)} units from {len(args.files)} file(s) -> {out}")
    print(f"Total characters: {sum(len(u['text']) for u in units)}")
    if low:
        print(f"Low-text units (look at their images): {low}")


if __name__ == "__main__":
    main()

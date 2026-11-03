"""Turn a podcast script (script.md) into MP3 files with the OpenAI TTS API.

Usage:
    python tts_openai.py <script.md> --out <audio_dir> [--voice coral]
        [--model gpt-4o-mini-tts] [--instructions "..."] [--speed 1.0] [--dry-run]

Each "## " section becomes one MP3 (01_intro.mp3 ...), then all are joined into full.mp3.
API key lookup: env OPENAI_API_KEY -> .env in the script's directory -> .env in the
skill folder. Already-generated chunks are skipped, so a failed run can simply be rerun.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_URL = "https://api.openai.com/v1/audio/speech"
MAX_CHARS = 4000  # API limit is 4096 characters per request
DEFAULT_INSTRUCTIONS = (
    "Speak like a calm, friendly lecturer explaining study material to a student. "
    "Clear pronunciation, moderate pace, natural pauses between ideas."
)
SKILL_DIR = Path(__file__).resolve().parent.parent


def read_env_file(folder):
    # Notepad on Windows often saves ".env" as ".env.txt"; accept both.
    for name in (".env", ".env.txt"):
        path = folder / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        # Prefer OPENAI_API_KEY, but accept any OPENAI_* name or a bare sk-... key.
        m = (re.search(r"(?m)^\s*OPENAI_API_KEY\s*=\s*['\"]?([^'\"\s]+)", text)
             or re.search(r"(?m)^\s*OPENAI_\w*\s*=\s*['\"]?(sk-[^'\"\s]+)", text)
             or re.search(r"(sk-[A-Za-z0-9_\-]{20,})", text))
        if m:
            return m.group(1)
    return None


def find_key(script_path):
    return (os.environ.get("OPENAI_API_KEY")
            or read_env_file(script_path.parent)
            or read_env_file(SKILL_DIR))


def clean(text):
    """Strip markdown that TTS would read aloud."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#>|]", "", text)
    text = re.sub(r"(?m)^\s*[-+]\s+", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_sections(md):
    md = re.sub(r"(?m)^# .*$", "", md, count=1)  # drop the document title
    pieces = re.split(r"(?m)^## +(.+)$", md)
    sections = []
    if clean(pieces[0]):
        sections.append(("00 intro", clean(pieces[0])))
    for i in range(1, len(pieces), 2):
        body = clean(pieces[i + 1])
        if body:
            sections.append((pieces[i].strip(), body))
    return sections


def chunk(text, limit=MAX_CHARS):
    """Split on paragraph, then sentence boundaries, keeping each chunk <= limit."""
    out, cur = [], ""
    units = []
    for para in re.split(r"\n\s*\n", text):
        if len(para) <= limit:
            units.append(para)
        else:
            units += re.split(r"(?<=[.!?。？！다요죠])\s+", para)
    for u in units:
        while len(u) > limit:  # pathological sentence with no breaks
            out.append(u[:limit])
            u = u[limit:]
        if cur and len(cur) + len(u) + 2 > limit:
            out.append(cur)
            cur = ""
        cur = (cur + "\n\n" + u).strip()
    if cur:
        out.append(cur)
    return out


def safe_name(title):
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", title).strip("_")
    return name[:60] or "part"


def synth(key, text, out_path, args):
    payload = {"model": args.model, "voice": args.voice, "input": text,
               "response_format": "mp3", "speed": args.speed}
    if args.model.startswith("gpt-4o") and args.instructions:
        payload["instructions"] = args.instructions
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(5):
        req = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                out_path.write_bytes(resp.read())
                return
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            # 429 is also used for account problems that retrying cannot fix.
            if any(c in body for c in ("billing_not_active", "insufficient_quota")):
                sys.exit("OpenAI account cannot be billed (no active billing or credits). "
                         "Add a payment method / credits at https://platform.openai.com/"
                         f"settings/organization/billing, then rerun. Details: {body}")
            if e.code in (401, 403):
                sys.exit(f"OpenAI rejected the API key (HTTP {e.code}). Check the key. {body}")
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = 2 ** attempt * 5
                print(f"    HTTP {e.code}, retrying in {wait}s")
                time.sleep(wait)
                continue
            sys.exit(f"TTS request failed: HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(5)
                continue
            sys.exit(f"Network error: {e}")


def join_mp3(parts, out_path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg and len(parts) > 1:
        listfile = out_path.with_suffix(".txt")
        listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
                            encoding="utf-8")
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                            "-i", str(listfile), "-c", "copy", str(out_path)])
        listfile.unlink(missing_ok=True)
        if r.returncode == 0:
            return
    with open(out_path, "wb") as fh:
        for p in parts:
            fh.write(p.read_bytes())


def duration(path):
    probe = shutil.which("ffprobe")
    if not probe:
        return None
    r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="coral")
    ap.add_argument("--model", default="gpt-4o-mini-tts")
    ap.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    script = Path(args.script)
    sections = parse_sections(script.read_text(encoding="utf-8"))
    if not sections:
        sys.exit("No content found in script. Use '## ' headings to mark parts.")

    plan = [(title, chunk(body)) for title, body in sections]
    total = sum(len(c) for _, chunks in plan for c in chunks)
    print(f"{len(plan)} parts, {sum(len(c) for _, c in plan)} requests, {total} characters")
    # Rough listening time: Korean ~ 350 chars/min, English ~ 900 chars/min.
    hangul = len(re.findall(r"[가-힣]", script.read_text(encoding="utf-8")))
    rate = 350 if hangul > total * 0.3 else 900
    print(f"Estimated length: ~{total / rate / args.speed:.0f} min")
    for i, (title, chunks) in enumerate(plan, start=1):
        print(f"  {title}: {len(chunks)} chunk(s), {sum(map(len, chunks))} chars")
    if args.dry_run:
        return

    key = find_key(script)
    if not key:
        sys.exit("No OpenAI API key. Set OPENAI_API_KEY or create "
                 f"{SKILL_DIR / '.env'} with the line OPENAI_API_KEY=sk-...")

    out = Path(args.out)
    tmp = out / "_chunks"
    tmp.mkdir(parents=True, exist_ok=True)
    part_files = []
    for i, (title, chunks) in enumerate(plan, start=1):
        chunk_files = []
        for j, text in enumerate(chunks, start=1):
            cf = tmp / f"{i:02d}_{j:03d}.mp3"
            if not (cf.exists() and cf.stat().st_size > 0):
                print(f"  synth {i:02d}.{j} ({len(text)} chars)")
                synth(key, text, cf, args)
            chunk_files.append(cf)
        label = safe_name(re.sub(r"^\d+\s*", "", title))
        pf = out / f"{i:02d}_{label}.mp3"
        join_mp3(chunk_files, pf)
        part_files.append(pf)
        print(f"  -> {pf.name}")

    full = out / "full.mp3"
    join_mp3(part_files, full)
    shutil.rmtree(tmp, ignore_errors=True)
    d = duration(full)
    print(f"Done: {full}" + (f" ({d / 60:.1f} min)" if d else ""))


if __name__ == "__main__":
    main()

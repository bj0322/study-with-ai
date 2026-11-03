---
name: study-podcast
description: Turns study materials (lecture slides as PDF/PPTX, textbook PDFs, DOCX, md/txt notes) into a detailed English explanation report (.md) that covers every page, slide and paragraph with nothing skipped, then rewrites that report as a single-narrator lecture-style podcast script and renders it to MP3 audio with OpenAI TTS (the user supplies their own API key). Use this skill whenever the user hands over exam-range or lecture material and asks to explain all of it, break it down slide by slide or page by page, write a study guide or explainer, listen to it while studying, or turn it into audio, a podcast or TTS, in any language (e.g. "explain every slide", "make this into a podcast", "전부 설명해줘", "슬라이드별로 정리해줘", "팟캐스트로 만들어줘"). Also use it when the user only wants a complete explanation of the material without mentioning audio, and ask before going on to the audio step.
---

# Study Podcast

A three-stage pipeline: study material → **explanation report (md)** → **podcast script** → **TTS audio (mp3)**.

The whole point of this skill is **completeness**. The user will study the entire exam range from these outputs, so a skipped slide or paragraph is material they never learn. This is an *explanation*, not a summary — the report is normally longer than the source.

## 0. Setup

- Work folder: create `<material-name>_study/` next to the input material and put every output there. If that folder is read-only (files uploaded into a chat usually are), create it in the environment's outputs folder instead and hand the finished files to the user for download.
- Audio is the only step that needs anything beyond this sandbox (an API key and access to `api.openai.com`). Before promising audio, read "Know where you are running" in step 4. The report and script work everywhere.
- Language: **all outputs are in English** — report, script and audio — whatever language the source is in. When the source is in another language, translate faithfully, and for key technical terms put the original-language term in parentheses the first time it appears so the user can match it to their lecture. Use another output language only if the user explicitly asks for one.
- Install missing Python packages as needed: `python -m pip install pymupdf python-pptx python-docx` (only the ones required).

Script paths below are relative to this SKILL.md's folder (`scripts/`).

## 1. Extract the content

```bash
python scripts/extract.py <input files...> --out <work folder>
```

- Several files can be passed at once; units are numbered in the order given.
- Outputs: `<work>/units.json` (unit list), `<work>/extracted.md` (readable dump of the source), `<work>/images/`.
- A **unit** is a page for PDF, a slide for PPTX (speaker notes included), and a heading-based section for DOCX/md/txt (paragraph groups when there are no headings).
- PDF pages that have little text or contain figures are rendered to PNG in `images/`. **Open those images and look at them** for any unit flagged `LOW TEXT` or with figures, and explain the diagrams, graphs and equations they show. Treating a figure slide as "just a picture" drops the core of that slide.
- PPTX slides cannot be rendered, so the pictures embedded in them are extracted to `images/` instead. If a slide still can't be understood, ask the user for a PDF export of the deck.
- If a PDF is a scan with no text layer at all, every page is flagged; read the rendered page images directly.

## 2. Write the explanation report (`report.md`)

One section per unit, in the format below. The HTML comment marker at the top is read by the coverage checker, so keep it exactly as shown.

```markdown
<!-- unit: 12 -->
## 12. <slide/page title, or a title that represents its content>
> Source: lecture3.pdf p.12

### Key content
What the source says. Cover every item in it — every bullet, table row, figure element and equation.

### Detailed explanation
Why it is so, how it works, and how it connects to what comes before and after, explained so that someone seeing it for the first time can follow.
For equations, explain what each symbol means and the intuition behind it; for figures and graphs, describe the axes, trends and what they mean.
Add a short example where it helps.

### Key terms
- **Term** (original-language term if not English): meaning — only terms that appear in the source

### Exam points
- Likely exam questions, easily confused points, common mistakes
```

Writing principles:
- **Cover every unit.** Title slides, outlines and reference lists still get a section — a line or two on what the unit is and where it sits in the overall flow. A duplicate slide can be handled briefly: "Same as unit n — difference: …".
- Adding background explanation beyond the source is good, but keep it distinguishable from what the source claims. Never change or misstate the source's content.
- Omit a subheading when it doesn't apply to a unit (e.g. no `Key terms`).
- At the top of the report put a title, the list of source files, the total unit count and a 3–6 line **Overview** of the material's overall flow. At the end put a **Final review**: the core concepts and how they relate to each other.

**For long material (roughly 15+ units):** don't write it in one pass. Append to `report.md` in batches of about 10 units. In one long pass, later units tend to get shallower or get skipped; batching keeps the same depth to the end. Right before writing each batch, re-read those units in `extracted.md` (and their images where relevant).

### Coverage check (required)

```bash
python scripts/check_coverage.py <work>/units.json <work>/report.md
```

If it lists missing or thin units, fill them in and re-run. Don't move on until it passes.

When the report is done, give the user its path and confirm before going on to audio (skip the confirmation if they asked for audio from the start).

## 3. Write the podcast script (`script.md`)

Single-narrator lecture style: one host calmly explaining the material to a student, like a recorded lecture. **Don't read the report aloud — rewrite it for the ear.** The listener can't see any screen; everything follows from that.

Format:
```markdown
# <Podcast title>

## 01 Intro
Paragraph introducing what this episode covers...

## 02 <Part title>
Body paragraphs...

## NN Wrap-up
```

- Each `## ` part becomes one audio file. Group roughly 3–8 units per part along the content's natural flow. Use two-digit part numbers.
- Separate paragraphs with blank lines. Don't use markdown formatting (bold, tables, bullets, code blocks, links) in the script body — TTS reads the symbols or stumbles over them.
- Every unit in the report must be reflected somewhere in the script. The script is more conversational and flows better; it is not the stage where content gets cut.
- Making it listenable:
  - Read equations in words: `E = mc^2` → "energy equals mass times the speed of light squared". For complicated equations, explain their structure and meaning rather than reciting every symbol.
  - Turn tables into "The first item is …, the second is …", or just the comparison that matters.
  - Describe figures so the listener can picture them: "On this graph the horizontal axis is time and the vertical axis is …".
  - Spell out abbreviations the first time they appear. Write symbols (%, →, ≥, ~) as words.
  - Keep sentences short. Use signposts like "Here's the key point" or "To recap", and restate the main takeaways at the end of each part.
  - Never use screen-dependent phrasing like "as you can see on slide 12".
- The intro lays out the episode; the wrap-up gives the exam-focused key review.

After finishing the script, show it to the user before TTS (for long scripts, just give the file path and the list of parts).

## 4. Generate TTS audio

Uses the OpenAI TTS API. **The user obtains and supplies their own API key.**

### Know where you are running

Audio needs two things: an API key the script can read, and a network that lets it reach `api.openai.com`. Both depend on the environment, so work out which one you are in before promising audio:

- **Claude Code** (CLI, or the Code tab of the desktop app): runs on the user's own computer. Both normally work. Recommended key location: `~/.study-podcast/.env` (`C:\Users\<name>\.study-podcast\.env` on Windows).
- **Cowork** (desktop app): runs in a sandbox on the user's computer that sees only the folders the user connected. It can't see `~/.study-podcast`, so the key goes in a `.env` file **in the folder with the study material**. Whether `api.openai.com` is reachable depends on the sandbox's network settings.
- **Chat** (claude.ai or the desktop app's Chat tab with code execution): runs in a remote sandbox that usually blocks outside connections, and there is no safe place to keep a key. Don't attempt audio here. Deliver the report and script, and tell the user they can turn `script.md` into audio from Claude Code or Cowork by asking "make audio from this script".

Then check access before anything else (costs nothing, generates nothing):
```bash
python scripts/tts_openai.py <work>/script.md --check
```
Exit code 0 means ready. Otherwise the message says what is wrong: 2 = no key or key rejected, 3 = network blocked, 4 = billing not active.

### Add the API key (exit code 2)

The script looks for the key in this order: the `OPENAI_API_KEY` environment variable → `.env` in the work folder → `.env` in the folder above it (the study material's folder) → `.env` in the current directory → `~/.study-podcast/.env` → `.env` in this skill's folder. A `.env.txt` file (what Notepad produces) and any `OPENAI_...=sk-...` variable name also work.

If there is no key, tell the user how to add it and wait:
1. Create a key at https://platform.openai.com/api-keys and turn on billing at https://platform.openai.com/settings/organization/billing (separate from a ChatGPT subscription).
2. Save it as a `.env` file containing the single line `OPENAI_API_KEY=sk-...`: in `~/.study-podcast/` for Claude Code, or in the study material's folder for Cowork. Offer to create the folder and an empty file for them (and open it) so they only have to paste the key in. Don't put the key in the skill's own folder: a plugin update replaces that folder and the key would be lost.

Don't ask the user to paste the key into the chat. If they paste it anyway, save it to the right `.env` for them, but never echo it back in replies or command output.

### When audio can't be made here (exit code 3 or 4)

These are environment or account problems that retrying won't fix. Tell the user plainly what the script said, deliver the report and script anyway, and give the next step:
- **3, network blocked:** generate the audio from Claude Code on their computer, or allow `api.openai.com` in the sandbox's network settings and rerun.
- **4, billing:** add a payment method or credits on the OpenAI billing page, then rerun.

### Run

First do a dry run to check length and chunking (no API calls):
```bash
python scripts/tts_openai.py <work>/script.md --out <work>/audio --dry-run
```
Tell the user the character count and estimated listening time (cost scales with these). Then generate:
```bash
python scripts/tts_openai.py <work>/script.md --out <work>/audio
```

Options:
- `--voice` (default `coral`): alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse
- `--model` (default `gpt-4o-mini-tts`): `tts-1` and `tts-1-hd` also work. Only `gpt-4o-mini-tts` supports `--instructions` (speaking-style direction).
- `--instructions`: defaults to a calm lecturer tone; change it if the user wants a different style.
- `--speed` (0.25–4.0, default 1.0)

The generate command repeats the access check first, so a key, network or billing problem stops it before any audio is made, with the same exit codes as above.

Output: one file per part (`audio/01_Intro.mp3` …) plus everything joined into `audio/full.mp3`. Finished chunks are skipped on re-run, so if a run fails partway, run the same command again to resume. With ffmpeg installed the parts are joined cleanly; without it the MP3s are concatenated byte-wise.

## Final report to the user

Tell the user:
- `report.md`: the explanation report (number of units, and that the coverage check passed)
- `script.md`: the podcast script
- `audio/full.mp3` and the per-part files, with the total running time

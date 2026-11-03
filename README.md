# study-with-ai

A Claude Code plugin marketplace of tools for studying.

| Plugin | What it does |
|---|---|
| [study-podcast](plugins/study-podcast) | Lecture slides / PDFs / notes → complete explanation report → podcast script → MP3 audio |

## study-podcast

Give Claude your lecture slides, textbook pages or notes, and it produces:

1. **An explanation report** (`report.md`): every page, slide and section explained in detail, nothing skipped. A coverage checker makes sure no unit is missing.
2. **A podcast script** (`script.md`): the report rewritten as a single-narrator lecture for listening, with equations read out in words and figures described.
3. **Audio** (`audio/full.mp3` plus one MP3 per part), rendered with the OpenAI TTS API.

All output is in English, whatever the language of the source material. Key technical terms keep their original-language form in parentheses.

Supported inputs: PDF, PPTX (speaker notes included), DOCX, Markdown and plain text.

### Requirements

- [Claude Code](https://claude.com/claude-code), either the CLI or the **Code** tab of the Claude desktop app
- Python 3.9+ ([download](https://www.python.org/downloads/); on Windows, tick **"Add Python to PATH"** during setup). Claude installs the packages it needs (`pymupdf`, `python-pptx`, `python-docx`) on first use.
- For audio only: an OpenAI API key with billing enabled
- Optional: [ffmpeg](https://ffmpeg.org/), for cleaner joins between audio parts

### Install

**Easiest:** open Claude Code (or the Code tab in the desktop app) and say:

> Install the study-podcast plugin from https://github.com/bj0322/study-with-ai

**Or run it yourself** in Claude Code:

```
/plugin install study-podcast --marketplace bj0322/study-with-ai
```

On older Claude Code versions, add the marketplace first:

```
/plugin marketplace add bj0322/study-with-ai
```
```
/plugin install study-podcast@study-with-ai
```

Restart Claude Code after installing. Get new versions later with `/plugin update study-podcast`.

**On claude.ai or the desktop app's Chat tab** (no Claude Code needed):

1. Download [**study-podcast.zip**](https://github.com/bj0322/study-with-ai/releases/latest/download/study-podcast.zip). Don't unzip it.
2. Make sure code execution is turned on in Settings → Capabilities.
3. Go to Customize → Skills (Settings → Capabilities → Skills on some versions), click **+**, and upload the ZIP.
4. Attach your PDF in a chat and ask Claude to explain all of it.

The report and script work everywhere. Audio needs Claude's sandbox to reach `api.openai.com`, which claude.ai may block depending on your network settings; if the audio step fails there, use Claude Code for it.

### Add your OpenAI API key (for audio)

1. Create a key at https://platform.openai.com/api-keys.
2. Turn on billing at https://platform.openai.com/settings/organization/billing. This is separate from a ChatGPT subscription; without it, audio generation fails with a billing error.
3. Save the key in a file named `.env` inside a `.study-podcast` folder in your home folder:
   - Windows: `C:\Users\<your name>\.study-podcast\.env`
   - macOS / Linux: `~/.study-podcast/.env`

   The file contains a single line:
   ```
   OPENAI_API_KEY=sk-...
   ```
   Claude can create the folder and empty file for you; just paste the key in yourself. Setting the `OPENAI_API_KEY` environment variable works too.

Treat the key like a password: don't commit it, share it, or paste it into a chat. It is read only by `scripts/tts_openai.py` and sent only to `api.openai.com`.

### Use

Open the folder that holds your material in Claude Code and ask, in any language:

> Explain every slide in `lecture5.pdf` in detail and turn it into a podcast I can listen to.

> 이 시험범위 슬라이드 전부 빠짐없이 설명해주고 팟캐스트로 만들어줘.

Results go into a `<material-name>_study/` folder next to your file. Claude asks before generating audio unless you asked for it. Before calling the API it does a dry run that shows the character count and estimated length.

**Cost:** audio is billed by OpenAI by length. With the default `gpt-4o-mini-tts` model, a 25-minute episode costs well under US$1.

### Troubleshooting

| Problem | Fix |
|---|---|
| Claude doesn't seem to use the skill | Restart Claude Code after installing; check `/plugin` lists study-podcast as enabled |
| `billing_not_active` or `insufficient_quota` | Add a payment method or credits on the OpenAI billing page, then ask Claude to rerun the audio step. Finished parts are kept. |
| `python` not found | Reinstall Python with "Add Python to PATH" ticked, then restart Claude Code |

### How it works

| Script | Purpose |
|---|---|
| `scripts/extract.py` | Splits inputs into numbered units (pages / slides / sections) and renders figure-heavy PDF pages to images so Claude can read the figures |
| `scripts/check_coverage.py` | Fails if any unit is missing from the report or too thin |
| `scripts/tts_openai.py` | Chunks the script, calls OpenAI TTS, joins the MP3s; resumable, with a `--dry-run` mode |

## License

MIT

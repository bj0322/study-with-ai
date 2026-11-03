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

### Where it works

| | Report + script | Audio | Best for |
|---|---|---|---|
| **Claude Code** (CLI or the desktop app's **Code** tab) | ✅ | ✅ | Everything, including large PDFs |
| **Cowork** (Claude desktop app) | ✅ | ✅ if the sandbox can reach `api.openai.com` | No terminal needed; files stay in your folder |
| **Chat** (claude.ai or the desktop app's **Chat** tab) | ✅ | ❌ usually blocked | Quick use with nothing to install |

### Requirements

- One of the Claude apps above (paid plan for Skills)
- For Claude Code: Python 3.9+ ([download](https://www.python.org/downloads/); on Windows, tick **"Add Python to PATH"** during setup). Claude installs the packages it needs (`pymupdf`, `python-pptx`, `python-docx`) on first use.
- For audio only: an OpenAI API key with billing enabled
- Optional: [ffmpeg](https://ffmpeg.org/), for cleaner joins between audio parts

### Install in Claude Code

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

### Install in Cowork or Chat

1. Download [**study-podcast.zip**](https://github.com/bj0322/study-with-ai/releases/latest/download/study-podcast.zip). Don't unzip it.
2. Make sure code execution is turned on in Settings → Capabilities.
3. Go to Customize → Skills (Settings → Capabilities → Skills on some versions), click **+**, and upload the ZIP. The skill is then available in both Cowork and Chat on your account.
4. **Cowork:** connect the folder that holds your material and ask. **Chat:** attach your PDF and ask. Large files may exceed the chat upload limit; split them to the exam range or use Cowork.

In Chat, Claude makes the report and script and skips audio, because the chat sandbox usually can't reach OpenAI. To turn that script into audio later, open it in Claude Code or Cowork and ask "make audio from this script".

### Add your OpenAI API key (for audio)

1. Create a key at https://platform.openai.com/api-keys.
2. Turn on billing at https://platform.openai.com/settings/organization/billing. This is separate from a ChatGPT subscription; without it, audio generation fails with a billing error.
3. Save the key in a file named `.env` that contains a single line:
   ```
   OPENAI_API_KEY=sk-...
   ```
   Where to put the file depends on the app:
   - **Claude Code:** in a `.study-podcast` folder in your home folder: `C:\Users\<your name>\.study-podcast\.env` on Windows, `~/.study-podcast/.env` on macOS / Linux.
   - **Cowork:** in the folder with your study material. Cowork's sandbox can only see the folders you connect.

   Claude can create the empty file for you; just paste the key in yourself. Setting the `OPENAI_API_KEY` environment variable works too. Before generating audio, Claude checks that the key works and that OpenAI is reachable, so a problem shows up before anything is spent.

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
| "Cannot reach api.openai.com" | The sandbox blocks outside connections (common in Chat, possible in Cowork). Make the audio in Claude Code, or allow `api.openai.com` in the app's network settings. |
| "No OpenAI API key found" in Cowork | Put the `.env` file in the folder you connected to Cowork, not in your home folder |

### How it works

| Script | Purpose |
|---|---|
| `scripts/extract.py` | Splits inputs into numbered units (pages / slides / sections) and renders figure-heavy PDF pages to images so Claude can read the figures |
| `scripts/check_coverage.py` | Fails if any unit is missing from the report or too thin |
| `scripts/tts_openai.py` | Chunks the script, calls OpenAI TTS, joins the MP3s; resumable, with `--dry-run` (length estimate) and `--check` (key and network test) modes |

## License

MIT

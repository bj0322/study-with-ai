# study-with-ai

Claude skills for studying.

## study-podcast

Give Claude your lecture slides, textbook pages or notes, and it produces:

1. **An explanation report** (`report.md`): every page, slide and section explained in detail, nothing skipped. A coverage checker makes sure no unit is missing.
2. **A podcast script** (`script.md`): the report rewritten as a single-narrator lecture for listening, with equations read out in words and figures described.
3. **Audio** (`audio/full.mp3` plus one MP3 per part), rendered with the OpenAI TTS API.

All output is in English, whatever the language of the source material. Key technical terms keep their original-language form in parentheses.

Supported inputs: PDF, PPTX (speaker notes included), DOCX, Markdown and plain text.

### Install

Copy the `study-podcast/` folder into your Claude skills directory:

- Claude Code: `~/.claude/skills/study-podcast/` (all projects) or `<project>/.claude/skills/study-podcast/`
- Claude.ai / Claude desktop: zip the folder and upload it under Settings → Capabilities → Skills

Python 3.9+ is required. Claude installs the packages it needs (`pymupdf`, `python-pptx`, `python-docx`) on first use. [ffmpeg](https://ffmpeg.org/) is optional; it gives cleaner joins between audio parts.

### Add your OpenAI API key

The audio step needs your own key from https://platform.openai.com/api-keys. Either set the `OPENAI_API_KEY` environment variable, or create a file named `.env` inside the `study-podcast/` folder:

```
OPENAI_API_KEY=sk-...
```

The key is read only by `scripts/tts_openai.py` and sent only to `api.openai.com`. `.env` files are git-ignored in this repo; never commit your key.

### Use

Just ask Claude, in any language:

> Explain every slide in `lecture5.pdf` in detail and turn it into a podcast I can listen to.

> 이 시험범위 슬라이드 전부 빠짐없이 설명해주고 팟캐스트로 만들어줘.

Claude asks before generating audio unless you requested it. Before calling the API it runs a dry run that shows the character count and estimated length; TTS cost scales with length.

### Scripts

| Script | Purpose |
|---|---|
| `scripts/extract.py` | Splits inputs into numbered units (pages / slides / sections) and renders figure-heavy PDF pages to images |
| `scripts/check_coverage.py` | Fails if any unit is missing from the report or too thin |
| `scripts/tts_openai.py` | Chunks the script, calls OpenAI TTS, joins the MP3s; resumable, with a `--dry-run` mode |

## License

MIT

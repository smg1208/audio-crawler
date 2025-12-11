# TANGTHUVIEN & BNSACH CRAWLER & AUDIO CONVERTER

This small Python project downloads story chapters from tangthuvien.net or bnsach.com, saves each chapter as a text file, and converts it to audio using an external CLI tool `ttx`.

Features
- Config-driven (config.json) so you can continue from last download
- Stores chapters as text and generated audio files in per-story folders
- Uses requests + BeautifulSoup for crawling and subprocess to call `ttx`

Requirements
- Python 3.8+
- pip packages: requests, beautifulsoup4
- `ttx` CLI installed and available in PATH
- (Optional) install `edge-tts` for higher-quality TTS without cloud keys

Quick start
1. Create and activate a virtualenv (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
If you'd like to use the built-in `edge-tts` backend for higher-quality voices, install it:

```bash
pip install edge-tts
```
3. Edit `config.json` to the correct story ID and other settings.

   **For tangthuvien.net:**
   ```json
   {
     "story_id": "17299",
     "source": "tangthuvien",
     "base_url": "https://tangthuvien.net",
     "chapters_api": "https://tangthuvien.net/story/chapters?story_id={}"
   }
   ```

   **For bnsach.com:**
   ```json
   {
     "story_id": "khau-van-tien-dao-convert",
     "source": "bnsach",
     "base_url": "https://bnsach.com",
     "chapters_api": "https://bnsach.com/reader/khau-van-tien-dao-convert/muc-luc",
     "bnsach_username": "your_username",
     "bnsach_password": "your_password"
   }
   ```
   Note: 
   - For bnsach, `chapters_api` should be the direct URL to the table of contents page (muc-luc), and `story_id` should be the story slug.
   - **bnsach.com requires login** to access chapters. Add your `bnsach_username` and `bnsach_password` to the config file.

4. Run the tool:
```bash
python3 run.py --config config.json
```

Dry-run with edge-tts backend (no conversion performed):

```bash
python3 run.py --config config.json --dry-run --tts-backend edge-tts
```

Real run with edge-tts (requires edge-tts installed):

```bash
python3 run.py --config config.json --tts-backend edge-tts --tts-voice "vi-VN-HoaiMyNeural"
```

Default voice from config.json
 - You can set a project-wide default TTS voice in `config.json` using the `tts_voice` field — the runner will use this voice when you don't pass `--tts-voice` on the CLI.
 - The example config in this repo now uses `"tts_voice": "vi-VN-NamMinhNeural"` (edge-tts). This means you can simply run:

```bash
python3 run.py --config config.json --tts-backend edge-tts
```

and `vi-VN-NamMinhNeural` will be used automatically.

Notes
- This project uses a small batch approach to avoid overloading the site and allow resuming downloads.
- If an error occurs during processing of a chapter, the program will stop and persist the last succesfully processed chapter in `config.json`.

Text improvement (optional AI-enhancement)
- The project includes an optional enhancer that can automatically improve chapter text using an LLM while preserving character names.
- New dependencies: `stanza` (for Vietnamese NER), `rapidfuzz` (fuzzy name matching), and `openai` (optional, only needed if you want to use OpenAI).
- Workflow: extract character names → substitute placeholders (<<NAME_1>>) → send to LLM for improvement → restore placeholders → validate.
- To enable OpenAI improvements, set the `OPENAI_API_KEY` env var and install `openai`.
  To enable OpenAI improvements, set the `OPENAI_API_KEY` env var and install `openai`.

  You can provide the OpenAI API key in three ways (in order of precedence):

  1. CLI flag (highest precedence):
	  ```bash
	  python3 run.py --config config.json --use-llm --openai-api-key "sk-..."
	  ```

  2. `config.json` (not recommended for public repos):
	  ```json
		 "openai_api_key": "sk-..."
	  ```

  3. Environment variable (recommended for safety):
	  ```bash
	  export OPENAI_API_KEY="sk-..."
	  ```

  The `run.py` loader uses the CLI flag first, then the `config.json` field, then the environment variable. Use your CI provider's secret storage for production runs (do not commit keys to source control).

Example (dry-run, no LLM):
```bash
python3 run.py --config config.json --dry-run --tts-backend edge-tts
```

Fetch retries & fallback behavior
- The fetcher will now try multiple sanitized URL variants and automatically retry requests when transient network/server errors are encountered.
- You can tune behaviour in `config.json` with two new fields:
	- `fetch_retries` (int) — total attempts per candidate URL (default: 3)
	- `fetch_backoff` (float) — initial backoff seconds (exponential backoff used, default: 1.0)

Example (override settings in config.json):

```json
	"fetch_retries": 5,
	"fetch_backoff": 0.5
```

If a candidate returns 404 the fetcher skips that candidate and tries the next; server errors (5xx) and network errors will be retried with exponential backoff.

Examples:

- Dry-run with local improvement (no LLM required):
```bash
python3 run.py --config config.json --dry-run --improve-text
```

- Real run using edge-tts and OpenAI LLM for textual improvement (requires edge-tts and OPENAI_API_KEY):
```bash
export OPENAI_API_KEY="sk-..."
python3 run.py --config config.json --tts-backend edge-tts --tts-voice "vi-VN-HoaiMyNeural" --improve-text --use-llm
```

Multiple stories & easy switching
--------------------------------
You can keep a separate config state for each story so the tool remembers where it left off per story.
- Set the active story by editing the top-level `"story_id"` in `config.json` and run `run.py`.
- The runner stores per-story configs in `./stories/<story_id>.json` automatically (created from your `config.json` template the first time).
- This lets you switch the `story_id` in `config.json` and the tool will load the last saved state for that story.

Example: switch to story 12345
```json
{
	"story_id": "12345"
}
```
When you run the tool, it will read and update `./stories/12345.json` so that `last_downloaded_chapter` and other story-specific settings are preserved.

Generate YouTube descriptions for every 5 chapters
-------------------------------------------------
You can generate YouTube description files (one per N-chapter group) using the helper script `gen_youtube_descriptions.py`.

```bash
python3 gen_youtube_descriptions.py --config config.json --group-size 5 --playlist "https://youtube.com/playlist?list=..."
```

This will create files in `./{story_id} - Youtube description/` such as `Tập_1_Chương_1_đến_5.txt` using our standard template.

Per-story metadata and template substitution
------------------------------------------
The generator now supports per-story metadata so the description template can be populated automatically when run for a given story.

You may add the following optional keys into the per-story config file `./stories/<story_id>.json` (these will be used when `--story-id` is set, or when `config.json`'s `story_id` points to that story):

- `author` — author name (e.g. "Trạch Trư")
- `lead` — one-line teaser/lead (shown right after chapter list)
- `synopsis` — longer synopsis used in the "GIỚI THIỆU TRUYỆN" section
- `work_title` — canonical work title (e.g. "Mục Thần Ký (Tales of Herding Gods)")
- `tags` — YouTube tags / hashtags to add at the bottom
- `narrator` — narrator credit text (e.g. "Giọng đọc Nam Minh (tts)")
- `playlist` — playlist URL to use for the "Nghe trọn bộ" link

Example per-story JSON (`./stories/38060.json`):

```json
{
	"story_id": "38060",
	"story_title": "Trận Vấn Trường Sinh",
	"author": "Trạch Trư",
	"lead": "Cùng theo chân Tần Mục khám phá bí ẩn Đại Khư và con đường trở thành Mục Thần!",
	"synopsis": "Đại Khư là đất bỏ hoang... (mô tả ngắn)",
	"work_title": "Mục Thần Ký (Tales of Herding Gods)",
	"tags": "#MucThanKy #TrachTru #TienHiep",
	"narrator": "Giọng đọc Nam Minh (tts)",
	"playlist": "https://www.youtube.com/playlist?list=PLxYgiuUshyZd..."
}
```

Usage with explicit story-id
---------------------------
You can override which story to use by supplying `--story-id` on the CLI (this will load/create `./stories/<story_id>.json` and use any metadata found there):

```bash
python3 gen_youtube_descriptions.py --config config.json --story-id 38060 --group-size 5 --playlist "https://..."
```

When no per-story metadata exists, the generator will fall back to the story name (fetched from the site, if available) and sensible defaults.

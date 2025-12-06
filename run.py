#!/usr/bin/env python3
"""Entry point for tangthuvien-crawler.

Usage:
    python3 run.py --config config.json
"""
import argparse
import sys

from crawler.config_manager import ConfigManager, StoryConfigStore
from crawler.fetcher import ChapterFetcher
from crawler.parser import HTMLParser
from crawler.converter import TextToAudioConverter
from crawler.utils import ensure_dirs, is_cli_available


def main(argv=None):
    parser = argparse.ArgumentParser(description="TangThuVien crawler & audio converter")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--dry-run", action="store_true", help="Do everything except call ttx")
    parser.add_argument("--verbose", action="store_true", help="Enable INFO logging to console for debugging")
    parser.add_argument("--openai-api-key", dest='openai_api_key', help='OpenAI API key (optional, overrides env and config)')
    parser.add_argument("--tts-backend", help="TTS backend to use (ttx|edge-tts)")
    parser.add_argument("--tts-voice", help="If using edge-tts or cloud backend, specify voice name")
    parser.add_argument("--improve-text", action='store_true', help="Improve chapter text using enhancer (local or LLM)")
    parser.add_argument("--use-llm", action='store_true', help='Use LLM (OpenAI) for improvement (requires OPENAI_API_KEY)')
    args = parser.parse_args(argv)

    config_path = args.config

    # configure logging early if requested
    import logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # global and per-story configuration
    global_cfg = ConfigManager(config_path)
    story_id = global_cfg.get('story_id')
    store = StoryConfigStore(config_path)
    story_cfg = store.load_story(story_id)

    def cfg_get(key, default=None):
        # prefer story-specific config, fallback to global config
        val = story_cfg.get(key)
        if val is None:
            val = global_cfg.get(key, default)
        return val

    base_url = cfg_get('base_url')
    chapters_api = cfg_get('chapters_api')
    last_idx = cfg_get('last_downloaded_chapter') or 0
    batch_size = cfg_get('batch_size') or 15

    text_dir = f"./{story_id} - Text"
    audio_dir = f"./{story_id} - Audio"
    ensure_dirs([text_dir, audio_dir])

    # Determine tts backend and ensure required dependency is available for non-dry-run
    tts_backend = args.tts_backend or cfg_get('tts_backend') or 'ttx'
    tts_voice = args.tts_voice or cfg_get('tts_voice')

    if not args.dry_run:
        if tts_backend == 'ttx' and not is_cli_available('ttx'):
            print("Fatal: 'ttx' command-line tool not found in PATH. Either install it or run with --dry-run.")
            sys.exit(2)
        if tts_backend == 'edge-tts':
            try:
                import edge_tts  # type: ignore
            except Exception:
                print("Fatal: 'edge-tts' Python package not available. Install with 'pip install edge-tts' or run with --dry-run.")
                sys.exit(2)

    fetcher = ChapterFetcher(chapters_api, base_url)
    # configure fetcher retries from config (allow override by config keys)
    fetch_retries = cfg_get('fetch_retries', None)
    fetch_backoff = cfg_get('fetch_backoff', None)
    if fetch_retries is not None or fetch_backoff is not None:
        fetcher.configure_retries(max_attempts=fetch_retries or 3, backoff_seconds=fetch_backoff or 1.0)
    html_parser = HTMLParser()
    converter = TextToAudioConverter(backend=tts_backend, ttx_cmd='ttx', dry_run=args.dry_run)

    # Get chapter list
    chapters = fetcher.fetch_chapter_list(story_id)
    if not chapters:
        print('No chapters found — aborting.')
        return 1

    start_idx = last_idx + 1
    end_idx = start_idx + batch_size

    # clamp
    chapters_to_process = [c for c in chapters if start_idx <= c['index'] < end_idx]

    print(f"Processing chapters {start_idx}..{end_idx-1}  — found {len(chapters_to_process)} chapters in range")

    current_success = last_idx
    for c in chapters_to_process:
        idx = c['index']
        print(f"-> #{idx}: {c['title']}  ({c['url']})")
        try:
            html = fetcher.fetch_chapter(c['url'])
            text = html_parser.parse_main_text(html)

            # Optional improvement step: keep original local copy and then improve
            if args.improve_text:
                from crawler.enhancer import improve_chapter_text
                from crawler.llm_wrapper import LLMClient

                llm_client = None
                if args.use_llm:
                    # Resolve OpenAI API key: CLI override -> config -> env
                    import os
                    openai_key = args.openai_api_key or cfg_get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
                    llm_client = LLMClient(api_key=openai_key)

                improved_text, cmap, warnings = improve_chapter_text(
                    text,
                    story_id=story_id,
                    storage_dir='.',
                    llm_client=llm_client,
                    dry_run=args.dry_run,
                )
                # Replace text with improved text for saving & TTS
                text = improved_text
            if not text.strip():
                raise RuntimeError('Parsed text is empty')

            text_path = f"{text_dir}/Chapter_{idx}.txt"
            with open(text_path, 'w', encoding='utf-8') as fh:
                fh.write(text)

            audio_path = f"{audio_dir}/Chapter_{idx}.mp3"
            converter.convert(text_path, audio_path, voice=tts_voice)

            # success
            current_success = idx
            # persist per-story state
            story_cfg.set('last_downloaded_chapter', current_success)
            story_cfg.save()
            print(f"✅ Saved text and audio for chapter {idx}")

        except Exception as err:
            print(f"⚠️  Error while processing chapter {idx}: {err}")
            print('Stopping further processing and leaving config at last successful chapter.')
            break

    print('Done — configuration saved with last_downloaded_chapter =', story_cfg.get('last_downloaded_chapter'))


if __name__ == '__main__':
    raise SystemExit(main())

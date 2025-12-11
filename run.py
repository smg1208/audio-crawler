#!/usr/bin/env python3
"""Entry point for tangthuvien-crawler.

Usage:
    python3 run.py --config config.json
"""
import argparse
import sys
import os
import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.config_manager import ConfigManager, StoryConfigStore
from crawler.fetcher import ChapterFetcher
from crawler.parser import HTMLParser
from crawler.converter import TextToAudioConverter
from crawler.utils import ensure_dirs, is_cli_available, extract_chapter_number_from_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="TangThuVien crawler & audio converter")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--dry-run", action="store_true", help="Do everything except call ttx")
    parser.add_argument("--fetch-concurrency", type=int, default=4, help="Number of concurrent chapter fetches (default: 4)")
    parser.add_argument("--tts-concurrency", type=int, default=4, help="Number of concurrent TTS syntheses (default: 4, recommended: 10-20 for google-cloud)")
    parser.add_argument("--tts-max-retries", type=int, default=3, help="Maximum number of retries for failed TTS tasks (default: 3)")
    parser.add_argument("--no-retry-failed", action='store_true', help="Disable automatic retry of failed tasks")
    parser.add_argument("--verbose", action="store_true", help="Enable INFO logging to console for debugging")
    parser.add_argument("--openai-api-key", dest='openai_api_key', help='OpenAI API key (optional, overrides env and config)')
    parser.add_argument("--tts-backend", help="TTS backend to use (ttx|edge-tts|macos|gtts|fpt-ai|piper|google-cloud|coqui|azure)")
    parser.add_argument("--tts-voice", help="If using edge-tts or cloud backend, specify voice name")
    parser.add_argument("--fpt-api-key", help="FPT.AI API key (required if using fpt-ai backend)")
    parser.add_argument("--piper-model-path", help="Path to Piper TTS model .onnx file (required if using piper backend)")
    parser.add_argument("--piper-config-path", help="Path to Piper TTS config .json file (optional)")
    parser.add_argument("--google-cloud-credentials", help="Path to Google Cloud credentials JSON file (required if using google-cloud backend)")
    parser.add_argument("--google-cloud-language", help="Google Cloud TTS language code (default: vi-VN)")
    parser.add_argument("--google-cloud-voice", help="Google Cloud TTS voice name (optional)")
    parser.add_argument("--google-cloud-gender", help="Google Cloud TTS SSML gender (FEMALE|MALE|NEUTRAL)")
    parser.add_argument("--coqui-model-name", help="Coqui TTS model name (default: tts_models/multilingual/multi-dataset/xtts_v2)")
    parser.add_argument("--coqui-device", help="Coqui TTS device (cpu|cuda, default: auto-detect)")
    parser.add_argument("--coqui-speaker-wav", help="Coqui TTS speaker audio file for voice cloning (required for XTTS v2)")
    parser.add_argument("--coqui-language", help="Coqui TTS language code (default: vi)")
    parser.add_argument("--azure-subscription-key", help="Azure TTS subscription key (required if using azure backend)")
    parser.add_argument("--azure-region", help="Azure TTS region (default: eastus)")
    parser.add_argument("--azure-voice", help="Azure TTS voice name (default: vi-VN-HoaiMyNeural)")
    parser.add_argument("--improve-text", action='store_true', help="Improve chapter text using enhancer (local or LLM)")
    parser.add_argument("--use-llm", action='store_true', help='Use LLM (OpenAI) for improvement (requires OPENAI_API_KEY)')
    parser.add_argument("--recreate-audio", action='store_true', help="Recreate audio files even if they already exist")
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
    source = cfg_get('source', 'tangthuvien')  # default to tangthuvien for backward compatibility
    # last_downloaded_chapter now tracks the last successfully converted AUDIO chapter
    last_audio_idx = cfg_get('last_downloaded_chapter') or 0
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
        if tts_backend == 'gtts':
            try:
                from gtts import gTTS  # type: ignore
            except Exception:
                print("Fatal: 'gtts' Python package not available. Install with 'pip install gtts' or run with --dry-run.")
                sys.exit(2)
        if tts_backend == 'macos':
            if sys.platform != 'darwin':
                print("Fatal: 'macos' backend only works on macOS. Use another backend or run with --dry-run.")
                sys.exit(2)
            try:
                result = subprocess.run(['which', 'say'], capture_output=True, timeout=2, text=True)
                if result.returncode != 0:
                    print("Fatal: 'say' command not found. This should be available on macOS.")
                    sys.exit(2)
            except Exception as e:
                print(f"Fatal: Cannot check for 'say' command: {e}")
                sys.exit(2)
        if tts_backend == 'piper':
            try:
                from piper import PiperVoice  # type: ignore
            except Exception:
                print("Fatal: 'piper-tts' Python package not available. Install with 'pip install piper-tts' or run with --dry-run.")
                sys.exit(2)
            piper_model_path = args.piper_model_path or cfg_get('piper_model_path')
            if not piper_model_path:
                print("Fatal: Piper model path is required. Set --piper-model-path or add 'piper_model_path' to config.json")
                print("   Example: 'models/vi_VN-vivos-x_low.onnx'")
                sys.exit(2)
            if not os.path.exists(piper_model_path):
                print(f"Fatal: Piper model file not found: {piper_model_path}")
                sys.exit(2)
        if tts_backend == 'google-cloud':
            try:
                from google.cloud import texttospeech  # type: ignore
            except Exception:
                print("Fatal: 'google-cloud-texttospeech' Python package not available. Install with 'pip install google-cloud-texttospeech' or run with --dry-run.")
                sys.exit(2)
            google_cloud_credentials = args.google_cloud_credentials or cfg_get('google_cloud_credentials_path') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not google_cloud_credentials:
                print("Fatal: Google Cloud credentials are required.")
                print("   Set --google-cloud-credentials, add 'google_cloud_credentials_path' to config.json,")
                print("   or set GOOGLE_APPLICATION_CREDENTIALS environment variable")
                sys.exit(2)
            if google_cloud_credentials and not os.path.exists(google_cloud_credentials):
                print(f"Fatal: Google Cloud credentials file not found: {google_cloud_credentials}")
                sys.exit(2)
        if tts_backend == 'fpt-ai':
            try:
                import requests  # type: ignore
            except Exception:
                print("Fatal: 'requests' Python package not available. Install with 'pip install requests' or run with --dry-run.")
                sys.exit(2)
            fpt_api_key = args.fpt_api_key or cfg_get('fpt_api_key')
            if not fpt_api_key:
                print("Fatal: FPT.AI API key is required. Set --fpt-api-key or add 'fpt_api_key' to config.json")
                sys.exit(2)
        if tts_backend == 'azure':
            try:
                import azure.cognitiveservices.speech as speechsdk  # type: ignore
            except Exception:
                print("Fatal: 'azure-cognitiveservices-speech' Python package not available. Install with 'pip install azure-cognitiveservices-speech' or run with --dry-run.")
                sys.exit(2)
            azure_subscription_key = args.azure_subscription_key or cfg_get('azure_subscription_key') or os.environ.get('AZURE_SPEECH_KEY')
            if not azure_subscription_key:
                print("Fatal: Azure TTS subscription key is required.")
                print("   Set --azure-subscription-key, add 'azure_subscription_key' to config.json,")
                print("   or set AZURE_SPEECH_KEY environment variable")
                sys.exit(2)

    fetcher = ChapterFetcher(chapters_api, base_url, source=source)
    # configure fetcher retries from config (allow override by config keys)
    fetch_retries = cfg_get('fetch_retries', None)
    fetch_backoff = cfg_get('fetch_backoff', None)
    if fetch_retries is not None or fetch_backoff is not None:
        fetcher.configure_retries(max_attempts=fetch_retries or 3, backoff_seconds=fetch_backoff or 1.0)
    
    # Login to bnsach if credentials are provided
    if source == 'bnsach':
        username = cfg_get('bnsach_username')
        password = cfg_get('bnsach_password')
        if username and password:
            print(f"Logging in to bnsach.com as {username}...")
            if fetcher.login_bnsach(username, password):
                print("✓ Login successful")
            else:
                print("⚠️  Login failed - continuing anyway (may need manual login)")
        else:
            print("⚠️  No bnsach credentials found in config. bnsach.com requires login to access chapters.")
            print("   Add 'bnsach_username' and 'bnsach_password' to your config.json")
    
    html_parser = HTMLParser()
    # Get configuration for TTS engines
    fpt_api_key = None
    fpt_voice = cfg_get('fpt_voice', 'banmai')  # default: banmai (female, Northern Vietnamese)
    macos_voice = cfg_get('macos_voice', 'Linh')  # default: Linh (female Vietnamese)
    edge_rate = cfg_get('edge_rate', 1.0)  # default: 1.0
    enable_fallback = cfg_get('enable_tts_fallback', False)  # default: False
    fallback_engines = cfg_get('fallback_engines', ['macos', 'gtts'])  # default fallbacks
    piper_model_path = None
    piper_config_path = None
    
    if tts_backend == 'fpt-ai':
        fpt_api_key = args.fpt_api_key or cfg_get('fpt_api_key')
    elif tts_backend == 'piper':
        piper_model_path = args.piper_model_path or cfg_get('piper_model_path')
        piper_config_path = args.piper_config_path or cfg_get('piper_config_path')
    elif tts_backend == 'google-cloud':
        google_cloud_credentials_path = args.google_cloud_credentials or cfg_get('google_cloud_credentials_path')
        google_cloud_language_code = args.google_cloud_language or cfg_get('google_cloud_language_code', 'vi-VN')
        google_cloud_voice_name = args.google_cloud_voice or cfg_get('google_cloud_voice_name')
        google_cloud_ssml_gender = args.google_cloud_gender or cfg_get('google_cloud_ssml_gender')
    elif tts_backend == 'coqui':
        coqui_model_name = args.coqui_model_name or cfg_get('coqui_model_name', 'tts_models/multilingual/multi-dataset/xtts_v2')
        coqui_device = args.coqui_device or cfg_get('coqui_device')
        coqui_speaker_wav = args.coqui_speaker_wav or cfg_get('coqui_speaker_wav')
        coqui_language = args.coqui_language or cfg_get('coqui_language', 'vi')
    elif tts_backend == 'azure':
        azure_subscription_key = args.azure_subscription_key or cfg_get('azure_subscription_key') or os.environ.get('AZURE_SPEECH_KEY')
        azure_region = args.azure_region or cfg_get('azure_region', 'eastus')
        azure_voice_name = args.azure_voice or cfg_get('azure_voice_name', 'vi-VN-HoaiMyNeural')
    
    converter = TextToAudioConverter(
        backend=tts_backend, 
        ttx_cmd='ttx', 
        dry_run=args.dry_run,
        fpt_api_key=fpt_api_key,
        fpt_voice=fpt_voice,
        macos_voice=macos_voice,
        edge_rate=edge_rate,
        enable_fallback=enable_fallback,
        fallback_engines=fallback_engines,
        piper_model_path=piper_model_path if tts_backend == 'piper' else None,
        piper_config_path=piper_config_path if tts_backend == 'piper' else None,
        google_cloud_credentials_path=google_cloud_credentials_path if tts_backend == 'google-cloud' else None,
        google_cloud_language_code=google_cloud_language_code if tts_backend == 'google-cloud' else 'vi-VN',
        google_cloud_voice_name=google_cloud_voice_name if tts_backend == 'google-cloud' else None,
        google_cloud_ssml_gender=google_cloud_ssml_gender if tts_backend == 'google-cloud' else None,
        coqui_model_name=coqui_model_name if tts_backend == 'coqui' else None,
        coqui_device=coqui_device if tts_backend == 'coqui' else None,
        coqui_speaker_wav=coqui_speaker_wav if tts_backend == 'coqui' else None,
        coqui_language=coqui_language if tts_backend == 'coqui' else 'vi',
        azure_subscription_key=azure_subscription_key if tts_backend == 'azure' else None,
        azure_region=azure_region if tts_backend == 'azure' else 'eastus',
        azure_voice_name=azure_voice_name if tts_backend == 'azure' else 'vi-VN-HoaiMyNeural'
    )

    # Get chapter list
    chapters = fetcher.fetch_chapter_list(story_id)
    if not chapters:
        print('No chapters found — aborting.')
        return 1

    total_chapters = len(chapters)
    print(f"Found {total_chapters} total chapters")
    
    # ============================================================
    # PHASE 1: Download ALL missing text files
    # ============================================================
    print("\n" + "="*60)
    print("PHASE 1: Downloading missing text files")
    print("="*60)
    
    # Find which chapters are missing text files
    missing_text_chapters = []
    for c in chapters:
        idx = c['index']
        # Try to find existing text file by checking common patterns
        # Pattern: Chapter_{idx:04d}_display_{display_idx}.txt
        found = False
        if os.path.exists(text_dir):
            for filename in os.listdir(text_dir):
                if filename.startswith(f"Chapter_{idx:04d}_"):
                    found = True
                    break
        if not found:
            missing_text_chapters.append(c)
    
    if missing_text_chapters:
        print(f"Found {len(missing_text_chapters)} chapters missing text files")
        print(f"Downloading chapters: {missing_text_chapters[0]['index']} to {missing_text_chapters[-1]['index']}")
    else:
        print("✓ All text files already exist")
    
    # Download missing chapters
    chapters_to_download = missing_text_chapters

    # Parallel fetch of chapter texts
    fetch_conc = max(1, int(args.fetch_concurrency))
    if chapters_to_download:
        print(f"Fetching {len(chapters_to_download)} chapters with concurrency={fetch_conc}...")

    fetched = {}  # idx -> dict{text_path, display_index}
    failed = {}

    def _fetch_and_parse(chap):
        idx = chap['index']
        try:
            html = fetcher.fetch_chapter(chap['url'])
            return (idx, html, None)
        except Exception as e:
            return (idx, None, e)

    with ThreadPoolExecutor(max_workers=fetch_conc) as ex:
        futures = {ex.submit(_fetch_and_parse, c): c for c in chapters_to_download}
        for fut in as_completed(futures):
            c = futures[fut]
            idx = c['index']
            try:
                idx, html, err = fut.result()
                if err:
                    failed[idx] = err
                    print(f"⚠️  Failed to fetch chapter {idx}: {err}")
                    continue
                if not html or not html.strip():
                    failed[idx] = RuntimeError('Fetched HTML empty')
                    print(f"⚠️  Empty HTML for chapter {idx}")
                    continue
                # Parse HTML with base_url and session for bnsach decryption
                text = html_parser.parse_main_text(html, base_url=base_url, session=fetcher.session)
                if not text or not text.strip():
                    failed[idx] = RuntimeError('Parsed text empty')
                    print(f"⚠️  Empty parsed text for chapter {idx}")
                    continue
                # extract display index from content or title (prefer content)
                display_idx = extract_chapter_number_from_text(text, c.get('title'))
                display_label = display_idx or idx
                
                # Extract chapter name from chapter title
                chapter_title_raw = c.get('title', '').strip()
                chapter_name = ''
                
                # If title contains "Chương X: ...", extract the part after colon
                if ':' in chapter_title_raw:
                    parts = chapter_title_raw.split(':', 1)
                    if len(parts) == 2:
                        chapter_name = parts[1].strip()
                
                # If we still don't have a name, try to extract from first line of text
                if not chapter_name:
                    lines = text.split('\n')
                    if lines and lines[0].strip().startswith('Chương'):
                        first_line = lines[0].strip()
                        if ':' in first_line:
                            chapter_name = first_line.split(':', 1)[1].strip()
                
                # Fallback: use the raw title if available, or empty string
                if not chapter_name:
                    chapter_name = chapter_title_raw if chapter_title_raw else ''
                
                # Clean chapter name to remove translator/uploader names (e.g., "Vong Mạng")
                if chapter_name:
                    chapter_name = html_parser._clean_chapter_title(chapter_name)
                
                # Add chapter header at the beginning (only if not already present)
                # Check if text already starts with "Chương {display_label}:"
                text_starts_with_chapter = text.strip().startswith(f'Chương {display_label}:')
                if not text_starts_with_chapter:
                    chapter_header = f"Chương {display_label}: {chapter_name}\n\n" if chapter_name else f"Chương {display_label}\n\n"
                    text_with_header = chapter_header + text
                else:
                    text_with_header = text
                
                # sanitize display label for filename and include original index to avoid collisions
                safe_label = str(display_label).replace('.', '_').replace(' ', '_')
                text_path = os.path.join(text_dir, f"Chapter_{idx:04d}_display_{safe_label}.txt")
                with open(text_path, 'w', encoding='utf-8') as fh:
                    fh.write(text_with_header)
                fetched[idx] = {'text_path': text_path, 'display_index': display_label}
                print(f"Fetched and saved chapter {idx} (display {display_label}) -> {text_path}")
            except Exception as e:
                failed[idx] = e
                print(f"⚠️  Unexpected error for chapter {idx}: {e}")

    if chapters_to_download and not fetched:
        print('⚠️  No chapters fetched successfully in Phase 1.')
        if not os.listdir(text_dir):
            print('No text files exist — aborting.')
            return 1
        print('Continuing with existing text files...')
    
    # ============================================================
    # PHASE 2: Convert text to audio (starting from last_audio_idx + 1)
    # ============================================================
    print("\n" + "="*60)
    print("PHASE 2: Converting text to audio")
    print("="*60)
    
    # Find text files that need audio conversion
    # Start from last_audio_idx + 1
    start_audio_idx = last_audio_idx + 1
    end_audio_idx = start_audio_idx + batch_size - 1
    print(f"Starting audio conversion from chapter {start_audio_idx} (batch_size={batch_size}, end={end_audio_idx})")
    
    # Scan text directory to find all available text files
    text_files_by_index = {}  # idx -> {text_path, display_index}
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.startswith("Chapter_") and filename.endswith(".txt"):
                # Extract index from filename: Chapter_0001_display_1.txt
                try:
                    parts = filename.replace(".txt", "").split("_")
                    if len(parts) >= 2 and parts[0] == "Chapter":
                        idx = int(parts[1])
                        if start_audio_idx <= idx <= end_audio_idx:
                            text_path = os.path.join(text_dir, filename)
                            # Try to extract display_index from first line
                            display_idx = idx
                            try:
                                with open(text_path, 'r', encoding='utf-8') as f:
                                    first_line = f.readline().strip()
                                    if first_line.startswith('Chương') and ':' in first_line:
                                        extracted = extract_chapter_number_from_text(first_line, '')
                                        if extracted:
                                            display_idx = int(float(extracted))
                            except Exception:
                                pass
                            text_files_by_index[idx] = {
                                'text_path': text_path,
                                'display_index': display_idx
                            }
                except (ValueError, IndexError):
                    continue
    
    # Also check if we need to download any missing text files for audio conversion
    chapters_needing_text = []
    for c in chapters:
        idx = c['index']
        if start_audio_idx <= idx <= end_audio_idx and idx not in text_files_by_index:
            chapters_needing_text.append(c)
    
    if chapters_needing_text:
        print(f"⚠️  Found {len(chapters_needing_text)} chapters missing text files for audio conversion")
        print(f"Downloading missing text files: {chapters_needing_text[0]['index']} to {chapters_needing_text[-1]['index']}")
        # Download missing text files
        with ThreadPoolExecutor(max_workers=fetch_conc) as ex:
            futures = {ex.submit(_fetch_and_parse, c): c for c in chapters_needing_text}
            for fut in as_completed(futures):
                c = futures[fut]
                idx = c['index']
                try:
                    idx, html, err = fut.result()
                    if err:
                        print(f"⚠️  Failed to fetch chapter {idx}: {err}")
                        continue
                    if not html or not html.strip():
                        print(f"⚠️  Empty HTML for chapter {idx}")
                        continue
                    # Parse HTML
                    text = html_parser.parse_main_text(html, base_url=base_url, session=fetcher.session)
                    if not text or not text.strip():
                        print(f"⚠️  Empty parsed text for chapter {idx}")
                        continue
                    # Extract display index and chapter name
                    display_idx = extract_chapter_number_from_text(text, c.get('title'))
                    display_label = display_idx or idx
                    
                    chapter_title_raw = c.get('title', '').strip()
                    chapter_name = ''
                    if ':' in chapter_title_raw:
                        parts = chapter_title_raw.split(':', 1)
                        if len(parts) == 2:
                            chapter_name = parts[1].strip()
                    if not chapter_name:
                        lines = text.split('\n')
                        if lines and lines[0].strip().startswith('Chương'):
                            first_line = lines[0].strip()
                            if ':' in first_line:
                                chapter_name = first_line.split(':', 1)[1].strip()
                    if not chapter_name:
                        chapter_name = chapter_title_raw if chapter_title_raw else ''
                    if chapter_name:
                        chapter_name = html_parser._clean_chapter_title(chapter_name)
                    
                    text_starts_with_chapter = text.strip().startswith(f'Chương {display_label}:')
                    if not text_starts_with_chapter:
                        chapter_header = f"Chương {display_label}: {chapter_name}\n\n" if chapter_name else f"Chương {display_label}\n\n"
                        text_with_header = chapter_header + text
                    else:
                        text_with_header = text
                    
                    safe_label = str(display_label).replace('.', '_').replace(' ', '_')
                    text_path = os.path.join(text_dir, f"Chapter_{idx:04d}_display_{safe_label}.txt")
                    with open(text_path, 'w', encoding='utf-8') as fh:
                        fh.write(text_with_header)
                    text_files_by_index[idx] = {'text_path': text_path, 'display_index': display_label}
                    print(f"Downloaded chapter {idx} (display {display_label}) -> {text_path}")
                except Exception as e:
                    print(f"⚠️  Unexpected error for chapter {idx}: {e}")
    
    # Prepare audio conversion tasks
    audio_tasks = []
    for idx in sorted(text_files_by_index.keys()):
        if start_audio_idx <= idx <= end_audio_idx:
            info = text_files_by_index[idx]
            text_path = info['text_path']
            display_label = info.get('display_index') or idx
            safe_label = str(display_label).replace('.', '_').replace(' ', '_')
            audio_path = os.path.join(audio_dir, f"Chapter_{idx:04d}_display_{safe_label}.mp3")
            # Check if audio already exists and is valid (non-empty)
            audio_exists = False
            if os.path.exists(audio_path):
                try:
                    audio_exists = os.path.getsize(audio_path) > 0
                except:
                    audio_exists = False
            
            if not audio_exists or args.recreate_audio:
                audio_tasks.append((idx, text_path, audio_path, display_label, tts_voice))
    
    if not audio_tasks:
        if args.recreate_audio:
            print(f"⚠️  --recreate-audio specified but no audio tasks found")
        else:
            print(f"✓ All audio files already exist and are valid (last_audio_idx={last_audio_idx})")
            print("   Use --recreate-audio to recreate existing audio files")
        print("Nothing to do.")
        return 0
    
    print(f"Found {len(audio_tasks)} chapters to convert to audio")

    # Optional improvement step (sequential to avoid LLM rate issues)
    if args.improve_text:
        from crawler.enhancer import improve_chapter_text
        from crawler.llm_wrapper import LLMClient

        llm_client = None
        if args.use_llm:
            openai_key = args.openai_api_key or cfg_get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
            llm_client = LLMClient(api_key=openai_key)

        for idx, info in sorted(fetched.items()):
            text_path = info['text_path']
            with open(text_path, 'r', encoding='utf-8') as fh:
                orig = fh.read()
            improved_text, cmap, warnings = improve_chapter_text(
                orig,
                story_id=story_id,
                storage_dir='.',
                llm_client=llm_client,
                dry_run=args.dry_run,
            )
            with open(text_path, 'w', encoding='utf-8') as fh:
                fh.write(improved_text)
            print(f"Improved chapter {idx} (display {info.get('display_index')}) text")

    # Prepare mapping CSV and TTS task list
    mapping_path = os.path.join(f"{story_id} - mapping.csv")
    # Đọc concurrency từ args hoặc config
    tts_conc = args.tts_concurrency or cfg_get('tts_concurrency', 4)
    tts_conc = max(1, int(tts_conc))
    
    # Tối ưu concurrency cho từng backend
    if tts_backend == 'edge-tts':
        # Edge TTS dễ bị rate limit, giảm concurrency xuống
        if tts_conc > 2:
            print(f"ℹ️  Edge TTS: giảm concurrency từ {tts_conc} xuống 2 (tránh rate limiting)")
            tts_conc = 2
        elif tts_conc < 1:
            tts_conc = 1
    elif tts_backend == 'google-cloud':
        # Google Cloud TTS client là thread-safe, có thể tăng concurrency lên 10-20
        if tts_conc < 10:
            print(f"ℹ️  Google Cloud TTS: tăng concurrency từ {tts_conc} lên 10 (tối ưu)")
            tts_conc = 10
        elif tts_conc > 20:
            print(f"ℹ️  Google Cloud TTS: giảm concurrency từ {tts_conc} xuống 20 (tránh rate limit)")
            tts_conc = 20
    
    # Đọc retry config từ args hoặc config file
    max_retries = args.tts_max_retries or cfg_get('tts_max_retries', 3)
    max_retries = max(1, int(max_retries))
    
    # Đọc retry_failed từ args hoặc config file
    if args.no_retry_failed:
        retry_failed = False
    else:
        retry_failed = cfg_get('tts_retry_failed', True)
    
    # Read existing mapping to preserve completed entries
    existing_mappings = {}  # idx -> row dict
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                idx = int(row['original_index'])
                existing_mappings[idx] = row
    
    # Prepare tasks for conversion
    tasks = []
    successful_audio_indices = []
    
    # Build complete mapping with all text files
    all_mappings = {}  # idx -> {original_index, display_index, text_path, audio_path, status}
    
    # Add existing mappings
    for idx, row in existing_mappings.items():
        all_mappings[idx] = {
            'original_index': row['original_index'],
            'display_index': row['display_index'],
            'text_path': row['text_path'],
            'audio_path': row['audio_path'],
            'status': row.get('status', 'completed' if os.path.exists(row.get('audio_path', '')) else 'queued')
        }
    
    # Add new tasks from text_files_by_index
    for idx, info in text_files_by_index.items():
        if idx not in all_mappings:
            display_label = info.get('display_index') or idx
            safe_label = str(display_label).replace('.', '_').replace(' ', '_')
            text_path = info['text_path']
            audio_path = os.path.join(audio_dir, f"Chapter_{idx:04d}_display_{safe_label}.mp3")
            all_mappings[idx] = {
                'original_index': str(idx),
                'display_index': str(display_label),
                'text_path': text_path,
                'audio_path': audio_path,
                'status': 'completed' if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0 else 'queued'
            }
    
    # Prepare conversion tasks (only for queued items)
    for idx, text_path, audio_path, display_label, voice in audio_tasks:
        tasks.append((text_path, audio_path, voice))
        all_mappings[idx]['status'] = 'queued'
    
    # Write complete mapping CSV
    with open(mapping_path, 'w', newline='', encoding='utf-8') as mapfh:
        writer = csv.writer(mapfh)
        writer.writerow(['original_index', 'display_index', 'text_path', 'audio_path', 'status'])
        for idx in sorted(all_mappings.keys()):
            m = all_mappings[idx]
            writer.writerow([m['original_index'], m['display_index'], m['text_path'], m['audio_path'], m['status']])
    
    print(f"Converting {len(tasks)} chapters to audio with tts_concurrency={tts_conc}...")
    
    # Track successful conversions
    # Hỗ trợ batch conversion cho tất cả TTS engines
    if tts_backend in ['edge-tts', 'macos', 'gtts', 'fpt-ai', 'piper', 'google-cloud', 'coqui', 'azure']:
        try:
            failed_tasks = converter.convert_batch(tasks, concurrency=tts_conc, max_retries=max_retries, retry_failed=retry_failed)
            if failed_tasks:
                print(f"\n⚠️  {len(failed_tasks)} tasks failed after all retries")
        except Exception as err:
            print(f"⚠️  Fatal error during batch conversion: {err}")
            # Continue to check which files were created successfully
        
        # Check which audio files were created successfully (regardless of errors)
        for idx, text_path, audio_path, display_label, voice in audio_tasks:
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                successful_audio_indices.append(idx)
                all_mappings[idx]['status'] = 'completed'
            else:
                # Mark as failed if file doesn't exist or is empty
                all_mappings[idx]['status'] = 'failed'
                print(f"⚠️  Chapter {idx} (display {display_label}) conversion failed or incomplete")
    else:
        # Sequential conversion for non-edge-tts backends
        for idx, text_path, audio_path, display_label, voice in audio_tasks:
            try:
                converter.convert(text_path, audio_path, voice=voice)
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    successful_audio_indices.append(idx)
                    all_mappings[idx]['status'] = 'completed'
            except Exception as err:
                print(f"⚠️  Error converting chapter {idx}: {err}")
                all_mappings[idx]['status'] = 'failed'
    
    # Update mapping CSV with final statuses
    with open(mapping_path, 'w', newline='', encoding='utf-8') as mapfh:
        writer = csv.writer(mapfh)
        writer.writerow(['original_index', 'display_index', 'text_path', 'audio_path', 'status'])
        for idx in sorted(all_mappings.keys()):
            m = all_mappings[idx]
            writer.writerow([m['original_index'], m['display_index'], m['text_path'], m['audio_path'], m['status']])

    # Update last_downloaded_chapter based on successfully converted AUDIO (not text)
    if successful_audio_indices:
        current_success = max(successful_audio_indices)
        story_cfg.set('last_downloaded_chapter', current_success)
        story_cfg.save()
        print(f"\n✓ Done — configuration saved with last_downloaded_chapter = {current_success} (audio)")
        print(f"  Successfully converted {len(successful_audio_indices)} audio files")
    else:
        print(f"\n⚠️  No audio files were successfully converted")
        if last_audio_idx > 0:
            print(f"  last_downloaded_chapter remains at {last_audio_idx}")


if __name__ == '__main__':
    raise SystemExit(main())

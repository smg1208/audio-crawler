#!/usr/bin/env python3
"""Generate YouTube descriptions for a story in groups of N chapters.

Creates files in the folder './{story_id} - Youtube description/' with one description per N chapters.

Usage:
    python3 gen_youtube_descriptions.py --config config.json --group-size 5
    python3 gen_youtube_descriptions.py --config config.json --group-size 20 --start-chapter 100 --num-episodes 5

The script uses ChapterFetcher to get the chapter list and the parser as fallback to extract a short
summary for chapters that don't have a readable title.
"""
import argparse
import os
import textwrap
from typing import List, Optional
from crawler.utils import extract_chapter_number_from_text

from crawler.config_manager import ConfigManager, StoryConfigStore
from crawler.fetcher import ChapterFetcher
from crawler.parser import HTMLParser
from crawler.utils import ensure_dirs


def chunk_list(lst: List, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def short_summary_from_html(html: str) -> str:
    p = HTMLParser()
    text = p.parse_main_text(html)
    # take first non-empty paragraph or first 120 chars
    for para in text.split('\n\n'):
        s = para.strip()
        if len(s) > 20:
            return s if len(s) <= 160 else s[:157].rstrip() + '...'
    return text[:160].rstrip() + '...'





def make_description(
    story_title: str,
    group_index: int,
    chapters: List[dict],
    playlist_link: str = '[Link_Playlist_Của_Bạn]',
    metadata: Optional[dict] = None,
    start_episode: int = 1,
    source_label: str = 'tangthuvien.net',
) -> str:
    # chapters is a list of dicts with keys: index, title, url
    # chapters may carry a 'display_index' (extracted from content) to reflect real numbering
    start_idx = chapters[0].get('display_index', chapters[0].get('index'))
    end_idx = chapters[-1].get('display_index', chapters[-1].get('index'))
    # allow caller to offset episode numbering (start_episode = 1 means first group -> episode 1)
    try:
        episode_base = int(start_episode or 1)
    except Exception:
        episode_base = 1
    episode_number = episode_base + (group_index - 1)

    # metadata may supply keys: author, lead, synopsis, work_title, tags, narrator
    if metadata is None:
        metadata = {}
    author = metadata.get('author', 'Trạch Trư')
    lead = metadata.get('lead', 'Cùng theo chân Tần Mục khám phá bí ẩn Đại Khư và con đường trở thành Mục Thần!')
    synopsis = metadata.get('synopsis', 'Đại Khư là đất bỏ hoang của chư thần, nơi bóng tối là tử địa. Tần Mục, một đứa trẻ được nhặt về nuôi bởi những "quái nhân" ở Tàn Lão Thôn, mang trong mình trọng trách chăn dắt chư thần. Một tác phẩm Tiên hiệp hài hước, bi tráng và đầy triết lý nhân sinh của "Heo Trạch" (Trạch Trư).')
    work_title = metadata.get('work_title', f'{story_title}')
    tags = metadata.get('tags', '#MucThanKy #TrachTru #TienHiep #AudioTruyen #DocTruyenDemKhuya')
    narrator = metadata.get('narrator', 'Giọng đọc Nam Minh (tts)')

    # Prefer work_title/story_title from metadata for display
    display_work_title = metadata.get('work_title') or metadata.get('story_title') or story_title

    header = f"🎧 {display_work_title} - Tập {episode_number} (Chương {start_idx} đến {end_idx}) | Tác giả: {author}"

    lines = [header, '👉 Đăng ký kênh để không bỏ lỡ chương mới nhất: https://www.youtube.com/@nghebangtai6875', '', '📜 NỘI DUNG TẬP NÀY:']

    # Create parser instance for cleaning chapter titles
    parser = HTMLParser()
    
    for ch in chapters:
        # Prefer display_index (from content) for human-facing numbering
        cidx = ch.get('display_index', ch.get('index'))
        title = ch.get('title') or ''
        short = ch.get('summary') or title
        # if title contains a colon, prefer the trailing descriptive part
        if not short or len(short) < 4:
            if ':' in title:
                parts = title.split(':', 1)
                short = parts[1].strip()
        # final fallback: use provided title
        if not short or len(short) < 2:
            short = title
        
        # Clean chapter title to remove translator/uploader names (e.g., "Vong Mạng")
        if short:
            short = parser._clean_chapter_title(short)
            # If still starts with "Chương X: ..." strip the leading prefix to avoid duplication
            if short.lower().startswith('chương'):
                parts2 = short.split(':', 1)
                if len(parts2) == 2:
                    short = parts2[1].strip()

        lines.append(f"- Chương {cidx}: {short}")

    lines += ['', lead, '', '📖 GIỚI THIỆU TRUYỆN ' + display_work_title + ':', synopsis, '', '🔗 DANH SÁCH PHÁT (PLAYLIST) TRỌN BỘ:', f'▶️ Nghe trọn bộ {display_work_title} tại đây: {playlist_link}', '', '---------------------------------------------------', '⚠️ BẢN QUYỀN & TÁC GIẢ:', f'- Tác phẩm: {display_work_title}', f'- Tác giả: {author}', f'- Nguồn dịch: {source_label}', f'- Giọng đọc: {narrator}', '- Hình ảnh & Video: Được biên tập bởi NGHE BẰNG TAI', '(Mọi vấn đề về bản quyền xin liên hệ: reading.ttv@gmail.com)', '', tags]

    return '\n'.join(lines)


def load_chapters_from_files(story_id: str) -> List[dict]:
    """Load chapters from mapping.csv and text files instead of fetching from server.
    
    If mapping.csv exists, uses it. Otherwise, or to supplement missing chapters,
    scans the Text directory directly for chapter files.
    
    Returns a list of chapter dicts with keys: index, display_index, title, url, summary
    """
    import csv
    import os
    import re
    import glob
    
    mapping_path = f"./{story_id} - mapping.csv"
    text_dir = f"./{story_id} - Text"
    
    chapters = []
    chapters_by_path = {}  # Track chapters by text_path to avoid duplicates
    parser = HTMLParser()
    
    # First, try to load from mapping.csv if it exists
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    idx = int(row['original_index'])
                    display_idx = int(row['display_index']) if row['display_index'] else idx
                    text_path = row['text_path']
                    
                    # Normalize path (handle relative paths)
                    if not os.path.isabs(text_path):
                        text_path = os.path.normpath(text_path)
                    
                    # Read title from first line of text file
                    title = f"Chương {display_idx}"
                    summary = ""
                    
                    if os.path.exists(text_path):
                        with open(text_path, 'r', encoding='utf-8') as tf:
                            first_line = tf.readline().strip()
                            if first_line.startswith('Chương') and ':' in first_line:
                                # Extract title from "Chương X: Title"
                                parts = first_line.split(':', 1)
                                if len(parts) == 2:
                                    title = first_line
                                    summary = parts[1].strip()
                                    # Clean summary
                                    if summary:
                                        summary = parser._clean_chapter_title(summary)
                            else:
                                # If no title in first line, use first few lines as summary
                                tf.seek(0)
                                lines = [l.strip() for l in tf.readlines()[:3] if l.strip()]
                                if lines:
                                    summary = ' '.join(lines[:2])[:160]
                    
                    chapter_data = {
                        'index': idx,
                        'display_index': display_idx,
                        'title': title,
                        'url': '',  # Not needed when loading from files
                        'summary': summary or title,
                        'text_path': text_path
                    }
                    chapters.append(chapter_data)
                    chapters_by_path[text_path] = chapter_data
                except (ValueError, KeyError) as e:
                    continue
    
    # Also scan Text directory for any chapter files not in mapping.csv
    if os.path.exists(text_dir):
        # Pattern: Chapter_XXXX_display_YYYY.txt
        pattern = re.compile(r'Chapter_(\d+)_display_(\d+)\.txt')
        text_files = glob.glob(os.path.join(text_dir, 'Chapter_*.txt'))
        
        for text_file in text_files:
            text_file_norm = os.path.normpath(text_file)
            # Skip if already loaded from mapping.csv
            if text_file_norm in chapters_by_path:
                continue
            
            filename = os.path.basename(text_file)
            match = pattern.match(filename)
            if match:
                try:
                    original_idx = int(match.group(1))
                    display_idx = int(match.group(2))
                    
                    # Read title from first line of text file
                    title = f"Chương {display_idx}"
                    summary = ""
                    
                    try:
                        with open(text_file, 'r', encoding='utf-8') as tf:
                            first_line = tf.readline().strip()
                            if first_line.startswith('Chương') and ':' in first_line:
                                parts = first_line.split(':', 1)
                                if len(parts) == 2:
                                    title = first_line
                                    summary = parts[1].strip()
                                    if summary:
                                        summary = parser._clean_chapter_title(summary)
                            else:
                                tf.seek(0)
                                lines = [l.strip() for l in tf.readlines()[:3] if l.strip()]
                                if lines:
                                    summary = ' '.join(lines[:2])[:160]
                    except Exception:
                        pass
                    
                    chapter_data = {
                        'index': original_idx,
                        'display_index': display_idx,
                        'title': title,
                        'url': '',
                        'summary': summary or title,
                        'text_path': text_file_norm
                    }
                    chapters.append(chapter_data)
                    chapters_by_path[text_file_norm] = chapter_data
                except (ValueError, IndexError):
                    continue
    
    return sorted(chapters, key=lambda x: x['index'])


def write_descriptions(cfg: ConfigManager, group_size: int = 5, out_playist: str = '[Link_Playlist_Của_Bạn]', story_id: Optional[str] = None, fast: bool = False, start_episode: int = 1, use_files: bool = False, num_episodes: Optional[int] = None) -> int:
    # optional start chapter index (None means from beginning)
    start_chapter = None
    # accept either a ConfigManager or StoryConfigStore
    if hasattr(cfg, 'global_cfg'):
        global_cfg = cfg.global_cfg
    else:
        global_cfg = cfg

    story_id = story_id or global_cfg.get('story_id')
    base_url = global_cfg.get('base_url')
    chapters_api = global_cfg.get('chapters_api')
    source = global_cfg.get('source', 'tangthuvien')  # default to tangthuvien for backward compatibility
    source_label = source
    try:
        from urllib.parse import urlparse
        if base_url:
            host = urlparse(base_url).netloc or ''
            if host:
                source_label = host
    except Exception:
        pass

    # Try to load from files first if use_files is True, or if fetch fails
    chapters = []
    if use_files:
        print(f"Loading chapters from mapping.csv and text files for {story_id}...")
        chapters = load_chapters_from_files(story_id)
        if chapters:
            print(f"✓ Loaded {len(chapters)} chapters from files")
        else:
            print("⚠️  No chapters found in files, trying to fetch from server...")
    
    # If not loaded from files, try fetching from server
    if not chapters:
        fetcher = ChapterFetcher(chapters_api, base_url, source=source)
        
        # Login to bnsach if credentials are provided
        if source == 'bnsach':
            username = global_cfg.get('bnsach_username')
            password = global_cfg.get('bnsach_password')
            if username and password:
                print(f"Logging in to bnsach.com as {username}...")
                try:
                    if fetcher.login_bnsach(username, password):
                        print("✓ Login successful")
                    else:
                        print("⚠️  Login failed - continuing anyway (may need manual login)")
                except Exception as e:
                    print(f"⚠️  Login error: {e}")
                    print("   Trying to load from files instead...")
                    chapters = load_chapters_from_files(story_id)
                    if chapters:
                        print(f"✓ Loaded {len(chapters)} chapters from files")
                    else:
                        print("No chapters found in files either. Aborting.")
                        return 0
            else:
                print("⚠️  No bnsach credentials found in config. Trying to load from files...")
                chapters = load_chapters_from_files(story_id)
                if chapters:
                    print(f"✓ Loaded {len(chapters)} chapters from files")
                else:
                    print("No chapters found in files. Aborting.")
                    return 0
        
        if not chapters:
            try:
                chapters = fetcher.fetch_chapter_list(story_id)
            except Exception as e:
                print(f"⚠️  Failed to fetch chapters from server: {e}")
                print("   Trying to load from files instead...")
                chapters = load_chapters_from_files(story_id)
                if chapters:
                    print(f"✓ Loaded {len(chapters)} chapters from files")
                else:
                    print("No chapters found in files either. Aborting.")
                    return 0
    
    if not chapters:
        print('No chapters found')
        return 0

    # If the global config or CLI provided a starting chapter, filter chapters.
    # Allow callers to set 'start_chapter' on the cfg object (optional) or
    # rely on external filtering prior to calling this function. If present, it
    # should be an integer index.
    try:
        sc = getattr(cfg, 'start_chapter', None) or cfg.get('start_chapter')
        if sc:
            try:
                start_chapter = int(sc)
            except Exception:
                start_chapter = None
    except Exception:
        start_chapter = None

    if start_chapter is not None:
        chapters = [c for c in chapters if c.get('index', 0) >= start_chapter]

    # determine story title from first chapter if available
    story_title = None
    try:
        first_html = fetcher.fetch_chapter(chapters[0]['url'])
        parser = HTMLParser()
        # try to extract h1.truyen-title
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(first_html, 'html.parser')
        h1 = soup.select_one('h1.truyen-title')
        if h1:
            story_title = h1.get_text().strip()
    except Exception:
        pass

    if not story_title:
        story_title = global_cfg.get('story_title') or f'Story {story_id}'

    # if per-story metadata exists, prefer it
    metadata = {}
    try:
        # if cfg is a StoryConfigStore (store), allow it to load per-story; if not, story-specific entries may already be present
        if hasattr(cfg, 'load_story'):
            story_cfg = cfg.load_story(story_id)
            for k in ('author', 'lead', 'synopsis', 'work_title', 'tags', 'narrator', 'story_title', 'playlist'):
                v = story_cfg.get(k)
                if v:
                    metadata[k] = v
        else:
            # check if the global config already contains per-story keys
            for k in ('author', 'lead', 'synopsis', 'work_title', 'tags', 'narrator', 'story_title', 'playlist'):
                v = global_cfg.get(k)
                if v:
                    metadata[k] = v
    except Exception:
        pass

    out_dir = f"./{story_id} - Youtube description"
    ensure_dirs([out_dir])

    # Calculate and display how many episodes can be created
    total_chapters_available = len(chapters)
    possible_episodes = (total_chapters_available + group_size - 1) // group_size  # Ceiling division
    if num_episodes is not None:
        if num_episodes > possible_episodes:
            print(f"⚠️  Yêu cầu {num_episodes} episodes, nhưng chỉ có thể tạo {possible_episodes} episodes từ {total_chapters_available} chương (group-size={group_size})")
            print(f"   Sẽ tạo {possible_episodes} episodes.")
        else:
            print(f"📝 Sẽ tạo {num_episodes} episodes từ {total_chapters_available} chương (group-size={group_size})")
    else:
        print(f"📝 Sẽ tạo {possible_episodes} episodes từ {total_chapters_available} chương (group-size={group_size})")

    count = 0
    # Enrich each chapter with display index and summary.
    # If `fast` is True, avoid fetching HTML and rely on chapter list titles only.
    parser = HTMLParser()
    for ch in chapters:
        title = ch.get('title') or ''
        # Try to extract display index from title first (fast path)
        display_idx = extract_chapter_number_from_text('', title)
        if display_idx:
            ch['display_index'] = display_idx
        else:
            ch['display_index'] = ch.get('index')

        # Summary: if fast, derive from title (strip leading 'Chương X:'), otherwise fetch HTML for better summary
        if fast:
            short = title
            if ':' in title:
                parts = title.split(':', 1)
                short = parts[1].strip()
            # Clean chapter title to remove translator/uploader names
            if short:
                short = parser._clean_chapter_title(short)
            ch['summary'] = short or title
        else:
            try:
                html = fetcher.fetch_chapter(ch['url'])
                main_text = parser.parse_main_text(html)
                summary = short_summary_from_html(html)
                # Clean chapter title to remove translator/uploader names
                if summary:
                    summary = parser._clean_chapter_title(summary)
                ch['summary'] = summary
                # also try to extract display index from content if available
                display_idx2 = extract_chapter_number_from_text(main_text, title)
                if display_idx2:
                    ch['display_index'] = display_idx2
            except Exception:
                # Clean title even in exception case
                cleaned_title = parser._clean_chapter_title(title) if title else ''
                ch['summary'] = cleaned_title

    for i, group in enumerate(chunk_list(chapters, group_size), start=1):
        # Limit number of episodes if specified
        if num_episodes is not None and count >= num_episodes:
            break
        desc = make_description(story_title, i, group, playlist_link=out_playist, metadata=metadata, start_episode=start_episode, source_label=source_label)
        # use display indices for filename where possible
        start_disp = group[0].get('display_index', group[0].get('index'))
        end_disp = group[-1].get('display_index', group[-1].get('index'))
        filename = f"{out_dir}/Tập_{i}_Chương_{start_disp}_đến_{end_disp}.txt"
        with open(filename, 'w', encoding='utf-8') as fh:
            fh.write(desc)
        count += 1

    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate YouTube descriptions per N chapters')
    parser.add_argument('--config', required=True, help='path to config.json')
    parser.add_argument('--group-size', type=int, default=5, help='number of chapters per description')
    parser.add_argument('--playlist', default='[Link_Playlist_Của_Bạn]', help='playlist link text')
    parser.add_argument('--story-id', default=None, help='override story_id and use per-story metadata')
    parser.add_argument('--start-chapter', type=int, default=None, help='start generating descriptions from this chapter index')
    parser.add_argument('--num-episodes', type=int, default=None, help='number of episodes to generate (default: all available chapters)')
    parser.add_argument('--fast', action='store_true', help='Use chapter list titles/numbers only and avoid fetching full chapter HTML (faster)')
    parser.add_argument('--start-episode', type=int, default=1, help='Episode number to assign to the first generated group (default: 1)')
    parser.add_argument('--use-files', action='store_true', help='Load chapters from mapping.csv and text files instead of fetching from server')
    args = parser.parse_args(argv)

    # Use StoryConfigStore so per-story files are available for metadata
    store = StoryConfigStore(args.config)
    # allow explicit override of story id
    story_id = args.story_id if hasattr(args, 'story_id') and args.story_id else store.global_cfg.get('story_id')
    cfg = store.global_cfg
    # pass start_chapter into the store object if provided so write_descriptions can pick it up
    if args.start_chapter is not None:
        try:
            setattr(store, 'start_chapter', int(args.start_chapter))
        except Exception:
            pass
    n = write_descriptions(store, group_size=args.group_size, out_playist=args.playlist, story_id=story_id, fast=args.fast, start_episode=args.start_episode, use_files=args.use_files, num_episodes=args.num_episodes)
    print(f'Wrote {n} descriptions into ./{story_id} - Youtube description')


if __name__ == '__main__':
    main()

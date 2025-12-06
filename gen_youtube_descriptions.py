#!/usr/bin/env python3
"""Generate YouTube descriptions for a story in groups of N chapters.

Creates files in the folder './{story_id} - Youtube description/' with one description per N chapters.

Usage:
    python3 gen_youtube_descriptions.py --config config.json --group-size 5

The script uses ChapterFetcher to get the chapter list and the parser as fallback to extract a short
summary for chapters that don't have a readable title.
"""
import argparse
import os
import textwrap
from typing import List, Optional

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
) -> str:
    # chapters is a list of dicts with keys: index, title, url
    start_idx = chapters[0]['index']
    end_idx = chapters[-1]['index']
    episode_number = group_index

    # metadata may supply keys: author, lead, synopsis, work_title, tags, narrator
    if metadata is None:
        metadata = {}
    author = metadata.get('author', 'Trạch Trư')
    lead = metadata.get('lead', 'Cùng theo chân Tần Mục khám phá bí ẩn Đại Khư và con đường trở thành Mục Thần!')
    synopsis = metadata.get('synopsis', 'Đại Khư là đất bỏ hoang của chư thần, nơi bóng tối là tử địa. Tần Mục, một đứa trẻ được nhặt về nuôi bởi những "quái nhân" ở Tàn Lão Thôn, mang trong mình trọng trách chăn dắt chư thần. Một tác phẩm Tiên hiệp hài hước, bi tráng và đầy triết lý nhân sinh của "Heo Trạch" (Trạch Trư).')
    work_title = metadata.get('work_title', f'{story_title}')
    tags = metadata.get('tags', '#MucThanKy #TrachTru #TienHiep #AudioTruyen #DocTruyenDemKhuya')
    narrator = metadata.get('narrator', 'Giọng đọc Nam Minh (tts)')

    header = f"🎧 {story_title} - Tập {episode_number} (Chương {start_idx} đến {end_idx}) | Tác giả: {author}"

    lines = [header, '👉 Đăng ký kênh để không bỏ lỡ chương mới nhất: https://www.youtube.com/@nghebangtai6875', '', '📜 NỘI DUNG TẬP NÀY:']

    for ch in chapters:
        cidx = ch.get('index')
        title = ch.get('title') or ''
        # clean title: remove leading 'Chương X' if present, keep descriptive part
        short = title
        if ':' in title:
            parts = title.split(':', 1)
            short = parts[1].strip()
        # If still not helpful, fetch and summarize
        if not short or len(short) < 4:
            try:
                html = ChapterFetcher('', '').fetch_chapter(ch['url'])
                short = short_summary_from_html(html).split('\n')[0]
            except Exception:
                short = title

        lines.append(f"- Chương {cidx}: {short}")

    lines += ['', lead, '', '📖 GIỚI THIỆU TRUYỆN ' + work_title + ':', synopsis, '', '🔗 DANH SÁCH PHÁT (PLAYLIST) TRỌN BỘ:', f'▶️ Nghe trọn bộ {story_title} tại đây: {playlist_link}', '', '---------------------------------------------------', '⚠️ BẢN QUYỀN & TÁC GIẢ:', f'- Tác phẩm: {work_title}', f'- Tác giả: {author}', '- Nguồn dịch: tangthuvien.net', f'- Giọng đọc: {narrator}', '- Hình ảnh & Video: Được biên tập bởi NGHE BẰNG TAI', '(Mọi vấn đề về bản quyền xin liên hệ: reading.ttv@gmail.com)', '', tags]

    return '\n'.join(lines)


def write_descriptions(cfg: ConfigManager, group_size: int = 5, out_playist: str = '[Link_Playlist_Của_Bạn]', story_id: Optional[str] = None) -> int:
    # accept either a ConfigManager or StoryConfigStore
    if hasattr(cfg, 'global_cfg'):
        global_cfg = cfg.global_cfg
    else:
        global_cfg = cfg

    story_id = story_id or global_cfg.get('story_id')
    base_url = global_cfg.get('base_url')
    chapters_api = global_cfg.get('chapters_api')

    fetcher = ChapterFetcher(chapters_api, base_url)
    chapters = fetcher.fetch_chapter_list(story_id)
    if not chapters:
        print('No chapters found')
        return 0

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
        story_title = cfg.get('story_title') or f'Story {story_id}'

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

    count = 0
    for i, group in enumerate(chunk_list(chapters, group_size), start=1):
        desc = make_description(story_title, i, group, playlist_link=out_playist, metadata=metadata)
        filename = f"{out_dir}/Tập_{i}_Chương_{group[0]['index']}_đến_{group[-1]['index']}.txt"
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
    args = parser.parse_args(argv)

    # Use StoryConfigStore so per-story files are available for metadata
    store = StoryConfigStore(args.config)
    # allow explicit override of story id
    story_id = args.story_id if hasattr(args, 'story_id') and args.story_id else store.global_cfg.get('story_id')
    cfg = store.global_cfg
    n = write_descriptions(store, group_size=args.group_size, out_playist=args.playlist, story_id=story_id)
    print(f'Wrote {n} descriptions into ./{story_id} - Youtube description')


if __name__ == '__main__':
    main()

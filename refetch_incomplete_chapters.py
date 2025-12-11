#!/usr/bin/env python3
"""Script to identify and re-fetch chapters that might be missing content.

This script:
1. Scans all chapter text files
2. Identifies chapters that seem too short compared to neighbors
3. Re-fetches and re-parses them with the improved parser
"""

import sys
import os
import json
import glob
from pathlib import Path

# Add crawler to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.fetcher import ChapterFetcher
from crawler.parser import HTMLParser
from crawler.utils import extract_chapter_number_from_text

def get_chapter_files(story_id):
    """Get all chapter text files sorted by index."""
    text_dir = f"./{story_id} - Text"
    if not os.path.exists(text_dir):
        return []
    
    files = []
    for filename in glob.glob(os.path.join(text_dir, "Chapter_*.txt")):
        # Extract index from filename: Chapter_0414_display_414.txt
        try:
            basename = os.path.basename(filename)
            # Remove .txt extension
            name_without_ext = basename.replace(".txt", "")
            # Split by underscore
            parts = name_without_ext.split("_")
            if len(parts) >= 2 and parts[0] == "Chapter":
                idx = int(parts[1])
                files.append((idx, filename))
        except (ValueError, IndexError) as e:
            # Skip files that don't match the pattern
            continue
    
    return sorted(files, key=lambda x: x[0])

def analyze_chapter_lengths(story_id):
    """Analyze chapter lengths to find potentially incomplete ones."""
    files = get_chapter_files(story_id)
    
    if len(files) < 3:
        print("Not enough chapters to analyze")
        return []
    
    # Calculate average length and identify outliers
    lengths = []
    for idx, filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Count non-empty lines
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                lengths.append((idx, len(lines), len(content)))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue
    
    if not lengths:
        return []
    
    # Calculate statistics
    line_counts = [l[1] for l in lengths]
    avg_lines = sum(line_counts) / len(line_counts)
    median_lines = sorted(line_counts)[len(line_counts) // 2]
    
    print(f"\nChapter length statistics:")
    print(f"  Total chapters: {len(lengths)}")
    print(f"  Average lines: {avg_lines:.1f}")
    print(f"  Median lines: {median_lines}")
    
    # Find chapters that are significantly shorter than neighbors
    # A chapter is suspicious if:
    # 1. It's < 40% of average (very short)
    # OR
    # 2. It's < 50% of average AND < 50% of its neighbors (both conditions)
    suspicious = []
    for i, (idx, line_count, char_count) in enumerate(lengths):
        is_suspicious = False
        
        # Very short compared to average
        if line_count < avg_lines * 0.4:
            is_suspicious = True
        
        # Moderately short but also much shorter than neighbors
        elif line_count < avg_lines * 0.5:
            if i > 0 and i < len(lengths) - 1:
                prev_lines = lengths[i-1][1]
                next_lines = lengths[i+1][1]
                neighbor_avg = (prev_lines + next_lines) / 2
                
                # Must be significantly shorter than neighbors too
                if line_count < neighbor_avg * 0.5 and neighbor_avg > 80:
                    is_suspicious = True
        
        # Also flag extremely short chapters (< 30 lines) regardless
        if line_count < 30 and line_count < avg_lines * 0.3:
            is_suspicious = True
        
        if is_suspicious:
            suspicious.append((idx, line_count, char_count))
    
    return suspicious

def refetch_chapter(story_id, chapter_idx, config):
    """Re-fetch a single chapter."""
    base_url = config['base_url']
    chapters_api = config['chapters_api']
    source = config.get('source', 'tangthuvien')
    
    fetcher = ChapterFetcher(chapters_api, base_url, source=source)
    
    # Login if needed
    if source == 'bnsach':
        username = config.get('bnsach_username')
        password = config.get('bnsach_password')
        if username and password:
            fetcher.login_bnsach(username, password)
    
    # Get chapter list
    chapters = fetcher.fetch_chapter_list(story_id)
    chapter = None
    for chap in chapters:
        if chap['index'] == chapter_idx:
            chapter = chap
            break
    
    if not chapter:
        print(f"  ❌ Chapter {chapter_idx} not found in chapter list")
        return False
    
    # Fetch and parse
    try:
        html = fetcher.fetch_chapter(chapter['url'])
        parser = HTMLParser()
        text = parser.parse_main_text(html, base_url=base_url, session=fetcher.session)
        
        if not text or not text.strip():
            print(f"  ❌ Parsed text is empty")
            return False
        
        # Extract display index and chapter name
        display_idx = extract_chapter_number_from_text(text, chapter.get('title'))
        display_label = display_idx or chapter_idx
        
        chapter_title_raw = chapter.get('title', '').strip()
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
            chapter_name = parser._clean_chapter_title(chapter_name)
        
        # Add chapter header
        text_starts_with_chapter = text.strip().startswith(f'Chương {display_label}:')
        if not text_starts_with_chapter:
            chapter_header = f"Chương {display_label}: {chapter_name}\n\n" if chapter_name else f"Chương {display_label}\n\n"
            text_with_header = chapter_header + text
        else:
            text_with_header = text
        
        # Save
        text_dir = f"./{story_id} - Text"
        os.makedirs(text_dir, exist_ok=True)
        
        safe_label = str(display_label).replace('.', '_').replace(' ', '_')
        text_path = os.path.join(text_dir, f"Chapter_{chapter_idx:04d}_display_{safe_label}.txt")
        
        with open(text_path, 'w', encoding='utf-8') as fh:
            fh.write(text_with_header)
        
        new_lines = len([l for l in text_with_header.splitlines() if l.strip()])
        new_chars = len(text_with_header)
        
        print(f"  ✓ Re-fetched: {new_lines} lines, {new_chars} chars")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    # Load config
    story_id = "38060"
    config_path = "stories/38060.json"
    
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Analyzing chapters for story {story_id}...")
    
    # Find suspicious chapters
    suspicious = analyze_chapter_lengths(story_id)
    
    if not suspicious:
        print("\n✓ No suspicious chapters found. All chapters seem complete.")
        return
    
    print(f"\n⚠️  Found {len(suspicious)} potentially incomplete chapters:")
    for idx, lines, chars in suspicious:
        print(f"  Chapter {idx}: {lines} lines, {chars} chars")
    
    # Ask for confirmation
    print(f"\nRe-fetch these chapters with improved parser? (y/n): ", end='')
    response = input().strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return
    
    # Re-fetch each suspicious chapter
    print("\nRe-fetching chapters...")
    success_count = 0
    for idx, lines, chars in suspicious:
        print(f"\nChapter {idx} (was {lines} lines):")
        if refetch_chapter(story_id, idx, config):
            success_count += 1
    
    print(f"\n✓ Re-fetched {success_count}/{len(suspicious)} chapters successfully")

if __name__ == '__main__':
    main()


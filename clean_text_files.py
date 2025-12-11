#!/usr/bin/env python3
"""Script để clean up các file text đã tải về, loại bỏ duplicate title và footer content."""

import os
import re
from pathlib import Path


def normalize_chapter_title(line: str) -> str:
    """Normalize chapter title: remove spaces before colon."""
    # "Chương 405 : xxx" -> "Chương 405: xxx"
    line = re.sub(r'(Chương\s+\d+)\s*:\s*', r'\1: ', line, flags=re.IGNORECASE)
    line = re.sub(r'(Chương\s+\d+)\s*：\s*', r'\1: ', line, flags=re.IGNORECASE)
    return line


def normalize_for_compare(s: str) -> str:
    """Normalize string for comparison (remove spaces, punctuation)."""
    s = s.lower().strip()
    s = re.sub(r'\s*:\s*', ':', s)
    s = re.sub(r'\s*：\s*', ':', s)
    s = re.sub(r"[^\w\sàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ-]", '', s)
    s = re.sub(r"\s+", ' ', s)
    return s


def extract_chapter_title_name(line: str) -> str:
    """
    Extract chapter title name from a line like "Chương 1002: "Thái tử gia"".
    Returns normalized title name (without the leading "Chương X:" part).
    For titles like "Chương 1009: 1007 nâng đỡ", extracts "1007 nâng đỡ".
    For titles like "Chương 1007 nâng đỡ", extracts "nâng đỡ" (the number is part of chapter number).
    """
    # Match pattern: "Chương 1002: "Thái tử gia"" or "Chương 1001 "Thái tử gia""
    # or "Chương 1008: 1006 thắng bại" or "Chương 1006 thắng bại"
    match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', line, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Remove quotes if present (only if entire title is quoted)
        if (title.startswith('"') and title.endswith('"')) or \
           (title.startswith("'") and title.endswith("'")):
            title = title[1:-1].strip()
        
        # Check if title starts with a number (like "1007 nâng đỡ")
        # If so, this number might be part of the title content
        num_match = re.match(r'^(\d+)\s+(.+)$', title)
        if num_match:
            # Title starts with number - include it in comparison
            # This handles cases like "Chương 1009: 1007 nâng đỡ" vs "Chương 1007 nâng đỡ"
            # We compare "1007 nâng đỡ" vs "nâng đỡ" - they should match
            # But we need to check if the number matches the chapter number
            title_num = num_match.group(1)
            title_after_num = num_match.group(2)
            # For comparison, use the part after number (to catch duplicates)
            # But also check if the number itself matches
            return normalize_for_compare(title_after_num)
        
        # Normalize for comparison (lowercase, remove extra spaces)
        return normalize_for_compare(title)
    return ""


def get_chapter_number(line: str) -> int:
    """Extract chapter number from a line like "Chương 1002: xxx"."""
    match = re.match(r'^Chương\s+(\d+)', line, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return -1


def is_footer_line(line: str) -> bool:
    """Check if a line is footer content."""
    line_lower = line.lower().strip()
    
    # Footer markers
    footer_markers = [
        'hãy nhấn like', 'tặng phiếu', 'link thảo luận', 'link thảo luận bên forum',
        'tấu chương xong', 'tấu chương', 'tạ ơn', 'cảm ơn', 'thư hữu',
        'thank', 'thanks', '感谢', '感谢支持'
    ]
    
    if any(marker in line_lower for marker in footer_markers):
        return True
    
    # Footer patterns
    footer_patterns = [
        r'^\s*\(?\s*tấu\s+chương\s*(xong)?\s*\)?\s*$',
        r'^\s*\(?\s*tấu\s+chương\s*\)?\s*$',
        r'^\s*tạ\s+ơn.*$',
        r'^\s*cảm\s+ơn.*$',
        r'^\s*thư\s+hữu.*$',
        r'^[-—–]{3,}\s*$',  # "---", "——", "–––"
        r'^[-—–]{1,2}\s*$',  # "-", "--" (standalone)
    ]
    
    for pattern in footer_patterns:
        if re.match(pattern, line, re.IGNORECASE):
            return True
    
    return False


def clean_text_file(file_path: Path, dry_run: bool = False) -> tuple[bool, int]:
    """
    Clean a text file:
    - Remove duplicate chapter titles
    - Remove footer content
    - Normalize chapter title format
    
    Args:
        file_path: Path to text file
        dry_run: If True, don't write file, only return what would be changed
    
    Returns: (was_modified, lines_removed)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  Error reading {file_path.name}: {e}")
        return False, 0
    
    original_line_count = len(lines)
    cleaned_lines = []
    seen_title_normalized = None
    seen_title_name = None  # Title name without chapter number
    seen_chapter_num = None  # Chapter number of the first title
    footer_start_idx = None
    
    # Metadata/header chrome patterns (site info)
    metadata_patterns = [
        r'^thứ\s+\d+\s+chương',        # "Thứ 1184 chương ..."
        r'^tên\s+sách',                # "Tên sách: ..."
        r'^tên\s+tác\s+giả',           # "Tên tác giả: ..."
        r'^(số|số)\s+lượng\s+từ',    # "Số lượng từ: ..."
        r'^thời\s+gian\s+đổi\s+mới',   # "Thời gian đổi mới: ..."
        r'^số\s+lượng\s+từ:\s*\d+\s+chữ',  # "Số lượng từ: 6113 chữ"
        r'^số\s+lượng\s+từ:\s*\d+\s+chữ',  # "Số lượng từ: 6113 chữ" (with Vietnamese diacritics)
    ]
    
    # Common author names to remove (standalone lines)
    author_names = ['Quan Hư', 'Vong Mạng', 'giang_04']

    # Process lines
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines at the beginning
        if not line_stripped and len(cleaned_lines) == 0:
            continue

        # Skip site metadata/header lines near the top (within first 10 lines)
        if i < 10:
            lower_no_space = line_stripped.lower()
            
            # Check for metadata patterns
            skip_metadata = False
            for pattern in metadata_patterns:
                if re.match(pattern, lower_no_space, re.IGNORECASE):
                    skip_metadata = True
                    break
            
            if skip_metadata:
                continue  # Skip this line
            
            # Check for "Số lượng từ: XXXX chữ" pattern (with or without diacritics)
            if re.match(r'^s[ôo]\s+l[ươu][ơo]?ng\s+t[ưu][ừu]?:\s*\d+\s+ch[ữu]', lower_no_space, re.IGNORECASE):
                continue  # Skip this line
            
            # Check for standalone author names
            if line_stripped in author_names:
                continue  # Skip this line
        
        # Check for footer content first (before processing title)
        if is_footer_line(line_stripped):
            if footer_start_idx is None:
                footer_start_idx = len(cleaned_lines)
            # Skip footer lines
            continue
        
        # If we've seen footer, stop processing
        if footer_start_idx is not None:
            continue
        
        # Check if this is a chapter title line
        if line_stripped.startswith('Chương'):
            # Extract chapter number and title name
            chapter_num = get_chapter_number(line_stripped)
            
            # Extract raw title (before normalization) for better comparison
            match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', line_stripped, re.IGNORECASE)
            raw_title = match.group(1).strip() if match else ""
            # Remove quotes if present
            if (raw_title.startswith('"') and raw_title.endswith('"')) or \
               (raw_title.startswith("'") and raw_title.endswith("'")):
                raw_title = raw_title[1:-1].strip()
            
            title_name = extract_chapter_title_name(line_stripped)
            
            # Check if we've seen a title before (only check first 5 lines for duplicates)
            if i < 5 and title_name:
                # If we have a previous title
                if seen_title_name is not None:
                    # Get raw seen title for comparison
                    raw_seen_title = ""
                    if cleaned_lines and cleaned_lines[-1].strip().startswith('Chương'):
                        seen_match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', cleaned_lines[-1].strip(), re.IGNORECASE)
                        if seen_match:
                            raw_seen_title = seen_match.group(1).strip()
                            if (raw_seen_title.startswith('"') and raw_seen_title.endswith('"')) or \
                               (raw_seen_title.startswith("'") and raw_seen_title.endswith("'")):
                                raw_seen_title = raw_seen_title[1:-1].strip()
                    
                    # Check if title name matches (duplicate content)
                    # Normalize both for comparison (remove punctuation, lowercase)
                    norm_title_name = normalize_for_compare(title_name)
                    norm_seen_title = normalize_for_compare(seen_title_name)
                    
                    # Also check raw titles (before normalization) for better matching
                    # This helps catch cases like "1007 nâng đỡ" vs "nâng đỡ"
                    raw_contains = (
                        raw_title and raw_seen_title and
                        len(raw_title) >= 5 and len(raw_seen_title) >= 5 and
                        (raw_title.lower() in raw_seen_title.lower() or raw_seen_title.lower() in raw_title.lower())
                    )
                    
                    # Also check if one title contains the other (for cases like "1006 thắng bại" vs "thắng bại")
                    min_len = min(len(norm_title_name), len(norm_seen_title))
                    max_len = max(len(norm_title_name), len(norm_seen_title))
                    
                    # Check if one contains the other (but require significant overlap)
                    title_contains_seen = (
                        min_len >= 3 and  # Lower threshold for short titles
                        max_len >= 5 and
                        (norm_title_name in norm_seen_title or norm_seen_title in norm_title_name) and
                        # Require at least 60% overlap (lowered from 70% to catch cases like "Đan" vs "Đan Chu")
                        min_len / max_len >= 0.6
                    )
                    titles_match = norm_title_name == norm_seen_title
                    
                    # Also check if one title is a clear substring of another (e.g., "Đan" in "Đan Chu")
                    # This helps catch cases where shorter title is incomplete version
                    is_substring = (
                        min_len >= 2 and
                        (norm_title_name in norm_seen_title or norm_seen_title in norm_title_name) and
                        # If one is clearly a substring, prefer the longer one
                        abs(len(norm_title_name) - len(norm_seen_title)) >= 2
                    )
                    
                    # Check if titles match (exact or one contains the other with sufficient overlap)
                    # Also check raw title containment
                    if titles_match or title_contains_seen or is_substring or (raw_contains and min_len >= 5):
                        # This is a duplicate title - skip it
                        # Prefer the one with higher chapter number and proper format
                        has_colon = ':' in line_stripped or '：' in line_stripped
                        seen_has_colon = ':' in (cleaned_lines[-1] if cleaned_lines else '') or '：' in (cleaned_lines[-1] if cleaned_lines else '')
                        
                        # Also prefer longer title (more complete)
                        # If one is substring of another, prefer the longer one
                        current_is_substring = norm_title_name in norm_seen_title and len(norm_title_name) < len(norm_seen_title)
                        seen_is_substring = norm_seen_title in norm_title_name and len(norm_seen_title) < len(norm_title_name)
                        
                        prefer_current = (
                            chapter_num > seen_chapter_num or
                            (chapter_num == seen_chapter_num and has_colon and not seen_has_colon) or
                            (chapter_num == seen_chapter_num and has_colon == seen_has_colon and len(norm_title_name) > len(norm_seen_title)) or
                            (chapter_num == seen_chapter_num and seen_is_substring)  # Current is longer and contains seen
                        )
                        
                        # If current is substring of seen, always skip current (prefer longer)
                        if current_is_substring:
                            continue
                        
                        if not prefer_current:
                            # Skip this duplicate (lower chapter number, worse format, or shorter)
                            if chapter_num < seen_chapter_num or (chapter_num == seen_chapter_num and not has_colon and seen_has_colon):
                                continue
                        else:
                            # Replace the previous one with this better formatted one
                            # Find and remove the last chapter title in cleaned_lines
                            for j in range(len(cleaned_lines) - 1, -1, -1):
                                if cleaned_lines[j].strip().startswith('Chương'):
                                    cleaned_lines.pop(j)
                                    break
                            line_normalized = normalize_chapter_title(line_stripped)
                            cleaned_lines.append(line_normalized + '\n')
                            seen_title_normalized = normalize_for_compare(line_normalized)
                            seen_title_name = title_name
                            seen_chapter_num = chapter_num
                            continue
                    else:
                        # Different title - keep both (might be different chapters)
                        line_normalized = normalize_chapter_title(line_stripped)
                        cleaned_lines.append(line_normalized + '\n')
                        if seen_title_name is None:
                            seen_title_normalized = normalize_for_compare(line_normalized)
                            seen_title_name = title_name
                            seen_chapter_num = chapter_num
                        continue
                else:
                    # First title - keep it
                    line_normalized = normalize_chapter_title(line_stripped)
                    cleaned_lines.append(line_normalized + '\n')
                    seen_title_normalized = normalize_for_compare(line_normalized)
                    seen_title_name = title_name
                    seen_chapter_num = chapter_num
                    continue
            else:
                # Not in first 5 lines - just normalize and add
                line_normalized = normalize_chapter_title(line_stripped)
                cleaned_lines.append(line_normalized + '\n')
                continue
        
        # Regular line - keep as is
        cleaned_lines.append(line)
    
    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    # Check if file was modified
    lines_removed = original_line_count - len(cleaned_lines)
    
    # Check if any chapter titles were normalized
    title_normalized = False
    for i, line in enumerate(lines[:5]):
        if line.strip().startswith('Chương') and (':' in line or '：' in line):
            normalized = normalize_chapter_title(line.strip())
            if normalized != line.strip():
                title_normalized = True
                break
    
    was_modified = lines_removed > 0 or title_normalized
    
    if was_modified and not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            return True, lines_removed
        except Exception as e:
            print(f"⚠️  Error writing {file_path.name}: {e}")
            return False, 0
    
    return was_modified, lines_removed


def main():
    """Main function to clean all text files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean text files: remove duplicate titles and footer content')
    parser.add_argument('--dir', default='38060 - Text', help='Directory containing text files (default: 38060 - Text)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    
    args = parser.parse_args()
    
    text_dir = Path(args.dir)
    if not text_dir.exists():
        print(f"❌ Directory not found: {text_dir}")
        return
    
    # Find all text files
    text_files = sorted(text_dir.glob('Chapter_*.txt'))
    
    if not text_files:
        print(f"⚠️  No text files found in {text_dir}")
        return
    
    print(f"Found {len(text_files)} text files")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'MODIFY FILES'}\n")
    
    total_modified = 0
    total_lines_removed = 0
    
    for file_path in text_files:
        was_modified, lines_removed = clean_text_file(file_path, dry_run=args.dry_run)
        if was_modified:
            if args.dry_run:
                print(f"  Would modify: {file_path.name} (remove {lines_removed} lines)")
            else:
                print(f"  ✓ Cleaned: {file_path.name} (removed {lines_removed} lines)")
            total_modified += 1
            total_lines_removed += lines_removed
    
    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"DRY RUN: Would modify {total_modified}/{len(text_files)} files")
        print(f"Would remove {total_lines_removed} total lines")
    else:
        print(f"✓ Completed: Modified {total_modified}/{len(text_files)} files")
        print(f"✓ Removed {total_lines_removed} total lines")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()


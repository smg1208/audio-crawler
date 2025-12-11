from bs4 import BeautifulSoup
import re
import base64


class HTMLParser:
    """Parse HTML and extract the main story text.

    Uses a list of selectors commonly used by web novels and falling back to heuristics.
    """

    # Common selectors plus site-specific ones for tangthuvien.net and bnsach.com
    CANDIDATE_SELECTORS = [
        '#chapter-content',
        '.chapter-content',
        '.chapter-c-content',
        '.box-chap',
        '.entry-content',
        '.content',
        'article',
        'div#content',
        '.chapter-c .box-chap',
        # bnsach.com selectors
        '.reader-content',
        '.chapter-text',
        '#reader-content',
        '.novel-content',
        'div.reader',
    ]

    def parse_main_text(self, html: str, base_url: str = None, session=None) -> str:
        soup = BeautifulSoup(html, 'html.parser')

        # remove scripts/styles
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'advertisement']):
            tag.decompose()

        # Check for encrypted content (bnsach.com uses encrypted-content element)
        encrypted_elem = soup.find(id='encrypted-content')
        if encrypted_elem and base_url and session:
            encrypted_content = encrypted_elem.get_text().strip()
            if encrypted_content:
                try:
                    # Call decrypt API
                    import requests
                    decrypt_url = f"{base_url}/reader/api/decrypt-content.php"
                    response = session.post(
                        decrypt_url,
                        json={'encryptedData': encrypted_content},
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if 'content' in data:
                            # Parse the decrypted HTML content
                            decrypted_html = data['content']
                            decrypted_soup = BeautifulSoup(decrypted_html, 'html.parser')
                            text = decrypted_soup.get_text(separator='\n')
                            # Continue with normal cleaning process
                            return self._clean_text(text)
                except Exception:
                    # If decryption fails, fall through to normal parsing
                    pass

        # Note: bnsach.com may have base64 encoded content, but it's often not the actual story text
        # We'll parse the HTML normally and filter out metadata/footer

        target = None
        for sel in self.CANDIDATE_SELECTORS:
            el = soup.select_one(sel)
            if el:
                target = el
                break

        if target is None:
            # as fallback, look for the longest <div> or <article>
            candidates = soup.find_all(['div', 'article', 'section'])
            candidates = sorted(candidates, key=lambda e: len(e.get_text()), reverse=True)
            if candidates:
                target = candidates[0]

        if target is None:
            # give up — return page text
            text = soup.get_text(separator='\n')
        else:
            text = target.get_text(separator='\n')

        return self._clean_text(text)
    
    def _clean_chapter_title(self, raw: str) -> str:
        """
        Loại tên dịch giả/các đuôi không dính vào tên chương thực sự.
        Xử lý cả trường hợp dính liền (không có khoảng trắng) như "thiếu niênVong Mạng"
        
        Sử dụng pattern detection để phát hiện tự động các tên dịch giả, không chỉ dựa vào blacklist.
        """
        import re
        RAW = raw.strip()
        if not RAW:
            return RAW
        
        # List các kiểu tên hay gặp cần loại (cả với và không có khoảng trắng)
        # Bao gồm: Vong Mạng (và các biến thể), sleepy, nila32, giang_04, Bạch Ngọc Sách, Convert, etc.
        blacklist = [
            'Vong Mạng', 'VongMạng', 'vong mạng', 'vongmạng', 'VONG MẠNG', 'VONGMẠNG',
            'sleepy', 'Sleepy', 'SLEEPY',
            'nila32', 'Nila32', 'NILA32',
            'giang_04', 'giang04', 'giang 04', 'giang04 convert',
            'Bạch Ngọc Sách', 'BạchNgọcSách', 'BNS', 
            'Convert', 'convert'
        ]
        
        # Bước 1: Thử loại bỏ từng từ trong blacklist (cả với và không có khoảng trắng, case-insensitive)
        RAW_lower = RAW.lower()
        for word in blacklist:
            word_lower = word.lower()
            # Loại bỏ nếu có khoảng trắng trước (case-insensitive)
            if RAW_lower.endswith(' ' + word_lower):
                # Tìm vị trí thực tế trong RAW (case-sensitive) để cắt chính xác
                pos = len(RAW_lower) - len(word_lower) - 1
                if pos >= 0:
                    RAW = RAW[:pos].strip()
                    RAW_lower = RAW.lower()  # Update lowercase version
                    continue
            # Loại bỏ nếu dính liền (không có khoảng trắng, case-insensitive)
            if RAW_lower.endswith(word_lower):
                pos = len(RAW_lower) - len(word_lower)
                if pos >= 0:
                    RAW = RAW[:pos].strip()
                    RAW_lower = RAW.lower()  # Update lowercase version
                    continue
            # Loại bỏ nếu có khoảng trắng sau (case-insensitive)
            if RAW_lower.endswith(word_lower + ' '):
                pos = len(RAW_lower) - len(word_lower) - 1
                if pos >= 0:
                    RAW = RAW[:pos].strip()
                    RAW_lower = RAW.lower()  # Update lowercase version
        
        # Bước 2: Pattern detection - phát hiện tên dịch giả dựa trên pattern
        # Trước tiên, tìm chính xác vị trí của các từ trong blacklist (case-insensitive)
        # Tìm từ cuối cùng trong blacklist xuất hiện trong chuỗi (cả với và không có khoảng trắng)
        best_match_pos = -1
        best_match_word = None
        for word in blacklist:
            # Tìm vị trí của từ trong chuỗi (case-insensitive)
            # Tìm cả với khoảng trắng và không có khoảng trắng
            # Pattern: tìm từ trong blacklist, có thể dính liền với từ trước (như "ThànhVong Mạng")
            # Loại bỏ khoảng trắng trong word để tìm pattern dính liền
            word_no_space = word.replace(' ', '')
            # Tìm cả "Vong Mạng" và "VongMạng"
            patterns_to_try = [word, word_no_space] if ' ' in word else [word]
            for pattern_str in patterns_to_try:
                # Tìm pattern trong chuỗi (case-insensitive)
                pattern_word = re.compile(re.escape(pattern_str), re.IGNORECASE)
                for match in pattern_word.finditer(RAW):
                    pos = match.start()
                    # Ưu tiên match gần cuối chuỗi hơn (tên dịch giả thường ở cuối)
                    if pos > best_match_pos:
                        best_match_pos = pos
                        best_match_word = word
        
        # Nếu tìm thấy match trong blacklist, cắt bỏ từ vị trí đó và dừng lại
        if best_match_pos >= 0:
            RAW = RAW[:best_match_pos].strip()
        else:
            # Nếu chưa tìm thấy trong blacklist, thử pattern detection: chữ thường/tiếng Việt + chữ hoa đột ngột
            pattern = re.compile(r'([a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])([A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ])')
            match = pattern.search(RAW)
        if match:
            # Tìm vị trí bắt đầu của chữ hoa đột ngột
            pos = match.end() - 1
            # Lấy phần còn lại sau chữ hoa đột ngột
            remaining = RAW[pos:]
            
            # Kiểm tra xem phần sau có phải là tên dịch giả không
            # Tiêu chí:
            # 1. Ngắn (< 25 ký tự) - tên dịch giả thường ngắn
            # 2. Không chứa dấu câu (.,!?;:–) - tên chương thật thường có dấu câu
            # 3. Không phải là câu hoàn chỉnh (không có động từ phổ biến)
            # 4. Có thể là 1-4 từ (tên dịch giả thường ngắn)
            
            is_likely_translator_name = (
                len(remaining) < 25 and  # Ngắn
                not any(ch in remaining for ch in '.!?,;:–') and  # Không có dấu câu
                len(remaining.split()) <= 4  # Tối đa 4 từ
            )
            
            # Kiểm tra thêm: không phải là câu hoàn chỉnh
            # Nếu có động từ phổ biến hoặc từ khóa câu, có thể là tên chương thật
            common_verbs = ['là', 'có', 'đã', 'sẽ', 'được', 'bị', 'phải', 'nên', 'muốn', 'cần']
            has_verb = any(verb in remaining.lower() for verb in common_verbs)
            
            # Kiểm tra xem có match với blacklist không (case-insensitive)
            remaining_lower = remaining.lower()
            matched_blacklist = False
            for word in blacklist:
                if word.lower() in remaining_lower or remaining_lower in word.lower():
                    matched_blacklist = True
                    break
            
            # Chỉ loại bỏ nếu:
            # 1. Match blacklist (ưu tiên cao nhất) HOẶC
            # 2. Pattern rất giống tên dịch giả (ngắn, không có động từ, không có dấu câu)
            # Và không phải là từ viết hoa toàn bộ dài (có thể là tên riêng trong tên chương)
            is_all_uppercase_long = remaining.isupper() and len(remaining) > 5
            # Kiểm tra xem có phải là camelCase không (như SomeName)
            has_camel_case = bool(re.search(r'[a-z][A-Z]', remaining))
            # Kiểm tra xem có phải là từ viết hoa toàn bộ không (như XYZ, ABC)
            is_all_uppercase = remaining.isupper()
            
            if matched_blacklist:
                # Nếu match blacklist, loại bỏ ngay
                RAW = RAW[:pos].strip()
            elif (is_likely_translator_name and not has_verb and 
                  len(remaining) < 15 and (has_camel_case or (len(remaining.split()) <= 2 and not is_all_uppercase_long))):
                # Loại bỏ nếu:
                # - Pattern giống tên dịch giả (camelCase hoặc ngắn)
                # - Không phải là từ viết hoa toàn bộ dài
                # - Không có động từ
                RAW = RAW[:pos].strip()
        
        # Bước 3: Xử lý trường hợp có khoảng trắng nhưng vẫn là tên dịch giả
        # Ví dụ: "Tên chương SomeName" hoặc "Tên chương Some Name"
        # Chỉ xử lý nếu từ cuối cùng rất ngắn và có pattern giống tên dịch giả
        words = RAW.split()
        if len(words) >= 2:
            last_word = words[-1]
            # Kiểm tra xem từ cuối có trong blacklist không
            last_lower = last_word.lower()
            matched_blacklist = any(word.lower() in last_lower or last_lower in word.lower() for word in blacklist)
            
            # Nếu match blacklist, loại bỏ ngay
            if matched_blacklist:
                RAW = ' '.join(words[:-1]).strip()
            else:
                # Kiểm tra pattern: từ ngắn, viết hoa, không có dấu câu
                # NHƯNG chỉ loại bỏ nếu có camelCase (như SomeName) hoặc là từ tiếng Anh viết hoa ngắn
                # KHÔNG loại bỏ các từ tiếng Việt bình thường (như "Thành", "Đạo", etc.)
                has_camel_case = bool(re.search(r'[a-z][A-Z]', last_word))
                # Kiểm tra xem có phải là từ tiếng Anh không (chỉ chứa a-z, A-Z, không có dấu)
                is_english_word = bool(re.match(r'^[a-zA-Z]+$', last_word))
                is_short_uppercase_english = (
                    is_english_word and
                    len(last_word) < 8 and  # Rất ngắn
                    last_word[0].isupper() and 
                    not any(ch in last_word for ch in '.!?,;:–') and
                    not (last_word.isupper() and len(last_word) > 4)  # Không phải từ viết hoa dài
                )
                
                # Chỉ loại bỏ nếu có camelCase hoặc là từ tiếng Anh ngắn viết hoa
                # KHÔNG loại bỏ các từ tiếng Việt bình thường
                if has_camel_case or is_short_uppercase_english:
                    RAW = ' '.join(words[:-1]).strip()
        
        return RAW

    def _clean_text(self, text: str) -> str:
        """Clean and process extracted text."""
        # clean up whitespace and ads markers
        lines = [ln.strip() for ln in text.splitlines()]
        # drop empty, ad markers and lines that are only punctuation/noise (like single dot lines)
        lines = [ln for ln in lines if ln and not ln.lower().startswith('advert')]
        
        # Remove bnsach-specific metadata lines and base64 strings
        metadata_patterns = [
            r'^\d+\s+từ$',  # "2013 từ"
            r'^\d{2}/\d{2}/\d{2}-\d{2}:\d{2}$',  # "14/05/21-23:00"
            r'^Convert:\s*',  # "Convert: Vong Mạng"
            r'^Nguồn:\s*',  # "Nguồn: Bachngocsach.com"
            r'^STK:\s*',  # "STK: 022198170"
            r'^Banks:\s*',  # "Banks: VIB"
            r'^Chủ TK:\s*',  # "Chủ TK: Ly Hong Trang"
            r'^Momo:',  # "Momo:"
            r'^Paypal:',  # "Paypal:"
            r'^Donate',  # "Donate ..."
            r'^Cầu donate',  # "Cầu donate ..."
            r'^Mời các bạn tham gia',  # "Mời các bạn tham gia ..."
            r'^\[Thảo Luận\]',  # "[Thảo Luận] ..."
            r'^Next$',  # "Next"
            r'^Prev$',  # "Prev"
        ]
        
        # Base64 pattern - lines that are mostly base64 characters and very long
        base64_line_pattern = re.compile(r'^[A-Za-z0-9+/]{100,}={0,2}$')
        
        filtered_lines = []
        for ln in lines:
            skip = False
            
            # Skip metadata
            for pattern in metadata_patterns:
                if re.match(pattern, ln, re.IGNORECASE):
                    skip = True
                    break
            
            # Skip long base64 strings (likely encoded data, not story text)
            if not skip and base64_line_pattern.match(ln):
                skip = True
            
            # Skip lines that are just author names (like "Vong Mạng", "Quan Hư" alone on a line)
            if not skip and len(ln.strip()) < 30 and not any(c in ln for c in ['。', '.', '!', '?', '，', ',', ':', '：']):
                # Common author names to skip
                author_names = ['Vong Mạng', 'giang_04', 'Quan Hư']
                if ln.strip() in author_names and len(filtered_lines) > 0:
                    # Check if previous line is chapter title
                    prev_line = filtered_lines[-1] if filtered_lines else ''
                    if 'Chương' not in prev_line:
                        skip = True
            
            # Skip "Số lượng từ: XXXX chữ" lines
            if not skip and re.match(r'^số\s+lượng\s+từ:\s*\d+\s+chữ', ln.strip(), re.IGNORECASE):
                skip = True
            
            if not skip:
                filtered_lines.append(ln)
        lines = filtered_lines
        
        def is_noise_line(s: str) -> bool:
            # True if line is 1-4 characters of punctuation/non-word only (e.g. '.' or '...')
            return bool(re.match(r"^[^\w\d\p{L}]{1,4}$", s))

        # Python's re doesn't support \p{L} by default; use an alternate check
        def is_noise_fallback(s: str) -> bool:
            return bool(re.match(r"^[^\w\dÀ-ÖØ-öø-ÿĀ-žẀ-ỿ]{1,4}$", s))

        cleaned_lines = []
        for ln in lines:
            try:
                if is_noise_line(ln):
                    continue
            except re.error:
                if is_noise_fallback(ln):
                    continue
            cleaned_lines.append(ln)

        # Remove site metadata/header lines near top (e.g., "Thứ 1184 chương...", "Tên sách", "Số lượng từ", "Thời gian đổi mới")
        metadata_patterns = [
            r'^thứ\s+\d+\s+chương',
            r'^tên\s+sách',
            r'^tên\s+tác\s+giả',
            r'^(số|số)\s+lượng\s+từ',
            r'^thời\s+gian\s+đổi\s+mới',
        ]
        filtered_meta = []
        for idx, ln in enumerate(cleaned_lines):
            if idx < 10 and any(re.match(pat, ln.strip().lower(), re.IGNORECASE) for pat in metadata_patterns):
                continue
            filtered_meta.append(ln)
        cleaned_lines = filtered_meta

        # --- BỔ SUNG sửa dòng tiêu đề chương ---
        if cleaned_lines and cleaned_lines[0].startswith('Chương') and ':' in cleaned_lines[0]:
            line = cleaned_lines[0]
            left, right = line.split(':', 1)
            cleaned_title = self._clean_chapter_title(right)
            cleaned_lines[0] = f'{left}: {cleaned_title}'

        # ----- Remove header chrome: find first plausible chapter-title and drop anything before it -----
        # prefer explicit chapter title with a number (avoid matching single 'Chương' words in the header)
        chapter_title_re = re.compile(r"^\s*Chương\s*\d+\b", re.IGNORECASE)
        start_idx = 0
        for i, ln in enumerate(cleaned_lines):
            if chapter_title_re.match(ln):
                start_idx = i
                break

        # keep the original cleaned_lines array while we scan for footers so indices remain stable
        orig_lines = cleaned_lines

        # ----- Remove trailing chrome: footer markers, counts, or forum links -----
        # Footer markers that should ONLY match when they appear as standalone phrases or at start of line
        # We need to be careful not to match these when they appear in story dialogue/content
        footer_markers_strict = [
            'hãy nhấn like', 'tặng phiếu', 'link thảo luận', 'link thảo luận bên forum', 
            'thank', 'thanks', '感谢', '感谢支持'
        ]
        
        # Footer patterns (regex) - these are more specific and safer
        footer_patterns = [
            r'^\s*\(?\s*tấu\s+chương\s*(xong)?\s*\)?\s*$',  # "( tấu chương xong)" - standalone
            r'^\s*\(?\s*tấu\s+chương\s*\)?\s*$',  # "( tấu chương)" - standalone
            r'^\s*tạ\s+ơn\s*[^a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]*$',  # "Tạ ơn" at start, nothing meaningful after
            r'^\s*cảm\s+ơn\s*[^a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]*$',  # "Cảm ơn" at start, nothing meaningful after
            r'^\s*thư\s+hữu\s*[^a-zàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]*$',  # "Thư hữu" at start
            r'^[-—–]{3,}\s*$',  # "---", "——", "–––" - standalone separators
        ]
        
        end_idx = len(cleaned_lines)
        # only search footer markers after the detected chapter title start
        # Use a smarter approach: look for footer markers but verify they're actually footers
        # by checking if there's meaningful content after them
        for i, ln in enumerate(orig_lines[start_idx:], start=start_idx):
            low = ln.lower().strip()
            
            # Skip empty lines
            if not low:
                continue
            
            # Check footer markers - but be very careful not to match story content
            for marker in footer_markers_strict:
                if marker in low:
                    line_len = len(low)
                    marker_pos = low.find(marker)
                    
                    # Calculate context around marker
                    before_marker = low[:marker_pos].strip()
                    after_marker = low[marker_pos + len(marker):].strip()
                    
                    # If there's substantial content (15+ chars) before marker, it's story content
                    # Example: "Thay ta tạ ơn chủ nhân" - "tạ ơn" is in the middle
                    if len(before_marker) > 15:
                        continue  # Skip this marker, it's embedded in story content
                    
                    # If there's substantial content after marker, it might be story continuation
                    # Example: "tạ ơn chủ nhân" - "chủ nhân" continues the sentence
                    if len(after_marker) > 8:
                        # Check if it looks like a complete sentence continuation
                        words_after = after_marker.split()
                        if len(words_after) >= 2:
                            continue  # Skip, it's story content
                    
                    # Only treat as footer if marker is at start/end of short line
                    # AND there's no meaningful continuation
                    if line_len < 60 and (marker_pos < 5 or marker_pos > line_len - len(marker) - 3):
                        # Look ahead: check if next few lines have meaningful content
                        # If they do, this is probably not a footer
                        look_ahead_count = 0
                        look_ahead_meaningful = 0
                        for j in range(i+1, min(i+6, len(orig_lines))):
                            next_line = orig_lines[j].strip()
                            if next_line:
                                look_ahead_count += 1
                                # Meaningful if it's a sentence (has punctuation or is long)
                                if len(next_line) > 30 or any(c in next_line for c in '.!?。！？'):
                                    look_ahead_meaningful += 1
                        
                        # If there's meaningful content ahead, don't stop here
                        if look_ahead_meaningful >= 2:
                            continue  # Continue parsing, this is not a footer
                        
                        # This looks like a footer - stop here
                        end_idx = i
                        break
            
            if end_idx < len(cleaned_lines):
                break
            
            # Check footer patterns (these are more specific and safer)
            for pattern in footer_patterns:
                if re.match(pattern, ln, re.IGNORECASE):
                    # For pattern matches, also do a look-ahead check
                    look_ahead_count = 0
                    look_ahead_meaningful = 0
                    for j in range(i+1, min(i+6, len(orig_lines))):
                        next_line = orig_lines[j].strip()
                        if next_line:
                            look_ahead_count += 1
                            if len(next_line) > 30 or any(c in next_line for c in '.!?。！？'):
                                look_ahead_meaningful += 1
                    
                    # Only stop if there's no meaningful content ahead
                    if look_ahead_meaningful < 2:
                        end_idx = i
                        break
            
            if end_idx < len(cleaned_lines):
                break
            
            # Check for standalone numbers (page numbers) - but only near the end
            # Don't stop on numbers if we're still in the middle of the chapter
            if i > start_idx + 20:  # Only check after at least 20 lines of content
                if re.fullmatch(r"\d{1,5}", ln.strip()):
                    # Check if next few lines are also short/empty (likely footer area)
                    look_ahead_lines = orig_lines[i+1:min(i+4, len(orig_lines))]
                    if all(len(l.strip()) < 10 for l in look_ahead_lines):
                        end_idx = i
                        break

        # slice from chapter start to the end index (removing header + footer chrome)
        cleaned_lines = orig_lines[start_idx:end_idx]

        # compress multiple blank lines
        cleaned = '\n\n'.join([ln for ln in cleaned_lines])

        # remove excessive repeated newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # ----- Remove duplicated chapter title lines (consecutive or near-consecutive) -----
        # e.g. pages that include the title twice at the top. We'll normalize and remove duplicates
        def normalize_for_compare(s: str) -> str:
            s = s.lower().strip()
            # Normalize chapter title format: remove spaces before colon, normalize colon
            s = re.sub(r'\s*:\s*', ':', s)  # "Chương 405 : xxx" -> "Chương 405:xxx"
            s = re.sub(r'\s*：\s*', ':', s)  # Chinese colon
            # remove punctuation and multiple spaces
            s = re.sub(r"[^\w\sàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ-]", '', s)
            s = re.sub(r"\s+", ' ', s)
            return s

        def extract_chapter_title_name(line: str) -> str:
            """
            Extract chapter title name from a line like "Chương 1002: "Thái tử gia"".
            For titles like "Chương 1009: 1007 nâng đỡ", extracts "nâng đỡ" (after the number).
            For titles like "Chương 1007 nâng đỡ", extracts "nâng đỡ".
            """
            match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', line, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Remove quotes if present
                if (title.startswith('"') and title.endswith('"')) or \
                   (title.startswith("'") and title.endswith("'")):
                    title = title[1:-1].strip()
                
                # Check if title starts with a number (like "1007 nâng đỡ")
                # If so, extract the part after the number for comparison
                num_match = re.match(r'^(\d+)\s+(.+)$', title)
                if num_match:
                    # Title starts with number - use the part after number for comparison
                    title_after_num = num_match.group(2)
                    return normalize_for_compare(title_after_num)
                
                return normalize_for_compare(title)
            return ""

        def get_chapter_number(line: str) -> int:
            """Extract chapter number from a line like "Chương 1002: xxx"."""
            match = re.match(r'^Chương\s+(\d+)', line, re.IGNORECASE)
            if match:
                return int(match.group(1))
            return -1

        lines = [ln for ln in cleaned.split('\n') if ln.strip()]
        if len(lines) >= 2:
            # Normalize first line (chapter title)
            first_line = lines[0]
            # Normalize colon spacing: "Chương 405 : xxx" -> "Chương 405: xxx"
            first_line = re.sub(r'(Chương\s+\d+)\s*:\s*', r'\1: ', first_line, flags=re.IGNORECASE)
            first_line = re.sub(r'(Chương\s+\d+)\s*：\s*', r'\1: ', first_line, flags=re.IGNORECASE)
            lines[0] = first_line
            
            # Extract first title info
            first_title_name = extract_chapter_title_name(lines[0]) if lines[0].startswith('Chương') else None
            first_chapter_num = get_chapter_number(lines[0]) if lines[0].startswith('Chương') else -1
            
            # Extract raw first title for better comparison
            first_raw_title = ""
            if lines[0].startswith('Chương'):
                first_match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', lines[0], re.IGNORECASE)
                if first_match:
                    first_raw_title = first_match.group(1).strip()
                    if (first_raw_title.startswith('"') and first_raw_title.endswith('"')) or \
                       (first_raw_title.startswith("'") and first_raw_title.endswith("'")):
                        first_raw_title = first_raw_title[1:-1].strip()
            
            # check first few lines for duplicates
            norm0 = normalize_for_compare(lines[0])
            # remove exact consecutive duplicates first
            new_lines = [lines[0]]
            for i, ln in enumerate(lines[1:], start=1):
                # Only check first 5 lines for duplicate titles
                if i >= 5:
                    new_lines.append(ln)
                    continue
                
                # Normalize colon spacing in current line too
                ln_normalized = re.sub(r'(Chương\s+\d+)\s*:\s*', r'\1: ', ln, flags=re.IGNORECASE)
                ln_normalized = re.sub(r'(Chương\s+\d+)\s*：\s*', r'\1: ', ln_normalized, flags=re.IGNORECASE)
                
                # Skip if exact duplicate
                if ln_normalized.strip() == new_lines[-1].strip():
                    continue
                
                # Check if this is a chapter title
                if ln_normalized.strip().startswith('Chương') and first_title_name:
                    # Extract title name and chapter number
                    title_name = extract_chapter_title_name(ln_normalized)
                    chapter_num = get_chapter_number(ln_normalized)
                    
                    # Extract raw title for comparison
                    raw_title = ""
                    ln_match = re.match(r'^Chương\s+\d+\s*[:：]?\s*(.+)$', ln_normalized, re.IGNORECASE)
                    if ln_match:
                        raw_title = ln_match.group(1).strip()
                        if (raw_title.startswith('"') and raw_title.endswith('"')) or \
                           (raw_title.startswith("'") and raw_title.endswith("'")):
                            raw_title = raw_title[1:-1].strip()
                    
                    # Check if title name matches (duplicate content, possibly different chapter number)
                    titles_match = title_name == first_title_name
                    
                    # Also check raw title containment (for cases like "1007 nâng đỡ" vs "nâng đỡ")
                    raw_contains = (
                        raw_title and first_raw_title and
                        len(raw_title) >= 5 and len(first_raw_title) >= 5 and
                        (raw_title.lower() in first_raw_title.lower() or first_raw_title.lower() in raw_title.lower())
                    )
                    
                    if titles_match or (raw_contains and len(title_name) >= 5):
                        # This is a duplicate title - skip it
                        # Prefer the one with higher chapter number and proper format
                        has_colon = ':' in ln_normalized or '：' in ln_normalized
                        if chapter_num < first_chapter_num or (not has_colon and (':' in lines[0] or '：' in lines[0])):
                            continue
                        else:
                            # Replace the previous one with this better formatted one
                            if new_lines and new_lines[0].strip().startswith('Chương'):
                                new_lines[0] = ln_normalized
                                first_chapter_num = chapter_num
                                first_title_name = title_name
                                first_raw_title = raw_title
                            continue
                
                # Check normalized comparison (fallback for exact match)
                norm_ln = normalize_for_compare(ln_normalized)
                if norm_ln and norm0 and norm_ln == norm0:
                    # This is a duplicate title, skip it
                    continue
                
                new_lines.append(ln_normalized)

            # then check for near-duplicates near top (e.g., title repeated in line 0 and 1 or 2)
            if len(new_lines) >= 2:
                norm1 = normalize_for_compare(new_lines[1])
                if norm0 and norm1 and norm0 == norm1:
                    # drop the second
                    new_lines.pop(1)
                elif len(new_lines) >= 3:
                    norm2 = normalize_for_compare(new_lines[2])
                    if norm0 and norm2 and norm0 == norm2:
                        # drop the third
                        new_lines.pop(2)

            cleaned = '\n'.join(new_lines)

        return cleaned.strip()

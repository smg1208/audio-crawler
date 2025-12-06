from bs4 import BeautifulSoup
import re


class HTMLParser:
    """Parse HTML and extract the main story text.

    Uses a list of selectors commonly used by web novels and falling back to heuristics.
    """

    # Common selectors plus site-specific ones for tangthuvien.net
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
    ]

    def parse_main_text(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')

        # remove scripts/styles
        for tag in soup(['script', 'style', 'noscript', 'iframe', 'advertisement']):
            tag.decompose()

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

        # clean up whitespace and ads markers
        lines = [ln.strip() for ln in text.splitlines()]
        # drop empty, ad markers and lines that are only punctuation/noise (like single dot lines)
        lines = [ln for ln in lines if ln and not ln.lower().startswith('advert')]
        import re
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
        footer_markers = ['hãy nhấn like', 'tặng phiếu', 'link thảo luận', 'link thảo luận bên forum', 'tặng phiếu']
        end_idx = len(cleaned_lines)
        # only search footer markers after the detected chapter title start
        for i, ln in enumerate(orig_lines[start_idx:], start=start_idx):
            low = ln.lower()
            if any(marker in low for marker in footer_markers):
                end_idx = i
                break
            if re.fullmatch(r"\d{1,5}", ln):
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
            # remove punctuation and multiple spaces
            s = re.sub(r"[^\w\sàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ-]", '', s)
            s = re.sub(r"\s+", ' ', s)
            return s

        lines = [ln for ln in cleaned.split('\n') if ln.strip()]
        if len(lines) >= 2:
            # check first few lines for duplicates
            norm0 = normalize_for_compare(lines[0])
            # remove exact consecutive duplicates first
            new_lines = [lines[0]]
            for ln in lines[1:]:
                if ln.strip() == new_lines[-1].strip():
                    continue
                new_lines.append(ln)

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

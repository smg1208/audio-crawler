import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)
from typing import List, Dict, Optional
import time


class ChapterFetcher:
    def __init__(self, chapters_api: str, base_url: str, source: str = 'tangthuvien', session: Optional[requests.Session] = None):
        self.chapters_api = chapters_api
        self.base_url = base_url
        # source can be 'tangthuvien' (default) or 'bnsach' — affects how chapter lists are parsed
        self.source = (source or 'tangthuvien').lower()
        # fetch retry configuration (defaults)
        self.max_attempts = 3
        self.backoff_seconds = 1
        self.timeout = 30  # Request timeout in seconds
        # Use provided session or create a new one (useful for maintaining cookies/auth)
        self.session = session if session is not None else requests.Session()

    def configure_retries(self, max_attempts: int = 3, backoff_seconds: float = 1.0):
        """Configure retry behaviour for network requests.

        max_attempts: total number of attempts per request
        backoff_seconds: initial seconds to wait; exponential backoff applied
        """
        self.max_attempts = max(1, int(max_attempts))
        self.backoff_seconds = float(max(0.0, backoff_seconds))

    def login_bnsach(self, username: str, password: str) -> bool:
        """Login to bnsach.com and maintain session cookies.
        
        Returns True if login successful, False otherwise.
        """
        if self.source != 'bnsach':
            logger.warning('login_bnsach called but source is not bnsach')
            return False
        
        login_url = f"{self.base_url}/forum/login"
        try:
            # Get login page first to get CSRF token
            resp = self.session.get(login_url, timeout=self.timeout)
            resp.raise_for_status()
            
            # Parse form to extract CSRF token
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            form = soup.find('form')
            if not form:
                logger.error('Could not find login form')
                return False
            
            # Extract _xfToken from hidden input
            xf_token = None
            xf_redirect = None
            for inp in form.find_all('input'):
                name = inp.get('name', '')
                if name == '_xfToken':
                    xf_token = inp.get('value', '')
                elif name == '_xfRedirect':
                    xf_redirect = inp.get('value', '/forum/')
            
            if not xf_token:
                logger.error('Could not find CSRF token in login form')
                return False
            
            # Post login credentials with required fields
            login_data = {
                '_xfToken': xf_token,
                'login': username,  # Note: field name is 'login', not 'username'
                'password': password,
                'remember': '1',  # Remember me checkbox
            }
            if xf_redirect:
                login_data['_xfRedirect'] = xf_redirect
            
            # POST to the form action URL
            form_action = form.get('action', '/forum/login/login')
            if not form_action.startswith('http'):
                form_action = urljoin(self.base_url, form_action)
            
            resp = self.session.post(form_action, data=login_data, allow_redirects=True, timeout=self.timeout)
            resp.raise_for_status()
            
            # Check if login was successful - look for user info or absence of login form
            if 'Đăng nhập để đọc truyện' in resp.text or 'Đăng nhập' in resp.text and 'Tạo tài khoản' in resp.text:
                # Still seeing login page, likely failed
                logger.warning('Login may have failed - still seeing login page')
                return False
            
            logger.info('Login to bnsach.com successful')
            return True
        except Exception as e:
            logger.error(f'Login to bnsach.com failed: {e}')
            return False

    def fetch_chapter_list(self, story_id: str) -> List[Dict]:
        """Return a list of chapters as dicts: {index, title, url}.

        The method will try to request the formatted chapters_api URL and either
        parse JSON (if returned) or fall back to HTML parsing.
        
        For bnsach source, chapters_api can be a direct URL (no formatting needed).
        """
        # For bnsach, chapters_api might be a direct URL, not a template
        if self.source == 'bnsach' and '{' not in self.chapters_api:
            url = self.chapters_api
        else:
            url = self.chapters_api.format(story_id)
        
        # Retry logic for fetching chapter list
        last_exc = None
        for attempt in range(self.max_attempts):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                break
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exc = e
                if attempt < self.max_attempts - 1:
                    wait = self.backoff_seconds * (2 ** attempt)
                    logger.warning(f'Connection error fetching chapter list (attempt {attempt+1}/{self.max_attempts}): {e}. Retrying in {wait}s...')
                    time.sleep(wait)
                else:
                    raise
        else:
            if last_exc:
                raise last_exc

        # Try JSON first
        ct = resp.headers.get('Content-Type', '')
        if 'application/json' in ct:
            data = resp.json()
            # Expecting list-like structure; try to normalize
            out = []
            for i, item in enumerate(data, start=1):
                title = item.get('title') or item.get('name') or f'Chapter {i}'
                raw_url = item.get('url') or item.get('link')
                url = urljoin(self.base_url, raw_url) if raw_url else ''
                out.append({'index': i, 'title': title, 'url': url})
            return out

        # Otherwise parse HTML. Behavior depends on source.
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        out = []
        seen = set()
        idx = 1

        if self.source == 'bnsach':
            # bnsach: chapter list page contains links to chapter pages under /reader/...
            # URL format: https://bnsach.com/reader/{story-slug}/{chapter-slug}
            # Example: /reader/khau-van-tien-dao-convert/xzgs
            
            # Extract story slug from chapters_api URL
            story_slug = None
            if '/reader/' in self.chapters_api and '/muc-luc' in self.chapters_api:
                try:
                    # Extract story slug from chapters_api
                    # e.g., https://bnsach.com/reader/khau-van-tien-dao-convert/muc-luc
                    api_parts = self.chapters_api.split('/reader/')[1].split('/muc-luc')[0]
                    story_slug = api_parts.strip('/')
                except Exception:
                    pass
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            
            # Filter for chapter links: must be /reader/{story-slug}/{chapter-slug}
            # where chapter-slug is a short alphanumeric string (not muc-luc, not pagination)
            for a in all_links:
                href = a.get('href', '')
                if not href:
                    continue
                
                # Normalize href
                from urllib.parse import unquote
                href = unquote(href).strip()
                href = href.replace('\u00a0', ' ').strip()
                href = href.strip('\"\'')
                
                # Must contain /reader/ and the story slug
                if '/reader/' not in href:
                    continue
                
                # Skip muc-luc, pagination, and other non-chapter pages
                if '/muc-luc' in href or '?page=' in href:
                    continue
                
                # Parse URL to extract story-slug and chapter-slug
                # Format: /reader/{story-slug}/{chapter-slug}
                parts = [p for p in href.split('/') if p]
                
                # Find 'reader' in path
                try:
                    reader_idx = parts.index('reader')
                except ValueError:
                    continue
                
                # Should have at least story-slug and chapter-slug after 'reader'
                if len(parts) < reader_idx + 3:
                    continue
                
                link_story_slug = parts[reader_idx + 1]
                chapter_slug = parts[reader_idx + 2]
                
                # Validate story slug matches (if we extracted it)
                if story_slug and link_story_slug != story_slug:
                    continue
                
                # Chapter slug should be a short alphanumeric string (typically 2-6 chars)
                # Skip if it looks like a page name or is too long
                if not chapter_slug or len(chapter_slug) > 20 or chapter_slug in ['recent', 'theloai', 'user', 'index']:
                    continue
                
                # Build full URL
                if ' ' in href:
                    href = href.replace(' ', '%20')
                
                full = urljoin(self.base_url, href)
                
                # Skip if already seen
                if full in seen:
                    continue
                
                seen.add(full)
                title = (a.get_text() or '').strip() or f'Chapter {idx}'
                
                # Clean up title (remove extra whitespace)
                title = ' '.join(title.split())
                
                # Skip empty titles
                if not title:
                    continue
                
                out.append({'index': idx, 'title': title, 'url': full})
                idx += 1

            return out

        # default/tangthuvien heuristics (older behavior)
        candidates = []
        selectors = [
            'ul.chapters a',
            'ul.chapter-list a',
            'div.list-chapters a',
            'a.chapter-link',
            'a[href]',
        ]

        for sel in selectors:
            elems = soup.select(sel)
            if elems:
                candidates = elems
                break

        # If still nothing, find all <a> tags with '/chapter/' in href
        if not candidates:
            candidates = [a for a in soup.find_all('a', href=True) if 'chapter' in a['href'].lower()]

        # Normalize into list of dicts
        for a in candidates:
            href = a.get('href')
            if not href:
                continue
            # sanitize href to avoid bad encodings or stray whitespace
            # decode percent-encoded spaces and similar then strip
            from urllib.parse import unquote
            href = unquote(href)
            href = href.strip()
            # fix common issue: 'https:/example.com' -> 'https://example.com'
            if href.startswith('http:/') and not href.startswith('http://'):
                href = href.replace('http:/', 'http://', 1)
            if href.startswith('https:/') and not href.startswith('https://'):
                href = href.replace('https:/', 'https://', 1)

            # some sites return full URL with leading/trailing spaces or encoded spaces
            href = href.replace('\u00a0', ' ').strip()
            href = href.strip('\"\'')

            # If there are raw spaces within, replace with %20 to avoid broken URLs
            if ' ' in href:
                href = href.replace(' ', '%20')

            full = urljoin(self.base_url, href)
            # Log normalized URL for debugging
            logger.info(f'Found chapter link -> normalized URL: {full}')
            if full in seen:
                continue
            seen.add(full)
            title = (a.get_text() or '').strip() or f'Chapter {idx}'
            out.append({'index': idx, 'title': title, 'url': full})
            idx += 1

        return out

    def _candidate_variants(self, raw_url: str) -> List[str]:
        """Return a list of sanitized candidate URLs to try (ordered by preference)."""
        from urllib.parse import unquote

        href = unquote(raw_url or '')
        href = href.strip()

        # remove surrounding quotes
        href = href.strip('"\'')

        # ensure no leading/trailing NBSP
        href = href.replace('\u00a0', ' ').strip()

        # common malformed scheme fixes
        if href.startswith('http:/') and not href.startswith('http://'):
            href = href.replace('http:/', 'http://', 1)
        if href.startswith('https:/') and not href.startswith('https://'):
            href = href.replace('https:/', 'https://', 1)

        # candidate list
        candidates = []

        # if the url looks absolute, first try it (with %20 cleaned)
        candidate = href.replace(' ', '%20')
        candidates.append(candidate)

        # try direct unquoted/space-stripped version
        candidates.append(href.replace(' ', ''))

        # if it is scheme-less like //domain/path
        if href.startswith('//'):
            candidates.append('https:' + href)
            candidates.append('http:' + href)

        # fallback: join with base_url (handles relative paths)
        try:
            candidates.append(urljoin(self.base_url, href))
        except Exception:
            # safest final fallback: base + / + href
            candidates.append(self.base_url.rstrip('/') + '/' + href.lstrip('/'))

        # ensure uniqueness and keep order
        unique = []
        for c in candidates:
            if not c:
                continue
            if c not in unique:
                unique.append(c)
        return unique


    def fetch_chapter(self, chapter_url: str) -> str:
        # sanitize requested URL and try multiple candidates and retries before failing
        url = (chapter_url or '').strip()
        if url.startswith('http:/') and not url.startswith('http://'):
            url = url.replace('http:/', 'http://', 1)
        if url.startswith('https:/') and not url.startswith('https://'):
            url = url.replace('https:/', 'https://', 1)
        candidates = self._candidate_variants(url)

        last_exc = None
        for candidate in candidates:
            # try the candidate with several attempts (exponential backoff)
            attempt = 0
            wait = self.backoff_seconds
            while attempt < self.max_attempts:
                try:
                    logger.info(f'Attempting fetch: {candidate} (attempt {attempt+1}/{self.max_attempts})')
                    resp = self.session.get(candidate, timeout=self.timeout)
                    # raise for status codes >= 400
                    if resp.status_code >= 400:
                        # treat 404 as definitive 'not found' — no further retries on this candidate
                        if resp.status_code == 404:
                            logger.info(f'Got 404 for {candidate}; skipping to next candidate')
                            last_exc = requests.HTTPError(f'404 for {candidate}')
                            break
                        # server errors are retriable
                        if 500 <= resp.status_code < 600:
                            logger.info(f'Server error {resp.status_code} for {candidate} — will retry')
                            last_exc = requests.HTTPError(f'{resp.status_code} for {candidate}')
                            attempt += 1
                            time.sleep(wait)
                            wait *= 2
                            continue
                        # other 4xx treat as not found/invalid
                        last_exc = requests.HTTPError(f'{resp.status_code} for {candidate}')
                        break
                    # success
                    resp.raise_for_status()
                    return resp.text
                except requests.RequestException as e:
                    last_exc = e
                    attempt += 1
                    if attempt < self.max_attempts:
                        logger.info(f'Retry after exception for {candidate}: {e}; waiting {wait}s')
                        time.sleep(wait)
                        wait *= 2
                    else:
                        logger.info(f'All attempts failed for {candidate} — trying next candidate if any')
            # move on to next candidate URL

        # if we exhausted all candidates and attempts, raise last observed exception
        if last_exc:
            raise last_exc
        raise RuntimeError('Failed to fetch chapter — no candidates succeeded')

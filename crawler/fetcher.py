import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)
from typing import List, Dict, Optional
import time


class ChapterFetcher:
    def __init__(self, chapters_api: str, base_url: str):
        self.chapters_api = chapters_api
        self.base_url = base_url
        # fetch retry configuration (defaults)
        self.max_attempts = 3
        self.backoff_seconds = 1

    def configure_retries(self, max_attempts: int = 3, backoff_seconds: float = 1.0):
        """Configure retry behaviour for network requests.

        max_attempts: total number of attempts per request
        backoff_seconds: initial seconds to wait; exponential backoff applied
        """
        self.max_attempts = max(1, int(max_attempts))
        self.backoff_seconds = float(max(0.0, backoff_seconds))

    def fetch_chapter_list(self, story_id: str) -> List[Dict]:
        """Return a list of chapters as dicts: {index, title, url}.

        The method will try to request the formatted chapters_api URL and either
        parse JSON (if returned) or fall back to HTML parsing.
        """
        url = self.chapters_api.format(story_id)
        resp = requests.get(url)
        resp.raise_for_status()

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

        # Otherwise parse HTML
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # Try a few heuristics to find chapter links
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
        out = []
        seen = set()
        idx = 1
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
            href = href.strip('"\'')

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
                    resp = requests.get(candidate)
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

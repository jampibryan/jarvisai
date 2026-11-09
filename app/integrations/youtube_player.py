from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode, urlsplit

from app.actions.productivity_actions import open_url


class YouTubePlayer:
    def __init__(self, profile: Path) -> None:
        self.profile = profile
        self.query = ''
        self._playwright = self._browser = self._page = None

    def search(self, query: str, *, play: bool = False) -> str:
        self.query = query
        url = 'https://www.youtube.com/results?' + urlencode({'search_query': query})
        if not play:
            return open_url(url)

        try:
            from playwright.sync_api import Error
        except ImportError:
            return self._fallback(url)

        try:
            page = self._ensure_page()
            page.goto(url, wait_until='domcontentloaded', timeout=12_000)
            for label in ('Rechazar todo', 'Reject all'):
                consent = page.get_by_role('button', name=label, exact=True)
                if consent.first.is_visible():
                    consent.first.click(timeout=2_000)
                    break
            result = page.locator('ytd-video-renderer a#video-title[href^="/watch"]').first
            title = result.get_attribute('title', timeout=9_000) or query
            result.click(timeout=6_000)
            page.wait_for_url('**/watch?**', timeout=7_000)
            if not self._is_watch_page(page.url):
                return self._fallback(url)
            video = page.locator('video.html5-main-video').first
            video.evaluate('(video) => { video.play().catch(() => {}); }', timeout=5_000)
            page.wait_for_function(
                '() => { const v = document.querySelector("video.html5-main-video"); return v && !v.paused && v.readyState >= 2; }',
                timeout=6_000,
            )
            return f'Reproduciendo en YouTube: {title}.'
        except (Error, OSError):
            if self._page is not None and self._is_watch_page(self._page.url):
                return 'Abrí el video en YouTube. Pulsa Reproducir si el navegador lo dejó en pausa.'
            if self._page is not None and '/results?' in self._page.url:
                return 'Dejé abierta la búsqueda en YouTube. No pude iniciar un video automáticamente.'
            return self._fallback(url)

    def control(self, action: str) -> str:
        if action == 'play_last' and self.query:
            return self.search(self.query, play=True)
        if self._page is None or self._page.is_closed() or not self._is_watch_page(self._page.url):
            return 'Abre una canción con Jarvis antes de controlar la reproducción.'
        from playwright.sync_api import Error

        try:
            video = self._page.locator('video.html5-main-video').first
            if action == 'pause':
                video.evaluate('(video) => video.pause()', timeout=4_000)
                return 'Pausé el video.'
            video.evaluate('(video) => { video.play().catch(() => {}); }', timeout=4_000)
            self._page.wait_for_function('() => document.querySelector("video")?.paused === false', timeout=4_000)
            return 'Reanudé el video.'
        except Error:
            return 'YouTube no confirmó el cambio de reproducción.'

    def _ensure_page(self):
        from playwright.sync_api import Error, sync_playwright

        if self._page is not None and not self._page.is_closed():
            return self._page
        if self._browser is not None and self._browser.pages:
            self._page = self._browser.new_page()
            return self._page
        self.close()
        self._playwright = sync_playwright().start()
        for channel in ('msedge', 'chrome'):
            try:
                self._browser = self._playwright.chromium.launch_persistent_context(
                    self.profile, channel=channel, headless=False, timeout=9_000,
                    args=['--autoplay-policy=no-user-gesture-required'],
                )
                self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
                return self._page
            except Error:
                continue
        self.close()
        raise Error('No hay un navegador compatible para reproducir YouTube.')

    def close(self) -> None:
        from contextlib import suppress

        if self._browser is not None:
            with suppress(Exception):
                self._browser.close()
        if self._playwright is not None:
            with suppress(Exception):
                self._playwright.stop()
        self._playwright = self._browser = self._page = None

    @staticmethod
    def _is_watch_page(url: str) -> bool:
        parsed = urlsplit(url)
        return parsed.hostname in {'youtube.com', 'www.youtube.com'} and parsed.path == '/watch'

    @staticmethod
    def _fallback(url: str) -> str:
        response = open_url(url)
        return 'Abrí la búsqueda en YouTube. No pude iniciar un video automáticamente.' if response.startswith('Abriendo') else response

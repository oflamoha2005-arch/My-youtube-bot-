import os
import time
import random
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

class BrowserManager:
    def __init__(self, base_dir: Optional[str] = None, headless: bool = False):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.headless = headless
        self._playwright: Optional[Playwright] = None

    def get_profile_path(self, account_id: str) -> str:
        profile_path = os.path.join(self.base_dir, "profiles", account_id)
        os.makedirs(profile_path, exist_ok=True)
        return profile_path

    def launch_account_context(self, account_id: str, headless: Optional[bool] = None) -> Tuple[BrowserContext, Page]:
        if headless is None:
            headless = self.headless

        profile_path = self.get_profile_path(account_id)

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        # Stealth user-agent & viewport
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--start-maximized",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-infobars",
            "--lang=en-US,en"
        ]

        context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=headless,
            viewport=None,  # Use window size
            user_agent=user_agent,
            args=args,
            locale="en-US",
            timezone_id="America/New_York"
        )

        # Inject stealth evasions
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        return context, page

    def close(self):
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # --- Human-like Simulation Helpers ---
    @staticmethod
    def human_delay(min_sec: float = 1.0, max_sec: float = 3.0):
        time.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    def human_type(page: Page, selector: str, text: str):
        page.click(selector)
        for char in text:
            page.keyboard.type(char)
            # Natural human typing speed (40ms - 110ms with occasional slight pauses)
            delay = random.uniform(0.04, 0.11)
            if char in " ,.!?":
                delay += random.uniform(0.08, 0.22)
            time.sleep(delay)

    @staticmethod
    def human_scroll(page: Page, distance: int = 400):
        """Scrolls smoothly with natural steps."""
        steps = random.randint(4, 8)
        step_distance = distance / steps
        for _ in range(steps):
            page.evaluate(f"window.scrollBy(0, {step_distance})")
            time.sleep(random.uniform(0.05, 0.15))

    # --- YouTube High-Level Actions ---
    @staticmethod
    def check_login_status(page: Page) -> bool:
        """Checks whether the active page is logged in to YouTube."""
        try:
            page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            # If avatar button exists, user is logged in
            avatar = page.query_selector("button#avatar-btn, ytd-topbar-menu-button-renderer img")
            sign_in_btn = page.query_selector("a[aria-label*='Sign in' i], ytd-button-renderer a[href*='accounts.google.com']")
            if avatar and not sign_in_btn:
                return True
            return avatar is not None
        except Exception:
            return False

    def post_video_comment(self, page: Page, video_url: str, comment_text: str) -> bool:
        """Navigates to a video and posts a top-level comment."""
        try:
            page.goto(video_url, wait_until="domcontentloaded", timeout=45000)
            self.human_delay(3, 5)

            # Scroll down to load the comments section
            self.human_scroll(page, distance=650)
            self.human_delay(2, 4)

            # Wait for comment box placeholder
            placeholder_selectors = [
                "#simplebox-placeholder",
                "#placeholder-area",
                "ytd-comments #placeholder-area",
                "#comments #placeholder-area"
            ]

            placeholder = None
            for sel in placeholder_selectors:
                try:
                    placeholder = page.wait_for_selector(sel, timeout=12000, state="visible")
                    if placeholder:
                        break
                except Exception:
                    continue

            if not placeholder:
                # Scroll slightly more
                self.human_scroll(page, distance=300)
                self.human_delay(2, 3)
                placeholder = page.wait_for_selector("#simplebox-placeholder, #placeholder-area", timeout=8000)

            if not placeholder:
                print("[-] Could not find comments placeholder. Comments might be disabled or login required.")
                return False

            # Click placeholder to activate the contenteditable box
            placeholder.click()
            self.human_delay(1, 2)

            # Locate contenteditable input box
            input_box = page.wait_for_selector(
                "#contenteditable-root, ytd-commentbox #contenteditable-root, div#contenteditable-root[contenteditable='true']",
                timeout=10000
            )

            if not input_box:
                print("[-] Could not focus comment input.")
                return False

            # Type comment humanly
            self.human_type(page, "#contenteditable-root", comment_text)
            self.human_delay(1.5, 3.0)

            # Click submit button
            submit_selectors = [
                "#submit-button button",
                "ytd-commentbox #submit-button button",
                "ytd-button-renderer#submit-button button"
            ]

            submit_btn = None
            for sel in submit_selectors:
                submit_btn = page.query_selector(sel)
                if submit_btn and submit_btn.is_enabled():
                    break

            if submit_btn:
                submit_btn.click()
                self.human_delay(3, 5)
                print("[+] Comment successfully submitted!")
                return True
            else:
                # Try hitting Ctrl+Enter inside the contenteditable
                page.keyboard.press("Control+Enter")
                self.human_delay(3, 5)
                print("[+] Comment submitted via shortcut!")
                return True

        except Exception as e:
            print(f"[-] Error posting comment: {e}")
            return False

    def like_video(self, page: Page) -> bool:
        """Clicks like button if not already liked (supports English, French, Arabic)."""
        try:
            like_selectors = [
                "ytd-watch-metadata #segmented-like-button button",
                "like-button-view-model button",
                "button[aria-label*='like' i]",
                "button[aria-label*=\"j'aime\" i]",
                "button[aria-label*='إعجاب' i]",
                "#top-level-buttons-computed ytd-toggle-button-renderer:first-child button"
            ]
            for sel in like_selectors:
                btn = page.query_selector(sel)
                if btn:
                    pressed = btn.get_attribute("aria-pressed")
                    if pressed == "true":
                        return False  # Already liked
                    btn.click()
                    self.human_delay(1, 2)
                    return True
            return False
        except Exception:
            return False

    def subscribe_channel(self, page: Page) -> bool:
        """Clicks subscribe button if not already subscribed (supports English, French, Arabic)."""
        try:
            sub_selectors = [
                "#subscribe-button button",
                "ytd-subscribe-button-renderer button",
                "subscribe-button-view-model button"
            ]
            for sel in sub_selectors:
                btn = page.query_selector(sel)
                if btn:
                    text = btn.inner_text().strip().lower()
                    if any(w in text for w in ["subscribed", "abonné", "مشترك"]):
                        return False  # Already subscribed
                    btn.click()
                    self.human_delay(1, 2)
                    return True
            return False
        except Exception:
            return False

    def reply_to_comment_element(self, page: Page, comment_element, reply_text: str) -> bool:
        """Finds the reply button inside a comment thread and posts a reply."""
        try:
            # Scroll comment into view
            comment_element.scroll_into_view_if_needed()
            self.human_delay(1, 2)

            reply_btn = comment_element.query_selector("#reply-button-end button, ytd-button-renderer#reply-button-end button, button[aria-label*='Reply' i]")
            if not reply_btn:
                return False

            reply_btn.click()
            self.human_delay(1.5, 2.5)

            # Find reply input box
            reply_input = page.wait_for_selector(
                "ytd-commentbox #contenteditable-root, #contenteditable-root[aria-label*='reply' i]",
                timeout=7000
            )
            if not reply_input:
                return False

            reply_input.click()
            for char in reply_text:
                page.keyboard.type(char)
                time.sleep(random.uniform(0.04, 0.10))

            self.human_delay(1.5, 3.0)

            # Click reply submit button
            submit_btn = page.query_selector("ytd-commentbox #submit-button button, #submit-button button")
            if submit_btn and submit_btn.is_enabled():
                submit_btn.click()
                self.human_delay(3, 4)
                return True
            else:
                page.keyboard.press("Control+Enter")
                self.human_delay(3, 4)
                return True

        except Exception as e:
            print(f"[-] Error submitting reply: {e}")
            return False

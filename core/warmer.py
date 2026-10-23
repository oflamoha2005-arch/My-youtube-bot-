import os
import sys
import time
import random
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
from playwright.sync_api import Page

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.database import Database
from core.browser_manager import BrowserManager

class ChannelWarmer:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.warmer_settings = config.get("warmer_settings", {})
        self.safety_limits = config.get("safety_limits", {})
        self.accounts = config.get("accounts", [])

    def search_niche_videos(self, page: Page, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Searches YouTube for niche keywords and extracts relevant video links."""
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            self.browser_mgr.human_delay(3, 5)

            # Scroll a bit to load results
            self.browser_mgr.human_scroll(page, distance=500)
            self.browser_mgr.human_delay(1.5, 3.0)

            video_elements = page.query_selector_all("ytd-video-renderer, ytd-grid-video-renderer")
            results = []

            for elem in video_elements:
                title_elem = elem.query_selector("#video-title")
                if not title_elem:
                    continue

                title = title_elem.inner_text().strip()
                href = title_elem.get_attribute("href")
                if not href or "/watch?v=" not in href:
                    continue

                video_id = href.split("v=")[1].split("&")[0]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                results.append({
                    "video_id": video_id,
                    "title": title,
                    "url": video_url
                })

                if len(results) >= limit:
                    break

            return results
        except Exception as e:
            print(f"[-] Search error for '{query}': {e}")
            return []

    def simulate_human_viewing(self, page: Page, min_sec: int, max_sec: int):
        """Simulates authentic human watching with pauses, small mouse moves, and scrolling."""
        watch_duration = random.randint(min_sec, max_sec)
        print(f"  [👀] Watching video for {watch_duration}s with natural behavior...")

        elapsed = 0
        while elapsed < watch_duration:
            chunk = random.randint(15, 30)
            time.sleep(chunk)
            elapsed += chunk

            # Human micro-actions during watching
            action = random.choice(["scroll_comments", "pause_play", "small_scroll", "nothing"])
            if action == "scroll_comments":
                self.browser_mgr.human_scroll(page, distance=random.randint(300, 600))
                time.sleep(random.uniform(2, 5))
                # Scroll back up a bit
                page.evaluate("window.scrollBy(0, -250)")
            elif action == "small_scroll":
                self.browser_mgr.human_scroll(page, distance=random.randint(150, 300))
            elif action == "pause_play":
                # Subtle tap on space or k
                pass

    def warm_account(self, account_config: Dict[str, Any], count: int = 3):
        """Runs an organic warming session for a specific account."""
        acc_id = account_config["id"]
        acc_name = account_config["name"]
        keywords = self.warmer_settings.get("niche_search_keywords", ["psychological thriller books"])
        like_prob = self.warmer_settings.get("like_probability", 0.41)         # 41%
        sub_prob = self.warmer_settings.get("subscribe_probability", 0.21)     # 21%
        min_watch = self.warmer_settings.get("min_watch_seconds", 60)
        max_watch = self.warmer_settings.get("max_watch_seconds", 180)

        print(f"\n[☕ WARMER] Starting organic session for: {acc_name}")
        print(f"  Target parameters: 41% Like chance, 21% Sub chance, Niche-only videos")

        context, page = self.browser_mgr.launch_account_context(acc_id)
        try:
            # Pick a random niche query
            query = random.choice(keywords)
            print(f"  [🔍] Searching niche topic: '{query}'")
            videos = self.search_niche_videos(page, query, limit=count + 3)

            watched_count = 0
            for vid in videos:
                if watched_count >= count:
                    break

                video_id = vid["video_id"]
                video_title = vid["title"]
                video_url = vid["url"]

                # Global de-duplication: NO other account will ever watch a video already watched!
                if self.db.is_video_warmed_globally(video_id):
                    print(f"  [⏭] Video '{video_title[:40]}...' already watched by another account. Skipping.")
                    continue

                print(f"\n  [🎬] Playing ({watched_count + 1}/{count}): {video_title[:60]}...")
                page.goto(video_url, wait_until="domcontentloaded", timeout=35000)
                self.browser_mgr.human_delay(3, 5)

                # Simulate human watching
                self.simulate_human_viewing(page, min_watch, max_watch)

                # Probabilistic Like (41%)
                did_like = False
                if random.random() < like_prob:
                    did_like = self.browser_mgr.like_video(page)
                    if did_like:
                        print("  [👍] Liked video! (Met 41% probability)")

                # Probabilistic Subscribe (21%)
                did_sub = False
                if random.random() < sub_prob:
                    did_sub = self.browser_mgr.subscribe_channel(page)
                    if did_sub:
                        print("  [🔔] Subscribed to channel! (Met 21% probability)")

                # Log to DB
                self.db.log_warmer_session(
                    account_id=acc_id,
                    video_id=video_id,
                    video_title=video_title,
                    watch_time_seconds=random.randint(min_watch, max_watch),
                    liked=did_like,
                    subscribed=did_sub
                )
                watched_count += 1

                # Rest between videos
                time.sleep(random.uniform(5, 12))

            print(f"[✓] Warmer session completed for {acc_name}: {watched_count} niche videos watched organically.")

        except Exception as e:
            print(f"[-] Warmer error for {acc_name}: {e}")
        finally:
            try:
                context.close()
            except Exception:
                pass

    def warm_all_accounts(self):
        """Warms all enabled accounts in sequence."""
        for acc in self.accounts:
            if acc.get("enabled", True):
                self.warm_account(acc, count=self.warmer_settings.get("videos_per_session_per_account", 3))
                time.sleep(random.uniform(10, 20))

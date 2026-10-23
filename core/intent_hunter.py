import os
import sys
import time
import random
from typing import Dict, Any, List
from playwright.sync_api import Page

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.database import Database
from core.browser_manager import BrowserManager
from core.ai_engine import AIEngine
from core.warmer import ChannelWarmer

class IntentHunter:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager, ai_engine: AIEngine):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.ai_engine = ai_engine
        self.hunter_settings = config.get("intent_hunter_settings", {})
        self.safety_limits = config.get("safety_limits", {})
        self.accounts = [acc for acc in config.get("accounts", []) if acc.get("enabled", True)]
        self.warmer = ChannelWarmer(config, db, browser_mgr)

    def scan_and_reply_video_comments(self, page: Page, video_info: Dict[str, str], active_account: Dict[str, Any]) -> int:
        """
        Loads comments of a niche video, detects high-intent readers, and posts unique replies.
        """
        video_url = video_info["url"]
        video_title = video_info["title"]
        video_id = video_info["video_id"]
        acc_id = active_account["id"]
        acc_name = active_account["name"]

        print(f"\n[🕵️ HUNTER] Inspecting comments on: '{video_title[:60]}...'")
        replies_posted = 0
        max_replies = self.hunter_settings.get("max_replies_per_session", 4)
        delay_range = self.hunter_settings.get("delay_between_replies_sec", [60, 140])

        try:
            page.goto(video_url, wait_until="domcontentloaded", timeout=40000)
            self.browser_mgr.human_delay(3, 5)

            # Scroll to trigger comments
            self.browser_mgr.human_scroll(page, distance=800)
            self.browser_mgr.human_delay(3, 5)

            # Scroll a few more times to load multiple comment batches
            for _ in range(3):
                self.browser_mgr.human_scroll(page, distance=600)
                time.sleep(random.uniform(1.5, 2.5))

            comment_threads = page.query_selector_all("ytd-comment-thread-renderer")
            print(f"  Found {len(comment_threads)} comment threads to evaluate.")

            for thread in comment_threads:
                if replies_posted >= max_replies:
                    break

                # Extract author & comment text
                author_elem = thread.query_selector("#author-text span, #author-text")
                content_elem = thread.query_selector("#content-text, yt-formatted-string#content-text")

                if not content_elem or not author_elem:
                    continue

                author_name = author_elem.inner_text().strip().replace("@", "")
                comment_text = content_elem.inner_text().strip()

                if len(comment_text) < 15:
                    continue

                # Unique ID for tracking (hash or composite of video_id + author_name)
                comment_key = f"{video_id}_{author_name}_{hash(comment_text)}"

                # Global de-duplication: Ensure NO account ever replies to the same person or comment twice!
                if self.db.is_comment_replied(comment_key) or self.db.is_person_replied(author_name):
                    continue

                # Check if this comment expresses reader intent
                reply_text = self.ai_engine.evaluate_and_reply_intent(comment_text, author_name, video_title)
                if not reply_text:
                    continue

                print(f"\n  [🎯 High Intent Found!] @{author_name} said: \"{comment_text[:80]}...\"")
                print(f"  [{acc_name}] Crafting tailored reply:")
                print(f"    \"{reply_text}\"")

                # Submit reply
                success = self.browser_mgr.reply_to_comment_element(page, thread, reply_text)
                if success:
                    replies_posted += 1
                    self.db.log_intent_reply(
                        comment_id=comment_key,
                        video_id=video_id,
                        video_title=video_title,
                        target_author=author_name,
                        original_comment=comment_text,
                        account_id=acc_id,
                        reply_text=reply_text
                    )
                    print(f"  [✓] Successfully replied to @{author_name}! ({replies_posted}/{max_replies})")

                    # Human-like delay between replies to stay 100% undetected
                    delay = random.uniform(delay_range[0], delay_range[1])
                    print(f"  [⏳] Resting for {delay:.1f}s before checking next comment...")
                    time.sleep(delay)

        except Exception as e:
            print(f"[-] Error hunting comments: {e}")

        return replies_posted

    def run_hunting_session(self):
        """Runs a complete high-intent reply hunting session across niche videos."""
        keywords = self.config.get("warmer_settings", {}).get("niche_search_keywords", [
            "psychological thriller book recommendations",
            "mystery thriller books plot twist"
        ])

        if not self.accounts:
            print("[!] No enabled accounts configured for Intent Hunter.")
            return

        # Rotate through accounts
        active_account = random.choice(self.accounts)
        print(f"\n[🚀 INTENT HUNTER] Active Account: {active_account['name']}")

        context, page = self.browser_mgr.launch_account_context(active_account["id"])
        try:
            # Search relevant niche videos
            query = random.choice(keywords)
            videos = self.warmer.search_niche_videos(page, query, limit=3)

            total_replies = 0
            for vid in videos:
                replies = self.scan_and_reply_video_comments(page, vid, active_account)
                total_replies += replies
                if total_replies >= self.hunter_settings.get("max_replies_per_session", 4):
                    break

            print(f"\n[✓] Intent Hunter session finished: Posted {total_replies} highly targeted replies.")
        finally:
            try:
                context.close()
            except Exception:
                pass

import os
import re
import sys
import time
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.database import Database
from core.browser_manager import BrowserManager
from core.ai_engine import AIEngine

class TopCommentSniper:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager, ai_engine: AIEngine):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.ai_engine = ai_engine
        self.sniper_settings = config.get("sniper_settings", {})
        self.accounts = config.get("accounts", [])
        self.safety_limits = config.get("safety_limits", {})
        self._channel_id_cache: Dict[str, str] = {}

    def resolve_channel_id(self, channel_url: str) -> Optional[str]:
        """Resolves the permanent channel ID from a channel URL or handle (@name)."""
        if channel_url in self._channel_id_cache:
            return self._channel_id_cache[channel_url]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        try:
            resp = requests.get(channel_url, headers=headers, timeout=12)
            if resp.status_code == 200:
                m = re.search(r'\"externalId\":\"([a-zA-Z0-9_-]+)\"', resp.text)
                if not m:
                    m = re.search(r'\"channelId\":\"([a-zA-Z0-9_-]+)\"', resp.text)
                if not m:
                    m = re.search(r'channel_id=([a-zA-Z0-9_-]+)', resp.text)

                if m:
                    cid = m.group(1)
                    self._channel_id_cache[channel_url] = cid
                    return cid
        except Exception:
            pass
        return None

    def fetch_latest_channel_video(self, channel_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest upload via YouTube's public XML RSS feed or /videos fallback.
        Ultra-fast (milliseconds) and consumes zero browser resources.
        """
        ch_name = channel_info.get("name", "Target Channel")
        ch_url = channel_info.get("url", "")
        ch_id = channel_info.get("channel_id", "")

        # Auto-resolve channel_id if missing or empty
        if not ch_id and ch_url:
            ch_id = self.resolve_channel_id(ch_url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }

        # Method 1: RSS Feed (Fastest & most accurate)
        if ch_id:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch_id}"
            try:
                resp = requests.get(rss_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    ns = {
                        'atom': 'http://www.w3.org/2005/Atom',
                        'yt': 'http://www.youtube.com/xml/schemas/2015'
                    }
                    entries = root.findall('atom:entry', ns)
                    if entries:
                        latest = entries[0]
                        vid_elem = latest.find('yt:videoId', ns)
                        title_elem = latest.find('atom:title', ns)
                        pub_elem = latest.find('atom:published', ns)

                        if vid_elem is not None and title_elem is not None:
                            video_id = vid_elem.text
                            title = title_elem.text
                            pub_str = pub_elem.text if pub_elem is not None else ""

                            age_minutes = 9999.0
                            if pub_str:
                                try:
                                    pub_dt = datetime.fromisoformat(pub_str)
                                    now_dt = datetime.now(timezone.utc)
                                    age_minutes = max(0.0, (now_dt - pub_dt).total_seconds() / 60)
                                except Exception:
                                    pass

                            return {
                                "video_id": video_id,
                                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                                "title": title,
                                "channel_name": ch_name,
                                "published_at": pub_str,
                                "age_minutes": age_minutes
                            }
            except Exception:
                pass

        # Method 2: Direct /videos HTML Fallback
        if ch_url:
            try:
                vid_url = ch_url.rstrip("/") + "/videos"
                resp = requests.get(vid_url, headers=headers, timeout=12)
                if resp.status_code == 200:
                    v_matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', resp.text)
                    if v_matches:
                        latest_id = v_matches[0]
                        return {
                            "video_id": latest_id,
                            "video_url": f"https://www.youtube.com/watch?v={latest_id}",
                            "title": f"Upload by {ch_name}",
                            "channel_name": ch_name,
                            "published_at": "",
                            "age_minutes": 15.0  # Fresh fallback estimate
                        }
            except Exception:
                pass

        return None

    def snipe_video_with_accounts(self, video_info: Dict[str, Any]):
        """
        Executes multi-account staggered commenting on a fresh video.
        Account 1, Account 2, Account 3 each post a unique comment.
        """
        video_id = video_info["video_id"]
        video_url = video_info["video_url"]
        video_title = video_info["title"]
        channel_name = video_info["channel_name"]

        print(f"\n[🎯 SNIPER TRIGGERED] Target: '{video_title}' on {channel_name} (Age: {video_info['age_minutes']:.1f} mins)")
        self.db.register_sniped_video(video_id, channel_name, video_title, video_url, video_info["published_at"])

        stagger_range = self.sniper_settings.get("stagger_delay_between_accounts_sec", [45, 110])
        max_daily_comments = self.safety_limits.get("max_sniper_comments_per_account_daily", 15)

        enabled_accounts = [acc for acc in self.accounts if acc.get("enabled", True)]

        for idx, acc in enumerate(enabled_accounts, 1):
            acc_id = acc["id"]
            acc_name = acc["name"]

            # Safety check: already commented?
            if self.db.is_video_sniped_by_account(video_id, acc_id):
                print(f"[*] Account {acc_name} already commented on this video. Skipping.")
                continue

            # Safety check: daily limit
            daily_act = self.db.get_account_daily_activity(acc_id)
            if daily_act["sniper_comments"] >= max_daily_comments:
                print(f"[!] Account {acc_name} reached daily comment limit ({max_daily_comments}). Skipping.")
                continue

            # Generate unique comment for this account
            comment_text = self.ai_engine.generate_sniper_comment(acc, video_title, channel_name)
            print(f"\n[{acc_name}] Generated Comment:")
            print(f"  \"{comment_text}\"")

            # Post comment via Playwright
            context, page = self.browser_mgr.launch_account_context(acc_id)
            try:
                success = self.browser_mgr.post_video_comment(page, video_url, comment_text)
                if success:
                    self.db.log_comment(video_id, acc_id, acc_name, comment_text, comment_type='sniper')
                    print(f"[✓] {acc_name} successfully sniped comment!")
                else:
                    print(f"[-] {acc_name} could not post comment. Check login state or video settings.")
            except Exception as e:
                print(f"[-] Error during {acc_name} commenting: {e}")
            finally:
                try:
                    context.close()
                except Exception:
                    pass

            # Stagger delay before next account posts (to look 100% natural and organic)
            if idx < len(enabled_accounts):
                delay = random.uniform(stagger_range[0], stagger_range[1])
                print(f"[⏳] Waiting {delay:.1f}s before dispatching next account...")
                time.sleep(delay)

    def scan_channels_once(self) -> int:
        """Scans all configured target channels for fresh videos."""
        target_channels = self.sniper_settings.get("target_channels", [])
        max_age = self.sniper_settings.get("max_video_age_minutes", 60)
        fresh_videos_found = 0

        print(f"\n[🔎] Scanning {len(target_channels)} target channels for new uploads...")
        for ch in target_channels:
            video = self.fetch_latest_channel_video(ch)
            if not video:
                continue

            # Check if video is fresh and hasn't been sniped by all accounts yet
            if video["age_minutes"] <= max_age:
                any_pending = any(
                    not self.db.is_video_sniped_by_account(video["video_id"], acc["id"])
                    for acc in self.accounts if acc.get("enabled", True)
                )
                if any_pending:
                    fresh_videos_found += 1
                    self.snipe_video_with_accounts(video)

            # Polite pause between channel queries
            time.sleep(1.0)

        return fresh_videos_found

    def run_daemon_loop(self):
        """Continuously monitors target channels at configured interval."""
        interval = self.sniper_settings.get("check_interval_seconds", 120)
        print(f"[🚀] Sniper Daemon started! Checking every {interval}s. Press Ctrl+C to stop.")
        try:
            while True:
                found = self.scan_channels_once()
                if found == 0:
                    print(f"[☕] No fresh unscored uploads found. Sleeping {interval}s...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[!] Sniper Daemon stopped by user.")

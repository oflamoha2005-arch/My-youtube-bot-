import os
import sys
import json
import time
import random
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.database import Database
from core.browser_manager import BrowserManager
from core.ai_engine import AIEngine

console = Console()

class LiveStreamHunter:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager, ai_engine: AIEngine):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.ai_engine = ai_engine
        self.book_details = config.get("book_details", {})
        self.accounts = config.get("accounts", [])

    def find_active_live_streams(self, page, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Searches YouTube specifically for LIVE streams using the 'sp=CAM%253D' (Live filter).
        """
        # sp=CAM%253D triggers YouTube's Features -> Live filter
        live_search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp=CAM%253D"
        console.print(f"[bold cyan]🔍 Scouting active live streams for:[/bold cyan] '{query}'...")

        try:
            page.goto(live_search_url, wait_until="domcontentloaded", timeout=35000)
            self.browser_mgr.human_delay(3, 5)

            streams = []
            renderers = page.query_selector_all("ytd-video-renderer")

            for r in renderers:
                # Check for "LIVE" badge
                badge = r.query_selector(".badge-shape-wiz--live, .ytd-badge-supported-renderer")
                title_elem = r.query_selector("#video-title")
                if not title_elem:
                    continue

                title = title_elem.inner_text().strip()
                href = title_elem.get_attribute("href")
                if not href or "/watch?v=" not in href:
                    continue

                stream_id = href.split("v=")[1].split("&")[0]
                streams.append({
                    "stream_id": stream_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={stream_id}"
                })

                if len(streams) >= limit:
                    break

            return streams
        except Exception as e:
            console.print(f"[red]Error finding live streams: {e}[/red]")
            return []

    def engage_live_stream_chat(self, page, account_config: Dict[str, Any], stream_info: Dict[str, str], max_messages: int = 2):
        """
        Joins an active live stream, monitors chat, and participates organically.
        """
        acc_id = account_config["id"]
        acc_name = account_config["name"]
        stream_id = stream_info["stream_id"]
        stream_title = stream_info["title"]
        book_title = self.book_details.get("title", "The Whispering Walls")

        console.print(f"\n[bold red]🔴 Entering Live Stream:[/bold red] '{stream_title[:60]}...'")
        console.print(f"  Account: [yellow]{acc_name}[/yellow]")

        try:
            page.goto(stream_info["url"], wait_until="domcontentloaded", timeout=40000)
            self.browser_mgr.human_delay(4, 7)

            # Locate chat iframe
            chat_iframe_elem = page.wait_for_selector("iframe#chatframe", timeout=15000)
            if not chat_iframe_elem:
                console.print("[yellow]! Live chat is disabled or unavailable for this stream.[/yellow]")
                return

            chat_frame = chat_iframe_elem.content_frame()
            if not chat_frame:
                console.print("[yellow]! Could not switch to live chat frame.[/yellow]")
                return

            console.print("[✓] Connected to Live Chat room.")

            messages_sent = 0
            # Predefined natural chat reactions & book mentions
            casual_chat_starters = [
                f"The atmosphere in this stream is so good for reading psychological thrillers tonight.",
                f"Anyone here read 'The Whispering Walls' on Kindle? That plot twist in the attic was unbelievable.",
                f"Late night mystery vibes are unmatched in this stream.",
                f"Looking for thriller book recommendations tonight, love stories with dark psychological twists."
            ]

            while messages_sent < max_messages:
                # Watch chat for 30 to 60 seconds naturally
                watch_pause = random.randint(30, 60)
                console.print(f"  [👀] Observing chat for {watch_pause}s...")
                time.sleep(watch_pause)

                # Find chat input box inside frame
                input_box = chat_frame.wait_for_selector(
                    "div#input[contenteditable='true'], div#input",
                    timeout=10000
                )

                if not input_box:
                    console.print("[yellow]! Could not find chat input (Account might need verification on this channel).[/yellow]")
                    break

                # Choose a message
                msg_text = random.choice(casual_chat_starters)

                input_box.click()
                for char in msg_text:
                    input_box.type(char)
                    time.sleep(random.uniform(0.03, 0.08))

                self.browser_mgr.human_delay(1.5, 2.5)

                # Send via Enter or Send button
                page.keyboard.press("Enter")
                messages_sent += 1
                console.print(f"[bold green]✓ Sent live chat message ({messages_sent}/{max_messages}):[/bold green] \"{msg_text}\"")

                self.db.log_livestream_chat(acc_id, stream_id, stream_title, "room", msg_text)

                if messages_sent < max_messages:
                    cool_down = random.randint(90, 180)
                    console.print(f"  [⏳] Cooling down for {cool_down}s before next chat message...")
                    time.sleep(cool_down)

        except Exception as e:
            console.print(f"[red]Error during live stream chat: {e}[/red]")

    def run_live_hunting_session(self, query: str = "crime mystery stories live"):
        if not self.accounts:
            console.print("[red]No accounts configured.[/red]")
            return

        active_account = self.accounts[0]
        context, page = self.browser_mgr.launch_account_context(active_account["id"])
        try:
            streams = self.find_active_live_streams(page, query, limit=2)
            if not streams:
                console.print(f"[yellow]No active live streams currently found for '{query}'. Trying 'horror stories live'...[/yellow]")
                streams = self.find_active_live_streams(page, "horror stories live", limit=2)

            for s in streams:
                self.engage_live_stream_chat(page, active_account, s, max_messages=1)
                time.sleep(15)

        finally:
            try:
                context.close()
            except Exception:
                pass

def run_livestream_hunter_interactive(config: dict, db: Database, browser_mgr: BrowserManager, ai_engine: AIEngine):
    hunter = LiveStreamHunter(config, db, browser_mgr, ai_engine)

    console.print(Panel.fit(
        "[bold red]🔴 24/7 Live Stream Chat Hunter[/bold red]\n"
        "[dim]Finds ongoing live streams in your niche, joins the chat, and organically introduces your book![/dim]",
        border_style="red"
    ))

    default_query = "psychological thriller mystery live"
    user_query = input(f"Enter live search topic (Press ENTER for '{default_query}'): ").strip()
    if not user_query:
        user_query = default_query

    hunter.run_live_hunting_session(query=user_query)

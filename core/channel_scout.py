import os
import sys
import re
import json
import time
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.database import Database
from core.sniper import TopCommentSniper

console = Console()
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

class NicheChannelScout:
    def __init__(self, config: Dict[str, Any], db: Database):
        self.config = config
        self.db = db
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

    def resolve_channel_id(self, channel_url: str) -> Optional[str]:
        """Fetches the channel page and extracts its permanent channel_id."""
        try:
            resp = requests.get(channel_url, headers=self.headers, timeout=12)
            if resp.status_code == 200:
                m = re.search(r'\"externalId\":\"([a-zA-Z0-9_-]+)\"', resp.text)
                if not m:
                    m = re.search(r'\"channelId\":\"([a-zA-Z0-9_-]+)\"', resp.text)
                if not m:
                    m = re.search(r'channel_id=([a-zA-Z0-9_-]+)', resp.text)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None

    def scout_channels_by_query(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Discovers active YouTube channels ranking for a specific niche query.
        Uses Type=Channel filter (sp=EgIQAg%253D%253D) and video creator extraction.
        """
        console.print(f"[bold cyan]🔍 Scouting YouTube for top channels in:[/bold cyan] '{query}'...")
        discovered = []
        seen_urls = set()

        # Existing channels in config
        existing_urls = {
            ch.get("url", "").rstrip("/").lower()
            for ch in self.config.get("sniper_settings", {}).get("target_channels", [])
        }

        # 1. Search Channels directly (sp=EgIQAg%253D%253D)
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp=EgIQAg%253D%253D"
        try:
            resp = requests.get(search_url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                # Find channel links: /@handle or /channel/UC...
                channel_matches = re.findall(r'\"canonicalBaseUrl\":\"(/@[a-zA-Z0-9_.-]+)\"', resp.text)
                title_matches = re.findall(r'\"channelTitle\":\"([^\"]+)\"', resp.text)

                for handle in channel_matches:
                    full_url = f"https://www.youtube.com{handle}"
                    if full_url.lower() in existing_urls or full_url in seen_urls:
                        continue

                    # Extract name from handle
                    ch_name = handle.replace("/@", "")
                    seen_urls.add(full_url)
                    discovered.append({
                        "name": ch_name,
                        "url": full_url
                    })

                    if len(discovered) >= limit:
                        break
        except Exception as e:
            console.print(f"[dim]Search channels note: {e}[/dim]")

        # 2. Search Top Videos if we need more channels
        if len(discovered) < limit:
            try:
                vid_search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                resp2 = requests.get(vid_search_url, headers=self.headers, timeout=15)
                if resp2.status_code == 200:
                    handles = re.findall(r'\"canonicalBaseUrl\":\"(/@[a-zA-Z0-9_.-]+)\"', resp2.text)
                    for handle in handles:
                        full_url = f"https://www.youtube.com{handle}"
                        if full_url.lower() in existing_urls or full_url in seen_urls:
                            continue

                        ch_name = handle.replace("/@", "")
                        seen_urls.add(full_url)
                        discovered.append({
                            "name": ch_name,
                            "url": full_url
                        })

                        if len(discovered) >= limit:
                            break
            except Exception:
                pass

        # Resolve permanent channel IDs for all discovered channels
        final_list = []
        for ch in discovered:
            console.print(f"  [⏳] Resolving permanent ID for: [yellow]{ch['name']}[/yellow] ({ch['url']})...")
            cid = self.resolve_channel_id(ch["url"])
            if cid:
                ch["channel_id"] = cid
                final_list.append(ch)
                console.print(f"  [green]✓ Found ID:[/green] {cid}")
            else:
                console.print(f"  [dim]Could not resolve ID, skipping.[/dim]")
            time.sleep(1.0)

        return final_list

    def save_channels_to_config(self, new_channels: List[Dict[str, str]], query: str) -> int:
        """Appends verified discovered channels into config.json and SQLite database."""
        if not new_channels:
            return 0

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        target_channels = config.setdefault("sniper_settings", {}).setdefault("target_channels", [])
        existing_ids = {ch.get("channel_id") for ch in target_channels if ch.get("channel_id")}

        added_count = 0
        for ch in new_channels:
            if ch["channel_id"] not in existing_ids:
                target_channels.append(ch)
                existing_ids.add(ch["channel_id"])
                added_count += 1
                self.db.log_scouted_channel(ch["name"], ch["url"], ch["channel_id"], query)

        if added_count > 0:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.config = config

        return added_count

def run_channel_scout_interactive(config: dict, db: Database):
    scout = NicheChannelScout(config, db)

    console.print(Panel.fit(
        "[bold cyan]🔍 Niche Channel Auto-Scout & Pipeline Feeder[/bold cyan]\n"
        "[dim]Automatically searches YouTube for top active channels in your niche, resolves IDs,\n"
        "and adds them directly to the Sniper's target list![/dim]",
        border_style="cyan"
    ))

    default_keywords = [
        "psychological thriller books",
        "mystery crime stories breakdown",
        "booktube thriller reviews",
        "dark mystery podcast"
    ]

    console.print("[bold yellow]Choose a search mode:[/bold yellow]")
    console.print("  [1] ⚡ Quick Auto-Scout using default niche keywords")
    console.print("  [2] ✍️  Custom Niche Keyword Search")
    console.print("  [0] 🔙 Return to Menu")

    choice = input("\nEnter choice (0-2): ").strip()
    if choice == "0":
        return

    queries = []
    if choice == "1":
        queries = default_keywords
    elif choice == "2":
        custom_q = input("Enter custom niche topic to scout (e.g. 'horror stories true crime'): ").strip()
        queries = [custom_q] if custom_q else default_keywords
    else:
        return

    total_added = 0
    all_discovered = []

    for q in queries:
        discovered = scout.scout_channels_by_query(q, limit=3)
        if discovered:
            added = scout.save_channels_to_config(discovered, q)
            total_added += added
            all_discovered.extend(discovered)
        time.sleep(1.5)

    if all_discovered:
        table = Table(title="Newly Scouted Channels Added to Sniper Pool", style="green")
        table.add_column("Channel Name", style="bold yellow")
        table.add_column("URL", style="white")
        table.add_column("Permanent Channel ID", style="cyan")

        for ch in all_discovered:
            table.add_row(ch["name"], ch["url"], ch["channel_id"])

        console.print(table)
        console.print(f"\n[bold green]✓ Successfully added {total_added} new channels to config.json target list![/bold green]")
        console.print("[dim]The Top-Comment Sniper will now automatically monitor all of these channels for fresh uploads![/dim]")
    else:
        console.print("[yellow]No new unique channels found that aren't already in your target list.[/yellow]")

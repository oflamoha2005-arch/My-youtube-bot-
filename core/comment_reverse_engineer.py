import os
import sys
import re
import json
import time
import random
from typing import Dict, Any, List
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
from core.warmer import ChannelWarmer

console = Console()

class CommentReverseEngineer:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.warmer = ChannelWarmer(config, db, browser_mgr)

    def scrape_top_comments_from_video(self, page, video_info: Dict[str, str], min_likes: int = 50) -> List[Dict[str, Any]]:
        """
        Navigates to a viral video and scrapes the #1 Top and Pinned comments.
        """
        video_url = video_info["url"]
        video_title = video_info["title"]
        video_id = video_info["video_id"]

        console.print(f"\n[bold cyan]🔬 Reverse-Engineering Top Comments on:[/bold cyan] '{video_title[:55]}...'")

        try:
            page.goto(video_url, wait_until="domcontentloaded", timeout=40000)
            self.browser_mgr.human_delay(3, 5)

            # Scroll down to trigger comments section
            self.browser_mgr.human_scroll(page, distance=800)
            self.browser_mgr.human_delay(3, 4)

            for _ in range(3):
                self.browser_mgr.human_scroll(page, distance=500)
                time.sleep(1.5)

            comment_threads = page.query_selector_all("ytd-comment-thread-renderer")
            extracted = []

            for thread in comment_threads[:15]:
                content_elem = thread.query_selector("#content-text, yt-formatted-string#content-text")
                author_elem = thread.query_selector("#author-text span, #author-text")
                likes_elem = thread.query_selector("#vote-count-middle")
                pinned_badge = thread.query_selector("ytd-pinned-comment-badge-renderer")

                if not content_elem:
                    continue

                comment_text = content_elem.inner_text().strip()
                author = author_elem.inner_text().strip().replace("@", "") if author_elem else "Unknown"

                # Parse like count string (e.g. "1.2K", "450", "12K")
                likes_text = likes_elem.inner_text().strip() if likes_elem else "0"
                likes_count = self._parse_likes_string(likes_text)

                is_pinned = pinned_badge is not None

                # We want winning comments (either pinned or has noticeable upvotes)
                if likes_count >= min_likes or is_pinned:
                    pattern_type = self._classify_comment_pattern(comment_text)
                    extracted.append({
                        "video_id": video_id,
                        "video_title": video_title,
                        "author": author,
                        "likes_count": likes_count,
                        "comment_text": comment_text,
                        "is_pinned": is_pinned,
                        "pattern_type": pattern_type
                    })

                    # Save to DB vault
                    self.db.save_top_comment(video_id, video_title, author, likes_count, comment_text, pattern_type)

            console.print(f"[✓] Extracted & analyzed {len(extracted)} viral comment blueprints!")
            return extracted

        except Exception as e:
            console.print(f"[red]Error scraping top comments: {e}[/red]")
            return []

    def _parse_likes_string(self, text: str) -> int:
        text = text.upper().strip()
        if not text:
            return 0
        try:
            if "K" in text:
                return int(float(text.replace("K", "").strip()) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "").strip()) * 1000000)
            elif text.isdigit():
                return int(text)
        except Exception:
            pass
        return 0

    def _classify_comment_pattern(self, text: str) -> str:
        """Classifies the psychological driver of why this comment went viral."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["the fact that", "the way he", "the way she", "notice how"]):
            return "Observation_Hook"
        elif any(w in text_lower for w in ["i love how", "nobody talks about", "underrated"]):
            return "Respectful_Awe"
        elif any(w in text_lower for w in ["literally", "my jaw", "gave me chills", "not sleeping"]):
            return "Emotional_Reaction"
        elif "?" in text:
            return "Debate_Trigger"
        return "Relatable_Humor"

    def analyze_winning_formula(self) -> Dict[str, Any]:
        """Reads stored top comments and derives the mathematical & structural winning formula."""
        examples = self.db.get_top_comments_examples(limit=25)
        if not examples:
            return {"total_analyzed": 0, "patterns": []}

        word_counts = [len(c.split()) for c in examples]
        avg_words = sum(word_counts) // len(word_counts) if word_counts else 15

        # Detect common opening hooks
        hooks = []
        for c in examples:
            words = c.split()
            if len(words) >= 3:
                hooks.append(" ".join(words[:3]))

        return {
            "total_analyzed": len(examples),
            "average_word_count": avg_words,
            "top_examples": examples[:5],
            "common_hooks": list(set(hooks))[:6]
        }

def run_reverse_engineer_interactive(config: dict, db: Database, browser_mgr: BrowserManager):
    engineer = CommentReverseEngineer(config, db, browser_mgr)

    console.print(Panel.fit(
        "[bold cyan]🧠 Top Comments Reverse-Engineer[/bold cyan]\n"
        "[dim]Scrapes viral & pinned comments from top videos, decodes their winning formula, and feeds your AI![/dim]",
        border_style="cyan"
    ))

    console.print("[bold]Select an action:[/bold]")
    console.print("  [1] 🔬 Scout & Reverse-Engineer Top Comments from Niche Videos")
    console.print("  [2] 📊 View Winning Formula DNA & Top Examples Saved in Vault")
    console.print("  [0] 🔙 Return")

    choice = input("\nEnter choice (0-2): ").strip()

    if choice == "1":
        accounts = config.get("accounts", [])
        if not accounts:
            console.print("[red]No accounts configured.[/red]")
            return

        niche_query = input("Enter niche to scout (default: 'psychological thriller mystery breakdown'): ").strip()
        if not niche_query:
            niche_query = "psychological thriller mystery breakdown"

        context, page = browser_mgr.launch_account_context(accounts[0]["id"])
        try:
            videos = engineer.warmer.search_niche_videos(page, niche_query, limit=3)
            total = 0
            for vid in videos:
                res = engineer.scrape_top_comments_from_video(page, vid, min_likes=20)
                total += len(res)
                time.sleep(3)
            console.print(f"\n[bold green]✓ Done! Stored {total} high-upvote blueprints into top_comments_vault![/bold green]")
        finally:
            try:
                context.close()
            except Exception:
                pass

    elif choice == "2":
        formula = engineer.analyze_winning_formula()
        console.print(f"\n[bold green]Vault Analysis: {formula['total_analyzed']} winning comments stored[/bold green]")
        console.print(f"• Average word length: [yellow]{formula.get('average_word_count', 0)} words[/yellow] (Sweet spot for Top Comments)")

        table = Table(title="Top High-Upvote Blueprints in Vault", style="magenta")
        table.add_column("#", justify="center")
        table.add_column("Winning Comment Text", style="white")

        for idx, ex in enumerate(formula.get("top_examples", []), 1):
            table.add_row(str(idx), ex)

        console.print(table)

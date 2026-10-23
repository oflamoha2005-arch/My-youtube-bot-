import os
import sys
import json
import time
import random
from typing import Dict, Any, List, Optional
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

console = Console()

class CommentCrossBooster:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.accounts = [acc for acc in config.get("accounts", []) if acc.get("enabled", True)]
        self.book_details = config.get("book_details", {})

    def boost_comment_on_video(self, video_url: str, target_comment_text: str, author_account_id: str = ""):
        """
        Dispatches all other accounts in the fleet to upvote (like) and hype the target comment.
        """
        book_title = self.book_details.get("title", "The Whispering Walls")
        video_id = video_url.split("v=")[1].split("&")[0] if "v=" in video_url else video_url

        # Filter out the account that actually posted the comment
        booster_accounts = [acc for acc in self.accounts if acc["id"] != author_account_id]
        if not booster_accounts:
            booster_accounts = self.accounts[1:] if len(self.accounts) > 1 else self.accounts

        console.print(f"\n[bold green]🚀 Launching Multi-Account Cross-Upvote Booster[/bold green]")
        console.print(f"  Target Video: [cyan]{video_url}[/cyan]")
        console.print(f"  Target Comment Snippet: [italic white]\"{target_comment_text[:60]}...\"[/italic white]")
        console.print(f"  Dispatching {len(booster_accounts)} booster accounts in sequence...\n")

        # Hype reply templates for Account 2 / booster
        hype_replies = [
            f"Wait, are you the author of '{book_title}'? That twist in the final chapters genuinely caught me off guard!",
            f"I just finished reading '{book_title}' on Kindle last weekend, couldn't put it down.",
            f"Is this the same author who wrote '{book_title}' on Amazon? Love your work!",
            f"Definitely agree with your point here, very observant!"
        ]

        likes_count = 0
        replies_count = 0

        for idx, acc in enumerate(booster_accounts, 1):
            acc_id = acc["id"]
            acc_name = acc["name"]
            console.print(f"[{idx}/{len(booster_accounts)}] [bold yellow]{acc_name}[/bold yellow] ({acc_id}) deploying...")

            context, page = self.browser_mgr.launch_account_context(acc_id)
            try:
                page.goto(video_url, wait_until="domcontentloaded", timeout=40000)
                self.browser_mgr.human_delay(3, 5)

                # Scroll to load comments
                self.browser_mgr.human_scroll(page, distance=700)
                self.browser_mgr.human_delay(2.5, 4)

                for _ in range(3):
                    self.browser_mgr.human_scroll(page, distance=500)
                    time.sleep(1.5)

                # Find the target comment thread
                comment_threads = page.query_selector_all("ytd-comment-thread-renderer")
                target_thread = None

                # Matching by text snippet
                clean_target = target_comment_text[:35].lower().strip()
                for thread in comment_threads:
                    text_elem = thread.query_selector("#content-text, yt-formatted-string#content-text")
                    if text_elem and clean_target in text_elem.inner_text().lower():
                        target_thread = thread
                        break

                if not target_thread and comment_threads:
                    # Fallback to the very first comment if it was freshly posted
                    target_thread = comment_threads[0]

                if target_thread:
                    target_thread.scroll_into_view_if_needed()
                    self.browser_mgr.human_delay(1, 2)

                    # Click Like button on the comment
                    like_btn = target_thread.query_selector(
                        "#like-button button, button[aria-label*='like' i], ytd-toggle-button-renderer#like-button button"
                    )

                    if like_btn:
                        # Check if already liked
                        pressed = like_btn.get_attribute("aria-pressed")
                        if pressed != "true":
                            like_btn.click()
                            likes_count += 1
                            console.print(f"  [bold green]👍 Liked target comment![/bold green]")
                            self.db.log_comment_boost(video_id, target_comment_text, acc_id, "like")
                            self.browser_mgr.human_delay(1.5, 2.5)

                    # If this is the second account in line, leave a hype reply!
                    if idx == 1 and len(booster_accounts) > 1:
                        reply_text = random.choice(hype_replies)
                        reply_success = self.browser_mgr.reply_to_comment_element(page, target_thread, reply_text)
                        if reply_success:
                            replies_count += 1
                            console.print(f"  [bold magenta]💬 Added Hype Reply:[/bold magenta] \"{reply_text}\"")
                            self.db.log_comment_boost(video_id, target_comment_text, acc_id, "reply")
                else:
                    console.print("  [yellow]! Could not find target comment thread on page.[/yellow]")

            except Exception as e:
                console.print(f"  [red]Error during boost: {e}[/red]")
            finally:
                try:
                    context.close()
                except Exception:
                    pass

            # Staggered natural delay between account visits
            if idx < len(booster_accounts):
                delay = random.uniform(25, 55)
                console.print(f"  [⏳] Resting {delay:.1f}s before next booster account...")
                time.sleep(delay)

        console.print(f"\n[bold green]✓ Boost Complete: +{likes_count} Likes & +{replies_count} Hype Replies added to comment![/bold green]")

def run_comment_booster_interactive(config: dict, db: Database, browser_mgr: BrowserManager):
    booster = CommentCrossBooster(config, db, browser_mgr)

    console.print(Panel.fit(
        "[bold green]👍 Multi-Account Comment Cross-Upvoter & Booster[/bold green]\n"
        "[dim]Uses your fleet of accounts to upvote your sniped comment and add organic hype replies\n"
        "to propel it straight to #1 Top Comment![/dim]",
        border_style="green"
    ))

    # Check database for recent sniped comments
    recent = db.get_recent_sniped_comments(limit=4)

    console.print("[bold yellow]Select a comment to boost:[/bold yellow]")
    if recent:
        for idx, c in enumerate(recent, 1):
            console.print(f"  [{idx}] Recent from '{c['video_title'][:35]}...':")
            console.print(f"      [dim]\"{c['comment_text'][:65]}...\"[/dim]")

        console.print(f"  [C] ✍️  Custom Video URL & Comment Text")
        console.print(f"  [0] 🔙 Cancel & Return")

        choice = input(f"\nEnter choice (1-{len(recent)}, C, 0): ").strip()
        if choice == "0":
            return
        elif choice.isdigit() and 1 <= int(choice) <= len(recent):
            selected = recent[int(choice) - 1]
            booster.boost_comment_on_video(
                video_url=selected["video_url"],
                target_comment_text=selected["comment_text"],
                author_account_id=selected.get("account_id", "")
            )
            return

    # Custom input
    video_url = input("\nEnter YouTube Video URL: ").strip()
    if not video_url:
        return
    comment_snippet = input("Enter comment snippet to search and upvote: ").strip()
    if not comment_snippet:
        return

    booster.boost_comment_on_video(video_url, comment_snippet)

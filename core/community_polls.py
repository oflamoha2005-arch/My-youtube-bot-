import os
import sys
import json
import time
import random
from typing import Dict, Any, List, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from playwright.sync_api import Page

from core.database import Database
from core.browser_manager import BrowserManager

console = Console()

VIRAL_MYSTERY_POLLS = [
    {
        "question": "You hear heavy footsteps in your attic at 3:17 AM. You live completely alone. What is your immediate move?",
        "options": [
            "Lock the bedroom door & call 911",
            "Grab a heavy weapon & go investigate",
            "Freeze in bed and pretend to sleep",
            "Climb out the window into the yard"
        ],
        "chapter_hook": "Straight out of the attic scene in Chapter 3 of 'The Whispering Walls'. If you love heart-pounding suspense, check the link in our bio/comment!"
    },
    {
        "question": "A stranger hands you a locked wooden box on the train and whispers: 'Whatever you do, don't open it before midnight.' What do you do?",
        "options": [
            "Open it immediately out of curiosity",
            "Toss it in the nearest trash bin",
            "Wait patiently until 12:00 AM",
            "Take it straight to the police"
        ],
        "chapter_hook": "Every locked box has a terrifying reason. Inspired by 'The Whispering Walls' on Kindle."
    },
    {
        "question": "You find an old photo of your current bedroom from 15 years ago... and someone is standing behind the closet door staring. Your reaction?",
        "options": [
            "Move out the exact same night",
            "Tear down the closet wall right now",
            "Research the house's dark history",
            "Convince myself it's just photoshop"
        ],
        "chapter_hook": "Some secrets refuse to stay buried. Discover the mystery in 'The Whispering Walls' on Amazon Kindle."
    },
    {
        "question": "You wake up in the middle of the night and your phone has a photo of you sleeping taken 10 minutes ago. What do you do?",
        "options": [
            "Run out of the house screaming",
            "Check the timestamp and closet",
            "Call my best friend or family",
            "Smash the phone into pieces"
        ],
        "chapter_hook": "The ultimate psychological nightmare. Read the thriller that will keep you awake: 'The Whispering Walls'."
    },
    {
        "question": "Which psychological thriller trope gives you the biggest chills when reading?",
        "options": [
            "The Unreliable Narrator (who's lying?)",
            "The Locked Room with no escape",
            "The Insane Final Page Twist",
            "The Neighbor with a secret basement"
        ],
        "chapter_hook": "If you crave mind-bending twists, check out 'The Whispering Walls' on Amazon Kindle!"
    }
]

class CommunityPollsPoster:
    def __init__(self, config: Dict[str, Any], db: Database, browser_mgr: BrowserManager):
        self.config = config
        self.db = db
        self.browser_mgr = browser_mgr
        self.book_details = config.get("book_details", {})
        self.ai_config = config.get("ai_settings", {})
        self.api_key = self.ai_config.get("gemini_api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = self.ai_config.get("model", "gemini-1.5-flash")

    def generate_poll(self) -> Dict[str, Any]:
        """Generates an engaging, high-vote dilemma poll using Gemini AI or curated viral templates."""
        book_title = self.book_details.get("title", "The Whispering Walls")
        kindle_url = self.book_details.get("amazon_kindle_url", "")

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)

                prompt = f"""
You are a viral YouTube Community Polls creator for a mystery/thriller fiction channel.
Create an irresistible psychological dilemma / spooky scenario poll that people on YouTube cannot resist voting on.
Book you are promoting: "{book_title}".

Output as clean JSON without markdown code fences:
{{
  "question": "Short intense scenario or dilemma question (under 120 chars)?",
  "options": [
    "Option 1",
    "Option 2",
    "Option 3",
    "Option 4"
  ],
  "chapter_hook": "A 1-sentence teaser connecting this dilemma to '{book_title}' on Amazon Kindle."
}}
"""
                resp = model.generate_content(prompt)
                raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
            except Exception as e:
                console.print(f"[dim]Gemini poll generation note: {e}. Using curated viral templates.[/dim]")

        # Pick from curated viral bank
        selected = random.choice(VIRAL_MYSTERY_POLLS).copy()
        selected["chapter_hook"] = selected["chapter_hook"].replace("The Whispering Walls", book_title)
        return selected

    def post_poll(self, account_config: Dict[str, Any], poll_data: Dict[str, Any]) -> bool:
        """Automates posting the poll on YouTube Community Tab."""
        acc_id = account_config["id"]
        acc_name = account_config["name"]
        question = poll_data["question"]
        options = poll_data["options"]
        hook = poll_data.get("chapter_hook", "")

        full_post_text = f"{question}\n\n📖 {hook}"

        console.print(f"\n[bold cyan]🚀 Posting Community Poll via:[/bold cyan] [yellow]{acc_name}[/yellow]")
        console.print(f"  [bold]Question:[/bold] {question}")

        context, page = self.browser_mgr.launch_account_context(acc_id)
        try:
            # Navigate to YouTube Create Post or Studio
            page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=40000)
            self.browser_mgr.human_delay(3, 5)

            # Look for the Create (+) button on top bar
            create_btn = page.query_selector("button[aria-label*='Create' i], ytd-topbar-menu-button-renderer button")
            if create_btn:
                create_btn.click()
                self.browser_mgr.human_delay(1.5, 2.5)

                # Look for "Create post" in the popup menu
                create_post_option = page.query_selector("ytd-compact-link-renderer a[href*='post'], a[href*='post']")
                if create_post_option:
                    create_post_option.click()
                    self.browser_mgr.human_delay(3, 5)

            # If not yet on post creator, go directly to channel community tab
            if "/post" not in page.url and "/community" not in page.url:
                page.goto("https://www.youtube.com/post/create", wait_until="domcontentloaded", timeout=30000)
                self.browser_mgr.human_delay(3, 5)

            # Select Poll Option
            poll_button = page.query_selector("button[aria-label*='poll' i], tp-yt-paper-tab[aria-label*='poll' i], ytd-button-renderer#poll-button button")
            if poll_button:
                poll_button.click()
                self.browser_mgr.human_delay(1.5, 2.5)

            # Find Question Box
            input_box = page.query_selector("#contenteditable-root, div#contenteditable-root[contenteditable='true']")
            if input_box:
                input_box.click()
                for char in full_post_text:
                    page.keyboard.type(char)
                    time.sleep(random.uniform(0.02, 0.06))
                self.browser_mgr.human_delay(1, 2)

            # Find Option inputs
            option_inputs = page.query_selector_all("input[placeholder*='option' i], ytd-backstage-poll-editor-renderer input")
            for i, opt_text in enumerate(options):
                if i < len(option_inputs):
                    option_inputs[i].click()
                    option_inputs[i].fill(opt_text)
                    self.browser_mgr.human_delay(0.5, 1.0)
                else:
                    # Click Add Option if available
                    add_opt_btn = page.query_selector("button[aria-label*='Add option' i], #add-option-button button")
                    if add_opt_btn:
                        add_opt_btn.click()
                        self.browser_mgr.human_delay(0.5, 1.0)
                        refreshed_inputs = page.query_selector_all("input[placeholder*='option' i]")
                        if i < len(refreshed_inputs):
                            refreshed_inputs[i].fill(opt_text)

            self.browser_mgr.human_delay(2, 4)

            # Submit Post
            post_submit = page.query_selector("button[aria-label*='Post' i], #post-button button, ytd-button-renderer#post-button button")
            if post_submit and post_submit.is_enabled():
                post_submit.click()
                self.browser_mgr.human_delay(4, 6)
                console.print(f"[bold green]✓ Community Poll successfully published on {acc_name}![/bold green]")
                self.db.log_community_poll(acc_id, question, json.dumps(options), hook, "success")
                return True
            else:
                console.print("[yellow]! Note: Post button not clickable. Make sure channel has Community Tab access enabled.[/yellow]")
                self.db.log_community_poll(acc_id, question, json.dumps(options), hook, "pending_manual")
                return False

        except Exception as e:
            console.print(f"[red]Error posting poll: {e}[/red]")
            return False
        finally:
            try:
                context.close()
            except Exception:
                pass

def run_community_polls_interactive(config: dict, db: Database, browser_mgr: BrowserManager):
    poster = CommunityPollsPoster(config, db, browser_mgr)
    accounts = config.get("accounts", [])

    if not accounts:
        console.print("[red]No accounts found in config.json.[/red]")
        return

    console.print(Panel.fit(
        "[bold cyan]📊 YouTube Community Polls Exploit Engine[/bold cyan]\n"
        "[dim]Create viral psychological dilemma polls that YouTube algorithm pushes to non-subscribers![/dim]",
        border_style="cyan"
    ))

    # Generate a poll preview
    poll = poster.generate_poll()

    table = Table(title="Generated Viral Poll Preview", style="magenta")
    table.add_column("Element", style="bold yellow")
    table.add_column("Content", style="white")

    table.add_row("Question", poll["question"])
    for idx, opt in enumerate(poll["options"], 1):
        table.add_row(f"Option {idx}", opt)
    table.add_row("Book Hook", poll.get("chapter_hook", ""))

    console.print(table)

    console.print("\n[bold]Choose an action:[/bold]")
    console.print("  [1] 🚀 Publish this Poll to Account 1")
    console.print("  [2] 🔄 Generate Another Poll Dilemma")
    console.print("  [0] 🔙 Cancel & Return")

    choice = input("\nEnter choice (0-2): ").strip()
    if choice == "1":
        poster.post_poll(accounts[0], poll)
    elif choice == "2":
        run_community_polls_interactive(config, db, browser_mgr)

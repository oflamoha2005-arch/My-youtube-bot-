import os
import sys
import json
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.database import Database
from core.browser_manager import BrowserManager
from core.ai_engine import AIEngine
from core.sniper import TopCommentSniper
from core.warmer import ChannelWarmer
from core.intent_hunter import IntentHunter

console = Console()

def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def display_banner():
    console.print(Panel.fit(
        "[bold red]🎥 YOUTUBE TRAFFIC & MARKETING BOT v1.0[/bold red]\n"
        "[bold cyan]Multi-Account Sniper 🎯 | Niche Warmer ☕ | High-Intent Hunter 💬[/bold cyan]\n"
        "[dim]Automated Organic Growth & Book Sales Engine for Amazon Kindle[/dim]",
        border_style="red"
    ))

def display_stats(db: Database):
    stats = db.get_total_stats()
    table = Table(title="📊 Bot Performance Dashboard", style="magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count / Value", style="bold green", justify="center")

    table.add_row("🎯 Sniped Top Comments Posted", str(stats["total_sniped_comments"]))
    table.add_row("💬 High-Intent Recommendations Replied", str(stats["total_intent_replies"]))
    table.add_row("👀 Niche Videos Watched (Warmer)", str(stats["total_warmed_views"]))
    table.add_row("👍 Video Likes Given (41% Target)", str(stats["total_likes_given"]))
    table.add_row("🔔 Channel Subscriptions (21% Target)", str(stats["total_subs_given"]))
    table.add_row("📊 Community Polls Published", str(stats.get("total_community_polls", 0)))
    table.add_row("🔍 Scouted Niche Channels Discovered", str(stats.get("total_scouted_channels", 0)))
    table.add_row("🚀 Comment Upvote Boosts Given", str(stats.get("total_comment_boosts", 0)))
    table.add_row("🔴 Live Stream Chat Messages", str(stats.get("total_livestream_messages", 0)))
    table.add_row("🧠 Viral Comment Blueprints in Vault", str(stats.get("total_reverse_engineered_patterns", 0)))

    console.print(table)

    if stats["recent_comments"]:
        console.print("\n[bold yellow]Recent Comments Posted:[/bold yellow]")
        for c in stats["recent_comments"][:3]:
            console.print(f"  • [bold white]{c['account_name']}[/bold white] on [cyan]{c['video_title'][:40]}...[/cyan]")
            console.print(f"    [dim]\"{c['comment_text'][:90]}...\"[/dim]")

def run_orchestrator_loop(sniper: TopCommentSniper, warmer: ChannelWarmer, hunter: IntentHunter):
    """Autonomous continuous routine combining Warmer + Sniper + Hunter."""
    console.print("\n[bold green]🚀 Launching Autonomous 24/7 Marketing Loop...[/bold green]")
    console.print("[dim]Sequence: Sniper Channel Check -> Warmer Organic Session -> Intent Hunter -> Rest[/dim]\n")

    try:
        round_num = 1
        while True:
            console.print(f"\n[bold cyan]=== [CYCLE #{round_num}] ===[/bold cyan] ({time.strftime('%Y-%m-%d %H:%M:%S')})")

            # 1. Sniper check
            console.print("\n[bold red]Step 1: Checking for fresh channel uploads (Sniper)...[/bold red]")
            sniper.scan_channels_once()

            # 2. Organic Warming Session
            console.print("\n[bold yellow]Step 2: Performing Human Niche Warming (41% Like, 21% Sub)...[/bold yellow]")
            warmer.warm_all_accounts()

            # 3. High-Intent Comment Hunter
            console.print("\n[bold magenta]Step 3: Hunting High-Intent Readers & Auto-Replying...[/bold magenta]")
            hunter.run_hunting_session()

            # 4. Rest interval between full cycles (e.g. 15-25 minutes)
            sleep_time = 900  # 15 minutes
            console.print(f"\n[dim]Cycle #{round_num} finished. Cooling down for {sleep_time // 60} minutes...[/dim]")
            round_num += 1
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        console.print("\n[yellow]Autonomous loop paused by user.[/yellow]")

def main():
    config = load_config()
    db = Database()
    browser_mgr = BrowserManager(headless=config.get("safety_limits", {}).get("headless", False))
    ai_engine = AIEngine(config, db)

    sniper = TopCommentSniper(config, db, browser_mgr, ai_engine)
    warmer = ChannelWarmer(config, db, browser_mgr)
    hunter = IntentHunter(config, db, browser_mgr, ai_engine)

    while True:
        # Reload config dynamically to catch any newly added accounts
        config = load_config()
        sniper.config = config
        sniper.accounts = config.get("accounts", [])
        warmer.config = config
        warmer.accounts = config.get("accounts", [])
        hunter.config = config
        hunter.accounts = [acc for acc in config.get("accounts", []) if acc.get("enabled", True)]

        display_banner()
        display_stats(db)

        acc_count = len(config.get("accounts", []))
        console.print(f"\n[bold green]Connected Accounts Fleet:[/bold green] [bold yellow]{acc_count} Accounts Configured[/bold yellow]")

        console.print("\n[bold]Select an action:[/bold]")
        console.print("  [1]  🎯 Top-Comment Sniper: Scan Target Channels Once (Multi-Account)")
        console.print("  [2]  ⚡ Top-Comment Sniper: Run Continuous Daemon Loop (Every 2 min)")
        console.print("  [3]  ☕ Human Niche Warmer: Warm Accounts (Zero Duplicate Watch, 41% Like, 21% Sub)")
        console.print("  [4]  💬 High-Intent Hunter: Auto-Reply to Readers (Zero Duplicate Reply)")
        console.print("  [5]  🚀 Autonomous Mode: Run Warmer + Sniper + Hunter Continuous Loop")
        console.print(f"  [6]  🔐 Accounts Fleet Manager: Add & Authenticate Accounts ({acc_count} Active)")
        console.print("  [7]  🏷️  Niche Hashtag & SEO Tag Engine: Get Best Hashtags for Your Topic")
        console.print("  [8]  📊 Community Tab Polls: Post Viral Dilemma Poll (Home Feed Exploit)")
        console.print("  [9]  🔍 Niche Channel Auto-Scout: Discover & Feed Hot Channels to Sniper")
        console.print("  [10] 🚀 Comment Cross-Upvoter: Boost Your Comments to #1 Top Rank")
        console.print("  [11] 🔴 24/7 Live Stream Chat Hunter: Engage Live Audiences with Book")
        console.print("  [12] 🧠 Top Comments Reverse-Engineer: Scrape & Learn Viral Patterns")
        console.print("  [0]  ❌ Exit")

        choice = input("\nEnter your choice (0-12): ").strip()

        if choice == "0":
            console.print("[dim]Goodbye![/dim]")
            break
        elif choice == "1":
            sniper.scan_channels_once()
        elif choice == "2":
            sniper.run_daemon_loop()
        elif choice == "3":
            warmer.warm_all_accounts()
        elif choice == "4":
            hunter.run_hunting_session()
        elif choice == "5":
            run_orchestrator_loop(sniper, warmer, hunter)
        elif choice == "6":
            import login_helper
            login_helper.main()
        elif choice == "7":
            from core.hashtag_engine import run_hashtag_interactive
            run_hashtag_interactive(config)
        elif choice == "8":
            from core.community_polls import run_community_polls_interactive
            run_community_polls_interactive(config, db, browser_mgr)
        elif choice == "9":
            from core.channel_scout import run_channel_scout_interactive
            run_channel_scout_interactive(config, db)
        elif choice == "10":
            from core.comment_booster import run_comment_booster_interactive
            run_comment_booster_interactive(config, db, browser_mgr)
        elif choice == "11":
            from core.livestream_hunter import run_livestream_hunter_interactive
            run_livestream_hunter_interactive(config, db, browser_mgr, ai_engine)
        elif choice == "12":
            from core.comment_reverse_engineer import run_reverse_engineer_interactive
            run_reverse_engineer_interactive(config, db, browser_mgr)
        else:
            console.print("[red]Invalid choice, please select 0 to 12.[/red]")

        input("\nPress ENTER to return to menu...")
        console.clear()

    browser_mgr.close()

if __name__ == "__main__":
    main()

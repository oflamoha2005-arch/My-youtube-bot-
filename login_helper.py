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

from core.browser_manager import BrowserManager

console = Console()
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def check_accounts_status(config: dict, browser_mgr: BrowserManager):
    table = Table(title="YouTube Accounts Fleet", style="cyan")
    table.add_column("#", justify="center", style="bold")
    table.add_column("ID", style="bold yellow")
    table.add_column("Account Name", style="white")
    table.add_column("Persona / Role", style="cyan")
    table.add_column("Session Status", justify="center")

    accounts = config.get("accounts", [])
    for idx, acc in enumerate(accounts, 1):
        acc_id = acc["id"]
        profile_dir = browser_mgr.get_profile_path(acc_id)
        has_data = os.path.exists(profile_dir) and len(os.listdir(profile_dir)) > 3
        status_text = "[green]✓ Ready[/green]" if has_data else "[yellow]⚠ Needs Login[/yellow]"
        table.add_row(str(idx), acc_id, acc["name"], acc.get("persona", ""), status_text)

    console.print(table)
    return accounts

def login_account(acc: dict, browser_mgr: BrowserManager):
    acc_id = acc["id"]
    acc_name = acc["name"]
    console.print(f"\n[bold cyan]Opening browser for:[/bold cyan] [yellow]{acc_name}[/yellow] ({acc_id})")
    console.print("[dim]A Chrome window will open. Sign in to your YouTube / Google account.[/dim]")
    console.print("[dim]Once logged in successfully, return to this terminal and press ENTER.[/dim]\n")

    context, page = browser_mgr.launch_account_context(acc_id, headless=False)
    try:
        page.goto("https://www.youtube.com", timeout=45000)
        time.sleep(2)

        input("\n>>> Press ENTER once you have logged in to this account in the browser... ")

        is_logged_in = browser_mgr.check_login_status(page)
        if is_logged_in:
            console.print(f"[bold green]✓ SUCCESS: {acc_name} ({acc_id}) session is permanently saved![/bold green]")
        else:
            console.print(f"[yellow]! Profile session saved to profiles/{acc_id}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error during session: {e}[/red]")
    finally:
        try:
            context.close()
        except Exception:
            pass

def add_new_account(config: dict):
    console.print("\n[bold green]➕ Add a New YouTube Account[/bold green]")
    accounts = config.get("accounts", [])
    next_idx = len(accounts) + 1
    default_id = f"acc_{next_idx}"

    name = input(f"Enter Account Display Name (e.g. Account {next_idx} - Mystery Reviewer): ").strip()
    if not name:
        name = f"Account {next_idx}"

    persona = input("Enter Account Persona (e.g. Dark Thriller Enthusiast / Avid Reader): ").strip()
    if not persona:
        persona = "Avid Mystery & Fiction Reader"

    style = input("Enter Comment Style (e.g. Relatable, intriguing observation): ").strip()
    if not style:
        style = "Relatable, witty, praises plot twists"

    signature = input("Enter signature in parentheses (Leave empty for none, or e.g. Author of ...): ").strip()

    new_acc = {
        "id": default_id,
        "name": name,
        "profile_dir": f"profiles/{default_id}",
        "persona": persona,
        "style": style,
        "signature": signature,
        "enabled": True
    }

    accounts.append(new_acc)
    config["accounts"] = accounts
    save_config(config)

    console.print(f"\n[bold green]✓ Account '{name}' ({default_id}) added to config.json![/bold green]")
    
    do_login = input("Would you like to open browser and log in right now? (y/n): ").strip().lower()
    if do_login in ["y", "yes"]:
        browser_mgr = BrowserManager(headless=False)
        login_account(new_acc, browser_mgr)
        browser_mgr.close()

def main():
    browser_mgr = BrowserManager(headless=False)

    while True:
        config = load_config()
        console.print(Panel.fit(
            "[bold white]YouTube Multi-Account Fleet Manager[/bold white]\n"
            "[dim]Add unlimited accounts & authenticate them once. Sessions persist in 'profiles/'[/dim]",
            border_style="bright_blue"
        ))

        accounts = check_accounts_status(config, browser_mgr)

        console.print("\n[bold]Options:[/bold]")
        console.print("  [1 to N] Login to specific account by its number")
        console.print("  [ALL]    Login to all accounts in sequence")
        console.print("  [ADD]    ➕ Add a New Account to the Fleet")
        console.print("  [0]      Exit to Main Menu")

        choice = input(f"\nEnter choice (1-{len(accounts)}, ALL, ADD, 0): ").strip()

        if choice == "0":
            break
        elif choice.lower() in ["add", "a", "+"]:
            add_new_account(config)
        elif choice.lower() in ["all", "login all"]:
            for acc in accounts:
                login_account(acc, browser_mgr)
                time.sleep(1)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                login_account(accounts[idx], browser_mgr)
            else:
                console.print("[red]Invalid account number.[/red]")
        else:
            console.print("[red]Invalid selection.[/red]")

        input("\nPress ENTER to continue...")
        console.clear()

    browser_mgr.close()

if __name__ == "__main__":
    main()

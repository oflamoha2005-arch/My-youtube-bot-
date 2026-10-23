import os
import sys
import json
import requests
from typing import Dict, Any, List

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class HashtagEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get("ai_settings", {})
        self.api_key = self.ai_config.get("gemini_api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = self.ai_config.get("model", "gemini-1.5-flash")

    def fetch_youtube_suggest_keywords(self, seed_query: str) -> List[str]:
        """
        Fetches live real-time search queries from YouTube Suggest API.
        These are the exact phrases real viewers are searching for on YouTube right now.
        """
        queries_to_test = [
            seed_query,
            f"{seed_query} books",
            f"{seed_query} recommendations",
            f"{seed_query} plot twist",
            f"{seed_query} shorts"
        ]

        results = set()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for q in queries_to_test:
            try:
                url = f"http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={q}"
                resp = requests.get(url, headers=headers, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1 and isinstance(data[1], list):
                        for item in data[1]:
                            results.add(item.strip())
            except Exception:
                continue

        return list(results)

    def generate_niche_hashtags(self, niche_prompt: str) -> Dict[str, Any]:
        """
        Combines live YouTube suggestions with AI to produce categorized, high-performing hashtags.
        """
        live_suggestions = self.fetch_youtube_suggest_keywords(niche_prompt)

        # Try Gemini AI for intelligent ranking & categorization
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)

                prompt = f"""
You are a YouTube SEO and Viral Growth Specialist.
The user's niche / topic is: "{niche_prompt}"
Live YouTube popular search suggestions found: {live_suggestions[:15]}

Generate the ultimate, highest-ranking hashtags and SEO tags for this niche.
Output your response as clean JSON matching this EXACT structure:
{{
  "viral_shorts_hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6"],
  "niche_book_hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"],
  "high_intent_tags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "youtube_seo_keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5", "keyword 6", "keyword 7"],
  "copy_paste_description_block": "#tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7 #tag8 #tag9 #tag10"
}}
Rules:
- Include high-traffic tags like #shorts, #booktok, #kindle, #thrillerbooks, #mysterybooks where appropriate.
- Only output the JSON object without markdown fences or backticks.
"""
                response = model.generate_content(prompt)
                raw = response.text.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
            except Exception as e:
                console.print(f"[dim]Gemini generation note: {e}. Using Smart Algorithmic Generator.[/dim]")

        # Smart Algorithmic Generator (Zero API Key needed)
        clean_words = [w.strip() for w in niche_prompt.replace("-", " ").replace("/", " ").split() if len(w) > 2]
        
        # Build hashtags from clean words and live suggestions
        shorts_tags = ["#shorts", "#youtubeshorts", "#viral", "#fyp"]
        if any("book" in w.lower() for w in clean_words) or "thriller" in niche_prompt.lower():
            shorts_tags.extend(["#booktok", "#booktube", "#scarystories"])

        niche_tags = []
        for word in clean_words:
            niche_tags.append(f"#{word.lower()}")
        
        # Add common high-converting tags based on topic
        if "thriller" in niche_prompt.lower() or "mystery" in niche_prompt.lower():
            niche_tags.extend(["#thrillerbooks", "#mysterybooks", "#psychologicalthriller", "#plottwist", "#darkfiction", "#kindlebestseller"])
        elif "romance" in niche_prompt.lower():
            niche_tags.extend(["#romancebooks", "#bookish", "#spicybooks", "#enemiestolovers", "#kindleunlimited"])
        elif "horror" in niche_prompt.lower() or "crime" in niche_prompt.lower():
            niche_tags.extend(["#truecrime", "#crimestories", "#horrorcommunity", "#creepyreads", "#unsolvedmysteries"])
        else:
            niche_tags.extend(["#mustread", "#bookrecommendations", "#indieauthor", "#kindlebooks", "#whattoread"])

        high_intent = ["#bookrecommendations", "#whattoreadnext", "#kindleunlimited", "#amazonbooks", "#bookreview"]
        
        # Deduplicate preserving order
        shorts_tags = list(dict.fromkeys(shorts_tags))
        niche_tags = list(dict.fromkeys(niche_tags))
        high_intent = list(dict.fromkeys(high_intent))
        
        all_tags = (shorts_tags[:4] + niche_tags[:8] + high_intent[:4])
        all_tags = list(dict.fromkeys(all_tags))

        seo_keywords = live_suggestions[:10] if live_suggestions else [
            f"best {niche_prompt}",
            f"{niche_prompt} recommendations",
            f"{niche_prompt} review",
            f"top {niche_prompt} 2026",
            f"{niche_prompt} with plot twists"
        ]

        return {
            "viral_shorts_hashtags": shorts_tags,
            "niche_book_hashtags": niche_tags,
            "high_intent_tags": high_intent,
            "youtube_seo_keywords": seo_keywords,
            "copy_paste_description_block": " ".join(all_tags[:15])
        }

    def display_and_save_hashtags(self, niche_prompt: str, data: Dict[str, Any]):
        """Renders rich tables and saves tags to a ready-to-copy file."""
        console.print(Panel.fit(
            f"[bold green]🎯 Best YouTube Hashtags & SEO Tags for:[/bold green] [bold yellow]\"{niche_prompt}\"[/bold yellow]",
            border_style="green"
        ))

        # 1. Shorts Tags Table
        table_shorts = Table(title="🎬 Viral YouTube Shorts Hashtags", style="magenta")
        table_shorts.add_column("Tag", style="bold yellow")
        for tag in data.get("viral_shorts_hashtags", []):
            table_shorts.add_row(tag)
        console.print(table_shorts)

        # 2. Niche Specific Hashtags
        table_niche = Table(title="📚 Niche & Fiction Targeted Hashtags", style="cyan")
        table_niche.add_column("Hashtag", style="bold cyan")
        for tag in data.get("niche_book_hashtags", []):
            table_niche.add_row(tag)
        console.print(table_niche)

        # 3. High Intent Buyer Tags
        table_intent = Table(title="💎 High-Intent Buyer Tags (Kindle / Book Lovers)", style="green")
        table_intent.add_column("Tag", style="bold green")
        for tag in data.get("high_intent_tags", []):
            table_intent.add_row(tag)
        console.print(table_intent)

        # 4. Search Keywords
        console.print("\n[bold yellow]🔍 Top YouTube Search Keywords (For Video Tags Settings):[/bold yellow]")
        keywords_str = ", ".join(data.get("youtube_seo_keywords", []))
        console.print(f"[white]{keywords_str}[/white]")

        # 5. Ready-to-Copy Block
        block = data.get("copy_paste_description_block", "")
        console.print("\n[bold cyan]📋 Copy-Ready Block for Video / Shorts Description:[/bold cyan]")
        console.print(Panel(block, border_style="bright_cyan"))

        # Save to file
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "niche_hashtags.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"=== BEST HASHTAGS & TAGS FOR: {niche_prompt.upper()} ===\n\n")
            f.write("--- 1. COPY-PASTE FOR DESCRIPTION ---\n")
            f.write(block + "\n\n")
            f.write("--- 2. VIRAL SHORTS HASHTAGS ---\n")
            f.write(" ".join(data.get("viral_shorts_hashtags", [])) + "\n\n")
            f.write("--- 3. NICHE BOOK HASHTAGS ---\n")
            f.write(" ".join(data.get("niche_book_hashtags", [])) + "\n\n")
            f.write("--- 4. HIGH-INTENT HASHTAGS ---\n")
            f.write(" ".join(data.get("high_intent_tags", [])) + "\n\n")
            f.write("--- 5. YOUTUBE STUDIO TAGS (COMMA SEPARATED) ---\n")
            f.write(keywords_str + "\n")

        console.print(f"\n[green]✓ All tags saved to [bold]niche_hashtags.txt[/bold] for easy copy-pasting![/green]")

def run_hashtag_interactive(config: dict):
    engine = HashtagEngine(config)
    default_niche = config.get("book_details", {}).get("genre", "psychological thriller book plot twist")

    console.print("\n[bold cyan]🏷️ Niche Hashtags & SEO Keyword Generator[/bold cyan]")
    user_niche = input(f"Enter your target niche/topic (Press ENTER for default: '{default_niche}'): ").strip()
    if not user_niche:
        user_niche = default_niche

    console.print(f"\n[bold yellow]🔎 Fetching live YouTube search queries & analyzing optimal tags for '{user_niche}'...[/bold yellow]")
    data = engine.generate_niche_hashtags(user_niche)
    engine.display_and_save_hashtags(user_niche, data)

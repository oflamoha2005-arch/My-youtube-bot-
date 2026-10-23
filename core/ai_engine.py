import os
import random
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class AIEngine:
    def __init__(self, config: Dict[str, Any], db=None):
        self.config = config
        self.db = db
        self.ai_config = config.get("ai_settings", {})
        self.book_details = config.get("book_details", {})
        self.api_key = self.ai_config.get("gemini_api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = self.ai_config.get("model", "gemini-1.5-flash")
        
        self.genai_client = None
        if HAS_GENAI and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.genai_client = genai.GenerativeModel(self.model_name)
            except Exception as e:
                print(f"[!] Warning: Failed to initialize Gemini model: {e}")

    # --- 1. Sniper Comment Generator for Multi-Account ---
    def generate_sniper_comment(self, account_config: Dict[str, Any], video_title: str, channel_name: str) -> str:
        """
        Generates a unique, high-engagement comment tailored specifically to the given account's persona.
        """
        account_id = account_config.get("id", "acc_1")
        persona = account_config.get("persona", "Mystery Reader")
        style = account_config.get("style", "Engaging")
        signature = account_config.get("signature", "")
        book_title = self.book_details.get("title", "The Whispering Walls")

        # Pull reverse-engineered winning patterns from vault
        winning_patterns = ""
        if self.db:
            try:
                examples = self.db.get_top_comments_examples(limit=2)
                if examples:
                    winning_patterns = "\nProven High-Upvote Reference Styles:\n" + "\n".join([f"- \"{ex}\"" for ex in examples])
            except Exception:
                pass

        # Try Gemini AI first if configured
        if self.genai_client:
            try:
                prompt = f"""
You are writing a top-level YouTube comment on a brand new video that was just uploaded.
Channel Name: "{channel_name}"
Video Title: "{video_title}"

Your Profile Persona: {persona}
Your Style: {style}
Book you authored/love: "{book_title}"
{winning_patterns}

CRITICAL RULES:
1. Write 1 or 2 sentences max. Keep it punchy, authentic, and natural like a real passionate viewer.
2. React genuinely to the theme or title of the video.
3. If this is Account 1 (Author), end with a gentle, humble signature in parentheses like: - ({signature}). Do NOT put a raw web link.
4. If this is Account 2 or Account 3, do NOT mention being an author. Just write an amazing, witty, or analytical comment that people will hit 'Like' on.
5. Never sound like a promotional bot. Do not use generic spam words. Output ONLY the comment text.
"""
                response = self.genai_client.generate_content(prompt)
                comment = response.text.strip().strip('"')
                if comment and len(comment) > 10:
                    return comment
            except Exception as e:
                print(f"[!] Gemini generation error for {account_id}: {e}. Using Smart Fallback.")

        # Smart Fallback Generator (Varied & High Converting)
        return self._smart_fallback_sniper(account_id, video_title, channel_name, signature)

    def _smart_fallback_sniper(self, account_id: str, video_title: str, channel_name: str, signature: str) -> str:
        """Dynamic contextual templates when Gemini API is offline or not configured."""
        title_lower = video_title.lower()

        if account_id == "acc_1":  # Primary / Author account
            templates = [
                f"The way {channel_name} builds psychological tension is pure storytelling masterclass. Another unforgettable case.\n- ({signature})",
                f"Drop everything when a new {channel_name} upload notifications hits. The suspense here is unmatched.\n- ({signature})",
                f"As someone obsessed with dark mystery twists, {channel_name} never fails to give genuine chills.\n- ({signature})",
                f"The psychological depth in this story is phenomenal. Exactly the kind of eerie atmosphere that keeps you up at night.\n- ({signature})",
                f"That revelation near the end sent chills straight down my spine. Exceptional breakdown as always.\n- ({signature})"
            ]
            return random.choice(templates)

        elif account_id == "acc_2":  # Relatable / Avid Reader
            templates = [
                f"The fact that this actually happened in real life is scarier than any horror movie ever written.",
                f"I swear {channel_name} has the best atmospheric narration on the entire platform. Instant coffee & chill time.",
                f"My jaw literally dropped at that detail. How does someone even begin to think like that?",
                f"Came here immediately after getting the notification. Nobody does storytelling quite like this.",
                f"The sheer amount of twists in this one... definitely not sleeping with the closet door unlocked tonight."
            ]
            return random.choice(templates)

        else:  # Account 3 / Deep Plot Analyst
            templates = [
                f"What fascinates me most is the psychology behind the turning point. The subtle signs were there all along.",
                f"Notice how the key timeline shift changed everything? The psychological breakdown here is fascinating.",
                f"Stories like this prove truth is infinitely stranger and darker than fiction. Phenomenal research.",
                f"The psychological tension in this narrative structure is incredible. Makes you question human behavior deeply."
            ]
            return random.choice(templates)

    # --- 2. High-Intent Detection & Reply Generator ---
    def evaluate_and_reply_intent(self, comment_text: str, commenter_name: str, video_title: str) -> Optional[str]:
        """
        Evaluates if a comment represents a reader seeking mystery/thriller recommendations.
        If yes, generates an organic, distinct, and highly converting reply.
        """
        book_title = self.book_details.get("title", "The Whispering Walls")
        genre = self.book_details.get("genre", "Psychological Thriller")
        hook = self.book_details.get("key_hook", "A twist you will never see coming.")

        # Keywords check for intent
        trigger_keywords = self.config.get("intent_hunter_settings", {}).get("trigger_keywords", [
            "recommend", "what to read", "next book", "plot twist", "psychological thriller"
        ])
        
        has_keyword = any(kw in comment_text.lower() for kw in trigger_keywords)
        if not has_keyword:
            return None

        # If Gemini is available, use it to craft a unique, empathetic reply
        if self.genai_client:
            try:
                prompt = f"""
You are an avid reader on YouTube replying to a comment on a mystery/thriller video.
Original Commenter: "@{commenter_name}"
Their Comment: "{comment_text}"
Video: "{video_title}"

You want to warmly recommend the book "{book_title}" ({genre}).
Book premise: {hook}

RULES:
1. Reply naturally and personally. Mention a detail from their comment.
2. Recommend "{book_title}" on Amazon Kindle with genuine enthusiasm, as a fellow reader who was stunned by the twist.
3. Keep it under 2 sentences. No raw affiliate links.
4. Speak warmly, e.g. "If you want that exact kind of twist, definitely check out 'The Whispering Walls' on Kindle..."
5. Output ONLY the reply text.
"""
                response = self.genai_client.generate_content(prompt)
                reply = response.text.strip().strip('"')
                if reply and len(reply) > 15:
                    return reply
            except Exception as e:
                print(f"[!] Gemini Intent Reply generation error: {e}")

        # Smart Fallback Reply
        reply_templates = [
            f"@{commenter_name} If you're looking for that exact kind of mind-bending psychological tension, you should definitely check out '{book_title}' on Kindle! The ending genuinely caught me off guard.",
            f"@{commenter_name} If you love crazy plot twists and dark suspense, look up '{book_title}' on Amazon. Literally finished it in two nights!",
            f"@{commenter_name} Highly recommend '{book_title}'! If you enjoy stories with deep psychological twists that leave you questioning everyone, it's an incredible read.",
            f"@{commenter_name} You would absolutely love '{book_title}' on Kindle. The psychological atmosphere and the final reveal are insane."
        ]
        return random.choice(reply_templates)

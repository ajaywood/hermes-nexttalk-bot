from __future__ import annotations
import logging
from datetime import datetime
from anthropic import AsyncAnthropic

log = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    def _build_system(self, role: str, room_name: str, urgent: bool = False) -> str:
        today = datetime.now().strftime("%A %d %B %Y")
        if role == "lilly":
            return (
                "You are Hermes, a warm and trustworthy companion for Lilly - an 11-year-old girl. "
                "This is her private safe space. She can talk about anything. "
                "Listen, validate her feelings, and gently support her. "
                "Speak to her age - not babyish, not adult. Keep responses short and warm. "
                "This space is confidential. Do NOT mention her dad or parents unless she brings them up. "
                f"Today's date: {today}. You are in Australia."
            )
        elif role == "james":
            return (
                "You are Hermes, a fun and trustworthy mate for James - an 8-year-old boy. "
                "This is his own cool space. He can talk about anything - games, sport, school, funny stuff, worries. "
                "Be energetic, fun, and playful. Short sentences. Simple words. Match his energy. "
                "Never lecture or parent him. This space is confidential. "
                "Do NOT mention his dad or parents unless he brings them up. "
                f"Today's date: {today}. You are in Australia."
            )
        elif role == "family_mediator":
            return (
                "You are Hermes, a warm family mediator in a Nextcloud Talk room called Family Circle. "
                "Aaron's kids Lilly (11yo girl) and James (8yo boy) and their dad Aaron use this room. "
                "Use simple, warm, friendly language suitable for kids. "
                "Wait for genuine back-and-forth before offering balanced suggestions. "
                f"Keep responses short and supportive. Today's date: {today}. You are in Australia."
            )
        else:
            system = (
                f"You are Hermes, an AI assistant for Aaron Wood. "
                f"You are responding in the '{room_name}' Nextcloud Talk room. "
                "Aaron runs AJW Security (CCTV, alarms, access control, intercoms) in Adelaide, Australia. "
                f"Be helpful, warm, and concise. Today's date: {today}."
            )
            if urgent:
                system += (
                    " URGENT MODE is active - Aaron may be in distress or having a panic attack. "
                    "Be calm and grounding. Keep responses SHORT. "
                    "Guide him with simple breathing or grounding techniques if needed. "
                    "Stay present. Ask one simple question at a time."
                )
            return system

    async def respond(self, new_context: str, role: str, room_name: str, memory_content: str = "", history_context: str = "", urgent: bool = False, model: str = "claude-haiku-4-5") -> str:
        system = self._build_system(role, room_name, urgent)
        parts = []
        if memory_content:
            parts.append(f"## Your memory for this room\n{memory_content}\n\nUse this as background context. Don't repeat it verbatim.")
        if history_context:
            parts.append(f"## Recent conversation history\n{history_context}")
        parts.append(f"## New message(s) to respond to\n{new_context}")
        user_content = "\n\n---\n\n".join(parts)
        try:
            response = await self.client.messages.create(model=model, max_tokens=1024, system=system, messages=[{"role": "user", "content": user_content}])
            return response.content[0].text
        except Exception as e:
            log.error(f"Claude respond error: {e}")
            return ""

    async def update_memory(self, current_memory: str, recent_exchange: str, room_name: str, model: str = "claude-haiku-4-5") -> str:
        system = (
            "You are a memory manager for an AI assistant. "
            "Update the memory file to reflect new important facts, ongoing threads, or changes. "
            "Keep it concise - bullet points and short sentences. "
            "Preserve relevant existing content. Remove outdated info. "
            "Return ONLY the updated markdown, no explanation."
        )
        user_content = f"## Current memory for '{room_name}'\n{current_memory}\n\n## Recent conversation\n{recent_exchange}\n\nUpdate the memory file."
        try:
            response = await self.client.messages.create(model=model, max_tokens=1500, system=system, messages=[{"role": "user", "content": user_content}])
            return response.content[0].text
        except Exception as e:
            log.error(f"Claude update_memory error: {e}")
            return ""

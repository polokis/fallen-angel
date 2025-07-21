"""Utility functions for Discord embeds and formatting"""

import discord
from datetime import datetime
from typing import Dict, List
from config import RANK_EMOJIS, GOLDBOX_EMOJI

def create_error_embed(title: str, description: str, color: int = 0xff0000) -> discord.Embed:
    """Create a standardized error embed"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    return embed

def create_success_embed(title: str, description: str, color: int = 0x00ff00) -> discord.Embed:
    """Create a standardized success embed"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    return embed

def format_number(number) -> str:
    """Format numbers with commas for readability"""
    if isinstance(number, (int, float)) and number >= 1000:
        return f"{number:,}"
    return str(number)

def get_position_emoji(position: int) -> str:
    """Get appropriate emoji for leaderboard position"""
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    else:
        return f"{position}."

def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to Discord field limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

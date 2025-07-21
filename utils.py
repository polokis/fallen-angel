import discord
from typing import Dict, List, Optional
import re

def create_player_embed(player_data: Dict, simplified: bool = False, detailed: bool = False) -> discord.Embed:
    """Create a Discord embed for player statistics"""
    nickname = player_data.get('nickname', 'Unknown')
    
    if simplified:
        return create_simplified_player_embed(player_data)
    elif detailed:
        return create_detailed_player_embed(player_data)
    else:
        return create_detailed_player_embed(player_data)

def create_simplified_player_embed(player_data: Dict) -> discord.Embed:
    """Create a simplified Discord embed for player statistics"""
    nickname = player_data.get('nickname', 'Unknown')
    
    # Create embed with player info
    embed = discord.Embed(
        title=f"🎮 {nickname}",
        description="RTanks Online Player Info",
        color=0x00ff00
    )
    
    # Add rank with emoji (bigger display)
    rank = player_data.get('rank')
    rank_emoji = player_data.get('rank_emoji')
    if rank and rank_emoji:
        embed.add_field(
            name="🎖️ Rank", 
            value=f"## {rank_emoji} {rank}", 
            inline=True
        )
    elif rank:
        embed.add_field(name="🎖️ Rank", value=f"## {rank}", inline=True)
    
    # Add experience
    experience = player_data.get('experience')
    if experience:
        embed.add_field(
            name="⭐ Experience", 
            value=f"{experience:,}", 
            inline=True
        )
    
    # Add activity status
    activity_status = player_data.get('activity_status', '❓ Unknown')
    embed.add_field(
        name="📡 Status", 
        value=activity_status, 
        inline=True
    )
    
    # Add footer with instructions
    embed.add_field(
        name="📊 More Details",
        value="Click the **+** button below to view detailed statistics!",
        inline=False
    )
    
    embed.set_footer(
        text="Data from RTanks Online Ratings • Click + for details"
    )
    
    return embed

def create_detailed_player_embed(player_data: Dict) -> discord.Embed:
    """Create a detailed Discord embed for player statistics"""
    nickname = player_data.get('nickname', 'Unknown')
    
    # Create embed with player info
    embed = discord.Embed(
        title=f"🎮 {nickname} - Detailed Stats",
        description="RTanks Online Player Statistics",
        color=0x0099ff
    )
    
    # Add rank with emoji (larger display)
    rank = player_data.get('rank')
    rank_emoji = player_data.get('rank_emoji')
    if rank and rank_emoji:
        embed.add_field(
            name="🎖️ Rank", 
            value=f"# {rank_emoji} **{rank}**", 
            inline=True
        )
    elif rank:
        embed.add_field(name="🎖️ Rank", value=f"# **{rank}**", inline=True)
    
    # Add experience
    experience = player_data.get('experience')
    if experience:
        embed.add_field(
            name="⭐ Experience", 
            value=f"**{experience:,}**", 
            inline=True
        )
    
    # Add activity status
    activity_status = player_data.get('activity_status', '❓ Unknown')
    embed.add_field(
        name="📡 Status", 
        value=activity_status, 
        inline=True
    )
    
    # Combat Statistics Section
    combat_stats = []
    
    destroyed = player_data.get('destroyed')
    hit = player_data.get('hit') 
    kills = player_data.get('kills')
    deaths = player_data.get('deaths')
    kd_ratio = player_data.get('kd_ratio')
    
    if destroyed is not None:
        combat_stats.append(f"💥 **Destroyed:** {destroyed:,}")
    elif kills is not None:
        combat_stats.append(f"💀 **Kills:** {kills:,}")
    
    if hit is not None:
        combat_stats.append(f"🎯 **Hit:** {hit:,}")
    
    if deaths is not None:
        combat_stats.append(f"☠️ **Deaths:** {deaths:,}")
    
    if kd_ratio is not None:
        combat_stats.append(f"⚔️ **K/D Ratio:** {kd_ratio:.2f}")
    
    if combat_stats:
        embed.add_field(
            name="⚔️ Combat Statistics",
            value="\n".join(combat_stats),
            inline=False
        )
    
    # Player Information Section
    player_info = []
    
    group = player_data.get('group')
    premium = player_data.get('premium')
    gold_boxes = player_data.get('gold_boxes')
    
    if group:
        player_info.append(f"👥 **Group:** {group}")
    
    if premium is not None:
        status = "✅ Yes" if premium else "❌ No"
        player_info.append(f"💎 **Premium:** {status}")
    
    if gold_boxes is not None:
        player_info.append(f"📦 **Gold Boxes:** {gold_boxes:,}")
    
    if player_info:
        embed.add_field(
            name="ℹ️ Player Information", 
            value="\n".join(player_info),
            inline=False
        )
    
    # Equipment Section (only turrets and hulls)
    equipment = player_data.get('equipment', {})
    equipment_text = []
    
    turrets = equipment.get('turrets', [])
    hulls = equipment.get('hulls', [])
    
    if turrets:
        turret_list = ', '.join(turrets[:5])  # Show up to 5 turrets
        equipment_text.append(f"🔫 **Turrets:** {turret_list}")
    
    if hulls:
        hull_list = ', '.join(hulls[:5])  # Show up to 5 hulls
        equipment_text.append(f"🛡️ **Hulls:** {hull_list}")
    
    if equipment_text:
        embed.add_field(
            name="🎯 Equipment",
            value="\n".join(equipment_text),
            inline=False
        )
    
    # Add rankings if available
    rankings = player_data.get('rankings', {})
    if rankings:
        ranking_text = []
        for category, data in list(rankings.items())[:5]:  # Limit to 5 rankings
            rank = data.get('rank', 'N/A')
            value = data.get('value', 'N/A')
            ranking_text.append(f"🏆 **{category}:** #{rank} ({value})")
        
        if ranking_text:
            embed.add_field(
                name="🏆 Current Rankings",
                value="\n".join(ranking_text),
                inline=False
            )
    
    # Add footer
    embed.set_footer(
        text="Data from RTanks Online Ratings • Updated automatically"
    )
    
    return embed

def create_leaderboard_embed(category_name: str, leaderboard_data: List[Dict]) -> discord.Embed:
    """Create a Discord embed for leaderboard with improved emojis"""
    embed = discord.Embed(
        title=f"🏆 Top 10 Players - {category_name}",
        description="RTanks Online Leaderboard",
        color=0xffd700
    )
    
    if not leaderboard_data:
        embed.add_field(
            name="No Data Available",
            value="Could not retrieve leaderboard data at this time.",
            inline=False
        )
        return embed
    
    # Create leaderboard text with proper emojis
    leaderboard_text = []
    
    for i, player in enumerate(leaderboard_data):
        rank = player.get('rank', i + 1)
        name = player.get('name', 'Unknown')
        value = player.get('formatted_value', player.get('value', 'N/A'))
        emoji = player.get('emoji', '🔸')
        
        # Clean up player name
        name = clean_player_name(name)
        
        leaderboard_text.append(f"{emoji} **{name}** - {value}")
    
    # Split into multiple fields if too long
    text = "\n".join(leaderboard_text)
    if len(text) > 1024:
        # Split into two fields
        mid = len(leaderboard_text) // 2
        embed.add_field(
            name="Rankings 1-5",
            value="\n".join(leaderboard_text[:mid]),
            inline=True
        )
        embed.add_field(
            name="Rankings 6-10",
            value="\n".join(leaderboard_text[mid:]),
            inline=True
        )
    else:
        embed.add_field(
            name="Rankings",
            value=text,
            inline=False
        )
    
    # Add timestamp info
    embed.add_field(
        name="ℹ️ Info",
        value="Rankings update regularly on the RTanks website.\n"
              "Some categories reset weekly on Monday at 2:00 UTC.",
        inline=False
    )
    
    embed.set_footer(
        text="Data from RTanks Online Ratings"
    )
    
    return embed

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xff0000
    )
    return embed

def clean_player_name(name: str) -> str:
    """Clean up player name for display"""
    if not name:
        return "Unknown"
    
    # Remove common prefixes and suffixes
    name = re.sub(r'^[\d\s\.\-\#]+', '', name).strip()
    name = re.sub(r'[\d\s\.\-\#]+$', '', name).strip()
    
    # Remove special characters but keep underscores and basic characters
    name = re.sub(r'[^\w\s\-_\.\u0400-\u04FF]', '', name)  # Include Cyrillic characters
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name or "Unknown"

def format_number(num: int) -> str:
    """Format large numbers with commas"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)

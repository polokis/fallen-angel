logger = import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime
import logging
from scraper import RTanksPlayerScraper
from translator import RTanksTranslator
from config import RANK_EMOJIS, LEADERBOARD_CATEGORIES, GOLDBOX_EMOJI
from keep_alive import keep_alive

# Setup logging
logging.basicConfig(level=logging.INFO)logging.getLogger(__name__)

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize scraper and translator
scraper = RTanksPlayerScraper()
translator = RTanksTranslator()

# Global variables for configuration
LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID', '0'))

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Wait a moment before syncing
    await asyncio.sleep(1)
    
    # Sync slash commands globally
    try:
        logger.info("Starting command sync...")
        # Add timeout to prevent hanging
        synced = await asyncio.wait_for(bot.tree.sync(), timeout=30.0)
        logger.info(f"Successfully synced {len(synced)} global command(s)")
        for cmd in synced:
            logger.info(f"Synced command: {cmd.name} - {cmd.description}")
    except asyncio.TimeoutError:
        logger.error("Command sync timed out - this usually means the bot lacks 'applications.commands' scope")
        logger.error("Please re-invite the bot with both 'bot' and 'applications.commands' scopes")
    except discord.Forbidden:
        logger.error("Bot lacks permissions to register slash commands")
        logger.error("Please re-invite the bot with 'applications.commands' scope")
    except Exception as e:
        logger.error(f"Failed to sync global commands: {e}")
        logger.error(f"Error type: {type(e).__name__}")
    
    # List current commands in tree
    logger.info(f"Commands in tree: {[cmd.name for cmd in bot.tree.get_commands()]}")
    
    # Start hourly leaderboard task
    if not hourly_leaderboard.is_running():
        hourly_leaderboard.start()

def get_rank_emoji(rank_name: str) -> str:
    """Get the appropriate emoji for a rank name"""
    # Translate rank name to English if needed
    translated_rank = translator.translate_rank(rank_name)
    
    # Always try lowercase first since our emoji keys are lowercase
    lowercase_rank = translated_rank.lower()
    
    if lowercase_rank in RANK_EMOJIS:
        return RANK_EMOJIS[lowercase_rank]
    else:
        # Try to find a partial match
        for rank_key in RANK_EMOJIS.keys():
            if lowercase_rank in rank_key or rank_key in lowercase_rank:
                return RANK_EMOJIS[rank_key]
        
        # If no match found, return question mark
        return "❓"

def detect_activity_status(html_content: str, nickname: str) -> str:
    """Detect if player is online or offline based on visual indicators"""
    try:
        # Look for activity indicators in the HTML content
        html_lower = html_content.lower()
        
        # Check for online indicators (green dots, online text)
        online_indicators = [
            'color: green', 'color:green', 'background: green', 'background:green',
            'онлайн', 'online', 'в сети', 'active'
        ]
        
        # Check for offline indicators (grey dots, offline text)
        offline_indicators = [
            'color: gray', 'color:gray', 'color: grey', 'color:grey',
            'background: gray', 'background:gray', 'background: grey', 'background:grey',
            'оффлайн', 'offline', 'не в сети', 'inactive', 'последний раз'
        ]
        
        # Check for online status
        for indicator in online_indicators:
            if indicator in html_lower:
                return "🟢 Online"
        
        # Check for offline status
        for indicator in offline_indicators:
            if indicator in html_lower:
                return "⚫ Offline"
        
        # Default to unknown status
        return "❓ Unknown"
        
    except Exception as e:
        logger.error(f"Error detecting activity status: {e}")
        return "❓ Unknown"

def create_simplified_player_embed(player_data: dict) -> discord.Embed:
    """Create a simplified Discord embed for player statistics (for /user command)"""
    
    # Get rank emoji - make it bigger
    rank_emoji = get_rank_emoji(player_data.get('rank', ''))
    
    # Create embed with player info
    embed = discord.Embed(
        title=f"🎮 {player_data['nickname']}",
        description="RTanks Online Player Info",
        color=0x00ff00,
        timestamp=datetime.utcnow()
    )
    
    # Add rank with BIGGER emoji display
    rank_text = translator.translate_text(player_data.get('rank', 'Unknown Rank'))
    embed.add_field(
        name="🎖️ Rank", 
        value=f"# {rank_emoji} **{rank_text}**", 
        inline=True
    )
    
    # Add experience
    embed.add_field(
        name="⭐ Experience", 
        value=f"**{player_data.get('experience', 'N/A'):,}**", 
        inline=True
    )
    
    # Add activity status (online/offline detection)
    activity_status = player_data.get('activity_status', '❓ Unknown')
    embed.add_field(
        name="📡 Status", 
        value=activity_status, 
        inline=True
    )
    
    # Add footer with button instructions
    embed.add_field(
        name="📊 More Details",
        value="Click the **+** button below to view detailed statistics!",
        inline=False
    )
    
    embed.set_footer(
        text="RTanks Online Statistics • Click + for details",
        icon_url="https://ratings.ranked-rtanks.online/public/images/logo.png"
    )
    
    return embed

def create_detailed_player_embed(player_data: dict) -> discord.Embed:
    """Create a detailed Discord embed for player statistics"""
    
    # Get rank emoji
    rank_emoji = get_rank_emoji(player_data.get('rank', ''))
    
    # Create embed with player info
    embed = discord.Embed(
        title=f"{rank_emoji} {player_data['nickname']} - Detailed Stats",
        description="RTanks Online Player Statistics",
        color=0x0099ff,
        timestamp=datetime.utcnow()
    )
    
    # Combat Statistics Section
    combat_stats = []
    
    # Add Destroyed
    destroyed = player_data.get('kills', 0)  # Using kills as destroyed
    if destroyed:
        combat_stats.append(f"💥 **Destroyed:** {destroyed:,}")
    
    # Add Hit (if available in future scraping updates)
    hit = player_data.get('hit', 'N/A')
    if hit and hit != 'N/A':
        combat_stats.append(f"🎯 **Hit:** {hit:,}")
    
    # Add K/D Ratio
    kd_ratio = player_data.get('kd_ratio', 0)
    if kd_ratio:
        combat_stats.append(f"⚔️ **K/D Ratio:** {kd_ratio}")
    
    if combat_stats:
        embed.add_field(
            name="⚔️ Combat Statistics",
            value="\n".join(combat_stats),
            inline=False
        )
    
    # Player Information Section
    player_info = []
    
    # Add Group
    group = player_data.get('group', 'Player')
    player_info.append(f"👥 **Group:** {group}")
    
    # Add Premium Status
    premium = player_data.get('premium', False)
    premium_status = "✅ Yes" if premium else "❌ No"
    player_info.append(f"💎 **Premium:** {premium_status}")
    
    # Add Gold Boxes with custom emoji
    goldboxes = player_data.get('goldboxes', 0)
    player_info.append(f"{GOLDBOX_EMOJI} **Gold Boxes:** {goldboxes:,}")
    
    if player_info:
        embed.add_field(
            name="ℹ️ Player Information", 
            value="\n".join(player_info),
            inline=False
        )
    
    # Equipment Section (only turrets and hulls)
    equipment_text = player_data.get('equipment', '')
    if equipment_text:
        # Parse equipment to show only turrets and hulls
        equipment_lines = []
        
        # This would need to be enhanced based on actual equipment data structure
        # For now, show the equipment as is
        equipment_lines.append(f"🔫 **Equipment:** {equipment_text}")
        
        if equipment_lines:
            embed.add_field(
                name="🎯 Equipment (Turrets & Hulls)",
                value="\n".join(equipment_lines),
                inline=False
            )
    
    # Add current rankings section
    rankings_data = []
    if player_data.get('experience_rank') and player_data.get('experience_rank') != 'N/A':
        rankings_data.append(f"📊 **By Experience:** #{player_data.get('experience_rank')}")
    if player_data.get('crystals_rank') and player_data.get('crystals_rank') != 'N/A':
        rankings_data.append(f"💎 **By Crystals:** #{player_data.get('crystals_rank')}")
    if player_data.get('kills_rank') and player_data.get('kills_rank') != 'N/A':
        rankings_data.append(f"⚔️ **By Kills:** #{player_data.get('kills_rank')}")
    if player_data.get('efficiency_rank') and player_data.get('efficiency_rank') != 'N/A':
        rankings_data.append(f"🏆 **By Efficiency:** #{player_data.get('efficiency_rank')}")
    
    if rankings_data:
        embed.add_field(
            name="🏆 Current Rankings", 
            value="\n".join(rankings_data), 
            inline=False
        )
    
    embed.set_footer(
        text="RTanks Online Statistics",
        icon_url="https://ratings.ranked-rtanks.online/public/images/logo.png"
    )
    
    return embed

class PlayerDetailsView(discord.ui.View):
    """View for expandable player details with + button"""
    
    def __init__(self, player_data: dict):
        super().__init__(timeout=300)  # 5 minute timeout
        self.player_data = player_data
    
    @discord.ui.button(label='+', style=discord.ButtonStyle.secondary, emoji='📊')
    async def show_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed player statistics"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create detailed embed
            embed = create_detailed_player_embed(self.player_data)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error showing player details: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="There was an error loading detailed player information.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        # Disable button when view times out
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True

@bot.tree.command(name="user", description="Get simplified RTanks Online player info with expandable details")
@discord.app_commands.describe(nickname="The player's nickname to look up")
async def user_stats(interaction: discord.Interaction, nickname: str):
    """Simplified player stats command with expandable details"""
    
    # Defer the response since scraping might take time
    await interaction.response.defer()
    
    try:
        # Scrape player data
        player_data = await scraper.get_player_stats(nickname)
        
        if not player_data:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"No player found with nickname: **{nickname}**",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Tip", 
                value="Make sure the nickname is spelled correctly and the player exists in RTanks Online.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Add activity status to player data by checking the HTML
        if hasattr(scraper, '_last_html_content'):
            player_data['activity_status'] = detect_activity_status(scraper._last_html_content, nickname)
        else:
            player_data['activity_status'] = "❓ Unknown"
        
        # Create simplified embed with expandable details
        embed = create_simplified_player_embed(player_data)
        view = PlayerDetailsView(player_data)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error fetching player stats for {nickname}: {e}")
        
        embed = discord.Embed(
            title="⚠️ Error",
            description="Failed to retrieve player statistics.",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="player", description="Get detailed RTanks Online player statistics")
@discord.app_commands.describe(nickname="The player's nickname to look up")
async def player_stats(interaction: discord.Interaction, nickname: str):
    """Detailed player stats command"""
    
    # Defer the response since scraping might take time
    await interaction.response.defer()
    
    try:
        # Scrape player data
        player_data = await scraper.get_player_stats(nickname)
        
        # Debug log the extracted data
        if player_data:
            logger.info(f"Player data for {nickname}: Experience={player_data.get('experience')}, Kills={player_data.get('kills')}, Deaths={player_data.get('deaths')}, K/D={player_data.get('kd_ratio')}")
        
        if not player_data:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"No player found with nickname: **{nickname}**",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Tip", 
                value="Make sure the nickname is spelled correctly and the player exists in RTanks Online.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create and send detailed embed
        embed = create_detailed_player_embed(player_data)
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error fetching player stats for {nickname}: {e}")
        
        embed = discord.Embed(
            title="⚠️ Error",
            description="Failed to retrieve player statistics.",
            color=0xffa500
        )
        await interaction.followup.send(embed=embed)

class LeaderboardView(discord.ui.View):
    """View for leaderboard category selection"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.select(
        placeholder="Choose a leaderboard category...",
        options=[
            discord.SelectOption(
                label="Experience Leaderboard",
                description="Top players by earned experience",
                value="experience",
                emoji="📊"
            ),
            discord.SelectOption(
                label="Crystals Leaderboard", 
                description="Top players by earned crystals",
                value="crystals",
                emoji="💎"
            ),
            discord.SelectOption(
                label="Kills Leaderboard",
                description="Top players by total kills",
                value="kills", 
                emoji="⚔️"
            ),
            discord.SelectOption(
                label="Efficiency Leaderboard",
                description="Top players by efficiency rating",
                value="efficiency",
                emoji="🏆"
            )
        ]
    )
    async def select_leaderboard(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        
        try:
            category = select.values[0]
            leaderboard_data = await scraper.get_leaderboard(category)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title="❌ Leaderboard Unavailable",
                    description=f"Could not retrieve {category} leaderboard data.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create leaderboard embed
            embed = create_leaderboard_embed(leaderboard_data, category)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error fetching leaderboard for {select.values[0]}: {e}")
            
            embed = discord.Embed(
                title="⚠️ Error",
                description="Failed to retrieve leaderboard data.",
                color=0xffa500
            )
            await interaction.followup.send(embed=embed)

def create_leaderboard_embed(leaderboard_data: list, category: str) -> discord.Embed:
    """Create a Discord embed for leaderboard data with fixed emojis"""
    
    category_info = LEADERBOARD_CATEGORIES.get(category, {})
    title = category_info.get('title', f'{category.title()} Leaderboard')
    emoji = category_info.get('emoji', '🏆')
    
    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=f"Top 10 players in RTanks Online",
        color=0x00ff00,
        timestamp=datetime.utcnow()
    )
    
    # Add top 10 players with CORRECT emojis
    leaderboard_text = ""
    for i, player in enumerate(leaderboard_data[:10], 1):
        rank_emoji = get_rank_emoji(player.get('rank', ''))
        
        # Format position with PROPER medals for top 3
        if i == 1:
            position = "🥇"
        elif i == 2:
            position = "🥈" 
        elif i == 3:
            position = "🥉"
        else:
            position = f"{i}."
        
        value = player.get('value', 'N/A')
        if isinstance(value, (int, float)) and value >= 1000:
            value = f"{value:,}"
        
        # Truncate long nicknames to prevent field overflow
        nickname = player['nickname']
        if len(nickname) > 15:
            nickname = nickname[:12] + "..."
        
        leaderboard_text += f"{position} {rank_emoji} **{nickname}** - {value}\n"
    
    # Split into multiple fields if still too long
    if len(leaderboard_text) > 1000:
        # Split into two fields
        lines = leaderboard_text.strip().split('\n')
        mid_point = len(lines) // 2
        
        embed.add_field(
            name="Rankings 1-5",
            value="\n".join(lines[:mid_point]),
            inline=True
        )
        embed.add_field(
            name="Rankings 6-10",
            value="\n".join(lines[mid_point:]),
            inline=True
        )
    else:
        embed.add_field(
            name="Rankings",
            value=leaderboard_text,
            inline=False
        )
    
    # Add timestamp info
    embed.add_field(
        name="ℹ️ Update Info",
        value="Rankings update regularly on the RTanks website.\nData refreshed every 15 minutes.",
        inline=False
    )
    
    embed.set_footer(
        text="RTanks Online Statistics",
        icon_url="https://ratings.ranked-rtanks.online/public/images/logo.png"
    )
    
    return embed

@bot.tree.command(name="top", description="View RTanks Online leaderboards by category")
async def top_players(interaction: discord.Interaction):
    """Show interactive category selection for leaderboards"""
    embed = discord.Embed(
        title="🏆 RTanks Online Leaderboards",
        description="Select a category to view the top 10 players:",
        color=0x00ff00
    )
    embed.add_field(
        name="Available Categories",
        value="📊 Experience Leaderboard\n💎 Crystals Leaderboard\n⚔️ Kills Leaderboard\n🏆 Efficiency Leaderboard",
        inline=False
    )
    embed.set_footer(text="Select a category from the dropdown below")
    
    view = LeaderboardView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="about", description="Information about the RTanks Online bot")
async def about(interaction: discord.Interaction):
    """Show information about the bot"""
    embed = discord.Embed(
        title="🤖 RTanks Online Bot",
        description="Enhanced Discord bot for viewing RTanks Online player statistics and leaderboards",
        color=0x0099ff
    )
    embed.add_field(
        name="Commands",
        value="• `/user <nickname>` - Simplified player stats with expandable details\n"
              "• `/player <nickname>` - Detailed player statistics\n"
              "• `/top` - View leaderboards by category\n"
              "• `/about` - Show this information",
        inline=False
    )
    embed.add_field(
        name="Features",
        value="• Real-time player statistics and activity status\n"
              "• Interactive leaderboard categories with proper emojis\n"
              "• Expandable player details with (+) button\n"
              "• Support for Russian text with translation\n"
              "• Cached data for improved performance",
        inline=False
    )
    embed.add_field(
        name="Data Source",
        value="[RTanks Online Ratings](https://ratings.ranked-rtanks.online/)",
        inline=False
    )
    embed.set_footer(text="RTanks Online - Nostalgic tank battles restored!")
    
    await interaction.response.send_message(embed=embed)

@tasks.loop(hours=1)
async def hourly_leaderboard():
    """Hourly task for leaderboard updates"""
    try:
        if LEADERBOARD_CHANNEL_ID:
            channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
            if channel:
                # This can be used for automated leaderboard posts
                logger.info("Hourly leaderboard task executed")
    except Exception as e:
        logger.error(f"Error in hourly leaderboard task: {e}")

# Start the bot
if __name__ == "__main__":
    # Start keep_alive for Render deployment
    keep_alive()
    
    # Run the bot
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)

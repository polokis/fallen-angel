import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
import re
from typing import Dict, List, Optional
import trafilatura

logger = logging.getLogger(__name__)

class RTanksPlayerScraper:
    """Scraper for RTanks Online player statistics and leaderboards"""
    
    def __init__(self):
        self.base_url = "https://ratings.ranked-rtanks.online"
        self.session = None
        self._last_html_content = ""  # Store last HTML for activity detection
        
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
        return self.session
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page and return its content"""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    self._last_html_content = content  # Store for activity detection
                    return content
                else:
                    logger.error(f"HTTP {response.status} when fetching {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_rank_from_image(self, img_src: str) -> str:
        """Extract rank name from image URL"""
        # Image URLs are like: https://i.imgur.com/a3UCeT5.png
        # We need to map these to rank names based on the pattern seen in the data
        rank_mappings = {
            'a3UCeT5.png': 'Warrant Officer 5',  # Уорэнт-офицер 5
            'O6Tb9li.png': 'Colonel',             # Полковник
            'rCN2gJm.png': 'Lieutenant Colonel',  # Подполковник
            'R69LmLt.png': 'Major',               # Майор
            'Ljy2jDX.png': 'Captain',             # Капитан
            'lTXxLVJ.png': 'First Lieutenant',    # Первый лейтенант
            'iTyjOt3.png': 'Second Lieutenant',   # Второй лейтенант
            'BIr8vRX.png': 'Warrant Officer 4',  # Уорэнт-офицер 4
            'sppjRis.png': 'Warrant Officer 3',  # Уорэнт-офицер 3
            'LATOpxZ.png': 'Warrant Officer 2',  # Уорэнт-офицер 2
            'ekbJYyf.png': 'Warrant Officer 1',  # Уорэнт-офицер 1
            'GzJRzgz.png': 'Master Sergeant',    # Мастер-сержант
            'pxzNyxi.png': 'Sergeant First Class', # Старший сержант
            'UWup9qJ.png': 'Staff Sergeant',     # Штаб-сержант
            'dSE90bT.png': 'Sergeant',           # Сержант
            'paF1myt.png': 'Corporal',           # Капрал
            'wPZnaG0.png': 'Lance Corporal',     # Младший капрал
            'Or6Ajto.png': 'Private First Class', # Рядовой первого класса
            'AYAs02w.png': 'Private',            # Рядовой
            'M4GBQIq.png': 'Recruit',            # Новобранец
            'Q2YgFQ1.png': 'Legend',             # Легенда
            'rO3Hs5f.png': 'Generalissimo',      # Генералиссимус
            'OQEHkm7.png': 'General',            # Генерал
            'BNZpCPo.png': 'Lieutenant General', # Генерал-лейтенант
            'eQXJOZE.png': 'Major General',      # Генерал-майор
            'Sluzy': 'Brigadier General'         # Бригадный генерал
        }
        
        # Extract filename from URL
        if 'imgur.com' in img_src:
            filename = img_src.split('/')[-1]
            return rank_mappings.get(filename, 'Unknown Rank')
        
        return 'Unknown Rank'
    
    def _detect_activity_status(self, soup: BeautifulSoup, nickname: str) -> str:
        """Detect if player is online or offline based on visual indicators"""
        try:
            # Convert soup to string for easier searching
            html_content = str(soup).lower()
            
            # Check for online indicators (green dots, online text)
            online_indicators = [
                'color: green', 'color:green', 'background: green', 'background:green',
                'rgb(0, 255, 0)', 'rgb(0,255,0)', '#00ff00', '#0f0',
                'онлайн', 'online', 'в сети', 'active', 'зеленый'
            ]
            
            # Check for offline indicators (grey dots, offline text)
            offline_indicators = [
                'color: gray', 'color:gray', 'color: grey', 'color:grey',
                'background: gray', 'background:gray', 'background: grey', 'background:grey',
                'rgb(128, 128, 128)', 'rgb(128,128,128)', '#808080', '#888',
                'оффлайн', 'offline', 'не в сети', 'inactive', 'последний раз', 'серый'
            ]
            
            # Look for status indicators near the player name
            player_section = soup.find(text=re.compile(nickname, re.I))
            if player_section:
                parent = player_section.parent
                if parent:
                    # Check the parent and nearby elements for status indicators
                    parent_html = str(parent).lower()
                    
                    # Check for online status
                    for indicator in online_indicators:
                        if indicator in parent_html:
                            return "🟢 Online"
                    
                    # Check for offline status
                    for indicator in offline_indicators:
                        if indicator in parent_html:
                            return "⚫ Offline"
            
            # Global check for online status
            for indicator in online_indicators:
                if indicator in html_content:
                    return "🟢 Online"
            
            # Global check for offline status
            for indicator in offline_indicators:
                if indicator in html_content:
                    return "⚫ Offline"
            
            # Default to unknown status
            return "❓ Unknown"
            
        except Exception as e:
            logger.error(f"Error detecting activity status: {e}")
            return "❓ Unknown"

    async def get_player_stats(self, nickname: str) -> Optional[Dict]:
        """Get player statistics by nickname"""
        try:
            # Construct player profile URL
            player_url = f"{self.base_url}/user/{nickname}"
            
            # Fetch player page
            html_content = await self._fetch_page(player_url)
            if not html_content:
                return None
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract player data
            player_data = {
                'nickname': nickname,
                'rank': 'Unknown',
                'experience': 0,
                'kills': 0,
                'deaths': 0,
                'kd_ratio': 0.0,
                'premium': False,
                'goldboxes': 0,
                'crystals_rank': 'N/A',
                'efficiency_rank': 'N/A',
                'experience_rank': 'N/A',
                'kills_rank': 'N/A',
                'equipment': '',
                'activity_status': self._detect_activity_status(soup, nickname),
                'hit': 'N/A',  # Added for future implementation
                'destroyed': 0,  # Will use kills value
                'group': 'Player'  # Default group
            }
            
            # Extract rank from image or text
            rank_img = soup.find('img', src=re.compile(r'imgur\.com'))
            if rank_img:
                player_data['rank'] = self._extract_rank_from_image(rank_img['src'])
            
            # Always try to extract rank from text since image method may not work
            # Look for any font element with gray color (more flexible approach)
            gray_fonts = soup.find_all('font', attrs={'style': lambda x: x and 'gray' in str(x).lower()})
            for font in gray_fonts:
                rank_text = font.get_text(strip=True)
                if rank_text and 2 < len(rank_text) < 30:  # Reasonable rank name length
                    player_data['rank'] = rank_text
                    break
            
            # Extract experience from XP bar and table
            exp_found = False
            
            # Method 1: Extract from XP progress bar (.text_xp class)
            xp_element = soup.find('div', class_='text_xp')
            if xp_element:
                xp_text = xp_element.get_text(strip=True)
                # Extract the first number from "2 106 / 3 700" format
                exp_match = re.search(r'(\d{1,3}(?:\s\d{3})*)', xp_text)
                if exp_match:
                    player_data['experience'] = int(exp_match.group(1).replace(' ', ''))
                    exp_found = True
            
            # Method 2: Look for "По опыту" (By experience) in ratings table
            if not exp_found:
                for table in soup.find_all('table'):
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:  # Need 3 columns: category, rank, value
                            category = cells[0].get_text(strip=True).lower()
                            value = cells[2].get_text(strip=True)
                            
                            if 'по опыту' in category or 'опыт' in category:
                                # Extract number from experience value
                                exp_match = re.search(r'(\d{1,3}(?:\s\d{3})*)', value)
                                if exp_match:
                                    player_data['experience'] = int(exp_match.group(1).replace(' ', ''))
                                    exp_found = True
                                    break
                    if exp_found:
                        break
            
            # Extract kills, deaths, and K/D ratio from tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'уничтожил' in key or 'kills' in key:
                            kills_value = int(re.sub(r'[^\d]', '', value) or 0)
                            player_data['kills'] = kills_value
                            player_data['destroyed'] = kills_value  # Use kills as destroyed
                        elif 'подбит' in key or 'deaths' in key:
                            player_data['deaths'] = int(re.sub(r'[^\d]', '', value) or 0)
                        elif 'у/п' in key or 'k/d' in key or 'эффективность' in key:
                            try:
                                player_data['kd_ratio'] = float(value.replace(',', '.'))
                            except:
                                pass
                        elif 'премиум' in key or 'premium' in key:
                            player_data['premium'] = 'да' in value.lower() or 'yes' in value.lower()
                        elif 'золот' in key or 'gold' in key:
                            player_data['goldboxes'] = int(re.sub(r'[^\d]', '', value) or 0)
            
            # Extract ranking positions from ratings table
            # Find the table with "Места в текущих рейтингах" (Current rankings)
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:  # category, rank, value
                        category = cells[0].get_text(strip=True).lower()
                        rank = cells[1].get_text(strip=True).replace('#', '')
                        
                        if 'по опыту' in category:
                            player_data['experience_rank'] = rank if rank != '0' else 'N/A'
                        elif 'голдоловов' in category or 'золот' in category:
                            # This is goldboxes, we can skip rank but get the value
                            pass
                        elif 'по киллам' in category:
                            player_data['kills_rank'] = rank if rank != '0' else 'N/A'
                        elif 'по эффективности' in category:
                            player_data['efficiency_rank'] = rank if rank != '0' else 'N/A'
            
            # Extract current equipment information - focus on turrets and hulls
            equipment_sections = soup.find_all('div', class_=re.compile(r'equipment|loadout'))
            equipment_parts = []
            
            # Look for equipment in various sections
            for section in equipment_sections:
                text = section.get_text(strip=True)
                if text:
                    equipment_parts.append(text)
            
            # Also check for equipment images
            equipment_imgs = soup.find_all('img', alt=re.compile(r'turret|hull|пушка|корпус|орудие|танк', re.I))
            for img in equipment_imgs:
                alt_text = img.get('alt', '')
                if alt_text and alt_text not in equipment_parts:
                    equipment_parts.append(alt_text)
            
            if equipment_parts:
                player_data['equipment'] = ' | '.join(equipment_parts[:5])  # Limit to 5 items
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error parsing player data for {nickname}: {e}")
            return None
    
    async def get_leaderboard(self, category: str) -> Optional[List[Dict]]:
        """Get leaderboard data for specified category"""
        try:
            # Map category to the appropriate section on the main page
            if category == 'experience':
                # Main page shows experience leaderboard by default
                url = self.base_url
            elif category == 'crystals':
                # Crystal leaderboard is also on main page
                url = self.base_url
            else:
                # For other categories, we'll parse what's available
                url = self.base_url
            
            html_content = await self._fetch_page(url)
            if not html_content:
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find leaderboard tables
            leaderboard_data = []
            
            # Look for the main leaderboard table
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        try:
                            # Extract position, player info, and value
                            position = cells[0].get_text(strip=True)
                            
                            # Player cell contains image and name
                            player_cell = cells[1]
                            player_link = player_cell.find('a')
                            if player_link:
                                nickname = player_link.get_text(strip=True)
                                
                                # Extract rank from image
                                rank_img = player_cell.find('img')
                                rank = 'Unknown'
                                if rank_img and rank_img.get('src'):
                                    rank = self._extract_rank_from_image(rank_img['src'])
                                
                                # Extract value
                                value_text = cells[2].get_text(strip=True)
                                
                                # Clean and parse value
                                value_clean = re.sub(r'[^\d\s]', '', value_text)
                                value_clean = value_clean.replace(' ', '')
                                
                                try:
                                    value = int(value_clean) if value_clean else 0
                                except ValueError:
                                    value = 0
                                
                                # Validate position
                                if position.isdigit() and 1 <= int(position) <= 100:
                                    leaderboard_data.append({
                                        'position': int(position),
                                        'nickname': nickname,
                                        'rank': rank,
                                        'value': value,
                                        'formatted_value': value_text
                                    })
                                    
                        except Exception as e:
                            logger.debug(f"Error parsing leaderboard row: {e}")
                            continue
            
            # Sort by position and return top 10
            leaderboard_data.sort(key=lambda x: x['position'])
            return leaderboard_data[:10]
            
        except Exception as e:
            logger.error(f"Error fetching leaderboard for {category}: {e}")
            return None
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup when scraper is destroyed"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            asyncio.create_task(self.close())

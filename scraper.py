import asyncio
import httpx
import re
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class RTanksScraper:
    def __init__(self):
        self.base_url = "https://ratings.ranked-rtanks.online"
        self.session = None
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes cache
        
        # Headers to mimic a real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def get_session(self):
        """Get or create httpx session"""
        if self.session is None or self.session.is_closed:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                headers=self.headers
            )
        return self.session
    
    async def close_session(self):
        """Close the httpx session"""
        if self.session and not self.session.is_closed:
            await self.session.aclose()
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp', 0)
        return time.time() - cached_time < self.cache_timeout
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if self.is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None
    
    def set_cache(self, cache_key: str, data: Any):
        """Set data in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling"""
        try:
            session = await self.get_session()
            response = await session.get(url)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"HTTP {response.status_code} for URL: {url}")
                return None
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def detect_activity_status(self, soup: BeautifulSoup, nickname: str) -> str:
        """Detect if player is online or offline based on visual indicators"""
        try:
            # Look for activity indicators near the player name
            # Green dot indicators for online status
            online_indicators = soup.find_all(['span', 'div', 'i'], class_=re.compile(r'online|active|green', re.I))
            offline_indicators = soup.find_all(['span', 'div', 'i'], class_=re.compile(r'offline|inactive|grey|gray', re.I))
            
            # Check for color-based indicators in style attributes
            elements_with_color = soup.find_all(attrs={"style": re.compile(r'color\s*:\s*green|background.*green', re.I)})
            if elements_with_color:
                return "🟢 Online"
            
            elements_with_gray = soup.find_all(attrs={"style": re.compile(r'color\s*:\s*gr[ae]y|background.*gr[ae]y', re.I)})
            if elements_with_gray:
                return "⚫ Offline"
            
            # Check for common online/offline text indicators
            page_text = soup.get_text().lower()
            if 'онлайн' in page_text or 'online' in page_text:
                return "🟢 Online"
            elif 'оффлайн' in page_text or 'offline' in page_text:
                return "⚫ Offline"
            
            # Check for status indicators in images
            status_imgs = soup.find_all('img', src=re.compile(r'online|offline|status', re.I))
            for img in status_imgs:
                src = img.get('src', '').lower()
                if 'online' in src or 'green' in src:
                    return "🟢 Online"
                elif 'offline' in src or 'grey' in src or 'gray' in src:
                    return "⚫ Offline"
            
            # Look for last seen information
            last_seen_pattern = re.compile(r'последн[ийая].*вход|last.*seen|был.*онлайн', re.I)
            last_seen = soup.find(text=last_seen_pattern)
            if last_seen:
                return "⚫ Offline"
            
            # Default to unknown status
            return "❓ Unknown"
            
        except Exception as e:
            logger.error(f"Error detecting activity status: {e}")
            return "❓ Unknown"
    
    def parse_player_profile(self, html: str, nickname: str) -> Optional[Dict]:
        """Parse player profile HTML with enhanced data extraction"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check if player exists
            if "профиль игрока" not in html.lower() and nickname.lower() not in html.lower():
                return None
            
            player_data = {
                'nickname': nickname,
                'rank': None,
                'rank_emoji': None,
                'experience': None,
                'kills': None,
                'deaths': None,
                'kd_ratio': None,
                'gold_boxes': None,
                'premium': None,
                'group': None,
                'activity_status': self.detect_activity_status(soup, nickname),
                'destroyed': None,
                'hit': None,
                'rankings': {},
                'equipment': {
                    'turrets': [],
                    'hulls': []
                }
            }
            
            # Enhanced rank detection with emoji mapping
            rank_patterns = [
                r'генерал',
                r'полковник',
                r'подполковник', 
                r'майор',
                r'капитан',
                r'старший лейтенант',
                r'лейтенант',
                r'младший лейтенант',
                r'старший прапорщик',
                r'прапорщик',
                r'старший сержант',
                r'сержант',
                r'младший сержант',
                r'ефрейтор',
                r'рядовой'
            ]
            
            # Find rank in text
            page_text = soup.get_text().lower()
            for pattern in rank_patterns:
                if re.search(pattern, page_text):
                    player_data['rank'] = pattern.title()
                    player_data['rank_emoji'] = self.get_rank_emoji(pattern)
                    break
            
            # Extract experience with multiple patterns
            exp_patterns = [
                re.compile(r'опыт[:\s]*(\d+)', re.I),
                re.compile(r'experience[:\s]*(\d+)', re.I),
                re.compile(r'(\d+)\s*/\s*\d+'),
                re.compile(r'(\d+)\s+/\s+\d+')
            ]
            
            for pattern in exp_patterns:
                match = pattern.search(html)
                if match:
                    try:
                        player_data['experience'] = int(match.group(1).replace(' ', ''))
                        break
                    except ValueError:
                        continue
            
            # Enhanced statistics extraction
            stat_patterns = {
                'kills': [r'уничтожил[:\s]*(\d+)', r'убийств[:\s]*(\d+)', r'kills[:\s]*(\d+)'],
                'deaths': [r'подбит[:\s]*(\d+)', r'смертей[:\s]*(\d+)', r'deaths[:\s]*(\d+)'],
                'destroyed': [r'уничтожено[:\s]*(\d+)', r'destroyed[:\s]*(\d+)'],
                'hit': [r'попаданий[:\s]*(\d+)', r'hit[:\s]*(\d+)', r'hits[:\s]*(\d+)'],
                'gold_boxes': [r'золотых ящиков[:\s]*(\d+)', r'gold.*boxes?[:\s]*(\d+)']
            }
            
            for stat_name, patterns in stat_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, html, re.I)
                    if match:
                        try:
                            player_data[stat_name] = int(match.group(1).replace(' ', ''))
                            break
                        except ValueError:
                            continue
            
            # Calculate K/D ratio
            if player_data['kills'] is not None and player_data['deaths'] is not None and player_data['deaths'] > 0:
                player_data['kd_ratio'] = round(player_data['kills'] / player_data['deaths'], 2)
            
            # Extract from tables (fallback method)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if any(word in key for word in ['уничтожил', 'убийств', 'kills']):
                            if value.isdigit():
                                player_data['kills'] = int(value)
                        elif any(word in key for word in ['подбит', 'смертей', 'deaths']):
                            if value.isdigit():
                                player_data['deaths'] = int(value)
                        elif 'у/п' in key or 'k/d' in key:
                            try:
                                player_data['kd_ratio'] = float(value)
                            except ValueError:
                                pass
                        elif 'золотых ящиков' in key:
                            if value.isdigit():
                                player_data['gold_boxes'] = int(value)
                        elif 'премиум' in key:
                            player_data['premium'] = 'да' in value.lower()
                        elif 'группа' in key:
                            player_data['group'] = value
            
            # Enhanced equipment parsing (only turrets and hulls)
            equipment_patterns = {
                'turrets': [r'turret', r'пушк', r'орудие'],
                'hulls': [r'hull', r'корпус', r'танк']
            }
            
            # Look for equipment images and descriptions
            imgs = soup.find_all('img')
            for img in imgs:
                src = str(img.get('src', '')).lower()
                alt = str(img.get('alt', '')).lower()
                title = str(img.get('title', '')).lower()
                
                for equip_type, patterns in equipment_patterns.items():
                    if any(pattern in src or pattern in alt or pattern in title for pattern in patterns):
                        equipment_name = alt or title or 'Unknown'
                        if equipment_name and equipment_name != 'unknown' and equipment_name not in player_data['equipment'][equip_type]:
                            player_data['equipment'][equip_type].append(equipment_name)
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error parsing player profile: {e}")
            return None

    def get_rank_emoji(self, rank: str) -> str:
        """Get appropriate emoji for player rank"""
        rank = rank.lower()
        rank_emojis = {
            'генерал': '⭐',
            'полковник': '🌟',
            'подполковник': '✨',
            'майор': '🎖️',
            'капитан': '🏅',
            'старший лейтенант': '🥇',
            'лейтенант': '🥈',
            'младший лейтенант': '🥉',
            'старший прапорщик': '🎯',
            'прапорщик': '🔰',
            'старший сержант': '⚔️',
            'сержант': '🛡️',
            'младший сержант': '⚡',
            'ефрейтор': '🔸',
            'рядовой': '🔹'
        }
        return rank_emojis.get(rank, '🎖️')
    
    async def get_player_stats(self, nickname: str) -> Optional[Dict]:
        """Get player statistics from RTanks ratings"""
        cache_key = f"player_{nickname}"
        
        # Check cache first
        cached_data = self.get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Fetch from website
        url = f"{self.base_url}/user/{nickname}"
        html = await self.fetch_page(url)
        
        if not html:
            return None
        
        player_data = self.parse_player_profile(html, nickname)
        
        if player_data:
            self.set_cache(cache_key, player_data)
        
        return player_data
    
    def get_leaderboard_emoji(self, rank: int) -> str:
        """Get appropriate emoji for leaderboard position"""
        if rank == 1:
            return '🥇'
        elif rank == 2:
            return '🥈'
        elif rank == 3:
            return '🥉'
        elif rank <= 5:
            return '🏅'
        elif rank <= 10:
            return '🎖️'
        else:
            return '🔸'
    
    def parse_leaderboard(self, html: str) -> List[Dict]:
        """Parse leaderboard HTML with improved emoji handling"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            players = []
            
            # Find the leaderboard table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Extract rank, player name, and value
                        rank_text = cells[0].get_text(strip=True)
                        player_cell = cells[1]
                        value_text = cells[2].get_text(strip=True)
                        
                        # Extract player name from link or img alt
                        player_name = None
                        player_link = player_cell.find('a')
                        if player_link:
                            player_name = player_link.get_text(strip=True)
                        
                        # Also check for img alt attribute
                        if not player_name:
                            img = player_cell.find('img')
                            if img:
                                player_name = img.get('alt', '').strip()
                        
                        # Try to extract from any text in the cell
                        if not player_name:
                            player_name = player_cell.get_text(strip=True)
                        
                        # Clean up player name
                        if player_name:
                            # Remove rank icons and other prefixes
                            player_name = re.sub(r'^[\d\s]+', '', player_name).strip()
                            player_name = re.sub(r'^\W+', '', player_name).strip()
                        
                        # Validate rank
                        if rank_text.isdigit() and player_name and value_text:
                            rank = int(rank_text)
                            
                            # Clean up value (remove non-numeric characters except spaces)
                            value_clean = re.sub(r'[^\d\s]', '', value_text).strip()
                            value_clean = value_clean.replace(' ', '')
                            
                            try:
                                if value_clean:
                                    value = int(value_clean)
                                else:
                                    value = 0
                            except ValueError:
                                value = 0
                            
                            players.append({
                                'rank': rank,
                                'name': player_name,
                                'value': value,
                                'formatted_value': value_text,
                                'emoji': self.get_leaderboard_emoji(rank)
                            })
            
            # Sort by rank and limit to top 10
            players.sort(key=lambda x: x['rank'])
            return players[:10]
            
        except Exception as e:
            logger.error(f"Error parsing leaderboard: {e}")
            return []
    
    async def get_leaderboard(self, category: str) -> Optional[List[Dict]]:
        """Get leaderboard for specified category"""
        cache_key = f"leaderboard_{category}"
        
        # Check cache first
        cached_data = self.get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Fetch main ratings page
        url = self.base_url
        html = await self.fetch_page(url)
        
        if not html:
            return None
        
        # Parse leaderboard data
        leaderboard_data = self.parse_leaderboard(html)
        
        if leaderboard_data:
            self.set_cache(cache_key, leaderboard_data)
        
        return leaderboard_data
    
    def __del__(self):
        """Cleanup when scraper is destroyed"""
        if self.session and not self.session.is_closed:
            asyncio.create_task(self.close_session())

# social_media_sync.py - synchronization of social media posts to db
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import requests
from typing import List, Dict, Optional
import asyncio
import aiohttp
import re

# Since this script is in sync directory, go back one in sys path to access shared config files
import sys
sys.path.append('..')
# Import shared configuration from main directory
from config import DatabaseConfig, SocialMediaConfig

class SocialMediaSync:
    def __init__(self, db_config: DatabaseConfig, social_config: SocialMediaConfig):
        self.db_config = db_config
        self.social_config = social_config
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('social_media_sync.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_db_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.database,
                user=self.db_config.user,
                password=self.db_config.password,
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def ensure_social_account_exists(self, platform: str, handle: str, account_name: str) -> int:
        """Ensure social media account exists in database and return account_id"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO social_media_accounts (platform, account_handle, account_name, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (platform, account_handle) DO UPDATE SET
                    account_name = EXCLUDED.account_name,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING account_id;
            """, (platform, handle, account_name))
            
            result = cursor.fetchone()
            if result is None:
                raise Exception(f"Failed to create or retrieve social media account for {platform}:{handle}")
            
            account_id = result[0]
            conn.commit()
            return account_id
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error ensuring social account exists: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    async def sync_instagram_business_data(self):
        """Sync Instagram data using Graph API (Business/Creator accounts only)"""
        if not self.social_config.instagram_access_token or not self.social_config.instagram_business_account_id:
            self.logger.warning("Instagram Graph API credentials not configured")
            self.logger.info("Note: Instagram now requires Business/Creator accounts only")
            self.logger.info("Setup instructions:")
            self.logger.info("1. Convert your Instagram to Business/Creator account")
            self.logger.info("2. Get Graph API access token")
            self.logger.info("3. Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID")
            return False
            
        self.logger.info("Starting Instagram Graph API sync (Business account)...")
        
        try:
            # Ensure account exists
            account_id = self.ensure_social_account_exists('instagram', '@test_handle', 'Test Name')
            
            # Get recent posts using Instagram Graph API
            async with aiohttp.ClientSession() as session:
                # Instagram Graph API endpoint for business accounts
                url = f"https://graph.facebook.com/v19.0/{self.social_config.instagram_business_account_id}/media"
                params = {
                    'fields': 'id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count',
                    'access_token': self.social_config.instagram_access_token,
                    'limit': 50
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Instagram Graph API error: {response.status} - {error_text}")
                        return False
                    
                    data = await response.json()
                    
                    if 'error' in data:
                        self.logger.error(f"Instagram API error: {data['error']}")
                        return False
                    
                    posts = data.get('data', [])
                    
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    
                    try:
                        for post in posts:
                            await self._sync_instagram_business_post(cursor, account_id, post, session)
                        
                        conn.commit()
                        self.logger.info(f"Successfully synced {len(posts)} Instagram business posts")
                        return True
                        
                    except Exception as e:
                        conn.rollback()
                        self.logger.error(f"Error syncing Instagram posts: {e}")
                        return False
                    finally:
                        cursor.close()
                        conn.close()
                    
        except Exception as e:
            self.logger.error(f"Instagram Graph API sync failed: {e}")
            return False

    async def _sync_instagram_business_post(self, cursor, account_id: int, post_data: Dict, session: aiohttp.ClientSession):
        """Sync single Instagram business post"""
        
        # Extract hashtags from caption
        caption = post_data.get('caption', '')
        hashtags = self._extract_hashtags(caption)
        mentions = self._extract_mentions(caption)
        
        # Parse timestamp
        timestamp_str = post_data.get('timestamp', '')
        posted_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')) if timestamp_str else datetime.now()
        
        # Prepare post data
        post_insert_data = {
            'account_id': account_id,
            'platform_post_id': post_data.get('id'),
            'post_type': post_data.get('media_type', '').lower(),
            'caption': caption,
            'post_url': post_data.get('permalink'),
            'posted_date': posted_date,
            'hashtags': hashtags,
            'mentions': mentions
        }
        
        # Insert post
        cursor.execute("""
            INSERT INTO social_media_posts (
                account_id, platform_post_id, post_type, caption, post_url, 
                posted_date, hashtags, mentions
            ) VALUES (
                %(account_id)s, %(platform_post_id)s, %(post_type)s, %(caption)s, 
                %(post_url)s, %(posted_date)s, %(hashtags)s, %(mentions)s
            )
            ON CONFLICT (platform_post_id) DO UPDATE SET
                caption = EXCLUDED.caption,
                post_url = EXCLUDED.post_url,
                updated_at = CURRENT_TIMESTAMP
            RETURNING post_id
        """, post_insert_data)
        
        result = cursor.fetchone()
        if result is None:
            raise Exception(f"Failed to insert/update Instagram post {post_data.get('id', 'unknown')}")
        
        post_id = result['post_id']  # Use dict key access
        
        # Insert metrics directly from post data (Graph API provides some metrics)
        metrics_data = {
            'post_id': post_id,
            'metric_date': datetime.now().date(),
            'likes': post_data.get('like_count', 0),
            'comments': post_data.get('comments_count', 0),
            # TODO: insights API call
            'impressions': 0,  # Requires additional insights API call
            'reach': 0,        # Requires additional insights API call
            'saves': 0,        # Requires additional insights API call
            'shares': 0,       # Requires additional insights API call
            'engagement_rate': 0  # Will calculate if we have reach data
        }
        
        # Insert metrics
        cursor.execute("""
            INSERT INTO social_media_metrics (
                post_id, metric_date, likes, comments, impressions, reach, 
                saves, shares, engagement_rate
            ) VALUES (
                %(post_id)s, %(metric_date)s, %(likes)s, %(comments)s, 
                %(impressions)s, %(reach)s, %(saves)s, %(shares)s, %(engagement_rate)s
            )
            ON CONFLICT (post_id, metric_date) DO UPDATE SET
                likes = EXCLUDED.likes,
                comments = EXCLUDED.comments,
                updated_at = CURRENT_TIMESTAMP
        """, metrics_data)

    async def sync_facebook_data(self):
        """Sync Facebook posts and metrics (still available)"""
        if not self.social_config.facebook_access_token:
            self.logger.warning("Facebook access token not configured, skipping Facebook sync")
            return False
            
        self.logger.info("Starting Facebook data sync...")
        
        try:
            # Ensure account exists
            account_id = self.ensure_social_account_exists('facebook', f'page_{self.social_config.facebook_page_id}', 'FB Page Name Test')
            
            async with aiohttp.ClientSession() as session:
                # Facebook Graph API endpoint for posts
                url = f"https://graph.facebook.com/v19.0/{self.social_config.facebook_page_id}/posts"
                params = {
                    'fields': 'id,message,created_time,permalink_url,type,reactions.summary(true),comments.summary(true),shares',
                    'access_token': self.social_config.facebook_access_token,
                    'limit': 50
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Facebook API error: {response.status} - {error_text}")
                        return False
                    
                    data = await response.json()
                    posts = data.get('data', [])
                    
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    
                    try:
                        for post in posts:
                            await self._sync_facebook_post(cursor, account_id, post)
                        
                        conn.commit()
                        self.logger.info(f"Successfully synced {len(posts)} Facebook posts")
                        return True
                        
                    except Exception as e:
                        conn.rollback()
                        self.logger.error(f"Error syncing Facebook posts: {e}")
                        return False
                    finally:
                        cursor.close()
                        conn.close()
                    
        except Exception as e:
            self.logger.error(f"Facebook sync failed: {e}")
            return False

    async def _sync_facebook_post(self, cursor, account_id: int, post_data: Dict):
        """Sync single Facebook post"""
        
        # Extract data
        message = post_data.get('message', '')
        hashtags = self._extract_hashtags(message)
        mentions = self._extract_mentions(message)
        
        # Parse timestamp
        created_time = post_data.get('created_time', '')
        posted_date = datetime.fromisoformat(created_time.replace('Z', '+00:00')) if created_time else datetime.now()
        
        # Prepare post data
        post_insert_data = {
            'account_id': account_id,
            'platform_post_id': post_data.get('id'),
            'post_type': post_data.get('type', 'status').lower(),
            'caption': message,
            'post_url': post_data.get('permalink_url'),
            'posted_date': posted_date,
            'hashtags': hashtags,
            'mentions': mentions
        }
        
        # Insert post
        cursor.execute("""
            INSERT INTO social_media_posts (
                account_id, platform_post_id, post_type, caption, post_url, 
                posted_date, hashtags, mentions
            ) VALUES (
                %(account_id)s, %(platform_post_id)s, %(post_type)s, %(caption)s, 
                %(post_url)s, %(posted_date)s, %(hashtags)s, %(mentions)s
            )
            ON CONFLICT (platform_post_id) DO UPDATE SET
                caption = EXCLUDED.caption,
                post_url = EXCLUDED.post_url,
                updated_at = CURRENT_TIMESTAMP
            RETURNING post_id
        """, post_insert_data)
        
        result = cursor.fetchone()
        if result is None:
            raise Exception(f"Failed to insert/update Facebook post {post_data.get('id', 'unknown')}")
        
        post_id = result['post_id']  # Use dict key access
        
        # Extract metrics from post data
        reactions = post_data.get('reactions', {}).get('summary', {}).get('total_count', 0)
        comments = post_data.get('comments', {}).get('summary', {}).get('total_count', 0)
        shares = post_data.get('shares', {}).get('count', 0)
        
        # Prepare metrics data
        metrics_data = {
            'post_id': post_id,
            'metric_date': datetime.now().date(),
            'likes': reactions,
            'comments': comments,
            'shares': shares,
            'impressions': 0,  # Would need insights API for this
            'reach': 0,        # Would need insights API for this
            'engagement_rate': 0  # Calculate if we had reach data
        }
        
        # Insert metrics
        cursor.execute("""
            INSERT INTO social_media_metrics (
                post_id, metric_date, likes, comments, shares, engagement_rate
            ) VALUES (
                %(post_id)s, %(metric_date)s, %(likes)s, %(comments)s, 
                %(shares)s, %(engagement_rate)s
            )
            ON CONFLICT (post_id, metric_date) DO UPDATE SET
                likes = EXCLUDED.likes,
                comments = EXCLUDED.comments,
                shares = EXCLUDED.shares,
                updated_at = CURRENT_TIMESTAMP
        """, metrics_data)

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        hashtags = re.findall(r'#\w+', text.lower())
        return [tag[1:] for tag in hashtags]  # Remove # symbol

    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        mentions = re.findall(r'@\w+', text.lower())
        return [mention[1:] for mention in mentions]  # Remove @ symbol

    async def full_sync(self):
        """Run complete social media synchronization"""
        self.logger.info("Starting full social media data synchronization...")
        
        success = True
        
        # Try to sync available platforms
        tasks = []
        
        # Instagram Graph API (Business accounts)
        if self.social_config.instagram_access_token:
            tasks.append(self.sync_instagram_business_data())
        
        # Facebook Graph API
        if self.social_config.facebook_access_token:
            tasks.append(self.sync_facebook_data())
        
        # Perform sync
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Platform sync {i} failed: {result}")
                    success = False
                elif not result:
                    success = False
        else: 
            self.logger.info("No social media APIs configured")
        
        # Log result of sync
        if success:
            self.logger.info("Full social media synchronization completed successfully")
        else:
            self.logger.error("Social media synchronization completed with errors")
        
        return success

# Configuration and main execution
if __name__ == "__main__":
    from config import load_config
    
    try:
        # Load configuration from shared config module
        config = load_config()
        
        # Initialize sync handler
        sync_handler = SocialMediaSync(config.database, config.social_media)
        
    
        # Run synchronization
        asyncio.run(sync_handler.full_sync())
    except Exception as e:
        logging.error(f"Social media synchronization failed: {e}")
        exit(1)

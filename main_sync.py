# main_sync.py - Main coordination script for all data synchronization

import asyncio
import logging
import sys
from datetime import datetime
import schedule
import time
from typing import Dict, Any

# Import shared configuration
from config import AppConfig, load_config, create_env_template, validate_environment

# Import our sync modules
from square_sync import SquareDataSync
from social_media_sync import SocialMediaSync

class MasterDataSync:
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Initialize sync handlers
        self.square_sync = SquareDataSync(config.database, config.square)
        self.social_sync = SocialMediaSync(config.database, config.social_media)
        
        # Set up logging with configuration
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

    def _setup_logging(self):
        """Set up logging based on configuration"""
        log_level = getattr(logging, self.config.logging.level.upper())
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.logging.file_path),
                logging.StreamHandler()
            ]
        )

    async def full_synchronization(self):
        """Run complete data synchronization across all platforms"""
        self.logger.info("=" * 60)
        self.logger.info(f"Starting master synchronization at {datetime.now()}")
        self.logger.info("=" * 60)
        
        success_results = {}
        
        try:
            # 1. Sync Square data (foundational business data)
            self.logger.info("Phase 1: Synchronizing Square data...")
            success_results['square'] = self.square_sync.full_sync()
            
            # 2. Sync Social Media data
            self.logger.info("Phase 2: Synchronizing Social Media data...")
            success_results['social_media'] = await self.social_sync.full_sync()
            
            # 3. Generate cross-platform analytics
            if all(success_results.values()):
                self.logger.info("Phase 3: Generating cross-platform analytics...")
                await self.generate_cross_platform_analytics()
            else:
                self.logger.warning("Skipping cross-platform analytics due to sync errors")
            
            # Summary
            total_success = all(success_results.values())
            self.logger.info("=" * 60)
            self.logger.info(f"Synchronization completed at {datetime.now()}")
            self.logger.info(f"Square: {'✓' if success_results['square'] else '✗'}")
            self.logger.info(f"Social Media: {'✓' if success_results['social_media'] else '✗'}")
            self.logger.info(f"Overall Status: {'SUCCESS' if total_success else 'PARTIAL/FAILED'}")
            self.logger.info("=" * 60)
            
            return total_success
            
        except Exception as e:
            self.logger.error(f"Master synchronization failed: {e}")
            return False

    async def generate_cross_platform_analytics(self):
        """Generate analytics that combine Square and social media data"""
        self.logger.info("Generating cross-platform analytics...")
        
        conn = None
        cursor = None
        
        try:
            conn = self.square_sync.get_db_connection()
            cursor = conn.cursor()
            
            # Update market performance with social media data
            cursor.execute("""
                -- Update market performance with social media engagement on market days
                UPDATE market_performance mp
                SET notes = COALESCE(mp.notes, '') || 
                    CASE 
                        WHEN social_stats.avg_engagement > 0 THEN 
                            ' | Social engagement: ' || ROUND(social_stats.avg_engagement::numeric, 4)::text
                        ELSE ''
                    END
                FROM (
                    SELECT 
                        DATE(p.posted_date) as post_date,
                        AVG(COALESCE(m.engagement_rate, 0)) as avg_engagement,
                        COUNT(*) as post_count
                    FROM social_media_posts p
                    LEFT JOIN social_media_metrics m ON p.post_id = m.post_id
                    WHERE p.posted_date >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(p.posted_date)
                ) social_stats
                WHERE mp.market_date = social_stats.post_date
                AND (mp.notes IS NULL OR mp.notes NOT LIKE '%Social engagement:%')
            """)
            
            # Create summary analytics view
            cursor.execute("""
                CREATE OR REPLACE VIEW business_performance_summary AS
                SELECT 
                    mp.market_date,
                    mp.location_id,
                    l.location_name,
                    mp.total_sales,
                    mp.total_transactions,
                    mp.average_transaction_value,
                    mp.net_profit,
                    
                    -- Social media metrics for the day
                    COALESCE(social_day.posts_count, 0) as social_posts_count,
                    COALESCE(social_day.avg_engagement, 0) as avg_social_engagement,
                    COALESCE(social_day.total_reach, 0) as total_social_reach,
                    
                    -- Customer acquisition
                    COALESCE(mp.customer_acquisition_count, 0) as new_customers,
                    
                    -- Calculate ROI metrics
                    CASE 
                        WHEN mp.booth_cost > 0 THEN 
                            ROUND((mp.net_profit / mp.booth_cost * 100)::numeric, 2)
                        ELSE NULL 
                    END as roi_percentage
                    
                FROM market_performance mp
                JOIN locations l ON mp.location_id = l.location_id
                LEFT JOIN (
                    SELECT 
                        DATE(p.posted_date) as post_date,
                        COUNT(*) as posts_count,
                        AVG(COALESCE(m.engagement_rate, 0)) as avg_engagement,
                        SUM(COALESCE(m.reach, 0)) as total_reach
                    FROM social_media_posts p
                    LEFT JOIN social_media_metrics m ON p.post_id = m.post_id
                    GROUP BY DATE(p.posted_date)
                ) social_day ON mp.market_date = social_day.post_date
                WHERE mp.market_date >= CURRENT_DATE - INTERVAL '90 days'
                ORDER BY mp.market_date DESC
            """)
            
            # Identify best performing combinations
            cursor.execute("""
                CREATE OR REPLACE VIEW best_performing_strategies AS
                SELECT 
                    l.location_name,
                    COUNT(*) as market_appearances,
                    AVG(mp.total_sales) as avg_sales,
                    AVG(mp.net_profit) as avg_profit,
                    AVG(COALESCE(social_stats.avg_engagement, 0)) as avg_social_engagement,
                    
                    -- Best performing post types for this location
                    STRING_AGG(DISTINCT top_hashtags.hashtag, ', ') as successful_hashtags
                    
                FROM market_performance mp
                JOIN locations l ON mp.location_id = l.location_id
                LEFT JOIN (
                    SELECT 
                        DATE(p.posted_date) as post_date,
                        AVG(COALESCE(m.engagement_rate, 0)) as avg_engagement
                    FROM social_media_posts p
                    LEFT JOIN social_media_metrics m ON p.post_id = m.post_id
                    GROUP BY DATE(p.posted_date)
                ) social_stats ON mp.market_date = social_stats.post_date
                LEFT JOIN (
                    SELECT 
                        DATE(p.posted_date) as post_date,
                        UNNEST(p.hashtags) as hashtag
                    FROM social_media_posts p
                    LEFT JOIN social_media_metrics m ON p.post_id = m.post_id
                    WHERE COALESCE(m.engagement_rate, 0) > 0.05  -- High engagement posts
                ) top_hashtags ON mp.market_date = top_hashtags.post_date
                WHERE mp.market_date >= CURRENT_DATE - INTERVAL '180 days'
                GROUP BY l.location_id, l.location_name
                HAVING COUNT(*) >= 2  -- Locations visited at least twice
                ORDER BY avg_profit DESC
            """)
            
            conn.commit()
            self.logger.info("Cross-platform analytics generated successfully")
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Failed to generate cross-platform analytics: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def quick_sync(self):
        """Quick synchronization for recent data only"""
        self.logger.info("Running quick synchronization...")
        
        try:
            # Use configured days for quick sync
            success_square = self.square_sync.sync_orders(days_back=self.config.quick_sync_days)
            
            # Sync recent social media data
            success_social = asyncio.run(self.social_sync.full_sync())
            
            if success_square and success_social:
                # Update customer aggregates
                self.square_sync.update_customer_aggregates()
                self.logger.info("Quick sync completed successfully")
                return True
            else:
                self.logger.warning("Quick sync completed with errors")
                return False
                
        except Exception as e:
            self.logger.error(f"Quick sync failed: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check system health and API connectivity"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'database': False,
            'square_api': False,
            'instagram_api': False,
            'facebook_api': False,
            'overall': False
        }
        
        # Test database connection
        try:
            conn = self.square_sync.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                health_status['database'] = True
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
        
        # Test Square API
        try:
            locations_api = self.square_sync.square_client.locations
            result = locations_api.list()
            health_status['square_api'] = hasattr(result, 'locations') or not hasattr(result, 'errors')
            
        except Exception as e:
            self.logger.error(f"Square API health check failed: {e}")
        
        # Test Instagram API (if configured)
        if self.config.social_media.has_instagram_config:
            try:
                import requests
                url = f"https://graph.facebook.com/v19.0/{self.config.social_media.instagram_business_account_id}"
                params = {
                    'fields': 'id,name',
                    'access_token': self.config.social_media.instagram_access_token
                }
                response = requests.get(url, params=params, timeout=self.config.health_check_timeout)
                health_status['instagram_api'] = response.status_code == 200
            except Exception as e:
                self.logger.error(f"Instagram API health check failed: {e}")
        
        # Test Facebook API (if configured)
        if self.config.social_media.has_facebook_config:
            try:
                import requests
                url = f"https://graph.facebook.com/v19.0/{self.config.social_media.facebook_page_id}"
                params = {
                    'fields': 'id,name',
                    'access_token': self.config.social_media.facebook_access_token
                }
                response = requests.get(url, params=params, timeout=self.config.health_check_timeout)
                health_status['facebook_api'] = response.status_code == 200
            except Exception as e:
                self.logger.error(f"Facebook API health check failed: {e}")
        
        # Overall health - require database and Square API
        health_status['overall'] = health_status['database'] and health_status['square_api']
        
        return health_status

    def setup_scheduler(self):
        """Set up automated synchronization schedule"""
        self.logger.info("Setting up synchronization scheduler...")
        
        # Full sync every day at 2 AM
        schedule.every().day.at("02:00").do(
            lambda: asyncio.run(self.full_synchronization())
        )
        
        # Quick sync every 4 hours
        schedule.every(4).hours.do(self.quick_sync)
        
        # Health check every hour
        schedule.every().hour.do(self.health_check)
        
        self.logger.info("Scheduler configured:")
        self.logger.info("- Full sync: Daily at 2:00 AM")
        self.logger.info("- Quick sync: Every 4 hours")
        self.logger.info("- Health check: Every hour")

    def run_scheduler(self):
        """Run the scheduler continuously"""
        self.logger.info("Starting scheduler...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Vintage Clothing Business Data Sync')
    parser.add_argument(
        'command', 
        choices=['full', 'quick', 'health', 'schedule', 'setup'], 
        help='Command to run')
    parser.add_argument(
        '--verbose', 
        '-v', 
        action='store_true',
        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        print("\nVintage Clothing Business Data Sync Setup")
        print("=" * 45)
        
        created = create_env_template()
        if created:
            print("✓ Created .env template file")
        else:
            print("✗ .env file already exists")
            
        print("\nNext steps:")
        print("1. Fill in your API credentials in the .env file")
        print("2. Set up your PostgreSQL database")
        print("3. Run the database schema creation script")
        print("4. Test with: python main_sync.py health")
        print("\nAPI Setup Instructions:")
        print("- Square: Get access token from Square Developer Dashboard")
        print("- Instagram: Convert to Business account, get Graph API token")
        print("- Facebook: Create app, get page access token")
        sys.exit(0)
    
    # Validate environment for all other commands
    is_valid, missing_required, missing_optional = validate_environment()
    if not is_valid:
        print("Error: Missing required environment variables:")
        for var in missing_required:
            print(f"  - {var}")
        print("\nRun 'python main_sync.py setup' to create a template .env file")
        sys.exit(1)
    
    # Load configuration
    try:
        config = load_config()
        
        # Override logging level if verbose flag is set
        if args.verbose:
            config.logging.level = 'DEBUG'
            
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        print("Check your .env file and ensure all required values are set")
        sys.exit(1)
    
    # Initialize master sync
    try:
        master_sync = MasterDataSync(config)
    except Exception as e:
        print(f"Failed to initialize sync system: {e}")
        print("Check your configuration and API credentials")
        sys.exit(1)
    
    if args.command == 'health':
        print("\nVintage Clothing Business - System Health Check")
        print("=" * 50)
        health = master_sync.health_check()
        
        components = [
            ('Database Connection', health['database']),
            ('Square API', health['square_api']),
            ('Instagram API', health['instagram_api']),
            ('Facebook API', health['facebook_api'])
        ]
        
        for name, status in components:
            status_symbol = "✓" if status else "✗"
            status_text = "OK" if status else "FAILED"
            print(f"{name:<20} {status_symbol} {status_text}")
        
        print("-" * 50)
        print(f"Configured Platforms: {', '.join(config.social_media.configured_platforms) or 'None'}")
        print(f"Sync Days (Full): {config.sync_days_back}")
        print(f"Sync Days (Quick): {config.quick_sync_days}")
        print(f"Square Environment: {config.square.environment}")
        print("-" * 50)
        
        overall_status = "HEALTHY" if health['overall'] else "ISSUES DETECTED"
        print(f"Overall Status: {overall_status}")
        
        if not health['overall']:
            print("\nTroubleshooting:")
            if not health['database']:
                print("- Check database connection settings in .env")
            if not health['square_api']:
                print("- Verify Square access token and environment setting")
            if not health['instagram_api'] and config.social_media.has_instagram_config:
                print("- Check Instagram Business account and access token")
            if not health['facebook_api'] and config.social_media.has_facebook_config:
                print("- Verify Facebook page ID and access token")
        
        sys.exit(0 if health['overall'] else 1)
        
    elif args.command == 'quick':
        print("Running quick synchronization...")
        success = master_sync.quick_sync()
        print(f"Quick sync {'completed successfully' if success else 'failed'}")
        sys.exit(0 if success else 1)
        
    elif args.command == 'full':
        print("Running full synchronization...")
        success = asyncio.run(master_sync.full_synchronization())
        print(f"Full sync {'completed successfully' if success else 'failed'}")
        sys.exit(0 if success else 1)
        
    elif args.command == 'schedule':
        print("Starting scheduled synchronization service...")
        print("Press Ctrl+C to stop")
        master_sync.setup_scheduler()
        try:
            master_sync.run_scheduler()
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nScheduler failed: {e}")
            sys.exit(1)

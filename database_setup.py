# database_setup.py - Updated to match test data generation

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

# Import shared configuration
try:
    from config import load_config, create_env_template
except ImportError:
    print("Error: config.py not found. Please ensure config.py is in the same directory.")
    sys.exit(1)

def create_database():
    """Create the database if it doesn't exist"""
    
    try:
        config = load_config()
    except Exception as e:
        print(f"Configuration error: {e}")
        print("No .env file found. Run 'python config.py --create-template' and edit template.")
        return False
    
    # Connect to PostgreSQL server
    try:
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            user=config.database.user,
            password=config.database.password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        # Create db if it doesn't exist
        try:
            cursor.execute(f"CREATE DATABASE {config.database.database}")
            print(f"✓ Database '{config.database.database}' created successfully")
        except psycopg2.Error as e:
            if "already exists" in str(e):
                print(f"✓ Database '{config.database.database}' already exists")
            else:
                raise e
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Failed to create database: {e}")
        return False

def create_tables():
    """Create all database tables"""
    
    try:
        config = load_config()
    except Exception as e:
        print(f"Configuration error: {e}")
        return False
    
    try:
        # Connect to the specific database
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        cursor = conn.cursor()
        
        # Create tables (updated to match test data schema)
        tables = [
            """
            CREATE TABLE IF NOT EXISTS locations (
                location_id SERIAL PRIMARY KEY,
                location_name VARCHAR(100) NOT NULL,
                location_type VARCHAR(50) NOT NULL,
                address TEXT,
                city VARCHAR(100),
                state_province VARCHAR(50),
                country VARCHAR(50),
                postal_code VARCHAR(20),
                market_fee DECIMAL(10,2),
                setup_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                square_customer_id VARCHAR(100) UNIQUE,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(20),
                date_of_birth DATE,
                customer_type VARCHAR(50),
                preferred_eras TEXT[],
                preferred_styles TEXT[],
                preferred_sizes TEXT[],
                total_orders INTEGER DEFAULT 0,
                total_spent DECIMAL(10,2) DEFAULT 0,
                average_order_value DECIMAL(10,2) DEFAULT 0,
                first_purchase_date DATE,
                last_purchase_date DATE,
                acquisition_source VARCHAR(100)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS inventory_items (
                item_id SERIAL PRIMARY KEY,
                square_catalog_id VARCHAR(100) UNIQUE,
                sku VARCHAR(100) UNIQUE,
                item_name VARCHAR(200) NOT NULL,
                brand VARCHAR(100),
                category VARCHAR(100) NOT NULL,
                subcategory VARCHAR(100),
                era_decade VARCHAR(20),
                size VARCHAR(50),
                measurements JSONB,
                condition_rating INTEGER CHECK (condition_rating BETWEEN 1 AND 5),
                condition_notes TEXT,
                material VARCHAR(200),
                color_primary VARCHAR(50),
                color_secondary VARCHAR(50),
                pattern VARCHAR(100),
                cost_price DECIMAL(10,2),
                selling_price DECIMAL(10,2) NOT NULL,
                suggested_retail_price DECIMAL(10,2),
                source VARCHAR(100),
                acquisition_date DATE,
                acquisition_location VARCHAR(200),
                is_one_of_a_kind BOOLEAN DEFAULT TRUE,
                weight_grams INTEGER,
                photo_urls TEXT[],
                tags TEXT[],
                status VARCHAR(50) DEFAULT 'available'
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS inventory_location_tracking (
                tracking_id SERIAL PRIMARY KEY,
                item_id INTEGER REFERENCES inventory_items(item_id),
                location_id INTEGER REFERENCES locations(location_id),
                quantity INTEGER DEFAULT 1,
                date_moved DATE NOT NULL,
                moved_by VARCHAR(100),
                reason VARCHAR(100)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                square_order_id VARCHAR(100) UNIQUE,
                customer_id INTEGER REFERENCES customers(customer_id),
                location_id INTEGER REFERENCES locations(location_id),
                order_date TIMESTAMP NOT NULL,
                order_status VARCHAR(50) NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                tax_amount DECIMAL(10,2) DEFAULT 0,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                tip_amount DECIMAL(10,2) DEFAULT 0,
                total_amount DECIMAL(10,2) NOT NULL,
                payment_method VARCHAR(50),
                order_source VARCHAR(50),
                staff_member VARCHAR(100),
                notes TEXT
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(order_id),
                item_id INTEGER REFERENCES inventory_items(item_id),
                quantity INTEGER DEFAULT 1,
                unit_price DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                total_price DECIMAL(10,2) NOT NULL
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id SERIAL PRIMARY KEY,
                square_payment_id VARCHAR(100) UNIQUE,
                order_id INTEGER REFERENCES orders(order_id),
                payment_date TIMESTAMP NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                payment_status VARCHAR(50) NOT NULL,
                processing_fee DECIMAL(10,2) DEFAULT 0,
                square_fee DECIMAL(10,2) DEFAULT 0,
                net_amount DECIMAL(10,2) NOT NULL,
                device_name VARCHAR(100),
                receipt_url VARCHAR(500)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS social_media_accounts (
                account_id SERIAL PRIMARY KEY,
                platform VARCHAR(50) NOT NULL,
                account_handle VARCHAR(100) NOT NULL,
                account_name VARCHAR(200),
                api_access_token TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(platform, account_handle)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS social_media_posts (
                post_id SERIAL PRIMARY KEY,
                account_id INTEGER REFERENCES social_media_accounts(account_id),
                platform_post_id VARCHAR(200) NOT NULL UNIQUE,
                post_type VARCHAR(50),
                caption TEXT,
                post_url VARCHAR(500),
                posted_date TIMESTAMP NOT NULL,
                hashtags TEXT[],
                mentions TEXT[],
                is_promotional BOOLEAN DEFAULT FALSE
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS post_items_featured (
                feature_id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES social_media_posts(post_id),
                item_id INTEGER REFERENCES inventory_items(item_id),
                is_primary_item BOOLEAN DEFAULT FALSE
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS social_media_metrics (
                metric_id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES social_media_posts(post_id),
                metric_date DATE NOT NULL,
                impressions INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                engagement_rate DECIMAL(5,4) DEFAULT 0,
                UNIQUE(post_id, metric_date)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS market_performance (
                performance_id SERIAL PRIMARY KEY,
                location_id INTEGER REFERENCES locations(location_id),
                market_date DATE NOT NULL,
                total_sales DECIMAL(10,2) DEFAULT 0,
                total_transactions INTEGER DEFAULT 0,
                items_sold INTEGER DEFAULT 0,
                average_transaction_value DECIMAL(10,2) DEFAULT 0,
                foot_traffic_estimate INTEGER,
                weather VARCHAR(100),
                competitor_count INTEGER,
                booth_cost DECIMAL(10,2),
                travel_expenses DECIMAL(10,2),
                net_profit DECIMAL(10,2),
                customer_acquisition_count INTEGER DEFAULT 0,
                notes TEXT,
                UNIQUE(location_id, market_date)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS social_media_attribution (
                attribution_id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id),
                order_id INTEGER REFERENCES orders(order_id),
                post_id INTEGER REFERENCES social_media_posts(post_id),
                attribution_type VARCHAR(50),
                attribution_confidence VARCHAR(20),
                time_from_post_to_purchase INTERVAL
            )
            """
        ]
        
        table_names = [
            'locations', 'customers', 'inventory_items', 'inventory_location_tracking',
            'orders', 'order_items', 'payments', 'social_media_accounts', 
            'social_media_posts', 'post_items_featured', 'social_media_metrics',
            'market_performance', 'social_media_attribution'
        ]
        
        for i, table_sql in enumerate(tables):
            try:
                cursor.execute(table_sql)
                print(f"✓ Created table: {table_names[i]}")
            except Exception as e:
                print(f"✗ Error creating table {table_names[i]}: {e}")
                return False
        
        conn.commit()
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
            "CREATE INDEX IF NOT EXISTS idx_customers_square_id ON customers(square_customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_era ON inventory_items(era_decade)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory_items(status)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_items(sku)",
            "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)",
            "CREATE INDEX IF NOT EXISTS idx_orders_location ON orders(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_date ON social_media_posts(posted_date)",
            "CREATE INDEX IF NOT EXISTS idx_social_metrics_date ON social_media_metrics(metric_date)",
            "CREATE INDEX IF NOT EXISTS idx_market_performance_date ON market_performance(market_date)",
            "CREATE INDEX IF NOT EXISTS idx_market_performance_location ON market_performance(location_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                print(f"⚠ Index creation warning: {e}")
        
        print("✓ All indexes created successfully")
        
        cursor.close()
        conn.close()
        print("✓ Database schema setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Setup for Curated Closet Vintage Clothing Business')
    parser.add_argument('--create-db', action='store_true', help='Create database')
    parser.add_argument('--create-tables', action='store_true', help='Create tables')
    parser.add_argument('--all', action='store_true', help='Run all setup steps')
    
    args = parser.parse_args()
    
    if args.all:
        print("Setting up complete database...")
        success = True
        success &= create_database()
        success &= create_tables()
        
        if success:
            print("\n✓ Database setup completed successfully!")
            print("\nNext steps:")
            print("1. Generate test data: python generate_test_data.py")
            print("2. Load test data: python load_csv_data.py")
            print("3. Test sync: python main_sync.py health")
        else:
            print("\n✗ Database setup failed. Check errors above.")
            sys.exit(1)
    else:
        if args.create_db:
            create_database()
        
        if args.create_tables:
            create_tables()
        
        if not any([args.create_db, args.create_tables]):
            print("Usage: python database_setup.py [--create-db] [--create-tables] [--all]")
            print("Run with --all for complete setup")

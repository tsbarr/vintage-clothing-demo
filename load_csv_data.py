# load_csv_data.py - Load CSV test data into PostgreSQL database

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
from datetime import datetime
import json
import ast
from typing import Optional

# Import shared configuration
try:
    from config import load_config
except ImportError:
    print("Error: config.py not found. Please ensure config.py is in the same directory.")
    sys.exit(1)

class DataLoader:
    def __init__(self):
        """Initialize the data loader with database connection"""
        try:
            self.config = load_config()
            self.data_dir = 'data'
            
        except Exception as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
    
    def connect_db(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.config.database.host,
                port=self.config.database.port,
                database=self.config.database.database,
                user=self.config.database.user,
                password=self.config.database.password
            )
            self.cursor = self.conn.cursor()
            print("✓ Database connection established")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def clean_dataframe(self, df, table_name):
        """
        Clean DataFrame for database insertion.
        
        Handles data type conversions and format transformations:
        - Converts NaN values to None for PostgreSQL compatibility
        - Parses string representations of arrays to Python lists for PostgreSQL TEXT[] columns
        - Converts dictionaries to proper format for JSONB storage
        - Normalizes boolean columns
        - Converts numpy types to Python native types
        
        Args:
            df (DataFrame): Raw pandas DataFrame from CSV
            table_name (str): Name of target database table
            
        Returns:
            DataFrame: Cleaned DataFrame ready for database insertion
        """
        df_clean = df.copy()
        
        # Step 1: Replace pandas NaN with None (PostgreSQL NULL)
        df_clean = df_clean.replace({np.nan: None})
        
        # Step 2: Convert string representations of arrays to Python lists
        # These will become PostgreSQL TEXT[] arrays
        list_columns = {
            'customers': ['preferred_eras', 'preferred_styles', 'preferred_sizes'],
            'inventory_items': ['photo_urls', 'tags'],
            'social_media_posts': ['hashtags', 'mentions']
        }
        
        if table_name in list_columns:
            for col in list_columns[table_name]:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].apply(self._parse_list_string)
        
        # Step 3: Handle JSON columns for JSONB storage
        if table_name == 'inventory_items' and 'measurements' in df_clean.columns:
            df_clean['measurements'] = df_clean['measurements'].apply(self._parse_json_string)
        
        # Step 4: Ensure boolean columns have proper boolean types
        bool_columns = {
            'locations': ['is_active'],
            'inventory_items': ['is_one_of_a_kind'],
            'social_media_accounts': ['is_active'],
            'social_media_posts': ['is_promotional'],
            'post_items_featured': ['is_primary_item']
        }
        
        if table_name in bool_columns:
            for col in bool_columns[table_name]:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].astype(bool)
        
        # Step 5: Convert numpy types to Python native types for psycopg2 compatibility
        # Skip array columns that were already processed above
        for col in df_clean.columns:
            # Skip columns that should remain as Python lists (for PostgreSQL arrays)
            if table_name in list_columns and col in list_columns[table_name]:
                continue
                
            # Convert numpy scalars to Python types
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].apply(self._convert_numpy_types)
            elif df_clean[col].dtype.kind in 'biufc':  # numeric types (bool, int, uint, float, complex)
                df_clean[col] = df_clean[col].astype('object').apply(self._convert_numpy_types)
        
        return df_clean
    
    def _safe_convert_value(self, val):
        """
        Safely convert a value for database insertion via psycopg2.
        
        Handles special data types that need conversion:
        - Python lists → PostgreSQL TEXT[] arrays (automatic)
        - Python dictionaries → JSON strings for JSONB columns
        - pandas NaN → None (PostgreSQL NULL)
        
        Args:
            val: Value to convert
            
        Returns:
            Value safe for psycopg2 insertion
        """
        if val is None:
            return None
        
        # Python lists are automatically converted to PostgreSQL arrays by psycopg2
        if isinstance(val, list):
            return val
        
        # Convert dictionaries to JSON strings for JSONB columns
        if isinstance(val, dict):
            return json.dumps(val)
        
        # Check for pandas NaN values safely (avoid array boolean ambiguity)
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
            # pd.isna() failed (e.g., on complex objects), value is not NaN
            pass
        
        return val
    
    def _convert_numpy_types(self, value):
        """
        Convert numpy data types to Python native types for psycopg2 compatibility.
        
        psycopg2 doesn't handle numpy types directly, so we convert:
        - numpy.int64 → int
        - numpy.float64 → float  
        - numpy.bool_ → bool
        - numpy arrays → lists (for single-element arrays) or Python lists
        
        Args:
            value: Value that may contain numpy types
            
        Returns:
            Value with Python native types
        """
        if pd.isna(value):
            return None
        
        # Preserve lists that were already processed
        if isinstance(value, list):
            return value
        
        # Convert numpy scalar types to Python equivalents
        if hasattr(value, 'dtype'):
            if np.issubdtype(value.dtype, np.integer):
                return int(value)
            elif np.issubdtype(value.dtype, np.floating):
                return None if np.isnan(value) else float(value)
            elif np.issubdtype(value.dtype, np.bool_):
                return bool(value)
        
        # Handle numpy arrays and generic numpy types
        if isinstance(value, (np.ndarray, np.generic)):
            if hasattr(value, 'size') and value.size == 1:
                return value.item()  # Extract single value
            else:
                return value.tolist()  # Convert array to list
        
        return value
    
    def _parse_list_string(self, value):
        """
        Parse string representations of lists back to Python lists.
        
        Handles test data that stores arrays as strings like "['item1', 'item2']"
        and converts them to actual Python lists for PostgreSQL TEXT[] columns.
        
        Args:
            value: String representation of a list or actual list
            
        Returns:
            Python list or None
        """
        try:
            if pd.isna(value) or value is None:
                return None
            if isinstance(value, list):
                return value  # Already a list
            if isinstance(value, str):
                # Parse string representations like "['item1', 'item2']"
                if value.startswith('[') and value.endswith(']'):
                    return ast.literal_eval(value)
                else:
                    return [value]  # Single item becomes single-element list
            return value
        except Exception:
            # Fallback: treat any parsing error as single-item list
            return [str(value)] if value is not None else None
    
    def _parse_json_string(self, value):
        """
        Parse string representations of JSON back to Python dictionaries.
        
        Handles test data that stores JSON as strings and converts them
        to Python dicts for eventual JSONB storage.
        
        Args:
            value: String representation of JSON or actual dict
            
        Returns:
            Python dictionary or None
        """
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, dict):
            return value  # Already a dictionary
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value
    
    def load_table(self, table_name, csv_file):
        """
        Load a single table from CSV file into PostgreSQL database.
        
        Process:
        1. Read CSV file using pandas
        2. Clean and transform data for database compatibility
        3. Batch insert using psycopg2's execute_values for performance
        4. Handle conflicts gracefully with ON CONFLICT DO NOTHING
        
        Args:
            table_name (str): Name of target database table
            csv_file (str): Name of CSV file in data directory
            
        Returns:
            bool: True if successful, False if failed
        """
        if self.conn is None or self.cursor is None:
            print("✗ Database connection not established")
            return False
            
        csv_path = os.path.join(self.data_dir, csv_file)
        
        if not os.path.exists(csv_path):
            print(f"⚠ CSV file not found: {csv_path}")
            return False
        
        try:
            # Read CSV file into pandas DataFrame
            df = pd.read_csv(csv_path)
            print(f"➜ Loading {table_name}: {len(df)} records from {csv_file}")
            
            # Clean and transform data for database insertion
            df_clean = self.clean_dataframe(df, table_name)
            
            # Convert DataFrame to list of tuples for batch insertion
            columns = list(df_clean.columns)
            values = []
            for _, row in df_clean.iterrows():
                row_tuple = tuple(
                    self._safe_convert_value(val) 
                    for val in row
                )
                values.append(row_tuple)
            
            # Prepare batch INSERT query using execute_values
            columns_str = ', '.join(columns)
            insert_query = f"""
                INSERT INTO {table_name} ({columns_str}) 
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            
            # Execute batch insert with automatic chunking for performance
            execute_values(
                self.cursor,
                insert_query,
                values,
                template=None,    # Let psycopg2 create the template
                page_size=100     # Insert in chunks of 100 rows
            )
            
            # Commit transaction
            self.conn.commit()
            print(f"✓ Successfully loaded {len(values)} records into {table_name}")
            return True
            
        except Exception as e:
            print(f"✗ Error loading {table_name}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def check_data_integrity(self):
        """
        Perform comprehensive data integrity checks after loading.
        
        Validates:
        - Record counts in all tables
        - Foreign key relationships
        - Data consistency across related tables
        
        Helps identify loading issues and ensures data quality.
        """
        if self.cursor is None:
            print("✗ Database connection not established")
            return
            
        print("\n✎ Performing data integrity checks...")
        
        checks = [
            ("Total customers", "SELECT COUNT(*) FROM customers"),
            ("Total inventory items", "SELECT COUNT(*) FROM inventory_items"), 
            ("Total orders", "SELECT COUNT(*) FROM orders"),
            ("Total order items", "SELECT COUNT(*) FROM order_items"),
            ("Orders with valid customer references", """
                SELECT COUNT(*) FROM orders o 
                JOIN customers c ON o.customer_id = c.customer_id
            """),
            ("Order items with valid references", """
                SELECT COUNT(*) FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                JOIN inventory_items i ON oi.item_id = i.item_id
            """),
            ("Social posts with metrics", """
                SELECT COUNT(*) FROM social_media_posts p
                JOIN social_media_metrics m ON p.post_id = m.post_id
            """),
            ("Market performance records", "SELECT COUNT(*) FROM market_performance"),
            ("Customers with purchase history", """
                SELECT COUNT(*) FROM customers 
                WHERE total_orders > 0 AND total_spent > 0
            """)
        ]
        
        for check_name, query in checks:
            try:
                self.cursor.execute(query)
                result = self.cursor.fetchone()
                if result is not None:
                    print(f"✓ {check_name}: {result[0]}")
                else:
                    print(f"⚠ {check_name}: No result returned")
            except Exception as e:
                print(f"✗ {check_name}: Error - {e}")
    
    def generate_insights(self):
        """
        Generate business insights from loaded data.
        
        Creates summary statistics and key business metrics to validate
        that the data loading was successful and the data makes business sense.
        """
        print("\n✎ BUSINESS INSIGHTS FROM LOADED DATA")
        print("=" * 50)
        
        insights = [
            ("☞ Total Revenue", """
                SELECT ROUND(SUM(total_amount), 2) as total_revenue
                FROM orders WHERE order_status = 'completed'
            """),
            ("☞ Average Order Value", """
                SELECT ROUND(AVG(total_amount), 2) as avg_order_value
                FROM orders WHERE order_status = 'completed'
            """),
            ("☞ Top Customer by Spending", """
                SELECT c.first_name, c.last_name, ROUND(SUM(o.total_amount), 2) as total_spent
                FROM customers c
                JOIN orders o ON c.customer_id = o.customer_id
                WHERE o.order_status = 'completed'
                GROUP BY c.customer_id, c.first_name, c.last_name
                ORDER BY total_spent DESC
                LIMIT 1
            """),
            ("☞ Most Popular Item Category", """
                SELECT i.category, COUNT(*) as items_sold
                FROM inventory_items i
                JOIN order_items oi ON i.item_id = oi.item_id
                GROUP BY i.category
                ORDER BY items_sold DESC
                LIMIT 1
            """),
            ("☞ Best Performing Location", """
                SELECT l.location_name, ROUND(AVG(mp.net_profit), 2) as avg_profit
                FROM locations l
                JOIN market_performance mp ON l.location_id = mp.location_id
                GROUP BY l.location_id, l.location_name
                ORDER BY avg_profit DESC
                LIMIT 1
            """),
            ("☞ Social Media Engagement", """
                SELECT 
                    COUNT(*) as total_posts,
                    ROUND(AVG(likes), 0) as avg_likes,
                    ROUND(AVG(engagement_rate), 4) as avg_engagement_rate
                FROM social_media_metrics
            """),
            ("☞ Customer Acquisition Sources", """
                SELECT acquisition_source, COUNT(*) as customer_count
                FROM customers
                WHERE acquisition_source IS NOT NULL
                GROUP BY acquisition_source
                ORDER BY customer_count DESC
            """),
            ("☞ Monthly Sales Trend (Last 6 Months)", """
                SELECT 
                    DATE_TRUNC('month', order_date) as month,
                    COUNT(*) as orders,
                    ROUND(SUM(total_amount), 2) as revenue
                FROM orders 
                WHERE order_date >= CURRENT_DATE - INTERVAL '6 months'
                AND order_status = 'completed'
                GROUP BY DATE_TRUNC('month', order_date)
                ORDER BY month DESC
                LIMIT 6
            """)
        ]
        
        for insight_name, query in insights:
            try:
                self.cursor.execute(query)
                result = self.cursor.fetchall()
                
                print(f"\n{insight_name}:")
                if len(result) == 1 and len(result[0]) == 1:
                    print(f"  {result[0][0]}")
                elif insight_name == "☞ Top Customer by Spending":
                    if result:
                        print(f"  {result[0][0]} {result[0][1]}: ${result[0][2]}")
                elif insight_name == "☞ Most Popular Item Category":
                    if result:
                        print(f"  {result[0][0]}: {result[0][1]} items sold")
                elif insight_name == "☞ Best Performing Location":
                    if result:
                        print(f"  {result[0][0]}: ${result[0][1]} avg profit")
                elif insight_name == "☞ Social Media Engagement":
                    if result:
                        print(f"  {result[0][0]} posts, {result[0][1]} avg likes, {result[0][2]:.2%} engagement")
                elif insight_name == "☞ Customer Acquisition Sources":
                    for row in result[:3]:  # Top 3
                        print(f"  {row[0]}: {row[1]} customers")
                elif insight_name == "☞ Monthly Sales Trend (Last 6 Months)":
                    for row in result:
                        month_str = row[0].strftime('%Y-%m') if row[0] else 'Unknown'
                        print(f"  {month_str}: {row[1]} orders, ${row[2]}")
                else:
                    for row in result:
                        print(f"  {', '.join(map(str, row))}")
                        
            except Exception as e:
                print(f"✗ Error generating {insight_name}: {e}")
    
    def load_all_data(self):
        """
        Load all CSV files into database in correct order.
        
        Loading order is critical due to foreign key constraints:
        1. Independent tables first (locations, customers, inventory_items)
        2. Tables with foreign keys next (orders, payments, social_media_posts)
        3. Junction/relationship tables last (order_items, social_media_metrics)
        
        Returns:
            bool: True if all tables loaded successfully, False otherwise
        """
        print("▶ Starting data loading process...")
        print("=" * 50)
        
        # Define loading order to respect foreign key constraints
        load_order = [
            # Independent tables (no foreign keys)
            ('locations', 'locations.csv'),
            ('customers', 'customers.csv'),
            ('inventory_items', 'inventory_items.csv'),
            ('social_media_accounts', 'social_media_accounts.csv'),
            
            # Tables with foreign keys to independent tables
            ('orders', 'orders.csv'),
            ('payments', 'payments.csv'),
            ('social_media_posts', 'social_media_posts.csv'),
            ('market_performance', 'market_performance.csv'),
            
            # Junction tables and tables with multiple foreign keys
            ('order_items', 'order_items.csv'),
            ('social_media_metrics', 'social_media_metrics.csv'),
            ('post_items_featured', 'post_items_featured.csv'),
        ]
        
        success_count = 0
        total_count = len(load_order)
        
        for table_name, csv_file in load_order:
            if self.load_table(table_name, csv_file):
                success_count += 1
            print()  # Add spacing between tables for readability
        
        print("=" * 50)
        print(f"➜ Loading Summary: {success_count}/{total_count} tables loaded successfully")
        
        if success_count == total_count:
            print("✓ All data loaded successfully!")
            self.check_data_integrity()
            return True
        else:
            print("⚠ Some tables failed to load. Check errors above.")
            return False

def main():
    """
    Main entry point for data loading script.
    
    Supports multiple modes:
    - Default: Load all CSV data into database
    - --insights: Additionally generate business insights after loading
    - --check-only: Only run data integrity checks (assumes data already loaded)
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Load CSV data into PostgreSQL database')
    parser.add_argument('--insights', action='store_true', help='Generate business insights after loading')
    parser.add_argument('--check-only', action='store_true', help='Only run data integrity checks')
    
    args = parser.parse_args()
    
    # Initialize data loader
    loader = DataLoader()
    
    # Connect to database
    if not loader.connect_db():
        sys.exit(1)
    
    try:
        if args.check_only:
            loader.check_data_integrity()
        else:
            # Load all data
            success = loader.load_all_data()
            
            if success and args.insights:
                loader.generate_insights()
                
        print("\n✓ Data loading process completed!")
        print("\nNext steps:")
        print("• View insights: python load_csv_data.py --insights")
        print("• Access database: psql -h localhost -U your_user -d curated_closet_db")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    finally:
        loader.close_db()

if __name__ == "__main__":
    main()

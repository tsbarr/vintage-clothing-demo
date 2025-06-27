# square_sync.py - for accesing square data and sync to db

import logging
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
from decimal import Decimal

# Since this script is in sync directory, find parent directory to access shared config files
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import shared configuration from main directory
from config import DatabaseConfig, SquareConfig

# Square SDK imports
from square import Square
from square.environment import SquareEnvironment
from square.core.api_error import ApiError


class SquareDataSync:
    def __init__(self, db_config: DatabaseConfig, square_config: SquareConfig):
        self.db_config = db_config
        self.square_config = square_config
        
        # Initialize Square client
        try:
            if square_config.environment.lower() == 'production':
                environment = SquareEnvironment.PRODUCTION
            else:
                environment = SquareEnvironment.SANDBOX
                
            self.square_client = Square(
                environment=environment,
                token=square_config.access_token
            )
            
        except Exception as e:
            logging.error(f"Failed to initialize Square client: {e}")
            raise
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('square_sync.log'),
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

    def sync_locations(self):
        """Sync Square locations to database"""
        self.logger.info("Starting location sync...")
        
        try:
            # check if this returns a pager or response object
            response = self.square_client.locations.list()
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            locations_synced = 0
            
            # locations.list() might return a response object, not a pager
            # Try direct access first, then iterate if it's a pager
            try:
                # If it has .locations attribute, it's a response object
                locations = response.locations or []
                if not locations:
                    self.logger.info("No locations found")
                    return True
                
                for location in locations:
                    self._sync_single_location(cursor, location)
                    locations_synced += 1
                    
            except AttributeError:
                # If no .locations attribute, it's probably a pager - iterate directly
                for location in response:
                    self._sync_single_location(cursor, location)
                    locations_synced += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Successfully synced {locations_synced} locations")
            return True
            
        except ApiError as e:
            self.logger.error(f"Square API error: {e.body}")
            return False
        except Exception as e:
            self.logger.error(f"Location sync failed: {e}")
            return False
    
    def _sync_single_location(self, cursor, location):
        """Helper method to sync a single location"""
        # Prepare location data
        location_data = {
            'square_location_id': location.id,
            'location_name': location.name,
            'location_type': 'square_location',
            'address': location.address.address_line_1 if location.address else None,
            'city': location.address.locality if location.address else None,
            'state_province': location.address.administrative_district_level_1 if location.address else None,
            'country': location.address.country if location.address else None,
            'postal_code': location.address.postal_code if location.address else None,
            'is_active': location.status == 'ACTIVE'
        }
        
        # Upsert location
        cursor.execute("""
            INSERT INTO locations (
                square_location_id, location_name, location_type, address, 
                city, state_province, country, postal_code, is_active, updated_at
            ) VALUES (
                %(square_location_id)s, %(location_name)s, %(location_type)s, 
                %(address)s, %(city)s, %(state_province)s, %(country)s, 
                %(postal_code)s, %(is_active)s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (square_location_id) DO UPDATE SET
                location_name = EXCLUDED.location_name,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                state_province = EXCLUDED.state_province,
                country = EXCLUDED.country,
                postal_code = EXCLUDED.postal_code,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP
        """, location_data)

    def sync_customers(self, limit: int = 100):
        """Sync Square customers to database"""
        self.logger.info("Starting customer sync...")
        
        try:
            conn = self.get_db_connection()
            db_cursor = conn.cursor()
            
            total_customers = 0
            
            # returns SyncPager, iterate directly with automatic pagination
            customers_pager = self.square_client.customers.list(
                limit=limit,
                sort_field='DEFAULT',
                sort_order='DESC'
            )
            
            # iterate directly over the pager
            for customer in customers_pager:
                customer_data = {
                    'square_customer_id': customer.id,
                    'first_name': customer.given_name,
                    'last_name': customer.family_name,
                    'email': customer.email_address,
                    'phone': customer.phone_number,
                    'created_at': None
                }
                
                # Handle creation date
                if customer.created_at:
                    try:
                        customer_data['created_at'] = datetime.fromisoformat(
                            customer.created_at.replace('Z', '+00:00')
                        )
                    except:
                        customer_data['created_at'] = None
                
                # Upsert customer
                db_cursor.execute("""
                    INSERT INTO customers (
                        square_customer_id, first_name, last_name, email, phone, created_at, updated_at
                    ) VALUES (
                        %(square_customer_id)s, %(first_name)s, %(last_name)s, 
                        %(email)s, %(phone)s, %(created_at)s, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (square_customer_id) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        updated_at = CURRENT_TIMESTAMP
                """, customer_data)
                
                total_customers += 1
            
            conn.commit()
            db_cursor.close()
            conn.close()
            
            self.logger.info(f"Successfully synced {total_customers} customers")
            return True
            
        except ApiError as e:
            self.logger.error(f"Square API error: {e.body}")
            return False
        except Exception as e:
            self.logger.error(f"Customer sync failed: {e}")
            return False

    def sync_catalog_items(self):
        """Sync Square catalog items to inventory_items table"""
        self.logger.info("Starting catalog items sync...")
        
        try:
            # returns a SyncPager, iterate directly
            catalog_pager = self.square_client.catalog.list(types="ITEM")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            items_synced = 0
            # iterate directly over the pager
            for catalog_object in catalog_pager:
                if catalog_object.type != 'ITEM':
                    continue
                
                item_data = catalog_object.item_data
                if not item_data:
                    continue
                    
                variations = item_data.variations or []
                
                for variation in variations:
                    # FIXED: Check if this is actually an ITEM_VARIATION type
                    if variation.type != 'ITEM_VARIATION':
                        continue
                        
                    # FIXED: Now safely access item_variation_data
                    variation_data = variation.item_variation_data
                    if not variation_data:
                        continue
                    
                    # Extract item information
                    inventory_data = {
                        'square_catalog_id': variation.id,
                        'item_name': item_data.name,
                        'sku': variation_data.sku if variation_data.sku else f"auto_{variation.id}",
                        'selling_price': None,
                        'category': 'uncategorized'  # Default category
                    }
                    
                    # Extract price
                    if variation_data.price_money and variation_data.price_money.amount:
                        amount = variation_data.price_money.amount
                        inventory_data['selling_price'] = Decimal(amount) / 100  # Convert cents to dollars
                    
                    # Extract category from item categories
                    if item_data.categories and len(item_data.categories) > 0:
                        inventory_data['category'] = item_data.categories[0].id
                    
                    # Upsert inventory item
                    cursor.execute("""
                        INSERT INTO inventory_items (
                            square_catalog_id, item_name, sku, selling_price, category, updated_at
                        ) VALUES (
                            %(square_catalog_id)s, %(item_name)s, %(sku)s, 
                            %(selling_price)s, %(category)s, CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (square_catalog_id) DO UPDATE SET
                            item_name = EXCLUDED.item_name,
                            sku = EXCLUDED.sku,
                            selling_price = EXCLUDED.selling_price,
                            category = EXCLUDED.category,
                            updated_at = CURRENT_TIMESTAMP
                    """, inventory_data)
                    
                    items_synced += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Successfully synced {items_synced} catalog items")
            return True
            
        except ApiError as e:
            self.logger.error(f"Square API error: {e.body}")
            return False
        except Exception as e:
            self.logger.error(f"Catalog sync failed: {e}")
            return False

    def sync_orders(self, days_back: int = 30):
        """Sync Square orders and payments"""
        self.logger.info(f"Starting orders sync for last {days_back} days...")
        
        try:
            # Set up date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # simplified search orders call with proper parameter structure
            search_response = self.square_client.orders.search(
                location_ids=[],  # Empty list is OK here - means all locations
                query={
                    'filter': {
                        'date_time_filter': {
                            'closed_at': {
                                'start_at': start_date.isoformat() + 'Z',
                                'end_at': end_date.isoformat() + 'Z'
                            }
                        },
                        'state_filter': {
                            'states': ['COMPLETED', 'CANCELED']  # This should be a list
                        }
                    },
                    'sort': {
                        'sort_field': 'CLOSED_AT',
                        'sort_order': 'DESC'
                    }
                },
                limit=100,
                return_entries=True
            )
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            orders_synced = 0
            # safe access to orders (can be None)
            orders = search_response.orders or []
            if not orders:
                self.logger.info("No orders found in the specified date range")
                return True
            
            for order in orders:
                # Process main order
                order_id = self._sync_single_order(cursor, order)
                
                # Process order items - safe access
                line_items = order.line_items or []
                for line_item in line_items:
                    self._sync_order_item(cursor, order_id, line_item)
                
                # Process payments (tenders) - safe access
                tenders = order.tenders or []
                for tender in tenders:
                    self._sync_payment(cursor, order_id, tender)
                
                orders_synced += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Successfully synced {orders_synced} orders")
            return True
            
        except ApiError as e:
            self.logger.error(f"Square API error: {e.body}")
            return False
        except Exception as e:
            self.logger.error(f"Orders sync failed: {e}")
            return False

    def _sync_single_order(self, cursor, order) -> int:
        """Sync a single order to database"""
        
        # Get customer ID from database if exists
        customer_id = None
        if order.customer_id:
            cursor.execute(
                "SELECT customer_id FROM customers WHERE square_customer_id = %s",
                (order.customer_id,)
            )
            result = cursor.fetchone()
            if result:
                customer_id = result['customer_id']
        
        # Get location ID from database
        location_id = None
        if order.location_id:
            cursor.execute(
                "SELECT location_id FROM locations WHERE square_location_id = %s",
                (order.location_id,)
            )
            result = cursor.fetchone()
            if result:
                location_id = result['location_id']
        
        # Calculate totals
        total_amount = Decimal(order.total_money.amount) / 100 if order.total_money else 0
        tax_amount = Decimal(order.total_tax_money.amount) / 100 if order.total_tax_money else 0
        discount_amount = Decimal(order.total_discount_money.amount) / 100 if order.total_discount_money else 0
        tip_amount = Decimal(order.total_tip_money.amount) / 100 if order.total_tip_money else 0
        
        subtotal = total_amount - tax_amount - tip_amount
        
        # Prepare order data
        order_insert_data = {
            'square_order_id': order.id,
            'customer_id': customer_id,
            'location_id': location_id,
            'order_date': datetime.fromisoformat(order.created_at.replace('Z', '+00:00')),
            'order_status': order.state.lower() if order.state else 'unknown',
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'tip_amount': tip_amount,
            'total_amount': total_amount,
            'order_source': 'square_pos'
        }
        
        # Upsert order
        cursor.execute("""
            INSERT INTO orders (
                square_order_id, customer_id, location_id, order_date, order_status,
                subtotal, tax_amount, discount_amount, tip_amount, total_amount, order_source, updated_at
            ) VALUES (
                %(square_order_id)s, %(customer_id)s, %(location_id)s, %(order_date)s, %(order_status)s,
                %(subtotal)s, %(tax_amount)s, %(discount_amount)s, %(tip_amount)s, %(total_amount)s, 
                %(order_source)s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (square_order_id) DO UPDATE SET
                order_status = EXCLUDED.order_status,
                subtotal = EXCLUDED.subtotal,
                tax_amount = EXCLUDED.tax_amount,
                discount_amount = EXCLUDED.discount_amount,
                tip_amount = EXCLUDED.tip_amount,
                total_amount = EXCLUDED.total_amount,
                updated_at = CURRENT_TIMESTAMP
            RETURNING order_id
        """, order_insert_data)
        
        result = cursor.fetchone()
        return result['order_id']

    def _sync_order_item(self, cursor, order_id: int, line_item):
        """Sync order line items"""
        
        # Get item ID from database
        item_id = None
        if line_item.catalog_object_id:
            cursor.execute(
                "SELECT item_id FROM inventory_items WHERE square_catalog_id = %s",
                (line_item.catalog_object_id,)
            )
            result = cursor.fetchone()
            if result:
                item_id = result['item_id']
        
        # Calculate prices
        quantity = int(line_item.quantity) if line_item.quantity else 1
        unit_price = Decimal(line_item.base_price_money.amount) / 100 if line_item.base_price_money else 0
        total_price = Decimal(line_item.total_money.amount) / 100 if line_item.total_money else 0
        
        # Prepare order item data
        order_item_data = {
            'order_id': order_id,
            'item_id': item_id,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price,
            'discount_amount': 0  # Calculate if discounts exist
        }
        
        # Insert order item (allowing duplicates for multiple calls)
        cursor.execute("""
            INSERT INTO order_items (
                order_id, item_id, quantity, unit_price, total_price, discount_amount
            ) VALUES (
                %(order_id)s, %(item_id)s, %(quantity)s, %(unit_price)s, %(total_price)s, %(discount_amount)s
            )
        """, order_item_data)

    def _sync_payment(self, cursor, order_id: int, tender):
        """Sync payment information"""
        
        # Calculate amounts
        amount = Decimal(tender.amount_money.amount) / 100 if tender.amount_money else 0
        
        # Prepare payment data
        payment_data = {
            'square_payment_id': tender.id,
            'order_id': order_id,
            'payment_date': datetime.fromisoformat(tender.created_at.replace('Z', '+00:00')),
            'amount': amount,
            'payment_method': tender.type.lower() if tender.type else 'unknown',
            'payment_status': 'completed',  # Tenders are typically completed
            'processing_fee': 0,  # Will need to calculate separately
            'square_fee': 0,  # Will need to calculate separately
            'net_amount': amount  # Will adjust after calculating fees
        }
        
        # Insert payment
        cursor.execute("""
            INSERT INTO payments (
                square_payment_id, order_id, payment_date, amount, payment_method,
                payment_status, processing_fee, square_fee, net_amount
            ) VALUES (
                %(square_payment_id)s, %(order_id)s, %(payment_date)s, %(amount)s, %(payment_method)s,
                %(payment_status)s, %(processing_fee)s, %(square_fee)s, %(net_amount)s
            )
            ON CONFLICT (square_payment_id) DO UPDATE SET
                payment_status = EXCLUDED.payment_status,
                updated_at = CURRENT_TIMESTAMP
        """, payment_data)

    def update_customer_aggregates(self):
        """Update customer aggregate fields"""
        self.logger.info("Updating customer aggregates...")
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Update customer totals and stats
        cursor.execute("""
            UPDATE customers SET
                total_orders = subquery.order_count,
                total_spent = subquery.total_amount,
                average_order_value = subquery.avg_amount,
                first_purchase_date = subquery.first_date,
                last_purchase_date = subquery.last_date,
                updated_at = CURRENT_TIMESTAMP
            FROM (
                SELECT 
                    customer_id,
                    COUNT(*) as order_count,
                    SUM(total_amount) as total_amount,
                    AVG(total_amount) as avg_amount,
                    MIN(order_date::date) as first_date,
                    MAX(order_date::date) as last_date
                FROM orders 
                WHERE customer_id IS NOT NULL 
                    AND order_status = 'completed'
                GROUP BY customer_id
            ) subquery
            WHERE customers.customer_id = subquery.customer_id
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        self.logger.info("Customer aggregates updated successfully")

    def full_sync(self):
        """Run complete synchronization"""
        self.logger.info("Starting full Square data synchronization...")
        
        success = True
        try:
            success &= self.sync_locations()
            success &= self.sync_customers()
            success &= self.sync_catalog_items()
            success &= self.sync_orders()
            
            if success:
                self.update_customer_aggregates()
                self.logger.info("Full synchronization completed successfully")
            else:
                self.logger.error("Synchronization completed with errors")
        except Exception as e:
            self.logger.error(f"Full synchronization failed: {e}")
            success = False
        
        return success

# Configuration and main execution
if __name__ == "__main__":
    from config import load_config
    
    try:
        # Load configuration from shared config module
        config = load_config()
        
        # Initialize sync handler
        sync_handler = SquareDataSync(config.database, config.square)
        
        # Run synchronization
        sync_handler.full_sync()
        
    except Exception as e:
        logging.error(f"Synchronization failed: {e}")
        exit(1)

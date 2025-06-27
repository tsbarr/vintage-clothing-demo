# test_data.py - Updated with better data directory handling

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from faker import Faker
import json
import os

# Ensure data directory exists
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# Set random seed for reproducibility
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
fake = Faker('en_CA')
Faker.seed(SEED)

# Configuration
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 12, 31)
NUM_LOCATIONS = 12
NUM_CUSTOMERS = 150
NUM_ITEMS = 300
NUM_ORDERS = 180

print("🎯 Generating test data for Vintage Clothing Business")
print("=" * 55)
print(f"📅 Date Range: {START_DATE.date()} to {END_DATE.date()}")
print(f"📊 Scale: {NUM_CUSTOMERS} customers, {NUM_ITEMS} items, {NUM_ORDERS} orders")
print(f"💾 Output Directory: {os.path.abspath(DATA_DIR)}")
print()

# Helper functions
def random_date(start, end):
    """Generate random date between start and end"""
    delta = end - start
    random_days = random.randrange(delta.days)
    return start + timedelta(days=random_days)

def weighted_choice(choices, weights):
    """Choose from list with weights"""
    return random.choices(choices, weights=weights, k=1)[0]

# 1. LOCATIONS DATA
print("📍 Generating locations data...")

location_types = ['pop_up_market', 'festival', 'craft_fair', 'online_only']
cities = [
    'Toronto', 'Toronto', 'Toronto', 'Mississauga', 'Brampton', 'Hamilton', 
    'Burlington', 'Oakville', 'Markham', 'Richmond Hill', 'Vaughan', 'Online'
]

locations_data = []
for i in range(NUM_LOCATIONS):
    if i == NUM_LOCATIONS - 1:  # Last one is online
        location = {
            'location_id': i + 1,
            'location_name': 'Online Store',
            'location_type': 'online_only',
            'address': None,
            'city': 'Online',
            'state_province': 'ON',
            'country': 'Canada',
            'postal_code': None,
            'market_fee': 0,
            'setup_date': None,
            'end_date': None,
            'is_active': True,
            'notes': 'Instagram and direct messages'
        }
    else:
        location = {
            'location_id': i + 1,
            'location_name': fake.street_name() + ' Market',
            'location_type': weighted_choice(location_types[:-1], [0.4, 0.3, 0.3]),
            'address': fake.street_address(),
            'city': cities[i],
            'state_province': 'ON',
            'country': 'Canada',
            'postal_code': fake.postcode_in_province('ON'),
            'market_fee': round(random.uniform(50, 200), 2),
            'setup_date': random_date(START_DATE, END_DATE),
            'end_date': None,
            'is_active': random.choice([True, True, True, False]),  # Mostly active
            'notes': fake.sentence()
        }
    locations_data.append(location)

locations_df = pd.DataFrame(locations_data)

# 2. CUSTOMERS DATA
print("👥 Generating customers data...")

customer_types = ['collector', 'casual_buyer', 'reseller']
acquisition_sources = ['instagram', 'tiktok', 'word_of_mouth', 'walk_by', 'referral']
preferred_eras = ['1960s', '1970s', '1980s', '1990s', 'Y2K']
preferred_styles = ['bohemian', 'grunge', 'preppy', 'punk', 'disco', 'band_tees', 'minimalist', 'romantic']
sizes = ['XS', 'S', 'M', 'L', 'XL', 'size_6', 'size_8', 'size_10', 'size_12', 'size_14']

customers_data = []
for i in range(NUM_CUSTOMERS):
    # Generate gender-appropriate names (vintage clothing: ~75% female, 25% male)
    gender = weighted_choice(['female', 'male'], [0.75, 0.25])
    first_name = fake.first_name_female() if gender == 'female' else fake.first_name_male()
    
    first_purchase = random_date(START_DATE, END_DATE - timedelta(days=30))
    customer = {
        'customer_id': i + 1,
        'square_customer_id': f'sq_cust_{i+1:03d}',
        'first_name': first_name,
        'last_name': fake.last_name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=65),
        'customer_type': weighted_choice(customer_types, [0.2, 0.7, 0.1]),
        'preferred_eras': str(random.sample(preferred_eras, random.randint(1, 2))),
        'preferred_styles': str(random.sample(preferred_styles, random.randint(1, 3))),
        'preferred_sizes': str(random.sample(sizes, random.randint(1, 2))),
        'total_orders': 0,  # Will update after orders
        'total_spent': float(0),   # Will update after orders
        'average_order_value': float(0),  # Will calculate later
        'first_purchase_date': None,  # Will set when we process orders
        'last_purchase_date': None,   # Will set when we process orders
        'acquisition_source': weighted_choice(acquisition_sources, [0.4, 0.2, 0.2, 0.15, 0.05])
    }
    customers_data.append(customer)

customers_df = pd.DataFrame(customers_data)

# 3. INVENTORY ITEMS DATA
print("👗 Generating inventory items data...")

categories = ['dresses', 'tops', 'bottoms', 'jackets', 'accessories', 'shoes']
subcategories = {
    'dresses': ['mini_dress', 'midi_dress', 'maxi_dress', 'cocktail_dress'],
    'tops': ['blouse', 'sweater', 't_shirt', 'tank_top', 'blazer'],
    'bottoms': ['jeans', 'skirt', 'pants', 'shorts'],
    'jackets': ['leather_jacket', 'denim_jacket', 'blazer', 'cardigan'],
    'accessories': ['handbag', 'scarf', 'jewelry', 'belt'],
    'shoes': ['boots', 'heels', 'flats', 'sneakers']
}

brands = [
    'Vintage Levi\'s', 'Unknown', 'Diane von Furstenberg', 'Chanel', 'Gucci', 
    'Zara', 'H&M', 'Forever 21', 'Ann Taylor', 'Banana Republic', 'J.Crew',
    'Vintage Band Tee', 'Local Designer', 'Handmade']

materials = ['cotton', 'silk', 'wool', 'polyester', 'leather', 'denim', 'cashmere', 'linen']
colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 'brown', 'gray']
patterns = ['solid', 'floral', 'stripes', 'polka_dot', 'geometric', 'animal_print']
sources = ['estate_sale', 'thrift_store', 'consignment', 'online_marketplace', 'donation']

inventory_data = []
for i in range(NUM_ITEMS):
    category = random.choice(categories)
    subcategory = random.choice(subcategories[category])
    cost = round(random.uniform(5, 80), 2)
    markup = random.uniform(2, 5)  # 200-500% markup
    selling_price = round(cost * markup, 2)
    
    # Some items sold, some still available
    status = weighted_choice(['sold', 'available', 'reserved'], [0.6, 0.35, 0.05])
    
    item = {
        'item_id': i + 1,
        'square_catalog_id': f'sq_item_{i+1:03d}',
        'sku': f'VIN{i+1:04d}',
        'item_name': f'{fake.color_name()} {subcategory.replace("_", " ").title()}',
        'brand': weighted_choice(brands, [0.15, 0.3, 0.05, 0.03, 0.03, 0.08, 0.08, 0.08, 0.05, 0.05, 0.05, 0.02, 0.02, 0.01]),
        'category': category,
        'subcategory': subcategory,
        'era_decade': weighted_choice(['1960s', '1970s', '1980s', '1990s', 'Y2K'], [0.1, 0.25, 0.3, 0.25, 0.1]),
        'size': random.choice(sizes),
        'measurements': json.dumps({
            'chest': f'{random.randint(32, 42)}"',
            'waist': f'{random.randint(24, 36)}"',
            'length': f'{random.randint(20, 50)}"'
        }),
        'condition_rating': weighted_choice([3, 4, 5], [0.2, 0.5, 0.3]),
        'condition_notes': fake.sentence() if random.random() < 0.3 else None,
        'material': random.choice(materials),
        'color_primary': random.choice(colors),
        'color_secondary': random.choice(colors) if random.random() < 0.3 else None,
        'pattern': random.choice(patterns),
        'cost_price': cost,
        'selling_price': selling_price,
        'suggested_retail_price': round(selling_price * 1.2, 2),
        'source': random.choice(sources),
        'acquisition_date': random_date(START_DATE, END_DATE),
        'acquisition_location': fake.city(),
        'is_one_of_a_kind': True,
        'weight_grams': random.randint(100, 2000),
        'photo_urls': str([f'https://example.com/photos/item_{i+1}_{j}.jpg' for j in range(random.randint(1, 4))]),
        'tags': str(random.sample(['bohemian', 'festival', 'statement_piece', 'vintage', 'retro', 'classic'], random.randint(1, 3))),
        'status': status
    }
    inventory_data.append(item)

inventory_df = pd.DataFrame(inventory_data)

# 4. ORDERS DATA
print("🛒 Generating orders data...")

order_sources = ['in_person', 'instagram_dm', 'website', 'phone']
payment_methods = ['card', 'cash', 'digital_wallet']

orders_data = []
order_items_data = []
payments_data = []

order_id = 1
for _ in range(NUM_ORDERS):
    customer_id = random.randint(1, NUM_CUSTOMERS)
    location_id = random.randint(1, NUM_LOCATIONS)
    order_date = random_date(START_DATE, END_DATE)
    
    # Determine number of items (most orders are 1-2 items)
    num_items = weighted_choice([1, 2, 3, 4], [0.6, 0.25, 0.1, 0.05])
    
    # Select sold items for this order
    available_items = inventory_df[inventory_df['status'] == 'sold'].sample(n=min(num_items, len(inventory_df[inventory_df['status'] == 'sold'])))
    
    if len(available_items) == 0:
        continue
    
    subtotal = available_items['selling_price'].sum()
    tax_rate = 0.13  # Ontario HST
    tax_amount = round(subtotal * tax_rate, 2)
    discount = round(random.uniform(0, subtotal * 0.2), 2) if random.random() < 0.1 else 0
    tip = round(random.uniform(0, 20), 2) if random.random() < 0.3 else 0
    total = round(subtotal + tax_amount - discount + tip, 2)
    
    order = {
        'order_id': order_id,
        'square_order_id': f'sq_order_{order_id:03d}',
        'customer_id': customer_id,
        'location_id': location_id,
        'order_date': order_date,
        'order_status': 'completed',
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'discount_amount': discount,
        'tip_amount': tip,
        'total_amount': total,
        'payment_method': weighted_choice(payment_methods, [0.7, 0.2, 0.1]),
        'order_source': weighted_choice(order_sources, [0.5, 0.3, 0.15, 0.05]),
        'staff_member': 'Elise',
        'notes': fake.sentence() if random.random() < 0.2 else None
    }
    orders_data.append(order)
    
    # Create order items
    for _, item in available_items.iterrows():
        order_item = {
            'order_item_id': len(order_items_data) + 1,
            'order_id': order_id,
            'item_id': item['item_id'],
            'quantity': 1,
            'unit_price': item['selling_price'],
            'discount_amount': 0,
            'total_price': item['selling_price']
        }
        order_items_data.append(order_item)
    
    # Create payment
    payment = {
        'payment_id': order_id,
        'square_payment_id': f'sq_pay_{order_id:03d}',
        'order_id': order_id,
        'payment_date': order_date,
        'amount': total,
        'payment_method': order['payment_method'],
        'payment_status': 'completed',
        'processing_fee': round(total * 0.029 + 0.30, 2),  # Typical card processing fee
        'square_fee': round(total * 0.026, 2),
        'net_amount': round(total - (total * 0.029 + 0.30), 2),
        'device_name': 'Square Terminal',
        'receipt_url': f'https://squareup.com/receipt/{order_id}'
    }
    payments_data.append(payment)
    
    order_id += 1

orders_df = pd.DataFrame(orders_data)
order_items_df = pd.DataFrame(order_items_data)
payments_df = pd.DataFrame(payments_data)

# Update customer totals
print("🔄 Updating customer totals...")
customer_order_stats = orders_df.groupby('customer_id').agg({
    'order_id': 'count',
    'total_amount': ['sum', 'mean'],
    'order_date': ['min', 'max']
}).round(2)

customer_order_stats.columns = ['total_orders', 'total_spent', 'average_order_value', 'first_purchase_date', 'last_purchase_date']

for idx, row in customer_order_stats.iterrows():
    customers_df.loc[customers_df['customer_id'] == idx, 'total_orders'] = row['total_orders']
    customers_df.loc[customers_df['customer_id'] == idx, 'total_spent'] = row['total_spent']
    customers_df.loc[customers_df['customer_id'] == idx, 'average_order_value'] = row['average_order_value']
    customers_df.loc[customers_df['customer_id'] == idx, 'first_purchase_date'] = row['first_purchase_date']
    customers_df.loc[customers_df['customer_id'] == idx, 'last_purchase_date'] = row['last_purchase_date']

# 5. SOCIAL MEDIA DATA
print("📱 Generating social media data...")

platforms = ['instagram', 'tiktok', 'facebook']
post_types = ['photo', 'video', 'carousel', 'story']

# Social media accounts
social_accounts_data = [
    {
        'account_id': 1,
        'platform': 'instagram',
        'account_handle': '@curatedcloset_vintage',
        'account_name': 'Curated Closet Vintage',
        'is_active': True
    },
    {
        'account_id': 2,
        'platform': 'tiktok',
        'account_handle': '@curatedcloset',
        'account_name': 'Curated Closet',
        'is_active': True
    },
    {
        'account_id': 3,
        'platform': 'facebook',
        'account_handle': 'curatedclosetvintage',
        'account_name': 'Curated Closet Vintage',
        'is_active': False
    }
]

social_accounts_df = pd.DataFrame(social_accounts_data)

# Social media posts
posts_data = []
post_metrics_data = []
post_items_featured_data = []

hashtags_pool = ['#vintage', '#thrifted', '#sustainable', '#90s', '#y2k', '#vintageootd', 
                '#torontovintage', '#vintageclothing', '#secondhand', '#upcycled']

for i in range(80):  # 80 posts over 2 years
    account_id = weighted_choice([1, 2], [0.7, 0.3])  # More Instagram posts
    post_date = random_date(START_DATE, END_DATE)
    
    post = {
        'post_id': i + 1,
        'account_id': account_id,
        'platform_post_id': f'post_{account_id}_{i+1:03d}',
        'post_type': weighted_choice(post_types, [0.4, 0.2, 0.3, 0.1]),
        'caption': fake.text(max_nb_chars=200),
        'post_url': f'https://instagram.com/p/{fake.uuid4()[:8]}',
        'posted_date': post_date,
        'hashtags': str(random.sample(hashtags_pool, random.randint(3, 8))),
        'mentions': str([]),
        'is_promotional': random.choice([True, False])
    }
    posts_data.append(post)
    
    # Generate metrics for each post
    base_impressions = random.randint(100, 2000)
    reach = int(base_impressions * random.uniform(0.7, 0.95))
    likes = int(reach * random.uniform(0.02, 0.15))
    comments = int(likes * random.uniform(0.02, 0.1))
    saves = int(likes * random.uniform(0.1, 0.3))
    shares = int(likes * random.uniform(0.01, 0.05))
    
    metrics = {
        'metric_id': i + 1,
        'post_id': i + 1,
        'metric_date': post_date.date(),
        'impressions': base_impressions,
        'reach': reach,
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'saves': saves,
        'clicks': random.randint(5, 50),
        'engagement_rate': round((likes + comments + saves + shares) / reach, 4) if reach > 0 else 0
    }
    post_metrics_data.append(metrics)
    
    # Feature 1-3 items per post
    featured_items = random.sample(range(1, NUM_ITEMS + 1), random.randint(1, 3))
    for j, item_id in enumerate(featured_items):
        feature = {
            'feature_id': len(post_items_featured_data) + 1,
            'post_id': i + 1,
            'item_id': item_id,
            'is_primary_item': j == 0
        }
        post_items_featured_data.append(feature)

social_posts_df = pd.DataFrame(posts_data)
social_metrics_df = pd.DataFrame(post_metrics_data)
post_items_featured_df = pd.DataFrame(post_items_featured_data)

# 6. MARKET PERFORMANCE DATA
print("📊 Generating market performance data...")

market_performance_data = []
for i in range(30):  # 30 market events
    location_id = random.randint(1, NUM_LOCATIONS - 1)  # Exclude online
    market_date = random_date(START_DATE, END_DATE)
    
    # Get orders for this location and date (approximate)
    location_orders = orders_df[
        (orders_df['location_id'] == location_id) & 
        (orders_df['order_date'].dt.date == market_date.date())
    ]
    
    if len(location_orders) == 0:
        # Generate synthetic performance data
        total_sales = round(random.uniform(200, 1500), 2)
        total_transactions = random.randint(5, 25)
        items_sold = random.randint(5, 30)
    else:
        total_sales = location_orders['total_amount'].sum()
        total_transactions = len(location_orders)
        items_sold = order_items_df[order_items_df['order_id'].isin(location_orders['order_id'])]['quantity'].sum()
    
    booth_cost = round(random.uniform(50, 200), 2)
    travel_expenses = round(random.uniform(20, 80), 2)
    
    performance = {
        'performance_id': i + 1,
        'location_id': location_id,
        'market_date': market_date.date(),
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'items_sold': items_sold,
        'average_transaction_value': round(total_sales / total_transactions, 2) if total_transactions > 0 else 0,
        'foot_traffic_estimate': random.randint(50, 300),
        'weather': random.choice(['sunny', 'cloudy', 'rainy', 'cold']),
        'competitor_count': random.randint(2, 12),
        'booth_cost': booth_cost,
        'travel_expenses': travel_expenses,
        'net_profit': round(total_sales - booth_cost - travel_expenses, 2),
        'customer_acquisition_count': random.randint(0, 8),
        'notes': fake.sentence() if random.random() < 0.3 else None
    }
    market_performance_data.append(performance)

market_performance_df = pd.DataFrame(market_performance_data)

# 7. Save all dataframes to CSV
print("💾 Saving data to CSV files...")

dataframes = {
    'locations': locations_df,
    'customers': customers_df,
    'inventory_items': inventory_df,
    'orders': orders_df,
    'order_items': order_items_df,
    'payments': payments_df,
    'social_media_accounts': social_accounts_df,
    'social_media_posts': social_posts_df,
    'social_media_metrics': social_metrics_df,
    'post_items_featured': post_items_featured_df,
    'market_performance': market_performance_df
}

for name, df in dataframes.items():
    filename = f'{name}.csv'
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"✓ Saved {filename} with {len(df)} records")

print("\n" + "="*60)
print("🎉 MOCK DATA GENERATION COMPLETE!")
print("="*60)
print(f"Generated data for vintage clothing business:")
print(f"• {len(locations_df)} locations")
print(f"• {len(customers_df)} customers")
print(f"• {len(inventory_df)} inventory items")
print(f"• {len(orders_df)} orders")
print(f"• {len(order_items_df)} order items")
print(f"• {len(social_posts_df)} social media posts")
print(f"• {len(market_performance_df)} market events")
print(f"\nData spans from {START_DATE.date()} to {END_DATE.date()}")
print(f"All CSV files saved to: {os.path.abspath(DATA_DIR)}")

# Generate some quick insights
print("\n" + "="*60)
print("📈 QUICK DATA INSIGHTS")
print("="*60)

print(f"\n🏆 TOP PERFORMING LOCATIONS:")
location_performance = market_performance_df.groupby('location_id')['net_profit'].mean().sort_values(ascending=False).head(3)
for loc_id, profit in location_performance.items():
    location_name = locations_df[locations_df['location_id'] == loc_id]['location_name'].iloc[0]
    print(f"• {location_name}: ${profit:.2f} avg profit")

print(f"\n💎 TOP CUSTOMERS BY SPENDING:")
top_customers = customers_df.nlargest(3, 'total_spent')[['first_name', 'last_name', 'total_spent', 'total_orders']]
for _, customer in top_customers.iterrows():
    print(f"• {customer['first_name']} {customer['last_name']}: ${customer['total_spent']:.2f} ({customer['total_orders']} orders)")

print(f"\n👗 INVENTORY BY CATEGORY:")
category_counts = inventory_df['category'].value_counts()
for category, count in category_counts.items():
    print(f"• {category}: {count} items")

print(f"\n📱 SOCIAL MEDIA PERFORMANCE:")
avg_engagement = social_metrics_df['engagement_rate'].mean()
total_likes = social_metrics_df['likes'].sum()
print(f"• Average engagement rate: {avg_engagement:.2%}")
print(f"• Total likes across all posts: {total_likes:,}")

print(f"\n💰 SALES SUMMARY:")
print(f"• Total revenue: ${orders_df['total_amount'].sum():,.2f}")
print(f"• Average order value: ${orders_df['total_amount'].mean():.2f}")
print(f"• Most popular payment method: {orders_df['payment_method'].mode().iloc[0]}")

print("\n" + "="*60)
print("🚀 NEXT STEPS:")
print("="*60)
print("1. Set up database:   python database_setup.py --all")
print("2. Load CSV data:     python load_csv_data.py")
print("3. Test system:       python main_sync.py health")
print("4. View insights:     python load_csv_data.py --insights")
print("\n✨ Your vintage clothing business data is ready!")

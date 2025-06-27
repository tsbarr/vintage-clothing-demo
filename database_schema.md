# Curated Closet Vintage Clothing Pop-up Business Database Schema

## Core Business Tables

### **locations**
```sql
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    location_type VARCHAR(50) NOT NULL, -- 'pop_up_market', 'festival', 'online_only'
    address TEXT,
    city VARCHAR(100),
    state_province VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    coordinates POINT, -- lat/lng for mapping
    market_fee DECIMAL(10,2), -- booth rental cost
    setup_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    square_location_id VARCHAR(100), -- Square API location ID
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **customers**
```sql
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    square_customer_id VARCHAR(100) UNIQUE, -- Square API customer ID
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    date_of_birth DATE,
    customer_type VARCHAR(50), -- 'collector', 'casual_buyer', 'reseller'
    preferred_eras TEXT[], -- ['1960s', '1970s']
    preferred_styles TEXT[]
    preferred_sizes TEXT[], -- ['S', 'M', 'size_8']
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    average_order_value DECIMAL(10,2) DEFAULT 0,
    first_purchase_date DATE,
    last_purchase_date DATE,
    acquisition_source VARCHAR(100), -- 'instagram', 'tiktok', 'word_of_mouth', 'walk_by'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Inventory Management

### **inventory_items**
```sql
CREATE TABLE inventory_items (
    item_id SERIAL PRIMARY KEY,
    square_catalog_id VARCHAR(100) UNIQUE, -- Square API catalog item ID
    sku VARCHAR(100) UNIQUE,
    item_name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(100) NOT NULL, -- 'dresses', 'jackets', 'accessories'
    subcategory VARCHAR(100), -- 'mini_dress', 'leather_jacket', 'vintage_bag'
    era_decade VARCHAR(20), -- '1960s', '1970s', '1980s'
    era_year_range VARCHAR(20), -- '1965-1970'
    size VARCHAR(50),
    measurements JSONB, -- {'chest': '36"', 'waist': '28"', 'length': '45"'}
    condition_rating INTEGER CHECK (condition_rating BETWEEN 1 AND 5), -- 1=poor, 5=mint
    condition_notes TEXT,
    material VARCHAR(200), -- 'wool', 'silk', 'cotton blend'
    color_primary VARCHAR(50),
    color_secondary VARCHAR(50),
    pattern VARCHAR(100), -- 'floral', 'polka_dot', 'solid'
    cost_price DECIMAL(10,2), -- what you paid for it
    selling_price DECIMAL(10,2) NOT NULL,
    suggested_retail_price DECIMAL(10,2),
    source VARCHAR(100), -- 'estate_sale', 'thrift_store', 'consignment'
    acquisition_date DATE,
    acquisition_location VARCHAR(200),
    is_one_of_a_kind BOOLEAN DEFAULT TRUE,
    weight_grams INTEGER, -- for shipping calculations
    photo_urls TEXT[], -- array of image URLs
    tags TEXT[], -- ['bohemian', 'festival', 'statement_piece']
    status VARCHAR(50) DEFAULT 'available', -- 'available', 'sold', 'reserved', 'damaged'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **inventory_location_tracking**
```sql
CREATE TABLE inventory_location_tracking (
    tracking_id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory_items(item_id),
    location_id INTEGER REFERENCES locations(location_id),
    quantity INTEGER DEFAULT 1, -- usually 1 for vintage items
    date_moved DATE NOT NULL,
    moved_by VARCHAR(100), -- staff member name
    reason VARCHAR(100), -- 'market_setup', 'returned_unsold', 'online_storage'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Sales & Orders

### **orders**
```sql
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    square_order_id VARCHAR(100) UNIQUE, -- Square API order ID
    customer_id INTEGER REFERENCES customers(customer_id),
    location_id INTEGER REFERENCES locations(location_id),
    order_date TIMESTAMP NOT NULL,
    order_status VARCHAR(50) NOT NULL, -- 'pending', 'completed', 'cancelled', 'refunded'
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    tip_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50), -- 'card', 'cash', 'digital_wallet'
    order_source VARCHAR(50), -- 'in_person', 'instagram_dm', 'website', 'phone'
    staff_member VARCHAR(100), -- who processed the sale
    notes TEXT, -- special requests, alterations needed, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **order_items**
```sql
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    item_id INTEGER REFERENCES inventory_items(item_id),
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **payments**
```sql
CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    square_payment_id VARCHAR(100) UNIQUE, -- Square API payment ID
    order_id INTEGER REFERENCES orders(order_id),
    payment_date TIMESTAMP NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- 'visa', 'mastercard', 'cash', 'apple_pay'
    payment_status VARCHAR(50) NOT NULL, -- 'completed', 'pending', 'failed', 'refunded'
    processing_fee DECIMAL(10,2) DEFAULT 0,
    square_fee DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(10,2) NOT NULL,
    device_name VARCHAR(100), -- which Square device processed payment
    receipt_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Social Media Integration

### **social_media_accounts**
```sql
CREATE TABLE social_media_accounts (
    account_id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL, -- 'instagram', 'tiktok', 'facebook'
    account_handle VARCHAR(100) NOT NULL,
    account_name VARCHAR(200),
    api_access_token TEXT, -- encrypted token for API access
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **social_media_posts**
```sql
CREATE TABLE social_media_posts (
    post_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES social_media_accounts(account_id),
    platform_post_id VARCHAR(200) NOT NULL, -- platform's unique post ID
    post_type VARCHAR(50), -- 'photo', 'video', 'carousel', 'story'
    caption TEXT,
    post_url VARCHAR(500),
    posted_date TIMESTAMP NOT NULL,
    hashtags TEXT[], -- array of hashtags used
    mentions TEXT[], -- array of accounts mentioned
    is_promotional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **post_items_featured**
```sql
CREATE TABLE post_items_featured (
    feature_id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES social_media_posts(post_id),
    item_id INTEGER REFERENCES inventory_items(item_id),
    is_primary_item BOOLEAN DEFAULT FALSE, -- main item featured in post
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **social_media_metrics**
```sql
CREATE TABLE social_media_metrics (
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
    engagement_rate DECIMAL(5,4) DEFAULT 0, -- calculated field
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Analytics & Business Intelligence

### **market_performance**
```sql
CREATE TABLE market_performance (
    performance_id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(location_id),
    market_date DATE NOT NULL,
    total_sales DECIMAL(10,2) DEFAULT 0,
    total_transactions INTEGER DEFAULT 0,
    items_sold INTEGER DEFAULT 0,
    average_transaction_value DECIMAL(10,2) DEFAULT 0,
    foot_traffic_estimate INTEGER, -- manual count or estimate
    weather VARCHAR(100), -- 'sunny', 'rainy', 'cold' - affects sales
    competitor_count INTEGER, -- how many other vintage vendors
    booth_cost DECIMAL(10,2),
    travel_expenses DECIMAL(10,2),
    net_profit DECIMAL(10,2),
    customer_acquisition_count INTEGER DEFAULT 0, -- new customers that day
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **social_media_attribution**
```sql
CREATE TABLE social_media_attribution (
    attribution_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_id INTEGER REFERENCES orders(order_id),
    post_id INTEGER REFERENCES social_media_posts(post_id),
    attribution_type VARCHAR(50), -- 'direct_message', 'post_comment', 'bio_link_click'
    attribution_confidence VARCHAR(20), -- 'high', 'medium', 'low'
    time_from_post_to_purchase INTERVAL, -- calculated field
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes for Performance

```sql
-- Customer lookups
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_square_id ON customers(square_customer_id);

-- Inventory searches
CREATE INDEX idx_inventory_category ON inventory_items(category);
CREATE INDEX idx_inventory_era ON inventory_items(era_decade);
CREATE INDEX idx_inventory_status ON inventory_items(status);
CREATE INDEX idx_inventory_sku ON inventory_items(sku);

-- Sales analysis
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_location ON orders(location_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Social media analytics
CREATE INDEX idx_social_posts_date ON social_media_posts(posted_date);
CREATE INDEX idx_social_metrics_date ON social_media_metrics(metric_date);

-- Performance tracking
CREATE INDEX idx_market_performance_date ON market_performance(market_date);
CREATE INDEX idx_market_performance_location ON market_performance(location_id);
```

## Key Features of This Schema

### **Vintage-Specific Elements**
- Era tracking (decade and year ranges)
- Condition ratings and detailed measurements
- One-of-a-kind item tracking
- Source and acquisition information
- Detailed material and pattern information

### **Pop-up Business Focus**
- Location-based inventory tracking
- Market performance metrics including costs
- Weather and competitor tracking
- Mobile payment device tracking

### **Social Media Integration**
- Multi-platform post tracking
- Item-to-post relationships
- Attribution tracking from social media to sales
- Comprehensive engagement metrics

### **Business Intelligence Ready**
- Profit calculation fields
- Customer lifetime value tracking
- Market performance comparisons
- Social media ROI analysis

This schema supports workflow of managing inventory, processing payments through Square, tracking social media performance, and analyzing which markets and posts drive the most sales for vintage clothing business.

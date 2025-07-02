# Social Media Analytics Dashboard - Vintage Clothing Demo

> **A demonstration of cross-platform social media analytics built with Dash and PostgreSQL**

## Project Overview

This project demonstrates a **social media analytics dashboard** specifically designed for creative businesses. Built using a vintage clothing business as the demo case, it showcases how small businesses can track marketing campaign performance across platforms, identify viral content, and build customer insights from social media data.

**Why This Matters**: Creative businesses often struggle to quantify social media ROI and identify which content actually drives business results. This dashboard bridges that gap.

## Key Features

### **Viral Content Detection**
- **Engagement vs Impressions Analysis**: Scatter plots identifying high-performing content
- **Platform Performance Comparison**: Cross-platform analytics (Instagram vs TikTok)  
- **Save Rate Tracking**: Identifies content with highest bookmark potential (future customer interest)

### **Audience Building Analytics**
- **Comment Engagement Trends**: Time-series analysis of audience interaction
- **Share Potential Analysis**: Content amplification metrics
- **Future Customer Identification**: Save behavior analysis for lead generation

### **Executive Summary Dashboard**
- **Real-time Performance Metrics**: Key performance indicators at a glance
- **Cross-platform Filtering**: Unified view across social media accounts
- **Business Impact Tracking**: Metrics that matter for creative businesses

## Technical Architecture

```
Frontend (Dash/Plotly) → PostgreSQL Database → Data Processing (Pandas)
                ↓
    Interactive Analytics Dashboard
```

### **Core Technologies**
- **Frontend**: Dash with Bootstrap components for responsive design
- **Backend**: PostgreSQL with comprehensive social media schema
- **Data Processing**: Pandas for analytics and SQLAlchemy for database operations
- **Visualization**: Plotly for interactive charts and real-time updates

### **Database Schema**
Comprehensive schema designed for creative businesses:
- **Social Media Posts & Metrics**: Multi-platform content tracking
- **Customer Data**: Purchase behavior linked to social engagement
- **Inventory Integration**: Products featured in posts with performance tracking
- **Market Performance**: Pop-up event analytics for offline-to-online attribution

## Dashboard Analytics

### **Viral Content Detection**
```python
# Example: Engagement Rate vs Impressions Analysis
fig = px.scatter(
    df, 
    x='impressions', 
    y='engagement_rate',
    color='platform',
    size='saves',
    title='Viral Content Detection'
)
```

### **Audience Building Metrics**
- **Save Rate Analysis**: Identifies content that generates future customer interest
- **Comment Engagement Over Time**: Tracks community building progress
- **Share Potential Visualization**: Content amplification opportunities

### **Cross-Platform Performance**
- **Platform Comparison**: Instagram vs TikTok performance metrics
- **Content Type Analysis**: Photos vs videos vs carousel posts
- **Engagement Pattern Recognition**: Optimal posting times and content formats

## Getting Started

### **Setup Instructions**
```bash
# 1. Clone repository
git clone https://github.com/tsbarr/vintage-clothing-demo.git
cd vintage-clothing-demo

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.template .env
# Edit .env with your database credentials

# 4. Initialize database
python database_setup.py --all

# 5. Generate demo data
python generate_test_data.py

# 6. Load data into database
python load_csv_data.py

# 7. Run dashboard
cd dashboards
python social_dashboard.py
```

### **View Dashboard**
Navigate to `http://localhost:8050` to see the interactive analytics dashboard

## Project Structure

```
vintage-clothing-demo/
├── dashboards/
│   ├── social_dashboard.py    # Main Dash application
│   └── README.md             # Dashboard documentation
├── data/                     # Generated CSV files
│   ├── customers.csv
│   ├── inventory_items.csv
│   ├── social_media_posts.csv
│   └── [10 more data files]
├── sync/                     # API integration modules
│   ├── main_sync.py
│   ├── social_media_sync.py
│   └── square_sync.py
├── config.py                 # Shared configuration
├── database_schema.md        # Complete database documentation
├── database_setup.py         # Database initialization
├── generate_test_data.py     # Mock data generation
├── load_csv_data.py         # Data loading utilities
└── requirements.txt         # Python dependencies
```

## Technical Highlights

### **Data Pipeline Design**
- **Automated Data Generation**: Realistic mock data with business logic
- **Database Integration**: PostgreSQL with proper foreign key relationships
- **Error Handling**: Comprehensive validation and data quality checks
- **Scalable Architecture**: Designed for multi-platform expansion

### **Dashboard Features**
- **Interactive Filtering**: Platform-specific and cross-platform views
- **Real-time Updates**: Dynamic chart updates based on user selections
- **Mobile Responsive**: Bootstrap components for cross-device compatibility
- **Performance Optimized**: Efficient SQL queries and data processing

### **Business Intelligence**
- **KPI Development**: Metrics specifically relevant to creative businesses
- **Trend Analysis**: Time-series patterns and seasonal insights  
- **Performance Benchmarking**: Comparative analysis across content types
- **Actionable Insights**: Dashboard designed for decision-making, not just reporting

## Demo Data Insights

The generated dataset includes:
- **150 customers** with realistic purchasing patterns
- **300 inventory items** across vintage categories
- **80 social media posts** with engagement metrics
- **30 market events** with performance data
- **Cross-platform analytics** spanning 2+ years

## Next Steps & Scalability

### **Enhancement Opportunities**
- **Real-time API Integration**: Live social media data feeds
- **Machine Learning Models**: Predictive content performance
- **A/B Testing Framework**: Systematic content optimization
- **Multi-business Dashboard**: Template for other creative industries

---

## 📧 Contact

**Tania Barrera, MSc** | Data Specialist  
[LinkedIn](https://linkedin.com/in/tania-sofia-barrera)

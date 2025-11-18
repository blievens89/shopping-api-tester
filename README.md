# 🛍️ Google Shopping Competitive Analysis Tool

A powerful Streamlit-based application for competitive analysis of Google Shopping results using the DataForSEO API. Track competitors, analyze pricing strategies, and extract rich product data including images, descriptions, and reviews.

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.38.0-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 🌟 Features

### Core Functionality
- **Real-time Google Shopping Data** - Fetch live product data via DataForSEO API
- **Multi-Region Support** - Search across UK, US, Germany, and France markets
- **Rich Data Extraction** - Captures images, descriptions, highlights, ratings, and reviews
- **Competitor Analysis** - Track target domains and their market positioning
- **Historical Tracking** - Save search results to SQLite database for trend analysis
- **Bulk Processing** - Upload CSV files to analyze multiple keywords at once

### Data Insights
- **Overview Dashboard** - Top 10 products with quality scoring
- **Domain Statistics** - Aggregated metrics by seller/domain
- **Target Tracking** - Detailed analysis of specific competitor domains
- **Price Analytics** - Average prices, price ranges, and distribution
- **Title Quality Scoring** - Algorithmic assessment of product title quality

### Rich Content Display
- **Product Images** - Full image galleries with carousel navigation
- **Descriptions** - Full product descriptions with preview snippets
- **Highlights & Features** - Bullet-point product specifications
- **Currency Support** - Auto-detection and proper display ($, £, €)
- **Drill-Down View** - Detailed product information with API fallback

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- DataForSEO API account (get credentials at [dataforseo.com](https://dataforseo.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/blievens89/shopping-api-tester.git
   cd shopping-api-tester
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**

   Create a `.env` file in the project root:
   ```env
   DATAFORSEO_LOGIN=your_email@example.com
   DATAFORSEO_PASSWORD=your_api_password
   ```

   **OR** use Streamlit secrets (for deployment):

   Create `.streamlit/secrets.toml`:
   ```toml
   DATAFORSEO_LOGIN = "your_email@example.com"
   DATAFORSEO_PASSWORD = "your_api_password"
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

6. **Open in browser**

   Navigate to `http://localhost:8501`

---

## 📖 Usage Guide

### Basic Search

1. **Select Location** - Choose your target market from the sidebar (UK/US/Germany/France)
2. **Enter Keyword** - Type a product search term (e.g., "running shoes")
3. **Set Max Results** - Choose how many results to fetch (10-100)
4. **Click Search** - Wait for results (progress bar shows polling status)

### Target Domain Tracking

1. **Add Target Domains** - Enter competitor domains in the text area (one per line):
   ```
   nike.com
   adidas.com
   amazon.co.uk
   ```
2. **Run Search** - Results will include detailed target domain analysis in Tab 3

### Bulk Keyword Analysis

1. **Prepare CSV** - Create a CSV file with a `keyword` column:
   ```csv
   keyword
   running shoes
   bluetooth headphones
   laptop backpack
   ```
2. **Upload File** - Use the file uploader
3. **Review Results** - Each keyword displays inline with full data

### Save Historical Data

1. **Check "Save results"** - Enable the checkbox after viewing results
2. **Data Stored** - Results saved to `data/history.db` SQLite database
3. **Includes** - Images, descriptions, highlights, ratings, reviews, pricing

---

## 📊 Understanding the Interface

### Tab 1: 📊 Overview
- **Data Stats Banner** - Shows how many products have descriptions/images/highlights
- **Top 10 Table** - Key metrics including title quality score and description preview
- **Product Details** - Expandable cards with image carousel and descriptions
- **Domain Frequency Chart** - Bar chart of top 10 domains by appearance

### Tab 2: 🏆 Top Domains
- **Aggregated Statistics** - Metrics grouped by domain/seller
- **Metrics Included**:
  - Appearances (product count)
  - Avg Position (ranking)
  - Best Position (highest rank achieved)
  - Avg Price
  - Avg Rating

### Tab 3: 🎯 Targets
- **Competitor Deep-Dive** - Expandable sections per target domain
- **Domain Metrics** - Appearances, average position, best position
- **Product List** - All products from target domain with links

### Tab 4: 📋 Full Data
- **Complete Dataset** - All columns and all rows
- **CSV Export** - Download button for offline analysis
- **Includes** - Title quality scores added to dataset

### Tab 5: 🔎 Drill-Down
- **Product Inspector** - Select any product from dropdown
- **Detailed API Call** - Fetches extended product information
- **Fallback Data** - Shows search results if detailed fetch fails
- **Image Carousel** - Navigate through up to 10 product images
- **Toggle Controls** - Show/hide descriptions and highlights
- **Debug JSON** - Raw API response for developers

---

## 🔧 Configuration

### Location Codes
```python
"United Kingdom": 2826
"United States": 2840
"Germany": 2276
"France": 2250
```

### API Endpoints Used
- **Search Products**: `/merchant/google/products/task_post`
- **Product Details**: `/merchant/google/product_info/task_post`

### Retry Logic
- **POST Requests**: 5 attempts, exponential backoff (1-8s)
- **GET Requests**: 7 attempts, exponential backoff (1-8s)
- **Max Wait Time**: 180 seconds (3 minutes)
- **Poll Interval**: 2 seconds

### Supported Currencies
- USD ($)
- GBP (£)
- EUR (€)
- CAD ($)
- AUD ($)

---

## 🏗️ Architecture

### Project Structure
```
shopping-api-tester/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version (3.12)
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── api/
│   ├── __init__.py
│   └── dataforseo.py          # DataForSEO API client wrapper
├── utils/
│   ├── __init__.py
│   └── analysis.py            # Data parsing and analysis functions
└── data/
    └── history.db             # SQLite database (created on first save)
```

### Data Flow
```
User Input → DataForSEO API → parse_shopping_results()
    ↓
pandas DataFrame → analyze_competitors() → Streamlit UI
    ↓
Optional: SQLite storage for historical tracking
```

### Key Functions

**`api/dataforseo.py`**
- `DataForSEOClient` - API wrapper with retry logic
- `search_products()` - Fetch shopping search results
- `get_product_info()` - Fetch detailed product information

**`utils/analysis.py`**
- `parse_shopping_results()` - Extract rich data from API response
- `analyze_competitors()` - Generate competitive metrics
- `calculate_title_quality_score()` - Score product titles (0-100)

---

## 📈 Recent Improvements (v2.1)

### Major Fixes
✅ **Full Rich Content Extraction** - Now stores complete images, descriptions, and highlights (not just metadata)
✅ **Dynamic Currency Display** - Automatically detects and displays correct currency symbols
✅ **Location Consistency** - Passes location_code to drill-down API for accurate data
✅ **Enhanced SQLite Schema** - Stores images, descriptions, highlights, ratings, reviews
✅ **Product ID Validation** - Graceful fallback when product_id missing

### UI Enhancements
✅ **Image Carousel** - Navigate through product images with controls
✅ **Description Visibility** - Descriptions now prominent in overview
✅ **Data Stats Banner** - Shows extraction success rate
✅ **Title Quality in Overview** - Quality scores visible in top 10 table
✅ **Better Drill-Down UX** - Falls back to search data when API fails

### Performance
✅ **Reduced API Calls** - Reuses search data instead of always fetching details
✅ **Progress Indicators** - Real-time feedback during API polling

---

## 🛠️ Development

### Run Tests
```bash
# Unit tests (if implemented)
pytest tests/

# Linting
flake8 app.py api/ utils/
```

### Environment Variables
```env
DATAFORSEO_LOGIN=your_email@example.com
DATAFORSEO_PASSWORD=your_api_password
```

### Deploy to Streamlit Cloud
1. Push to GitHub
2. Connect repository at [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in Streamlit Cloud dashboard
4. Deploy automatically on push

### Deploy to Heroku
1. Ensure `runtime.txt` specifies Python 3.12
2. Set environment variables:
   ```bash
   heroku config:set DATAFORSEO_LOGIN=your_email@example.com
   heroku config:set DATAFORSEO_PASSWORD=your_api_password
   ```
3. Deploy:
   ```bash
   git push heroku main
   ```

---

## 📝 Title Quality Scoring Algorithm

Products are scored 0-100 based on these factors:

| Criteria | Points |
|----------|--------|
| Length 70-150 chars | +30 |
| Length ≥50 chars | +15 |
| Word count ≥8 | +25 |
| Word count ≥5 | +15 |
| Contains attributes (size, color, etc) | +20 |
| Capitalization ratio <50% | +15 |
| Starts with capital letter | +10 |

**Attributes detected**: size, color, colour, cm, mm, inch, ml, l, kg, g

---

## 🐛 Troubleshooting

### "Missing DataForSEO credentials" Error
- Ensure `.env` file exists in project root
- OR set secrets in `.streamlit/secrets.toml`
- Verify credentials are correct at [dataforseo.com](https://dataforseo.com)

### "0/50 products with descriptions"
- DataForSEO's search endpoint may not return descriptions
- Descriptions are fetched in drill-down (Tab 5) via detailed API
- This is normal behavior - not all products have descriptions

### "Timed out waiting for task result"
- Increase `max_wait_sec` in `api/dataforseo.py` (line 63)
- Check DataForSEO API status
- Reduce `depth` parameter (fewer results = faster)

### Images Not Displaying
- Check browser console for CORS errors
- Verify image URLs in "Raw details (debug)" section
- Some merchant sites block image embedding

### Empty DataFrame / No Results
- Keyword may have no shopping results
- Try different location/market
- Check raw API response in expander for error messages

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use type hints where applicable
- Add docstrings to functions
- Keep functions under 50 lines when possible

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **DataForSEO** - API provider for Google Shopping data
- **Streamlit** - Web framework for rapid development
- **Pandas** - Data manipulation and analysis
- **Tenacity** - Retry logic with exponential backoff

---

## 📧 Support

For issues, questions, or suggestions:
- **GitHub Issues**: [Create an issue](https://github.com/blievens89/shopping-api-tester/issues)
- **DataForSEO Docs**: [API Documentation](https://docs.dataforseo.com/)

---

## 🗺️ Roadmap

### Planned Features
- [ ] Historical trend visualization
- [ ] Email alerts for competitor changes
- [ ] Multi-keyword comparison view
- [ ] Export to Excel with formatting
- [ ] Price change notifications
- [ ] Automated daily/weekly reports
- [ ] Advanced filtering options
- [ ] Image download functionality
- [ ] Custom location codes

---

**Built with ❤️ by the shopping-api-tester team**

*Last updated: 2025-01-18*

import os, io, time, sqlite3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from api.dataforseo import DataForSEOClient, DataForSEOError
from utils.analysis import parse_shopping_results, analyze_competitors, calculate_title_quality_score

load_dotenv()

st.set_page_config(page_title="Google Shopping Competitive Analysis", page_icon="🛍️", layout="wide")

# Custom CSS for image sizing and highlights
st.markdown("""
<style>
/* Force constrain carousel images */
.carousel-img-wrapper {
    max-width: 250px !important;
    max-height: 250px !important;
    overflow: hidden !important;
}
.carousel-img-wrapper img {
    max-width: 250px !important;
    max-height: 250px !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
}
/* Legacy - keep for backwards compat */
.product-image-container img {
    max-height: 280px;
    width: auto;
    object-fit: contain;
    display: block;
    margin: 0 auto;
}
.thumbnail-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}
.thumbnail-grid img {
    width: 60px;
    height: 60px;
    object-fit: cover;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
}
.thumbnail-grid img:hover {
    border-color: #ff4b4b;
}
.thumbnail-grid img.active {
    border-color: #ff4b4b;
}
/* Highlights styling */
.highlight-chip {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 6px 12px;
    border-radius: 16px;
    margin: 4px;
    font-size: 0.85em;
    font-weight: 500;
}
.highlight-list {
    background: #f8f9fa;
    border-left: 4px solid #667eea;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
}
.highlight-list li {
    margin: 6px 0;
    color: #333;
}
/* Seller card styling */
.seller-card {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.seller-price {
    font-size: 1.2em;
    font-weight: bold;
    color: #2e7d32;
}
/* Variation badges */
.variation-badge {
    display: inline-block;
    background: #e3f2fd;
    color: #1565c0;
    padding: 4px 10px;
    border-radius: 12px;
    margin: 3px;
    font-size: 0.8em;
}
</style>
""", unsafe_allow_html=True)

st.title("Google Shopping Competitive Analysis")
st.caption("DataForSEO → Streamlit tester")

login = st.secrets.get("DATAFORSEO_LOGIN", os.getenv("DATAFORSEO_LOGIN"))
password = st.secrets.get("DATAFORSEO_PASSWORD", os.getenv("DATAFORSEO_PASSWORD"))

st.sidebar.header("Configuration")
if not login or not password:
    st.sidebar.error("Add DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD to secrets or .env")
    st.stop()

@st.cache_resource
def get_api_client(api_login: str, api_password: str) -> DataForSEOClient:
    """Cache the API client to avoid re-initialization on every rerun."""
    return DataForSEOClient(api_login, api_password)

try:
    client = get_api_client(login, password)
    st.sidebar.success("API client ready")
except Exception as e:
    st.sidebar.error(f"Init failed: {e}")
    st.stop()

location_options = {"United Kingdom": 2826, "United States": 2840, "Germany": 2276, "France": 2250}
selected_location = st.sidebar.selectbox("Location", list(location_options.keys()))
location_code = location_options[selected_location]

col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("Keyword", placeholder="e.g. running shoes, bluetooth headphones")
with col2:
    depth = st.number_input("Max results", min_value=10, max_value=100, value=50, step=10)

st.markdown("### Target Domains (optional)")
competitor_domains = st.text_area("One per line", placeholder="nike.com\nadidas.com\namazon.co.uk")
target_domains = [x.strip() for x in competitor_domains.splitlines() if x.strip()] or None

uploaded = st.file_uploader("Upload CSV with 'keyword' column (optional)", type=["csv"])

def search_with_progress(k: str, loc: int, dep: int):
    prog = st.progress(0); status = st.empty()
    def on_tick(elapsed, maximum):
        pct = min(99, int((elapsed / max(1, maximum)) * 100))
        prog.progress(pct)
        status.info(f"⏳ Fetching Google Shopping results... {elapsed}s (typically 10-30s)")
    data = client.search_products(keyword=k, location_code=loc, depth=dep, on_tick=on_tick)
    prog.progress(100); status.success("✅ Results received!")
    df = parse_shopping_results(data)
    return data, df

def get_cached_product_info(pid: str, loc: int):
    """Fetch product info with session state caching to prevent refetch on rerun."""
    cache_key = f"product_cache_{pid}_{loc}"
    if cache_key not in st.session_state:
        prog = st.progress(0); status = st.empty()
        def on_tick(elapsed, maximum):
            pct = min(99, int((elapsed / max(1, maximum)) * 100))
            prog.progress(pct)
            status.info(f"⏳ Loading product details... {elapsed}s (typically 5-15s)")
        try:
            details = client.get_product_info(pid, location_code=loc, on_tick=on_tick)
            prog.progress(100); status.success("✅ Product details loaded & cached")
            st.session_state[cache_key] = {"data": details, "error": None}
        except Exception as e:
            status.error(f"❌ Could not load details: {e}")
            st.session_state[cache_key] = {"data": None, "error": str(e)}
    return st.session_state[cache_key]

def render_image_carousel(images: list, carousel_key: str, show_thumbnails: bool = True):
    """Render an image carousel with optional thumbnail navigation."""
    if not images:
        st.info("No images available")
        return

    # Initialize carousel state
    if carousel_key not in st.session_state:
        st.session_state[carousel_key] = 0

    current_idx = st.session_state[carousel_key]
    current_idx = max(0, min(current_idx, len(images) - 1))
    st.session_state[carousel_key] = current_idx  # Sync back

    # Main image - wrapped in div with CSS class for reliable sizing
    img_url = images[current_idx]
    st.markdown(f'<div class="carousel-img-wrapper"><img src="{img_url}"></div>', unsafe_allow_html=True)

    # Navigation controls
    if len(images) > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Prev", key=f"prev_{carousel_key}", disabled=(current_idx == 0)):
                st.session_state[carousel_key] = current_idx - 1
                st.rerun()
        with col2:
            st.markdown(f"<center><strong>{current_idx + 1} / {len(images)}</strong></center>", unsafe_allow_html=True)
        with col3:
            if st.button("Next ▶", key=f"next_{carousel_key}", disabled=(current_idx >= len(images) - 1)):
                st.session_state[carousel_key] = current_idx + 1
                st.rerun()

        # Thumbnail grid
        if show_thumbnails and len(images) > 1:
            st.markdown("**Quick navigation:**")
            thumb_cols = st.columns(min(len(images), 6))
            for i, img_url in enumerate(images[:6]):
                with thumb_cols[i]:
                    border = "2px solid #ff4b4b" if i == current_idx else "2px solid #ddd"
                    st.markdown(f'''
                        <div style="border: {border}; border-radius: 4px; padding: 2px; cursor: pointer;">
                            <img src="{img_url}" style="width: 100%; height: 50px; object-fit: cover; border-radius: 2px;">
                        </div>
                    ''', unsafe_allow_html=True)
                    if st.button("Select", key=f"thumb_{carousel_key}_{i}", use_container_width=True):
                        st.session_state[carousel_key] = i
                        st.rerun()

def render_highlights(highlights: list, style: str = "chips"):
    """Render product highlights with improved visibility."""
    if not highlights:
        st.write("—")
        return

    if style == "chips":
        chips_html = "".join([f'<span class="highlight-chip">{h}</span>' for h in highlights])
        st.markdown(f'<div style="margin: 10px 0;">{chips_html}</div>', unsafe_allow_html=True)
    else:
        items = "".join([f'<li>{h}</li>' for h in highlights])
        st.markdown(f'<div class="highlight-list"><ul style="margin: 0; padding-left: 20px;">{items}</ul></div>', unsafe_allow_html=True)

def render_sellers(sellers: list, currency_symbol: str = "£"):
    """Render seller comparison cards."""
    if not sellers:
        st.info("No seller data available")
        return

    for seller in sellers[:5]:  # Show top 5 sellers
        price = seller.get("price") or {}
        price_val = price.get("current") or price.get("regular") or seller.get("price")
        seller_name = seller.get("seller") or seller.get("title") or "Unknown"

        st.markdown(f'''
            <div class="seller-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{seller_name}</strong><br>
                        <small style="color: #666;">{seller.get("delivery_info") or ""}</small>
                    </div>
                    <div class="seller-price">{currency_symbol}{price_val:.2f if isinstance(price_val, (int, float)) else price_val}</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

def render_variations(variations: list):
    """Render product variations as badges."""
    if not variations:
        return

    st.markdown("**Available Variations:**")
    badges = []
    for var in variations[:12]:  # Limit to 12
        var_text = var.get("title") or var.get("value") or str(var)
        if isinstance(var_text, str) and len(var_text) < 50:
            badges.append(f'<span class="variation-badge">{var_text}</span>')

    if badges:
        st.markdown(f'<div style="margin: 8px 0;">{"".join(badges)}</div>', unsafe_allow_html=True)

col_search, col_clear = st.columns([3, 1])
with col_search:
    search_clicked = st.button("🔍 Search Products", type="primary")
with col_clear:
    if st.button("🗑️ Clear Results"):
        for key in ["results_df", "keyword", "analysis"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

if search_clicked:
    if not keyword and not uploaded:
        st.warning("Enter a keyword or upload a CSV")
    elif keyword:
        raw, df = search_with_progress(keyword, location_code, depth)
        if df.empty:
            with st.expander("Raw API response"):
                st.json(raw)
            st.warning("No results found.")
        else:
            st.session_state.results_df = df
            st.session_state.keyword = keyword
            st.session_state.analysis = analyze_competitors(df, target_domains)
            st.success(f"Found {len(df)} products.")
    if uploaded:
        bulk = pd.read_csv(uploaded)
        # Deduplicate keywords to avoid redundant API calls
        all_keywords = bulk["keyword"].dropna().astype(str).tolist()
        unique_keywords = list(dict.fromkeys(all_keywords))  # Preserves order, removes dupes
        duplicates_removed = len(all_keywords) - len(unique_keywords)

        if duplicates_removed > 0:
            st.info(f"📋 Removed {duplicates_removed} duplicate keyword(s). Processing {len(unique_keywords)} unique terms.")
        else:
            st.info(f"📋 Processing {len(unique_keywords)} keyword(s)...")

        for i, k in enumerate(unique_keywords, 1):
            st.subheader(f"({i}/{len(unique_keywords)}) {k}")
            raw, dfk = search_with_progress(k, location_code, depth)
            st.dataframe(dfk, use_container_width=True)

        st.success(f"✅ Bulk processing complete! Searched {len(unique_keywords)} keywords.")

if "results_df" in st.session_state:
    df = st.session_state.results_df.copy()
    analysis = st.session_state.analysis

    st.markdown("---")
    st.header(f"Results: {st.session_state.keyword}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Products", analysis.get("total_products", 0))
    c2.metric("Unique Domains", analysis.get("unique_domains", 0))

    # Get the most common currency from the results
    currency_symbol = "£"  # default
    if not df.empty and "currency" in df.columns:
        most_common_currency = df["currency"].mode().iloc[0] if not df["currency"].mode().empty else None
        if most_common_currency:
            currency_map = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "$", "AUD": "$"}
            currency_symbol = currency_map.get(most_common_currency, most_common_currency)

    if analysis.get("avg_price") is not None:
        c3.metric("Avg Price", f"{currency_symbol}{analysis['avg_price']:.2f}")
    if pr := analysis.get("price_range"):
        if pr["min"] is not None and pr["max"] is not None:
            c4.metric("Price Range", f"{currency_symbol}{pr['min']:.0f} – {currency_symbol}{pr['max']:.0f}")

    save_results = st.checkbox("Save these results to local history (SQLite)", value=False)
    if save_results and not df.empty:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect("data/history.db")
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS results(
            ts INTEGER,
            keyword TEXT,
            position INT,
            title TEXT,
            domain TEXT,
            price REAL,
            currency TEXT,
            url TEXT,
            images TEXT,
            description TEXT,
            highlights TEXT,
            rating REAL,
            reviews INT
        )""")
        rows = [
            (int(time.time()), st.session_state.keyword, int(r.get("position") or 0),
             str(r.get("title") or ""), str(r.get("domain") or ""),
             float(r["price"]) if pd.notna(r.get("price")) else None,
             str(r.get("currency") or ""), str(r.get("url") or ""),
             str(r.get("images") or []),  # Store as string representation
             str(r.get("description") or ""),
             str(r.get("highlights") or []),  # Store as string representation
             float(r["rating"]) if pd.notna(r.get("rating")) else None,
             int(r["reviews"]) if pd.notna(r.get("reviews")) else None)
            for r in df.to_dict("records")
        ]
        cur.executemany("INSERT INTO results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        conn.commit(); conn.close()
        st.success("Saved to data/history.db")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🏆 Top Domains", "🎯 Targets", "📋 Full Data", "🔎 Drill-down"])

    with tab1:
        st.subheader("Top 10 Products")

        # Show data extraction stats - check for actual content, not just non-empty strings
        def has_real_content(x):
            if x is None or pd.isna(x) if isinstance(x, float) else False:
                return False
            if isinstance(x, str):
                return len(x.strip()) > 0 and x.strip().lower() not in ('none', 'nan', '')
            if isinstance(x, list):
                return len(x) > 0
            return bool(x)

        desc_count = df["description"].apply(has_real_content).sum() if "description" in df.columns else 0
        img_count = df["images"].apply(lambda x: isinstance(x, list) and len(x) > 0).sum() if "images" in df.columns else 0
        highlights_count = df["highlights"].apply(lambda x: isinstance(x, list) and len(x) > 0).sum() if "highlights" in df.columns else 0

        st.info(f"📊 Data extracted: **{desc_count}/{len(df)}** products with descriptions | **{img_count}/{len(df)}** with images | **{highlights_count}/{len(df)}** with highlights")

        # Calculate title quality for display
        top10 = df.head(10).copy()
        top10["title_quality"] = top10["title"].apply(calculate_title_quality_score)

        # Display enhanced table with description preview
        display_cols = ["position", "title", "domain", "price", "currency", "title_quality", "images_count", "description_preview"]
        available_cols = [col for col in display_cols if col in top10.columns]
        st.dataframe(top10[available_cols], use_container_width=True)

        # Show images and descriptions for each product
        st.markdown("#### Product Details (Top 10)")
        for idx, row in top10.iterrows():
            # Show expander for any product with images OR description OR highlights
            has_images = row.get("images") and len(row["images"]) > 0
            has_desc = row.get("description") and len(str(row.get("description", ""))) > 0
            has_highlights = row.get("highlights") and len(row["highlights"]) > 0

            if has_images or has_desc or has_highlights:
                with st.expander(f"#{int(row['position'])} - {row['title'][:60]}..."):
                    col_left, col_right = st.columns([1, 1])

                    with col_left:
                        # Show description if available
                        if has_desc:
                            st.markdown("**Description:**")
                            st.write(row["description"])

                        # Show highlights with improved styling
                        if has_highlights:
                            st.markdown("**Key Features:**")
                            render_highlights(row["highlights"], style="list")

                    with col_right:
                        # Show images with carousel if available
                        if has_images:
                            st.markdown("**Product Images:**")
                            carousel_key = f"carousel_overview_{int(row['position'])}"
                            render_image_carousel(row["images"], carousel_key, show_thumbnails=True)

        st.markdown("---")
        st.subheader("Domain Frequency")
        freq = pd.DataFrame.from_dict(analysis["domain_frequency"], orient="index", columns=["count"]).head(10)
        st.bar_chart(freq)

    with tab2:
        st.subheader("Domain stats")
        stats = df.groupby("domain").agg(
            Appearances=("position", "count"),
            Avg_Position=("position", "mean"),
            Best_Position=("position", "min"),
            Avg_Price=("price", "mean"),
            Avg_Rating=("rating", "mean"),
        ).round(2).sort_values("Appearances", ascending=False)
        st.dataframe(stats, use_container_width=True)

    with tab3:
        if target_domains and "target_domains" in analysis:
            for dom, s in analysis["target_domains"].items():
                with st.expander(dom):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Appearances", s["appearances"])
                    if s["avg_position"] is not None:
                        c2.metric("Avg Position", f"{s['avg_position']:.1f}")
                    if s["best_position"] is not None:
                        c3.metric("Best Position", s["best_position"])
                    if s["products"]:
                        sub = pd.DataFrame(s["products"])[["position", "title", "price", "url"]]
                        st.dataframe(sub, use_container_width=True)
        else:
            st.info("Add target domains to see details.")

    with tab4:
        df["title_quality"] = df["title"].apply(calculate_title_quality_score)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False), file_name=f"shopping_results_{st.session_state.keyword}.csv", mime="text/csv")

    with tab5:
        st.subheader("Inspect a product")
        if df.empty:
            st.info("Run a search first.")
        else:
            display = df.apply(lambda r: f"[{int(r['position']) if pd.notna(r['position']) else '-'}] {r['title']}", axis=1)
            choice = st.selectbox("Pick a product", options=display.tolist())
            idx = display.tolist().index(choice)
            pid = df.iloc[idx]["product_id"]
            search_data = df.iloc[idx]

            # Helper to extract details from API response
            def _extract_details(d):
                items = (((d or {}).get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []
                return items[0] if items else {}

            # Validate product_id and fetch with caching
            if not pid or pd.isna(pid):
                st.warning("This product has no product_id. Showing search results data only.")
                details = None
                item = {}
            else:
                # Use cached API call - prevents refetch on carousel navigation
                cached = get_cached_product_info(str(pid), location_code)
                if cached["error"]:
                    st.error(f"Could not fetch details: {cached['error']}")
                details = cached["data"]
                item = _extract_details(details)

            # Display options
            col_opts = st.columns(4)
            with col_opts[0]:
                show_desc = st.toggle("Description", value=True)
            with col_opts[1]:
                show_high = st.toggle("Highlights", value=True)
            with col_opts[2]:
                show_sellers = st.toggle("Compare Sellers", value=True)
            with col_opts[3]:
                show_raw = st.toggle("Raw JSON", value=False)

            # Main content layout
            left, right = st.columns([2, 1])

            with left:
                # Basic product info
                st.markdown("### Product Info")
                title = item.get("title") or search_data.get("title")
                st.markdown(f"**{title}**")

                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    st.write("**Seller:**", item.get("seller") or item.get("domain") or search_data.get("domain"))
                    price_val = item.get("price") or search_data.get("price")
                    curr = item.get("currency") or search_data.get("currency") or ""
                    if price_val:
                        st.markdown(f"**Price:** <span style='font-size: 1.3em; color: #2e7d32; font-weight: bold;'>{currency_symbol}{price_val}</span>", unsafe_allow_html=True)
                with info_col2:
                    rating_val = (item.get("product_rating") or {}).get("value") or search_data.get("rating")
                    reviews_val = (item.get("product_rating") or {}).get("votes_count") or item.get("reviews_count") or search_data.get("reviews")
                    if rating_val:
                        stars = "★" * int(float(rating_val)) + "☆" * (5 - int(float(rating_val)))
                        st.markdown(f"**Rating:** {stars} ({rating_val})")
                    if reviews_val:
                        st.write(f"**Reviews:** {reviews_val:,}" if isinstance(reviews_val, int) else f"**Reviews:** {reviews_val}")

                # Product variations (colors, sizes, etc.)
                variations = item.get("product_variations") or item.get("variations") or []
                if variations:
                    st.markdown("---")
                    render_variations(variations)

            with right:
                # Image carousel with thumbnails
                imgs = item.get("product_images") or item.get("images") or search_data.get("images") or []
                if imgs:
                    carousel_key = f"carousel_drilldown_{pid or idx}"
                    render_image_carousel(imgs, carousel_key, show_thumbnails=True)
                else:
                    st.info("No images available")

            # Description section
            if show_desc:
                st.markdown("---")
                st.markdown("### Description")
                desc = item.get("description") or item.get("product_description") or search_data.get("description")
                if desc:
                    st.write(desc)
                else:
                    st.write("No description available")

            # Highlights section with improved styling
            if show_high:
                st.markdown("---")
                st.markdown("### Key Features & Highlights")
                feats = item.get("product_highlights") or item.get("highlights") or item.get("features") or search_data.get("highlights") or []
                if isinstance(feats, dict):
                    feats = [f"{k}: {v}" for k, v in feats.items()]
                render_highlights(feats, style="chips")

            # Sellers comparison section
            if show_sellers:
                st.markdown("---")
                st.markdown("### Price Comparison - All Sellers")
                sellers = item.get("sellers") or item.get("offers") or []
                if sellers:
                    render_sellers(sellers, currency_symbol)
                else:
                    st.info("No multi-seller data available for this product")

            # Raw JSON debug
            if show_raw and details:
                st.markdown("---")
                st.markdown("### Raw API Response")
                st.json(details)

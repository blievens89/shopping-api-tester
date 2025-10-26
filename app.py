import os, io, time, sqlite3
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from api.dataforseo import DataForSEOClient, DataForSEOError
from utils.analysis import parse_shopping_results, analyze_competitors, calculate_title_quality_score

load_dotenv()

st.set_page_config(page_title="Google Shopping Competitive Analysis", page_icon="🛍️", layout="wide")
st.title("Google Shopping Competitive Analysis")
st.caption("DataForSEO → Streamlit tester")

login = st.secrets.get("DATAFORSEO_LOGIN", os.getenv("DATAFORSEO_LOGIN"))
password = st.secrets.get("DATAFORSEO_PASSWORD", os.getenv("DATAFORSEO_PASSWORD"))

st.sidebar.header("Configuration")
if not login or not password:
    st.sidebar.error("Add DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD to secrets or .env")
    st.stop()

try:
    client = DataForSEOClient(login, password)
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
        status.info(f"Polling DataForSEO… {elapsed}s / {maximum}s")
    data = client.search_products(keyword=k, location_code=loc, depth=dep, on_tick=on_tick)
    prog.progress(100); status.success("Results received")
    df = parse_shopping_results(data)
    return data, df

if st.button("🔍 Search Products", type="primary"):
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
        for k in bulk["keyword"].dropna().astype(str).tolist():
            st.subheader(k)
            raw, dfk = search_with_progress(k, location_code, depth)
            st.dataframe(dfk, use_container_width=True)

if "results_df" in st.session_state:
    df = st.session_state.results_df.copy()
    analysis = st.session_state.analysis

    st.markdown("---")
    st.header(f"Results: {st.session_state.keyword}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Products", analysis.get("total_products", 0))
    c2.metric("Unique Domains", analysis.get("unique_domains", 0))
    if analysis.get("avg_price") is not None:
        c3.metric("Avg Price", f"£{analysis['avg_price']:.2f}")
    if pr := analysis.get("price_range"):
        if pr["min"] is not None and pr["max"] is not None:
            c4.metric("Price Range", f"£{pr['min']:.0f} – £{pr['max']:.0f}")

    save_results = st.checkbox("Save these results to local history (SQLite)", value=False)
    if save_results and not df.empty:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect("data/history.db")
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS results(
            ts INTEGER, keyword TEXT, position INT, title TEXT, domain TEXT, price REAL, currency TEXT, url TEXT
        )""")
        rows = [
            (int(time.time()), st.session_state.keyword, int(r.get("position") or 0),
             str(r.get("title") or ""), str(r.get("domain") or ""), float(r["price"]) if pd.notna(r.get("price")) else None,
             str(r.get("currency") or ""), str(r.get("url") or ""))
            for r in df.to_dict("records")
        ]
        cur.executemany("INSERT INTO results VALUES(?,?,?,?,?,?,?,?)", rows)
        conn.commit(); conn.close()
        st.success("Saved to data/history.db")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🏆 Top Domains", "🎯 Targets", "📋 Full Data", "🔎 Drill-down"])

    with tab1:
        st.subheader("Top 10 Products")
        st.dataframe(df[["position", "title", "domain", "price", "images_count", "has_description", "has_highlights"]].head(10), use_container_width=True)

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

            p2 = st.progress(0); s2 = st.empty()
            def tick2(el, mx):
                pct = min(99, int((el/max(1,mx))*100)); p2.progress(pct); s2.info(f"Fetching details… {el}s / {mx}s")

            try:
                details = client.get_product_info(pid, on_tick=tick2)
                p2.progress(100); s2.success("Details received")
            except Exception as e:
                s2.error(f"Detail fetch failed: {e}")
                details = None

            def _extract_details(d):
                items = (((d or {}).get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or []
                return items[0] if items else {}
            item = _extract_details(details)

            show_desc = st.toggle("Show product description", value=False)
            show_high = st.toggle("Show product highlights/features", value=False)
            max_imgs = st.slider("Show up to N images", min_value=0, max_value=10, value=4)

            left, right = st.columns([2,1])
            with left:
                st.write("Title:", item.get("title") or df.iloc[idx]["title"])
                st.write("Seller/Domain:", item.get("seller") or item.get("domain") or df.iloc[idx]["domain"])
                st.write("Price:", item.get("price") or df.iloc[idx]["price"])
                st.write("Currency:", item.get("currency") or df.iloc[idx]["currency"])
                st.write("Rating:", (item.get("product_rating") or {}).get("value"))
                st.write("Reviews:", (item.get("product_rating") or {}).get("votes_count") or item.get("reviews_count"))

            with right:
                imgs = item.get("product_images") or item.get("images") or []
                if max_imgs and imgs:
                    st.image(imgs[:max_imgs], use_column_width=True)

            if show_desc:
                st.markdown("### Description")
                st.write(item.get("description") or item.get("product_description") or "—")

            if show_high:
                st.markdown("### Highlights / Features")
                feats = item.get("product_highlights") or item.get("highlights") or item.get("features") or []
                if isinstance(feats, dict):
                    feats = [f"{k}: {v}" for k,v in feats.items()]
                if feats:
                    for f in feats:
                        st.write("•", f)
                else:
                    st.write("—")

            st.markdown("### Raw details (debug)")
            st.json(details or {})

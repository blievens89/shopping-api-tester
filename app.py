import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from api.dataforseo import DataForSEOClient, DataForSEOError
from utils.analysis import parse_shopping_results, analyze_competitors, calculate_title_quality_score

load_dotenv()

st.set_page_config(page_title="Google Shopping Competitive Analysis", page_icon="🛍️", layout="wide")
st.title("🛍️ Google Shopping Competitive Analysis")
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

@st.cache_data(show_spinner=False, ttl=3600)
def run_search(k: str, loc: int, dep: int):
    data = client.search_products(keyword=k, location_code=loc, depth=dep)
    df = parse_shopping_results(data)
    return data, df

if st.button("🔍 Search Products", type="primary"):
    if not keyword:
        st.warning("Enter a keyword")
    else:
        with st.spinner(f"Searching '{keyword}' …"):
            try:
                raw, df = run_search(keyword, location_code, depth)
                if df.empty:
                    with st.expander("Raw API response"):
                        st.json(raw)
                    st.warning("No results found.")
                else:
                    st.session_state.results_df = df
                    st.session_state.keyword = keyword
                    st.session_state.analysis = analyze_competitors(df, target_domains)
                    st.success(f"Found {len(df)} products.")
            except Exception as e:
                st.error(f"API error: {e}")

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

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🏆 Top Domains", "🎯 Targets", "📋 Full Data"])

    with tab1:
        st.subheader("Top 10 Products")
        st.dataframe(df[["position", "title", "domain", "price"]].head(10), use_container_width=True)

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
        st.download_button("📥 Download CSV", df.to_csv(index=False), file_name=f"shopping_results_{st.session_state.keyword}.csv", mime="text/csv")

st.markdown("---")
st.caption("Built with DataForSEO & Streamlit")

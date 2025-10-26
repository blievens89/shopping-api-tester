from typing import Dict, List
import pandas as pd

def _safe_price(item):
    p = item.get("price")
    if isinstance(p, dict):
        return p.get("current"), p.get("currency")
    if isinstance(p, (int, float)):
        return float(p), item.get("currency")
    return None, item.get("currency")

def parse_shopping_results(api_response: Dict) -> pd.DataFrame:
    if not api_response or "tasks" not in api_response:
        return pd.DataFrame()
    tasks = api_response.get("tasks", [])
    if not tasks:
        return pd.DataFrame()
    results = tasks[0].get("result") or []
    if not results:
        return pd.DataFrame()
    items = results[0].get("items") or []
    accept = {"google_shopping_product", "shopping_product", "product", "google_shopping_serp"}
    out = []
    for it in items:
        if it.get("type") not in accept:
            continue
        price, currency = _safe_price(it)
        url = it.get("url") or it.get("shopping_url")
        pid = it.get("product_id") or it.get("data_docid") or it.get("gid")
        out.append({
            "position": it.get("rank_absolute"),
            "title": it.get("title"),
            "domain": it.get("domain") or it.get("seller") or it.get("shop_name"),
            "price": price,
            "currency": currency,
            "rating": (it.get("product_rating") or {}).get("value"),
            "reviews": it.get("votes_count") or it.get("reviews_count"),
            "product_id": pid,
            "url": url,
            "images_count": len(it.get("product_images") or it.get("images") or []),
            "has_description": bool(it.get("description") or it.get("product_description")),
            "has_highlights": bool(it.get("product_highlights") or it.get("highlights") or it.get("features")),
        })
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df["domain"] = df["domain"].astype(str).str.replace(r"^https?://", "", regex=True).str.split("/").str[0]
    if "position" in df:
        df = df.sort_values("position", na_position="last").reset_index(drop=True)
    return df

def analyze_competitors(df: pd.DataFrame, target_domains: List[str] | None = None) -> Dict:
    if df.empty:
        return {}
    analysis = {
        "total_products": int(len(df)),
        "unique_domains": int(df["domain"].nunique()),
        "domain_frequency": df["domain"].value_counts().to_dict(),
        "avg_price": float(df["price"].mean()) if "price" in df and df["price"].notna().any() else None,
        "price_range": {
            "min": float(df["price"].min()) if "price" in df and df["price"].notna().any() else None,
            "max": float(df["price"].max()) if "price" in df and df["price"].notna().any() else None
        }
    }
    if target_domains:
        td = {}
        for d in target_domains:
            sub = df[df["domain"].str.lower() == d.lower()]
            td[d] = {
                "appearances": int(len(sub)),
                "avg_position": float(sub["position"].mean()) if not sub.empty else None,
                "best_position": int(sub["position"].min()) if not sub.empty else None,
                "products": sub.to_dict("records") if not sub.empty else []
            }
        analysis["target_domains"] = td
    return analysis

def calculate_title_quality_score(title: str) -> int:
    if not title:
        return 0
    score = 0
    if 70 <= len(title) <= 150:
        score += 30
    elif len(title) >= 50:
        score += 15
    wc = len(title.split())
    if wc >= 8:
        score += 25
    elif wc >= 5:
        score += 15
    attrs = ["size", "color", "colour", "cm", "mm", "inch", "ml", "l ", "kg", " g"]
    if any(k in title.lower() for k in attrs):
        score += 20
    caps_ratio = sum(1 for c in title if c.isupper()) / max(1, len(title))
    if caps_ratio < 0.5:
        score += 15
    if title.split()[0][:1].isupper():
        score += 10
    return min(score, 100)

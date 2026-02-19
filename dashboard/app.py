'''app.py

Streamlit backend analytics dashboard for the AURA SQLite database.

Feb 2026
'''
import os
import json
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="AURA Analytics", layout="wide")

DB_PATH = os.getenv('DB_PATH', '/app/data/aura.db')

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=300)
def load_articles():
    conn = get_conn()
    return pd.read_sql("SELECT * FROM articles", conn)

@st.cache_data(ttl=300)
def load_keyword_count():
    conn = get_conn()
    row = pd.read_sql("SELECT COUNT(*) as cnt FROM keywords", conn)
    return int(row["cnt"].iloc[0])


arxiv_cats = {
    # "cs.AI": "Artificial Intelligence",
    "cs.CE": "Computational Engineering",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision",
    "cs.CY": "Computers and Society",
    "cs.DB": "Databases",
    "cs.DC": "Distributed Computing",
    "cs.ET": "Emerging Technologies",
    "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval",
    # "cs.LG": "Machine Learning",
    "cs.MA": "Multiagent Systems",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.PF": "Performance",
    "cs.RO": "Robotics",
    "cs.SE": "Software Engineering",
}

# load data from sqlite db
df = load_articles()
total_keywords = load_keyword_count()

st.title("AURA Database Analytics")

col1, col2, col3 = st.columns(3)
col1.metric("Total Papers", f"{len(df):,}")
col2.metric("Total Keywords", f"{total_keywords:,}")
col3.metric("Columns per Paper", len(df.columns))

st.divider()

# daily metrics graph
st.subheader("Daily Scraping Activity")

# parse date_scraped to date-only for grouping
df["scrape_date"] = pd.to_datetime(df["date_scraped"], errors="coerce").dt.date

# count keywords per article from the articles.keywords json column
def count_kw(val):
    if not val:
        return 0
    try:
        return len(json.loads(val))
    except (json.JSONDecodeError, TypeError):
        return 0

df["kw_count"] = df["keywords"].apply(count_kw)

# group by day
daily = (
    df.dropna(subset=["scrape_date"])
    .groupby("scrape_date")
    .agg(papers=("article_id", "count"), keywords=("kw_count", "sum"))
    .reset_index()
)
daily["scrape_date"] = pd.to_datetime(daily["scrape_date"])
daily = daily.sort_values("scrape_date")

# timeframe selector
window = st.radio(
    "Time window",
    ["1 month", "3 months", "6 months"],
    index=1,
    horizontal=True,
)
months = {"1 month": 1, "3 months": 3, "6 months": 6}[window]
cutoff = datetime.now() - timedelta(days=months * 30)
daily_filtered = daily[daily["scrape_date"] >= cutoff].copy()

if daily_filtered.empty:
    st.info("No scraping data in the selected window.")
else:
    daily_filtered = daily_filtered.set_index("scrape_date")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.caption("Papers scraped per day")
        st.bar_chart(daily_filtered["papers"], color="#ff6900")

    with chart_col2:
        st.caption("Keywords extracted per day")
        st.bar_chart(daily_filtered["keywords"], color="#6a008e")

st.divider()

st.subheader("arXiv Category Distribution")
# parse json tag arrays
all_tags = {}
for raw in df["tags"].dropna():
    try:
        tags = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        continue
    for tag in tags:
        all_tags[tag] = all_tags.get(tag, 0) + 1

# split into known arXiv CS categories and other
labeled_tags = {}
for tag, count in all_tags.items():
    label = arxiv_cats.get(tag)
    if label:
        labeled_tags[label] = labeled_tags.get(label, 0) + count

df_tags = (
    pd.DataFrame({"category": list(labeled_tags.keys()), "count": list(labeled_tags.values())})
    .sort_values("count", ascending=True)
)

if not df_tags.empty:
    st.bar_chart(df_tags.set_index("category"), color="#ff6900", horizontal=True)
else:
    st.info("No tag data available.")

st.divider()

# raw data preview
with st.expander("Raw articles table (first 50 rows)"):
    preview_cols = ["article_id", "title", "date_submitted", "date_scraped", "tags", "keywords"]
    st.dataframe(df[preview_cols].head(50))

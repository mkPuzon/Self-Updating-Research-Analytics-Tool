'''app.py

A Streamlit front end for the AURA PostgreSQL db.

Nov 2025
'''
import os
import sqlite3
import pandas as pd
import streamlit as st

def get_conn():
    try:
        db_path = os.getenv('DB_PATH', 'app/data/db.sqlite3')
        conn = sqlite3.connect(db_path) 
        return conn
    except Exception as e:
        print(f"PG connection error: {e}")
        return None
    
all_cs_cats = {
    "cs.AI": "Artificial Intelligence",
    "cs.AR": "Hardware Architecture",
    "cs.CC": "Computational Complexity",
    "cs.CE": "Computational Engineering, Finance, and Science",
    "cs.CG": "Computational Geometry",
    "cs.CL": "Computation and Language",
    "cs.CR": "Cryptography and Security",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.CY": "Computers and Society",
    "cs.DB": "Databases",
    "cs.DC": "Distributed, Parallel, and Cluster Computing",
    "cs.DL": "Digital Libraries",
    "cs.DM": "Discrete Mathematics",
    "cs.DS": "Data Structures and Algorithms",
    "cs.ET": "Emerging Technologies",
    "cs.FL": "Formal Languages and Automata Theory",
    "cs.GL": "General Literature",
    "cs.GR": "Graphics",
    "cs.GT": "Computer Science and Game Theory",
    "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval",
    "cs.IT": "Information Theory",
    "cs.LG": "Machine Learning",
    "cs.LO": "Logic in Computer Science",
    "cs.MA": "Multiagent Systems",
    "cs.MM": "Multimedia",
    "cs.MS": "Mathematical Software",
    "cs.NA": "Numerical Analysis",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.NI": "Networking and Internet Architecture",
    "cs.OH": "Other Computer Science",
    "cs.OS": "Operating Systems",
    "cs.PF": "Performance",
    "cs.PL": "Programming Languages",
    "cs.RO": "Robotics",
    "cs.SC": "Symbolic Computation",
    "cs.SD": "Sound",
    "cs.SE": "Software Engineering",
    "cs.SI": "Social and Information Networks",
    "cs.SY": "Systems and Control"
}

arxiv_cats = {
    "cs.AI": "Artificial Intelligence",
    "cs.CE": "Computational Engineering, Finance, and Science",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.CY": "Computers and Society",
    "cs.DB": "Databases",
    "cs.DC": "Distributed, Parallel, and Cluster Computing",
    "cs.ET": "Emerging Technologies",
    "cs.HC": "Human-Computer Interaction",
    "cs.LG": "Machine Learning",
    "cs.MA": "Multiagent Systems",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.PF": "Performance",
    "cs.RO": "Robotics",
}

colors = [
    '#ff9400', '#ff8b00', '#ff8300',
    '#ff6900', '#ff6100', '#ff5800',
    '#ff3f00', '#ff3600', '#ff2e00',
    '#ff1400', '#ff0c00', '#ff0300',
    '#ea0014', '#e2001c', '#da0024',
    '#c2003b', '#ba0042', '#b2004a',
    '#9a0061', '#920068', '#8a0070',
    '#820077', '#7a007f', '#720087', '#6a008e', '#800080'
]


conn = get_conn()
df = conn.query('SELECT * FROM articles;', ttl="0")

st.title(body="AURA Database Analytics")

with st.sidebar:
    st.title("Options")
    # TODO add filtering by dates
    st.checkbox(label="Toggle Graph", value=False)

st.subheader(body="STATISTICS", divider="orange")
st.text(body=f"PostgreSQL database currently contains {df.shape[0]} total papers, each with the following features:")
st.text(body=f"{[col for col in df.columns]}")

all_tags = {}
for row in df.itertuples():
    for tag in row.tags:
        if all_tags.get(tag):
            all_tags[tag] += 1
        else:
            all_tags[tag] = 1
            
labeled_tags = {}
other_tags = {}
for tag in all_tags:
    if arxiv_cats.get(tag):
        labeled_tags[arxiv_cats[tag]] = all_tags[tag]
    else:
        other_tags[tag] = other_tags.get(tag, 0) + 1

df_tags = pd.DataFrame({
    "tag": list(labeled_tags.keys()),
    "count": list(labeled_tags.values())
})

bar_colors = colors[: len(df_tags)]


if __name__ == "__main__":
    pass
import streamlit as st

# Apply a monospaced, dark-themed font suitable for a threat-intel dashboard
font_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: #EAEAEA !important;
    background-color: #0E1117 !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Share Tech Mono', monospace !important;
    color: #00ffcc !important;
}
</style>
"""
st.markdown(font_css, unsafe_allow_html=True)

import ast
import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import requests
import streamlit.components.v1 as components
import umap.umap_ as umap
from dotenv import load_dotenv
from google import genai
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from settings import settings

# ----------------- Paths ------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shodan_data_path = os.path.join(project_root, "data", "shodan", "shodan_data.csv")
cve_db_path = os.path.join(project_root, "data", "shodan", "cvedb_shodan.csv")
attack_matrix_path = os.path.join(project_root, "data", "mitre", "enterprise-attack-v17.1.xlsx")
news_data_path = os.path.join(project_root, "data", "news_data.json")

GEMINI_API_KEY = settings.GEMINI_API_KEY

def summarize_with_gemini(prompt):
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text

@st.cache_data
def load_news_data():
    with open(news_data_path, "r") as f:
        news_list = json.load(f)
    df_news = pd.DataFrame(news_list)
    df_news["date"] = pd.to_datetime(df_news["date"])
    df_news["date_str"] = df_news["date"].dt.strftime("%Y-%m-%d")
    return df_news


# ----------------- Data load & preprocessing -----------------
@st.cache_data
def load_data():
    df_shodan = pd.read_csv(shodan_data_path)
    df_shodan = df_shodan.dropna(subset=['latitude', 'longitude'])
    df_shodan['cve_list'] = df_shodan['cve_list'].apply(eval)
    df_shodan['region_full'] = df_shodan['country_code'] + " - " + df_shodan['region_code']

    df_cvedb = pd.read_csv(cve_db_path)
    df_cvedb['mitre_match'] = df_cvedb['mitre_match'].apply(ast.literal_eval)
    df_cvedb['technique_id'] = df_cvedb['mitre_match'].apply(lambda d: d.get('id'))
    df_cvedb['similarity'] = df_cvedb['mitre_match'].apply(lambda d: d.get('score'))
    df_cvedb = df_cvedb.dropna(subset=['cvss', 'technique_id', 'similarity'])

    mitre_df = pd.read_excel(attack_matrix_path)
    for col in mitre_df.columns:
        if col.strip().lower() in ['id', 'technique id']:
            mitre_df.rename(columns={col: 'technique_id'}, inplace=True)
        elif col.strip().lower() in ['name', 'technique name']:
            mitre_df.rename(columns={col: 'technique_name'}, inplace=True)
        elif col.strip().lower() == 'description':
            mitre_df.rename(columns={col: 'description'}, inplace=True)

    mitre_df = mitre_df[['technique_id', 'technique_name', 'description']].dropna()
    df_cvedb = df_cvedb.merge(mitre_df, on='technique_id', how='left')

    return df_shodan, df_cvedb, mitre_df

# ----------------- Sidebar -----------------
st.sidebar.title("Dashboard Menu")

# Session state
if "menu_option" not in st.session_state:
    st.session_state.menu_option = "Group Analysis"

button_style = """
<style>
.sidebar-button {
    display: block;
    width: 100%;
    padding: 0.5rem;
    text-align: center;
    font-size: 16px;
    margin-bottom: 8px;
    background-color: #f0f2f6;
    border: 1px solid #ccc;
    border-radius: 5px;
    cursor: pointer;
}
.sidebar-button:hover {
    background-color: #e0e0e0;
}
</style>
"""
st.markdown(button_style, unsafe_allow_html=True)

# Menu buttons
if st.sidebar.button("Group Analysis", key="btn_group"):
    st.session_state.menu_option = "Group Analysis"
if st.sidebar.button("TTP Analysis", key="btn_cluster"):
    st.session_state.menu_option = "TTP Analysis"
if st.sidebar.button("News Summary Slides", key="btn_news"):
    st.session_state.menu_option = "News Summary Slides"

menu_option = st.session_state.menu_option

# ----------------- Load data -----------------
df_shodan, df_cvedb, mitre_df = load_data()

cve_to_ttp = df_cvedb.set_index('cve_id')['technique_name'].to_dict()
df_shodan['cve_summary'] = df_shodan['cve_list'].apply(lambda cves: ', '.join(cves[:3]) + ('...' if len(cves) > 3 else ''))
df_shodan['ttp_summary'] = df_shodan['cve_list'].apply(
    lambda cves: ', '.join({cve_to_ttp[cve] for cve in cves if cve in cve_to_ttp})
)
df_shodan['tooltip_info'] = df_shodan.apply(
    lambda row: f"Group: {row['group']}\nDomain: {row['domain']}\nCVE: {row['cve_summary']}\nTTP: {row['ttp_summary']}", axis=1
)

# ----------------- Group Analysis -----------------
if menu_option == "Group Analysis":
    st.title("Shodan-based Threat Analysis — by Group")

    group_list = sorted(df_shodan['group'].dropna().unique())
    selected_group = st.selectbox("Select group to analyze", group_list)
    group_df = df_shodan[df_shodan['group'] == selected_group]
    group_cves = sum(group_df['cve_list'], [])
    group_cvedb = df_cvedb[df_cvedb['cve_id'].isin(group_cves)].copy()

    st.subheader("Server Locations and Threat Info")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=group_df,
        get_position='[longitude, latitude]',
        get_fill_color='[200, 30, 0, 160]',
        get_radius=50000,
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=group_df['latitude'].mean(),
        longitude=group_df['longitude'].mean(),
        zoom=2,
        pitch=0
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{tooltip_info}"}
    )
    st.pydeck_chart(r)

    st.subheader("Server Count by Region")
    region_count = group_df['region_full'].value_counts().reset_index()
    region_count.columns = ['region_full', 'server_count']
    st.plotly_chart(px.bar(region_count, x='region_full', y='server_count'), use_container_width=True)

    st.subheader("ATT&CK Technique Distribution (by TTP ID)")
    tech_count = group_cvedb.groupby(['technique_id', 'technique_name', 'description']).size().reset_index(name='count')
    fig = px.bar(
        tech_count,
        x='technique_id',
        y='count',
        hover_data=['technique_name'],
        title=f"ATT&CK Technique Matches for {selected_group} (by TTP ID)",
        labels={'technique_id': 'TTP ID', 'count': 'Matching Count'}
    )
    fig.update_traces(
        marker_color='indianred',
        hovertemplate='<b>TTP ID:</b> %{x}<br><b>Count:</b> %{y}<br><b>Name:</b> %{customdata[0]}'
    )
    st.plotly_chart(fig, use_container_width=True)

# ----------------- TTP Analysis (clustering) -----------------
elif menu_option == "TTP Analysis":
    st.title("Shodan-based Threat Analysis — TTP Clustering")

    tech_pivot = (
        df_shodan.explode('cve_list')
        .merge(df_cvedb[['cve_id', 'technique_id']], left_on='cve_list', right_on='cve_id')
        .groupby(['group', 'technique_id']).size()
        .unstack(fill_value=0)
    )
    scaler = StandardScaler()
    tech_scaled = scaler.fit_transform(tech_pivot)

    distortions, silhouette_scores = [], []
    best_k, best_score = 2, -1
    K = range(2, min(11, len(tech_pivot)))
    for k in K:
        kmeans_model = KMeans(n_clusters=k, random_state=42).fit(tech_scaled)
        distortions.append(kmeans_model.inertia_)
        score = silhouette_score(tech_scaled, kmeans_model.labels_)
        silhouette_scores.append(score)
        if score > best_score:
            best_score, best_k = score, k

    if st.sidebar.checkbox("Show Elbow Curve"):
        st.plotly_chart(px.line(x=list(K), y=distortions, markers=True, title="Elbow Curve"))
        st.plotly_chart(px.line(x=list(K), y=silhouette_scores, markers=True, title="Silhouette Score"))

    st.sidebar.markdown(f"**Auto-selected number of clusters: {best_k}**")
    kmeans = KMeans(n_clusters=best_k, random_state=42)
    cluster_labels = kmeans.fit_predict(tech_scaled)
    tech_pivot['cluster'] = cluster_labels

    reducer = umap.UMAP(random_state=42)
    embedding = reducer.fit_transform(tech_scaled)
    tech_pivot['umap_x'] = embedding[:, 0]
    tech_pivot['umap_y'] = embedding[:, 1]

    tech_pivot_reset = tech_pivot.reset_index()

    st.subheader("Group Positions by Cluster (UMAP)")
    fig_umap = px.scatter(
        tech_pivot_reset,
        x='umap_x',
        y='umap_y',
        color='cluster',
        hover_data=['group'],
    )
    st.plotly_chart(fig_umap)

    df_shodan_clustered = df_shodan.merge(tech_pivot[['cluster']].reset_index(), on='group', how='left')
    selected_clusters = st.multiselect(
        "Select clusters to analyze",
        sorted(df_shodan_clustered['cluster'].dropna().unique()),
        default=sorted(df_shodan_clustered['cluster'].dropna().unique())
    )

    st.subheader("Technique Distribution by Cluster")
    df_exploded = df_shodan_clustered[df_shodan_clustered['cluster'].isin(selected_clusters)].explode('cve_list')
    merged = df_exploded.merge(df_cvedb[['cve_id', 'technique_id']], left_on='cve_list', right_on='cve_id')
    merged = merged.merge(mitre_df[['technique_id', 'technique_name', 'description']], on='technique_id', how='left')
    tech_count = merged.groupby(['cluster', 'technique_id', 'technique_name', 'description']).size().reset_index(name='count')
    fig_tech = px.bar(tech_count, x='technique_id', y='count', color='cluster', facet_col='cluster', hover_data=['technique_name'])
    st.plotly_chart(fig_tech, use_container_width=True)

    st.subheader("Cluster-wise TTP Summary (Gemini)")

    top_ttps = tech_count.groupby('cluster').apply(lambda d: d.sort_values('count', ascending=False).head(5)).reset_index(drop=True)

    for clus in sorted(top_ttps['cluster'].unique()):
        st.markdown(f"### Cluster {clus}")
        top_df = top_ttps[top_ttps['cluster'] == clus]

        description_text = ". ".join(
            f"{row['technique_name']} ({row['technique_id']}): {row['description']}" for _, row in top_df.iterrows()
        )

        prompt = f"""
Below are descriptions of MITRE ATT&CK TTPs that frequently appear in cluster {clus}:

{description_text}

Summarize the cluster's likely threat behavior:
- Which attack phases are represented (e.g., initial access, lateral movement)
- What the characteristic TTP combination implies
- Example ransomware groups if relevant

Return a concise analytical summary.
        """

        if st.button(f"Generate summary with Gemini — Cluster {clus}", key=f"gemini_btn_{clus}"):
            with st.spinner("Generating summary with Gemini..."):
                try:
                    summary = summarize_with_gemini(prompt)
                    st.success("Summary generated")
                    st.markdown(f"**LLM Analysis:**\n\n{summary}")
                except Exception as e:
                    st.error(f"Gemini API call failed: {e}")
                    st.markdown("### Fallback: TTP Descriptions")
                    for _, row in top_df.iterrows():
                        st.markdown(f"- **{row['technique_name']} ({row['technique_id']})**: {row['description']}")

    st.subheader("Top TTP Radar by Cluster")
    top_ttp_ids = tech_count.groupby('technique_id')['count'].sum().nlargest(8).index.tolist()
    pivot_radar = tech_count[tech_count['technique_id'].isin(top_ttp_ids)].pivot(index='cluster', columns='technique_id', values='count').fillna(0)
    fig_radar = go.Figure()
    for cluster in pivot_radar.index:
        fig_radar.add_trace(go.Scatterpolar(
            r=pivot_radar.loc[cluster].values,
            theta=top_ttp_ids,
            fill='toself',
            name=f'Cluster {cluster}'
        ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), title="Radar Chart of TTPs")
    st.plotly_chart(fig_radar)

    with st.expander("Full TTP Description Table"):
        st.dataframe(mitre_df[['technique_id', 'technique_name', 'description']].drop_duplicates().sort_values('technique_id'))

# ----------------- News slides -----------------
elif menu_option == "News Summary Slides":
    st.title("News Summary Slides")

    news_data_path = os.path.join(project_root, "data", "news_data.json")

    @st.cache_data
    def load_news_data():
        with open(news_data_path, "r") as f:
            news_list = json.load(f)
        df_news = pd.DataFrame(news_list)
        df_news["date"] = pd.to_datetime(df_news["date"])
        df_news["date_str"] = df_news["date"].dt.strftime("%Y-%m-%d")
        return df_news

    import streamlit.components.v1 as components

    df_news = load_news_data()

    if "d_idx" not in st.session_state:
        st.session_state.d_idx = 0
    if "n_idx" not in st.session_state:
        st.session_state.n_idx = 0

    dates = sorted(df_news["date_str"].unique())
    sel_date = st.sidebar.selectbox("Date", dates, index=st.session_state.d_idx)
    if sel_date != dates[st.session_state.d_idx]:
        st.session_state.d_idx = dates.index(sel_date)
        st.session_state.n_idx = 0

    c1, _, c2 = st.columns([1, 6, 1])
    with c1:
        if st.button("Previous date"):
            st.session_state.d_idx = max(0, st.session_state.d_idx - 1)
            st.session_state.n_idx = 0
    with c2:
        if st.button("Next date"):
            st.session_state.d_idx = min(len(dates) - 1, st.session_state.d_idx + 1)
            st.session_state.n_idx = 0

    today = dates[st.session_state.d_idx]
    st.header(today)

    daily = df_news[df_news["date_str"] == today].reset_index(drop=True)
    if daily.empty:
        st.info("No news for this date.")
    else:
        p1, _, p2 = st.columns([1, 6, 1])
        with p1:
            if st.button("Previous article"):
                st.session_state.n_idx = (st.session_state.n_idx - 1) % len(daily)
        with p2:
            if st.button("Next article"):
                st.session_state.n_idx = (st.session_state.n_idx + 1) % len(daily)

        rec = daily.iloc[st.session_state.n_idx]
        title = rec["title"]
        summary = rec["summary"]
        mitre_id = rec["mitre_match"]["id"]
        mitre_name = rec["mitre_match"]["name"]
        mitre_score = rec["mitre_match"]["score"]

        html = f"""
        <style>
          .flip-card {{ perspective:1000px; width:600px; height:260px; margin:auto; }}
          .flip-card-inner {{ position:relative; width:100%; height:100%;
                             transition:transform 0.8s; transform-style:preserve-3d; }}
          .flip-card:hover .flip-card-inner {{ transform:rotateY(180deg); }}
          .flip-card-front, .flip-card-back {{ position:absolute; width:100%; height:100%;
                                             backface-visibility:hidden;
                                             border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.15);
                                             padding:20px; background:white; }}
          .flip-card-back {{ transform:rotateY(180deg); }}
        </style>
        <div class="flip-card"><div class="flip-card-inner">
          <div class="flip-card-front">
            <h3>{title}</h3>
            <p style="font-size:14px; line-height:1.4;">{summary}</p>
          </div>
          <div class="flip-card-back">
            <h4>Related TTP</h4>
            <p><strong>{mitre_id}</strong><br>{mitre_name}</p>
            <p>Similarity score: {mitre_score:.2f}</p>
          </div>
        </div></div>
        """

        components.html(html, height=300)
        st.caption(f"[{st.session_state.n_idx + 1}/{len(daily)}]")

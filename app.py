import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ─── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    .main > div { padding-top: 1rem; }
    .stMetric { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 1.2rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    .stMetric label { color: rgba(255,255,255,0.85) !important; font-size: 0.85rem !important; }
    .stMetric [data-testid="stMetricValue"] { color: white !important; font-weight: 700 !important; }
    .stMetric [data-testid="stMetricDelta"] { color: rgba(255,255,255,0.9) !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); }
    div[data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }
    .block-container { padding: 1rem 2rem; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
</style>
""", unsafe_allow_html=True)


# ─── Data Loading ───────────────────────────────────────────
@st.cache_data(show_spinner="Loading data...")
def load_data():
    """Load and enrich the sales dataset from Excel."""
    data_path = Path(__file__).parent / "Sale+Dataset.xlsx"
    if not data_path.exists():
        # Try alternative names
        for alt in ["Sale Dataset.xlsx", "SaleDataset.xlsx", "sale_dataset.xlsx"]:
            alt_path = Path(__file__).parent / alt
            if alt_path.exists():
                data_path = alt_path
                break

    if not data_path.exists():
        st.error(f"❌ Dataset tidak ditemukan! Letakkan file `Sale+Dataset.xlsx` di folder: {Path(__file__).parent}")
        st.stop()

    xf = pd.ExcelFile(data_path, engine="openpyxl")

    df_product = xf.parse("Product")
    df_campaign = xf.parse("Campaign")
    df_date = xf.parse("Date")
    df_geo = xf.parse("Geo")
    df_customer = xf.parse("Customer", usecols=["CustomerID", "ZipCode"])
    df_fact = xf.parse("Sales_2015-2019")

    # Enrich
    df_fact["Date"] = pd.to_datetime(df_fact["Date"], errors="coerce")
    sales = df_fact.merge(df_product, on="ProductID", how="left")
    sales = sales.merge(df_campaign, on="CampaignID", how="left")
    sales = sales.merge(df_customer, on="CustomerID", how="left")
    sales = sales.merge(df_geo, left_on="ZipCode", right_on="Zip", how="left")
    sales = sales.merge(df_date, on="Date", how="left", suffixes=("", "_dim"))

    # Financial metrics
    sales["Revenue"] = sales["Units"] * sales["Unit Price"]
    sales["Cost"] = sales["Units"] * sales["Unit Cost"]
    sales["Profit"] = sales["Revenue"] - sales["Cost"]
    sales["ProfitMargin"] = np.where(sales["Revenue"] != 0, sales["Profit"] / sales["Revenue"], np.nan)

    # Time features
    sales["Year"] = sales["Date"].dt.year.astype("Int64")
    sales["Month"] = sales["Date"].dt.month
    sales["YearMonth"] = sales["Date"].dt.to_period("M").astype(str)
    sales["Quarter"] = sales["Date"].dt.quarter

    # Cleaning
    sales = sales.drop_duplicates()
    sales = sales[sales["Units"] > 0]
    sales = sales.dropna(subset=["Unit Price", "Unit Cost"])
    if "Region" in sales.columns:
        sales["Region"] = sales["Region"].fillna("Unknown")

    return sales


sales = load_data()

# ─── Sidebar Filters ───────────────────────────────────────
st.sidebar.markdown("## 🎛️ Filters")

# Year filter
years = sorted(sales["Year"].dropna().unique())
selected_years = st.sidebar.multiselect("📅 Year", years, default=years)

# Region filter
regions = sorted(sales["Region"].dropna().unique())
selected_regions = st.sidebar.multiselect("🌍 Region", regions, default=regions)

# Category filter
categories = sorted(sales["Category"].dropna().unique())
selected_categories = st.sidebar.multiselect("📦 Category", categories, default=categories)

# Channel filter
channels = sorted(sales["TrafficChannel"].dropna().unique())
selected_channels = st.sidebar.multiselect("📡 Channel", channels, default=channels)

# Apply filters
df = sales[
    (sales["Year"].isin(selected_years)) &
    (sales["Region"].isin(selected_regions)) &
    (sales["Category"].isin(selected_categories)) &
    (sales["TrafficChannel"].isin(selected_channels))
].copy()

st.sidebar.markdown("---")
st.sidebar.metric("Filtered Rows", f"{len(df):,}")
st.sidebar.markdown(f"*{len(df)/len(sales)*100:.1f}% of total data*")

# ─── Header ────────────────────────────────────────────────
st.markdown("# 📊 Sales Performance Dashboard")
st.markdown("*Interactive analytics for Revenue, Profit & Strategic Insights*")
st.markdown("---")

# ─── KPI Cards ─────────────────────────────────────────────
total_revenue = df["Revenue"].sum()
total_profit = df["Profit"].sum()
total_units = df["Units"].sum()
total_txn = len(df)
avg_margin = df["ProfitMargin"].mean()
unique_customers = df["CustomerID"].nunique()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("💰 Revenue", f"${total_revenue:,.0f}")
col2.metric("📈 Profit", f"${total_profit:,.0f}")
col3.metric("📊 Margin", f"{avg_margin:.1%}")
col4.metric("📦 Units Sold", f"{total_units:,.0f}")
col5.metric("🧾 Transactions", f"{total_txn:,.0f}")
col6.metric("👥 Customers", f"{unique_customers:,.0f}")

st.markdown("---")

# ─── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Trend Analysis",
    "🌍 Regional Performance",
    "📦 Product Analytics",
    "📡 Channel & Device",
    "👥 Customer Segments",
])

# ════════════════════════════════════════════════════════════
# TAB 1: TREND ANALYSIS
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Monthly Revenue & Profit Trend")

    monthly = (df.groupby("YearMonth", dropna=False)
               .agg(Revenue=("Revenue", "sum"),
                    Profit=("Profit", "sum"),
                    Units=("Units", "sum"),
                    Transactions=("Revenue", "size"))
               .reset_index())
    monthly["ProfitMargin"] = np.where(monthly["Revenue"] != 0, monthly["Profit"] / monthly["Revenue"], np.nan)
    monthly["YearMonth_dt"] = pd.to_datetime(monthly["YearMonth"] + "-01")
    monthly = monthly.sort_values("YearMonth_dt")

    # Dual axis chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=monthly["YearMonth_dt"], y=monthly["Revenue"],
               name="Revenue", marker_color="#667eea", opacity=0.7),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=monthly["YearMonth_dt"], y=monthly["ProfitMargin"],
                   name="Profit Margin", line=dict(color="#f093fb", width=3),
                   mode="lines+markers"),
        secondary_y=True,
    )
    fig.update_layout(
        height=420,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
    fig.update_yaxes(title_text="Profit Margin", tickformat=".0%", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # Quarterly breakdown
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Quarterly Revenue by Year")
        quarterly = (df.groupby(["Year", "Quarter"])["Revenue"].sum().reset_index())
        quarterly["Q_Label"] = "Q" + quarterly["Quarter"].astype(str)
        fig_q = px.bar(quarterly, x="Q_Label", y="Revenue", color="Year",
                       barmode="group", template="plotly_dark",
                       color_discrete_sequence=px.colors.sequential.Plasma_r)
        fig_q.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_q, use_container_width=True)

    with col_b:
        st.subheader("YoY Growth Rate")
        yearly = df.groupby("Year")["Revenue"].sum().reset_index()
        yearly["Growth"] = yearly["Revenue"].pct_change()
        fig_yoy = px.bar(yearly.dropna(subset=["Growth"]), x="Year", y="Growth",
                         template="plotly_dark",
                         color="Growth",
                         color_continuous_scale=["#ff6b6b", "#51cf66"],
                         text=yearly.dropna(subset=["Growth"])["Growth"].apply(lambda x: f"{x:.1%}"))
        fig_yoy.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        fig_yoy.update_traces(textposition="outside")
        st.plotly_chart(fig_yoy, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 2: REGIONAL PERFORMANCE
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Regional Performance Overview")

    region_perf = (df.groupby("Region", dropna=False)
                   .agg(Revenue=("Revenue", "sum"),
                        Profit=("Profit", "sum"),
                        Units=("Units", "sum"),
                        Txn=("Revenue", "size"))
                   .reset_index())
    region_perf["ProfitMargin"] = np.where(region_perf["Revenue"] != 0,
                                           region_perf["Profit"] / region_perf["Revenue"], np.nan)
    region_perf = region_perf.sort_values("Revenue", ascending=False)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        fig_reg = px.bar(region_perf, x="Region", y="Revenue",
                         color="ProfitMargin",
                         color_continuous_scale="RdYlGn",
                         template="plotly_dark",
                         title="Revenue by Region (colored by Margin)")
        fig_reg.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_reg, use_container_width=True)

    with col_r2:
        fig_scatter = px.scatter(region_perf, x="Revenue", y="ProfitMargin",
                                 size="Txn", color="Region",
                                 template="plotly_dark",
                                 title="Revenue vs Margin (bubble = transactions)",
                                 size_max=60)
        fig_scatter.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Region x Category heatmap
    st.subheader("🔥 Region × Category Profit Margin Heatmap")
    pivot = (df.groupby(["Region", "Category"])
             .agg(Revenue=("Revenue", "sum"), Profit=("Profit", "sum"))
             .reset_index())
    pivot["ProfitMargin"] = np.where(pivot["Revenue"] != 0, pivot["Profit"] / pivot["Revenue"], np.nan)
    heatmap_data = pivot.pivot_table(index="Region", columns="Category", values="ProfitMargin")

    fig_heat = px.imshow(heatmap_data, text_auto=".1%",
                         color_continuous_scale="RdYlGn",
                         template="plotly_dark",
                         aspect="auto")
    fig_heat.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_heat, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 3: PRODUCT ANALYTICS
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Product Category Performance")

    cat = (df.groupby("Category", dropna=False)
           .agg(Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum"),
                Units=("Units", "sum"))
           .reset_index())
    cat["ProfitMargin"] = np.where(cat["Revenue"] != 0, cat["Profit"] / cat["Revenue"], np.nan)
    cat = cat.sort_values("Revenue", ascending=False)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig_cat = px.pie(cat, values="Revenue", names="Category",
                         template="plotly_dark",
                         title="Revenue Share by Category",
                         color_discrete_sequence=px.colors.sequential.Plasma)
        fig_cat.update_traces(textposition="inside", textinfo="percent+label")
        fig_cat.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_p2:
        fig_cat_bar = px.bar(cat, x="Category", y=["Revenue", "Profit"],
                             barmode="group", template="plotly_dark",
                             title="Revenue vs Profit by Category",
                             color_discrete_sequence=["#667eea", "#f093fb"])
        fig_cat_bar.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cat_bar, use_container_width=True)

    # Top 10 Products
    st.subheader("🏆 Top 10 Products by Revenue")
    top_prod = (df.groupby("Product", dropna=False)
                .agg(Revenue=("Revenue", "sum"),
                     Profit=("Profit", "sum"),
                     Units=("Units", "sum"))
                .reset_index()
                .sort_values("Revenue", ascending=False)
                .head(10))
    top_prod["ProfitMargin"] = np.where(top_prod["Revenue"] != 0,
                                        top_prod["Profit"] / top_prod["Revenue"], np.nan)

    fig_top = px.bar(top_prod, x="Revenue", y="Product", orientation="h",
                     color="ProfitMargin", color_continuous_scale="RdYlGn",
                     template="plotly_dark")
    fig_top.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_top, use_container_width=True)

    # Pareto Analysis
    st.subheader("📊 Pareto Analysis (Revenue Concentration)")
    prod_rev = df.groupby("Product")["Revenue"].sum().sort_values(ascending=False).reset_index()
    prod_rev["CumulativePct"] = prod_rev["Revenue"].cumsum() / prod_rev["Revenue"].sum()
    prod_rev["ProductRank"] = range(1, len(prod_rev) + 1)
    prod_rev["ProductPct"] = prod_rev["ProductRank"] / len(prod_rev)

    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Scatter(x=prod_rev["ProductPct"], y=prod_rev["CumulativePct"],
                                    mode="lines", fill="tozeroy",
                                    line=dict(color="#667eea", width=2),
                                    fillcolor="rgba(102,126,234,0.2)"))
    fig_pareto.add_hline(y=0.8, line_dash="dash", line_color="#f093fb",
                         annotation_text="80% Revenue")
    fig_pareto.update_layout(
        height=350, template="plotly_dark",
        xaxis_title="% of Products", yaxis_title="Cumulative % Revenue",
        xaxis_tickformat=".0%", yaxis_tickformat=".0%",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_pareto, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 4: CHANNEL & DEVICE
# ════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Traffic Channel & Device Analysis")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        chan = (df.groupby("TrafficChannel", dropna=False)
                .agg(Revenue=("Revenue", "sum"),
                     Profit=("Profit", "sum"),
                     Txn=("Revenue", "size"))
                .reset_index())
        chan["ProfitMargin"] = np.where(chan["Revenue"] != 0, chan["Profit"] / chan["Revenue"], np.nan)
        chan = chan.sort_values("Revenue", ascending=False)

        fig_chan = px.bar(chan, x="TrafficChannel", y="Revenue",
                         color="ProfitMargin", color_continuous_scale="Viridis",
                         template="plotly_dark",
                         title="Revenue by Traffic Channel")
        fig_chan.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_chan, use_container_width=True)

    with col_c2:
        dev = (df.groupby("Device", dropna=False)
               .agg(Revenue=("Revenue", "sum"),
                    Profit=("Profit", "sum"),
                    Txn=("Revenue", "size"))
               .reset_index())
        dev["ProfitMargin"] = np.where(dev["Revenue"] != 0, dev["Profit"] / dev["Revenue"], np.nan)

        fig_dev = px.pie(dev, values="Revenue", names="Device",
                         template="plotly_dark",
                         title="Revenue by Device",
                         color_discrete_sequence=px.colors.sequential.Magma_r,
                         hole=0.4)
        fig_dev.update_traces(textposition="inside", textinfo="percent+label")
        fig_dev.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_dev, use_container_width=True)

    # Channel Trend over time
    st.subheader("Channel Revenue Trend Over Time")
    chan_monthly = (df.groupby(["YearMonth", "TrafficChannel"])["Revenue"].sum().reset_index())
    chan_monthly["YearMonth_dt"] = pd.to_datetime(chan_monthly["YearMonth"] + "-01")
    chan_monthly = chan_monthly.sort_values("YearMonth_dt")

    fig_chan_trend = px.area(chan_monthly, x="YearMonth_dt", y="Revenue",
                            color="TrafficChannel", template="plotly_dark",
                            color_discrete_sequence=px.colors.qualitative.Set2)
    fig_chan_trend.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_chan_trend, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 5: CUSTOMER SEGMENTS
# ════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Customer Segmentation (RFM-lite)")

    cust_agg = (df.groupby("CustomerID", dropna=False)
                .agg(Txn=("Revenue", "size"),
                     Units=("Units", "sum"),
                     Revenue=("Revenue", "sum"),
                     Profit=("Profit", "sum"),
                     LastDate=("Date", "max"))
                .reset_index())
    cust_agg["ProfitMargin"] = np.where(cust_agg["Revenue"] != 0,
                                        cust_agg["Profit"] / cust_agg["Revenue"], np.nan)

    ref_date = df["Date"].max()
    cust_agg["RecencyDays"] = (ref_date - cust_agg["LastDate"]).dt.days

    # RFM scoring
    cust_agg["R_Score"] = pd.qcut(cust_agg["RecencyDays"], 4, labels=[4, 3, 2, 1])
    cust_agg["F_Score"] = pd.qcut(cust_agg["Txn"].rank(method="first"), 4, labels=[1, 2, 3, 4])
    cust_agg["M_Score"] = pd.qcut(cust_agg["Revenue"].rank(method="first"), 4, labels=[1, 2, 3, 4])
    cust_agg["RFM_Score"] = (cust_agg["R_Score"].astype(int) +
                             cust_agg["F_Score"].astype(int) +
                             cust_agg["M_Score"].astype(int))

    def label_segment(score):
        if score >= 10:
            return "🌟 High Value"
        elif score >= 7:
            return "🚀 Growth"
        elif score >= 5:
            return "📌 Regular"
        else:
            return "⚠️ Low Value"

    cust_agg["Segment"] = cust_agg["RFM_Score"].apply(label_segment)

    seg = (cust_agg.groupby("Segment")
           .agg(Customers=("CustomerID", "nunique"),
                Revenue=("Revenue", "sum"),
                Profit=("Profit", "sum"),
                AvgTxn=("Txn", "mean"))
           .reset_index())
    seg["ProfitMargin"] = np.where(seg["Revenue"] != 0, seg["Profit"] / seg["Revenue"], np.nan)
    seg = seg.sort_values("Revenue", ascending=False)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_seg = px.bar(seg, x="Segment", y="Revenue",
                         color="Segment", template="plotly_dark",
                         title="Revenue by Customer Segment",
                         color_discrete_sequence=["#667eea", "#764ba2", "#f093fb", "#ff6b6b"])
        fig_seg.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_seg, use_container_width=True)

    with col_s2:
        fig_seg_pie = px.pie(seg, values="Customers", names="Segment",
                             template="plotly_dark",
                             title="Customer Count by Segment",
                             color_discrete_sequence=["#667eea", "#764ba2", "#f093fb", "#ff6b6b"],
                             hole=0.4)
        fig_seg_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_seg_pie.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_seg_pie, use_container_width=True)

    # Scatter: Txn vs Revenue colored by segment
    st.subheader("Customer Scatter: Frequency vs Revenue")
    sample_cust = cust_agg.sample(min(5000, len(cust_agg)), random_state=42)
    fig_cust_scatter = px.scatter(sample_cust, x="Txn", y="Revenue",
                                  color="Segment", opacity=0.6,
                                  template="plotly_dark",
                                  color_discrete_sequence=["#667eea", "#764ba2", "#f093fb", "#ff6b6b"],
                                  hover_data=["CustomerID", "ProfitMargin"])
    fig_cust_scatter.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_cust_scatter, use_container_width=True)

    # Segment metrics table
    st.subheader("📋 Segment Summary")
    seg_display = seg.copy()
    seg_display["Revenue"] = seg_display["Revenue"].apply(lambda x: f"${x:,.0f}")
    seg_display["Profit"] = seg_display["Profit"].apply(lambda x: f"${x:,.0f}")
    seg_display["ProfitMargin"] = seg_display["ProfitMargin"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "-")
    seg_display["AvgTxn"] = seg_display["AvgTxn"].apply(lambda x: f"{x:.1f}")
    st.dataframe(seg_display, use_container_width=True, hide_index=True)

# ─── Footer ────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85rem;'>"
    "📊 Sales Analytics Dashboard | Fullstack Bangalore – Data Analyst Bootcamp Sesi 10 | "
    "Built with Streamlit & Plotly"
    "</div>",
    unsafe_allow_html=True,
)

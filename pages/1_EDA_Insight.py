"""Halaman EDA: alur cleaning dan tujuh insight dari notebook, dihitung langsung dari Sale+Dataset.xlsx."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="EDA Insight", layout="wide")

PURPLE, TEAL, ORANGE, RED, GREY = "#6D28D9", "#0F9D9A", "#E08A2E", "#C2283C", "#9CA3AF"
DATA_PATH = Path(__file__).resolve().parents[1] / "Sale+Dataset.xlsx"


# ---------------------------------------------------------------- data
@st.cache_data(show_spinner="Membaca Sale+Dataset.xlsx (sekitar 30 detik pertama kali)...")
def load_raw():
    xf = pd.ExcelFile(DATA_PATH, engine="openpyxl")
    tables = {
        "Sales_2015-2019": xf.parse("Sales_2015-2019"),
        "Product": xf.parse("Product"),
        "Customer": xf.parse("Customer", usecols=["CustomerID", "ZipCode"]),
        "Geo": xf.parse("Geo"),
        "Campaign": xf.parse("Campaign"),
        "Date": xf.parse("Date"),
    }
    return tables


@st.cache_data(show_spinner="Menggabungkan tabel dan cleaning...")
def build_clean(_tables):
    t = _tables
    fact = t["Sales_2015-2019"].copy()
    fact["Date"] = pd.to_datetime(fact["Date"], errors="coerce")
    s = (fact.merge(t["Product"], on="ProductID", how="left")
             .merge(t["Campaign"], on="CampaignID", how="left")
             .merge(t["Customer"], on="CustomerID", how="left")
             .merge(t["Geo"], left_on="ZipCode", right_on="Zip", how="left")
             .merge(t["Date"], on="Date", how="left", suffixes=("", "_dim")))
    s["Revenue"] = s["Units"] * s["Unit Price"]
    s["Cost"] = s["Units"] * s["Unit Cost"]
    s["Profit"] = s["Revenue"] - s["Cost"]
    s["ProfitMargin"] = np.where(s["Revenue"] != 0, s["Profit"] / s["Revenue"], np.nan)
    s["Year"] = s["Date"].dt.year
    s["Month"] = s["Date"].dt.month
    s["Quarter"] = s["Date"].dt.quarter

    steps = [("Setelah join 6 tabel", len(s))]
    s = s.drop_duplicates()
    steps.append(("Buang baris duplikat", len(s)))
    s = s[s["Units"] > 0]
    steps.append(("Buang Units <= 0", len(s)))
    s = s.dropna(subset=["Unit Price", "Unit Cost"])
    steps.append(("Buang harga atau cost kosong", len(s)))
    s["Region"] = s["Region"].fillna("Unknown")
    return s, steps


def margin(df):
    rev = df["Revenue"].sum()
    return df["Profit"].sum() / rev if rev else np.nan


def usd(x, unit="M"):
    return f"${x / 1e6:,.2f}M" if unit == "M" else f"${x:,.0f}"


if not DATA_PATH.exists():
    st.error(f"File Sale+Dataset.xlsx tidak ditemukan di {DATA_PATH.parent}. Letakkan di folder yang sama dengan app.py.")
    st.stop()

tables = load_raw()
sales, steps = build_clean(tables)

# ---------------------------------------------------------------- header
st.title("EDA dan Insight: Sale Dataset 2015 sampai 2019")
st.caption("Pertanyaan bisnis: bagaimana menaikkan profit margin sebesar 10% di kuartal berikutnya? "
           "Margin dihitung sebagai total profit dibagi total revenue.")

years = sorted(sales["Year"].dropna().astype(int).unique())
year = st.sidebar.selectbox("Tahun untuk insight 1 sampai 5 dan 7", years, index=len(years) - 1)
d = sales[sales["Year"] == year]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"Transaksi {year}", f"{len(d):,}")
c2.metric(f"Revenue {year}", usd(d["Revenue"].sum()))
c3.metric(f"Profit {year}", usd(d["Profit"].sum()))
c4.metric(f"Margin {year}", f"{margin(d):.1%}")
c5.metric("Target margin (+10% relatif)", f"{margin(d) * 1.1:.1%}")

tab_data, t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "Data dan cleaning", "Insight 1: Distribusi", "Insight 2: Region", "Insight 3: Tren", "Insight 4: Korelasi",
    "Insight 5: Outlier", "Insight 6: Segmentasi", "Insight 7: Akar masalah"])

# ---------------------------------------------------------------- data dan cleaning
with tab_data:
    st.subheader("Tabel di Sale+Dataset.xlsx (star schema)")
    info = pd.DataFrame([{"Tabel": k, "Baris": len(v), "Kolom": len(v.columns),
                          "Duplikat": int(v.duplicated().sum()), "Contoh kolom": ", ".join(map(str, v.columns[:5]))}
                         for k, v in tables.items()])
    st.dataframe(info, hide_index=True, use_container_width=True)
    st.caption("Sales_2015-2019 adalah tabel fakta (satu baris satu transaksi). Lima tabel lain adalah dimensi yang di-join lewat ID.")

    st.subheader("Langkah cleaning")
    st_df = pd.DataFrame(steps, columns=["Langkah", "Sisa baris"])
    st_df["Baris dibuang"] = (-st_df["Sisa baris"].diff()).fillna(0).astype(int)
    st.dataframe(st_df, hide_index=True, use_container_width=True)

    st.subheader("Missing value setelah join (kolom yang dipakai analisis)")
    cols = ["Units", "Unit Price", "Unit Cost", "Category", "Segment", "Product", "Region", "TrafficChannel", "Device"]
    cols = [c for c in cols if c in sales.columns]
    miss = (sales[cols].isna().mean() * 100).round(2).rename("Persen kosong").reset_index().rename(columns={"index": "Kolom"})
    st.dataframe(miss, hide_index=True, use_container_width=True)

    st.subheader("Ringkasan per tahun")
    yr = sales.groupby("Year").agg(Transaksi=("Revenue", "size"), Revenue=("Revenue", "sum"),
                                   Profit=("Profit", "sum")).reset_index()
    yr["Margin"] = yr["Profit"] / yr["Revenue"]
    st.dataframe(yr.style.format({"Revenue": "${:,.0f}", "Profit": "${:,.0f}", "Margin": "{:.1%}", "Transaksi": "{:,}"}),
                 hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- 1 distribusi
with t1:
    bins, labels = [0, 500, 1000, 2000, 5000, np.inf], ["$0-500", "$500-1K", "$1K-2K", "$2K-5K", "$5K+"]
    b = pd.cut(d["Revenue"], bins, labels=labels, right=False).value_counts().reindex(labels).fillna(0)
    share = b / b.sum()
    fig = px.bar(x=b.index, y=b.values, text=[f"{v:,.0f} ({p:.1%})" for v, p in zip(b.values, share.values)],
                 labels={"x": "Rentang revenue per transaksi", "y": "Jumlah transaksi"},
                 color_discrete_sequence=[PURPLE])
    fig.update_traces(textposition="outside")
    fig.update_layout(height=420, margin=dict(t=30))
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, use_container_width=True)
    mid = share["$500-1K"] + share["$1K-2K"]
    right.metric("Transaksi di \\$500 sampai \\$2.000", f"{mid:.1%}")
    right.metric("Median revenue per transaksi", f"${d['Revenue'].median():,.0f}")
    right.metric("Rata-rata revenue per transaksi", f"${d['Revenue'].mean():,.0f}")
    right.info(f"Mayoritas transaksi bernilai \\$500 sampai \\$2.000. Transaksi di bawah \\$500 ({share['$0-500']:.1%}) "
               "bisa jadi sasaran bundling atau upsell.")

# ---------------------------------------------------------------- 2 region
with t2:
    g = d.groupby("Region").agg(Revenue=("Revenue", "sum"), Profit=("Profit", "sum")).reset_index()
    g["Margin"] = g["Profit"] / g["Revenue"]
    g = g.sort_values("Revenue", ascending=False)
    fig = go.Figure([go.Bar(name="Revenue", x=g["Region"], y=g["Revenue"], marker_color=PURPLE),
                     go.Bar(name="Profit", x=g["Region"], y=g["Profit"], marker_color=TEAL)])
    fig.update_layout(barmode="group", height=420, margin=dict(t=30), yaxis_title="USD")
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, use_container_width=True)
    right.dataframe(g.style.format({"Revenue": "${:,.0f}", "Profit": "${:,.0f}", "Margin": "{:.1%}"}),
                    hide_index=True, use_container_width=True)
    low, high = g.loc[g["Margin"].idxmin()], g.loc[g["Margin"].idxmax()]
    gain = low["Revenue"] * (high["Margin"] - low["Margin"])
    right.info(f"{low['Region']} punya margin terendah ({low['Margin']:.1%}), {high['Region']} tertinggi "
               f"({high['Margin']:.1%}). Kalau margin {low['Region']} naik setara {high['Region']}, "
               f"tambahan profit sekitar {usd(gain)}.")

# ---------------------------------------------------------------- 3 tren
with t3:
    zero_products = d.loc[d["Profit"] == 0, "Product"].unique()
    m_all = d.groupby("Month").apply(margin, include_groups=False)
    m_ex = d[~d["Product"].isin(zero_products)].groupby("Month").apply(margin, include_groups=False)
    fig = go.Figure([
        go.Scatter(x=m_all.index, y=m_all.values, name="Semua transaksi", mode="lines+markers", line=dict(color=PURPLE, width=3)),
        go.Scatter(x=m_ex.index, y=m_ex.values, name="Tanpa produk bermargin 0", mode="lines",
                   line=dict(color=GREY, dash="dash")),
    ])
    fig.update_layout(height=420, margin=dict(t=30), yaxis_tickformat=".0%", xaxis_title="Bulan",
                      yaxis_title="Profit margin", xaxis=dict(dtick=1))
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, use_container_width=True)
    right.metric(f"Puncak (bulan {m_all.idxmax()})", f"{m_all.max():.1%}")
    right.metric(f"Terendah (bulan {m_all.idxmin()})", f"{m_all.min():.1%}")
    right.info("Garis putus-putus menghitung ulang margin tanpa produk yang dijual dengan profit 0 (insight 5). "
               "Kalau garis itu datar, penurunan margin bukan pola musiman.")

# ---------------------------------------------------------------- 4 korelasi
with t4:
    cols = ["Units", "Unit Price", "Unit Cost", "Revenue", "Cost", "Profit", "ProfitMargin"]
    corr = d[cols].corr().round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto")
    fig.update_layout(height=480, margin=dict(t=30))
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, use_container_width=True)
    right.metric("Margin dan Unit Price", f"{corr.loc['ProfitMargin', 'Unit Price']:+.2f}")
    right.metric("Margin dan Unit Cost", f"{corr.loc['ProfitMargin', 'Unit Cost']:+.2f}")
    right.metric("Margin dan Units", f"{corr.loc['ProfitMargin', 'Units']:+.2f}")
    right.info("Korelasi bukan sebab akibat. Angka ini menunjukkan yang perlu diperiksa: harga dan cost di master "
               "data produk, bukan jumlah unit yang terjual.")

# ---------------------------------------------------------------- 5 outlier
with t5:
    zp = d[d["Profit"] == 0]
    q1, q3 = d["Revenue"].quantile([0.25, 0.75])
    iqr_out = (d["Revenue"] > q3 + 1.5 * (q3 - q1)).sum()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Transaksi dengan profit \\$0", f"{len(zp):,}")
    k1.caption(f"{len(zp) / len(d):.1%} dari semua transaksi")
    k2.metric("Revenue tanpa profit", usd(zp["Revenue"].sum()))
    k2.caption(f"{zp['Revenue'].sum() / d['Revenue'].sum():.1%} dari revenue tahun ini")
    k3.metric("Produk penyebab", f"{zp['Product'].nunique()}")
    k4.metric("Outlier revenue (IQR)", f"{iqr_out:,}")
    k4.caption("transaksi besar, masih wajar")
    left, right = st.columns([3, 2])
    if len(zp):
        q = zp.groupby(["Quarter", "Product"]).size().reset_index(name="Transaksi")
        fig = px.bar(q, x="Quarter", y="Transaksi", color="Product", text="Transaksi",
                     color_discrete_sequence=[PURPLE, ORANGE, TEAL])
        fig.update_layout(height=380, margin=dict(t=30), xaxis=dict(dtick=1))
        left.plotly_chart(fig, use_container_width=True)
        prod = (zp.groupby(["Product", "Category", "Segment"])
                  .agg(UnitCost=("Unit Cost", "first"), UnitPrice=("Unit Price", "first"), Transaksi=("Revenue", "size"),
                       Revenue=("Revenue", "sum")).reset_index())
        right.dataframe(prod.style.format({"UnitCost": "${:,.0f}", "UnitPrice": "${:,.0f}", "Revenue": "${:,.0f}"}),
                        hide_index=True, use_container_width=True)
        right.warning("Unit Cost sama dengan Unit Price, jadi setiap unit terjual tidak menghasilkan profit. "
                      "Ini perlu dicek ke master data produk.")
    else:
        left.info("Tidak ada transaksi dengan profit $0 di tahun ini.")

# ---------------------------------------------------------------- 6 segmentasi
with t6:
    @st.cache_data(show_spinner="Menghitung skor RFM...")
    def rfm(df):
        ca = df.groupby("CustomerID").agg(Txn=("Revenue", "size"), Revenue=("Revenue", "sum"),
                                         LastDate=("Date", "max")).reset_index()
        ca["Recency"] = (df["Date"].max() - ca["LastDate"]).dt.days
        ca["R"] = pd.qcut(ca["Recency"], 4, labels=[4, 3, 2, 1]).astype(int)
        ca["F"] = pd.qcut(ca["Txn"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
        ca["M"] = pd.qcut(ca["Revenue"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
        score = ca["R"] + ca["F"] + ca["M"]
        ca["Segmen"] = np.select([score >= 10, score >= 7, score >= 5], ["High Value", "Growth", "Regular"], "Low Value")
        sg = ca.groupby("Segmen").agg(Pelanggan=("CustomerID", "nunique"), Revenue=("Revenue", "sum")).reset_index()
        sg["% pelanggan"] = sg["Pelanggan"] / sg["Pelanggan"].sum()
        sg["% revenue"] = sg["Revenue"] / sg["Revenue"].sum()
        sg["Revenue per pelanggan"] = sg["Revenue"] / sg["Pelanggan"]
        order = ["High Value", "Growth", "Regular", "Low Value"]
        return sg.set_index("Segmen").reindex(order).reset_index()

    sg = rfm(sales[["CustomerID", "Revenue", "Date"]])
    long = sg.melt(id_vars="Segmen", value_vars=["% pelanggan", "% revenue"], var_name="Ukuran", value_name="Porsi")
    fig = px.bar(long, y="Segmen", x="Porsi", color="Ukuran", barmode="group", orientation="h",
                 text=long["Porsi"].map("{:.1%}".format), color_discrete_sequence=["#C4B5FD", PURPLE])
    fig.update_layout(height=420, margin=dict(t=30), xaxis_tickformat=".0%", yaxis=dict(autorange="reversed"))
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, use_container_width=True)
    right.dataframe(sg.style.format({"Revenue": "${:,.0f}", "% pelanggan": "{:.1%}", "% revenue": "{:.1%}",
                                     "Revenue per pelanggan": "${:,.0f}", "Pelanggan": "{:,}"}),
                    hide_index=True, use_container_width=True)
    right.caption("Data 2015 sampai 2019 (tidak terpengaruh pilihan tahun). Skor R, F, M masing-masing 1 sampai 4 "
                  "berdasarkan kuartil. Total 10 ke atas High Value, 7 sampai 9 Growth, 5 sampai 6 Regular.")

# ---------------------------------------------------------------- 7 akar masalah
with t7:
    zp_products = d.loc[d["Profit"] == 0, "Product"].unique()
    base = margin(d)
    target = base * 1.1
    zp = d[d["Product"].isin(zp_products)]
    fixed_profit = d["Profit"].sum() + zp["Revenue"].sum() * base
    fixed_margin = fixed_profit / d["Revenue"].sum()
    k1, k2, k3 = st.columns(3)
    k1.metric(f"Margin {year} sekarang", f"{base:.1%}")
    k2.metric("Kalau produk bermargin 0 diperbaiki", f"{fixed_margin:.1%}")
    k2.caption(f"tambahan profit sekitar {usd(zp['Revenue'].sum() * base)}")
    k3.metric("Target (+10% relatif)", f"{target:.1%}")
    if target > base:
        k3.caption(f"perbaikan produk menutup {(fixed_margin - base) / (target - base):.0%} dari selisih ke target")
    fig = go.Figure(go.Bar(x=["Sekarang", "Setelah perbaikan produk", "Target"],
                           y=[base, fixed_margin, target], marker_color=[GREY, PURPLE, TEAL],
                           text=[f"{v:.1%}" for v in (base, fixed_margin, target)], textposition="outside"))
    fig.update_layout(height=380, margin=dict(t=30), yaxis_tickformat=".0%",
                      yaxis_range=[min(base, fixed_margin) * 0.9, target * 1.05])
    st.plotly_chart(fig, use_container_width=True)
    st.success(f"Rekomendasi: cek ke tim pricing harga dan cost {', '.join(map(str, zp_products)) or '-'}. "
               "Perbaikan ini saja belum cukup untuk target 10%; sisanya dicari dari region dan kategori bermargin rendah.")

# Sales Performance Dashboard dan EDA

Project Sesi 10 Data Analyst Bootcamp Fullstack Bangalore. Analisis penjualan 2015 sampai 2019 untuk menjawab pertanyaan bisnis: bagaimana menaikkan profit margin sebesar 10% di kuartal berikutnya.

## Isi aplikasi

Aplikasi Streamlit punya dua halaman (pilih di sidebar):

| Halaman | Isi |
|---|---|
| app (dashboard) | KPI, tren revenue dan margin, performa region, produk, channel dan device, segmen pelanggan, dengan filter Year, Region, Category, Channel |
| EDA Insight | data dan langkah cleaning, lalu tujuh insight: distribusi, region, tren, korelasi, outlier, segmentasi RFM-lite, dan akar masalah |

Margin di halaman EDA Insight dihitung sebagai total profit dibagi total revenue, sama dengan notebook.

## Cara menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Buka http://localhost:8501. Pembacaan Excel pertama kali butuh sekitar 30 detik, setelah itu data disimpan di cache.

## Struktur project

```
sales-dashboard/
├── app.py                                     # dashboard Streamlit (halaman utama)
├── pages/
│   └── 1_EDA_Insight.py                       # halaman EDA dan tujuh insight
├── EDA_Cleaning_Insight_SaleDataset_ID.ipynb  # notebook EDA lengkap
├── Sale+Dataset.xlsx                          # dataset (star schema)
├── requirements.txt
└── README.md
```

## Dataset

`Sale+Dataset.xlsx` berisi satu tabel fakta dan lima tabel dimensi:

- Sales_2015-2019: transaksi (611.170 baris, 19 duplikat dibuang saat cleaning)
- Product: kategori, segmen, unit cost, unit price (212 produk)
- Customer, Geo: pelanggan dan lokasi (Region, State)
- Campaign: TrafficChannel dan Device
- Date: kalender

## Temuan utama

- Margin 2019 adalah 44,2%. Target naik 10% relatif berarti 48,6%.
- 7.925 transaksi 2019 tidak menghasilkan profit sama sekali ($6,07M revenue). Semuanya berasal dari dua produk, Maximus UM-92 dan Maximus UC-69, yang Unit Cost-nya sama dengan Unit Price.
- Memperbaiki harga dua produk itu menaikkan margin ke 46,5%, sekitar setengah jalan menuju target.

## Tech stack

Python, pandas, NumPy, Plotly, Streamlit, openpyxl.

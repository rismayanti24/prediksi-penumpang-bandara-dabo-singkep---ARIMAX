# ✈️ Sistem Prediksi & Analitik Penumpang per Rute - Bandara Dabo Singkep (SIQ)
**Metode Penambangan Data (Data Mining): Model ARIMAX (AutoRegressive Integrated Moving Average with eXogenous Variables)**

---

## 📌 Ringkasan Proyek
Proyek ini mengimplementasikan siklus lengkap **Penambangan Data (CRISP-DM)** untuk memprediksi jumlah penumpang mingguan per rute penerbangan di **Bandara Dabo Singkep (UPBU Kelas III Dabo Singkep - Kepulauan Riau)** yang dilayani oleh armada perintis **Susi Air (Cessna 208B Grand Caravan, kapasitas 12 kursi)**.

### ✨ Karakteristik & Ketentuan Pemodelan:
1. **Pemodelan per Rute (5 Rute Utama)**:
   - `SIQ <-> BTH` (Batam) $\rightarrow$ **ARIMAX(2, 0, 3)**
   - `SIQ <-> PKU` (Pekanbaru) $\rightarrow$ **ARIMAX(0, 1, 3)**
   - `SIQ <-> DJB` (Jambi) $\rightarrow$ **ARIMAX(3, 0, 3)**
   - `SIQ <-> TNJ` (Tanjungpinang) $\rightarrow$ **ARIMAX(3, 0, 3)**
   - `SIQ <-> TJB` (Tanjung Balai Karimun) $\rightarrow$ **ARIMAX(3, 0, 3)**
   - Serta model agregat **Semua Rute** ARIMAX(2, 0, 3), yang dilatih dan dievaluasi sendiri pada total penumpang mingguan (bukan penjumlahan prediksi kelima rute). Hasilnya: MAPE rolling 1 minggu 6,9% dan MAPE 25 minggu sekaligus 10,0% (lebih kecil dari per rute karena fluktuasi antar rute saling menutupi, sehingga **tidak sebanding langsung** dengan MAPE per rute; MAE/RMSE-nya justru lebih besar karena skala total jauh lebih besar). Hasilnya ada sebagai baris `SEMUA` di `ringkasan_model.csv`, `metrik_model.csv`, `prediksi_model.csv`, dan `pencarian_orde.csv`.
2. **Variabel Eksogen ($X$)**: Penanda musiman libur Idul Fitri ($\pm 1$ minggu di sekitar Lebaran, jadi 3 minggu per tahun) yang kalendernya dinamis maju $\sim 11$ hari setiap tahun. Definisinya hanya ada di satu file, `lebaran.py`, yang dipakai bersama oleh `scripts/clean.py`, `streamlit_app.py`, dan `app.py`, sehingga model yang dievaluasi sama dengan model di dashboard.
3. **Pembagian Data (Train/Test Split)** Sesuai Ketentuan Tugas:
   - **Data Latih (Train)**: $\sim 71\%$ (61 minggu, Jan 2025 s/d awal Maret 2026).
   - **Data Uji (Test)**: $\sim 29\%$ (25 minggu, **mulai momen mudik Lebaran Maret 2026** s/d Agustus 2026).
4. **Evaluasi Out-of-Sample**:
   - Rolling forecast 1-minggu & Multi-step 25-minggu diuji terhadap data aktual Lebaran 2026.
   - Metrik: **MAE, RMSE, MAPE**.
   - **Penentuan orde**: `d` ditentukan dari uji ADF pada data latih (p < 0,05 → d=0, selain itu d=1), sehingga hanya PKU (p=0,083) memakai d=1. Uji ADF di `eda.py` (grafik `eda8`) memakai deret dan data latih yang sama dengan model. Catatan BTH: ADF menyatakan BTH stasioner (p=0,026) hanya karena lonjakan ATR 72 Juni–Juli 2025; tanpa penerbangan ATR, p=0,461 (tidak stasioner, d=1), dan versi itu memang memilih d=1 di `model_bth_tanpa_atr.py`. AIC hanya dipakai memilih `p` dan `q` pada `d` yang sama (AIC antar `d` berbeda tidak sebanding). Nilai `q=3` adalah batas atas grid pencarian yang disengaja: saat grid diperluas ke p,q=0..5, AIC/BIC terus turun sampai q=5 (batas baru) tetapi MAPE data uji tidak membaik (PKU 11,7% → 14,1%, TJB 25,1% → 28,0%), tanda model terlalu fleksibel untuk 61 minggu data latih.
   - MAPE skenario rolling 1 minggu berkisar **11,7% s/d 31,6%** (PKU terbaik, TNJ terlemah).
   - MAPE skenario 25 minggu sekaligus lebih tinggi, terutama **TNJ 32,1%, TJB 32,0%, dan BTH 31,0%**, karena data latih hanya memuat satu Lebaran (2025), sehingga lonjakan Lebaran 2026 sulit diprediksi.
   - Keterbatasan: data hanya sekitar 20 bulan (Jan 2025 – Agu 2026), sehingga model belum stabil untuk rute berpenumpang sedikit.

---

## 📁 Struktur Folder Proyek

```text
Project kelompok/
├── data_mentah/               <- File laporan bulanan LLAU Excel asli (Jan 2025 - Agu 2026)
├── dokumen_tugas/             <- Dokumen pedoman & ketentuan tugas data mining
├── hasil/
│   ├── data_bersih/           <- Dataset bersih hasil preprocessing
│   │   ├── data_penerbangan_bersih.csv  <- 1.820 baris data level penerbangan
│   │   ├── data_mingguan_per_rute.csv   <- Data mingguan per 5 rute utama
│   │   ├── data_mingguan.csv            <- Data mingguan agregat bandara
│   │   └── log_pembersihan.txt          <- Ringkasan proses pembersihan data
│   ├── eda/                   <- Grafik visualisasi analisis eksplorasi data (EDA 1 - 8)
│   └── model/                 <- Hasil metrik & grafik evaluasi ARIMAX per rute
│       ├── ringkasan_model.csv & .txt   <- Rangkuman orde, AIC, MAE, RMSE, MAPE
│       ├── metrik_model.csv             <- Evaluasi skenario rolling & multi-step
│       ├── prediksi_model.csv           <- Data prediksi vs aktual periode uji
│       ├── pencarian_orde.csv           <- Hasil pencarian orde (AIC/BIC) per rute
│       ├── perbandingan_bth_tanpa_atr.csv <- BTH dengan vs tanpa ATR 72
│       └── model1 s/d model5.png        <- Grafik evaluasi ARIMAX
├── scripts/
│   ├── clean.py               <- Step 1: Pembersihan data & penyusunan deret mingguan per rute
│   ├── eda.py                 <- Step 2: Analisis Eksplorasi Data (EDA) & visualisasi pola
│   ├── model_bth_tanpa_atr.py <- Analisis sensitivitas BTH tanpa penerbangan ATR 72
│   ├── model_arimax.py        <- Step 3: Pelatihan model ARIMAX, tuning AIC, & backtesting split 70:30
│   └── visualisasi_model.py   <- Step 3: Pembuatan grafik evaluasi performa model
├── templates/
│   └── dashboard.html         <- Frontend dashboard versi Flask
├── lebaran.py                 <- Definisi tunggal variabel eksogen Lebaran (+/- 1 minggu)
├── app.py                     <- Dashboard versi Flask (REST API), port 5000
├── streamlit_app.py           <- Dashboard versi Streamlit, port 8501
├── requirements.txt           <- Daftar library Python yang dibutuhkan
├── JALANKAN_WEB.bat           <- Launcher dashboard Flask
├── JALANKAN_STREAMLIT.bat     <- Launcher dashboard Streamlit
└── README.md                  <- Dokumentasi proyek
```

---

## 🚀 Cara Menjalankan Dashboard

### 1. Pasang library (sekali saja)
```bash
pip install -r requirements.txt
```

### 2a. Versi Streamlit (disarankan)
Klik dua kali **`JALANKAN_STREAMLIT.bat`**, atau lewat terminal dari folder project:
```bash
streamlit run streamlit_app.py
```
Buka **`http://localhost:8501`**. Isinya lima tab: Ringkasan, Peramalan, Evaluasi model, Operasional, dan Data.

### 2b. Versi Flask
Klik dua kali **`JALANKAN_WEB.bat`**, atau lewat terminal:
```bash
python app.py
```
Buka **`http://localhost:5000`**.

> Kedua dashboard hanya berjalan di komputer yang menjalankannya. Untuk dibagikan, kirim seluruh folder project (jangan hanya `app.py`) dan minta penerima menjalankan langkah di atas.

### Catatan Asumsi
- **Januari 2026 (5 minggu)** tidak punya data operasi normal, sehingga dikeluarkan dari data mingguan. Hanya untuk melatih model, 5 minggu ini diisi interpolasi linear (agar deret mingguan tidak berlubang). Pada grafik (`eda1`, `model1`, `model5`) minggu tersebut digambar sebagai celah, bukan garis, dan ditandai pita abu-abu.
- **Lonjakan BTH Juni–Juli 2025** (hingga 200 penumpang/minggu) bukan efek Lebaran, melainkan 18 penerbangan **ATR 72 (72 kursi) milik Wings Abadi**. Jika penerbangan ATR dikeluarkan, MAPE BTH skenario 25 minggu turun dari 31,0% menjadi 22,5% (rolling 1 minggu: 17,1% vs 20,0%, tidak membaik karena rute BTH tanpa ATR punya variasi kecil dan model lebih sulit menebak fluktuasinya). Detail di `hasil/model/perbandingan_bth_tanpa_atr.csv` dan `model5_bth_tanpa_atr.png`. Model utama tetap memakai seluruh penerbangan.
- **Jadwal reguler** (flight per minggu) dihitung dari **median flight mingguan pada data** (Semua 22, BTH 6, PKU 4, DJB 4, TNJ 4, TJB 4). Ini asumsi, bukan angka resmi UPBU. Di Streamlit nilainya bisa diubah lewat sidebar.
- Berangkat dan datang dicatat sebagai flight terpisah.
- Tanggal Idul Fitri 2027 dan 2028 pada variabel eksogen adalah estimasi.
- Angka tab operasional (keterisian kursi, delay, pola hari) dihitung langsung dari `data_penerbangan_bersih.csv`.
- **Keterisian kursi** = (dewasa + anak) ÷ jumlah kursi, karena bayi dipangku dan tidak memakai kursi (kolom `pax_kursi`). Kolom `pax_total` tetap memuat bayi dan dipakai untuk jumlah penumpang serta peramalan. Keterisian hanya dihitung untuk flight Cessna 12 kursi (79,0%; BTH 88,8%); 18 flight ATR 72 di rute BTH (keterisian 34,9%) dikeluarkan agar tidak menarik turun angka BTH (jika ikut dihitung: 76,5% dan BTH 78,4%). Dua flight (6 Apr 2025 PKU dan 21 Des 2025 BTH) tercatat melebihi 12 kursi walau bayi tidak dihitung; diduga salah input dan dibiarkan apa adanya (tercatat di log pembersihan).

### Fitur Dashboard Flask:
1. **Pemilih Rute Interaktif (Pills/Tabs)**: Beralih instan antara Semua Rute, Batam (BTH), Pekanbaru (PKU), Jambi (DJB), Tanjungpinang (TNJ), dan Karimun (TJB).
2. **Tab 1: Peramalan (Forecasting)**:
   - Grafik tren historis per rute + proyeksi ARIMAX ke masa depan.
   - Pilihan horizon peramalan: 1, 2, 3, 6, 12, hingga 24 bulan (slider bebas).
   - Rekomendasi *Extra Flight* muncul saat model mendeteksi lonjakan mudik Lebaran; tabel prediksi memuat kebutuhan flight per minggu (penumpang ÷ 12 kursi).
3. **Tab 2: Validasi Akurasi**:
   - Visualisasi perbandingan aktual vs tebakan model pada data latih dan data uji (mulai Lebaran 2026).
   - Evaluasi akurasi mingguan dengan sorotan baris interaktif.
4. **Tab 3: Eksplorasi & Evaluasi Model**:
   - Tabel perbandingan performa 5 model rute (orde, AIC, Latih/Uji, MAE, RMSE, MAPE).
   - Analisis tren mingguan, pangsa rute, hari tersibuk, ketepatan waktu (*on-time vs delay*), dan keterisian kursi (*load factor*).
5. **Tab 4: Data Explorer**:
   - Penjelajah dataset mingguan bersih dengan fitur pencarian dan filter rute.

---

## 🔄 Menjalankan Ulang Pipeline Pengolahan Data

Jika ingin memproses ulang seluruh data dari file mentah secara berurutan:
```bash
# 1. Bersihkan data mentah Excel & buat data mingguan per rute
python scripts/clean.py

# 2. Hasilkan grafik Exploratory Data Analysis (EDA)
python scripts/eda.py

# 3. Latih & evaluasi model ARIMAX per rute (Split 70:30 Lebaran 2026)
python scripts/model_arimax.py

# 4. Hasilkan grafik evaluasi performa model
python scripts/visualisasi_model.py
```

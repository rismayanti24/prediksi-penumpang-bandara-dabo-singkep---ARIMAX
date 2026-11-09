# PANDUAN & KERANGKA LAPORAN AKHIR PROYEK PENAMBANGAN DATA
**Sesuai Format RTM (Rencana Tugas Mahasiswa) Mata Kuliah Penambangan Data - UMRAH**

---

### FORMAT COVER & PENAMAAN FILE
- **Nama File PDF**: `FinPD_[NIM_KETUA].pdf` (contoh: `FinPD_220102001.pdf`)
- **Format Judul**:
  > **LAPORAN AKHIR PROJECT PENAMBANGAN DATA**  
  > **PREDIKSI JUMLAH PENUMPANG PER RUTE DAN PERENCANAAN KEBUTUHAN ARMADA PESAWAT MENGGUNAKAN METODE ARIMAX (STUDI KASUS: UPBU KELAS III BANDARA DABO SINGKEP)**  
  > Ketua: [NIM] – [NAMA]  
  > Anggota: [NIM] – [NAMA]  
  > Teknik Informatika, Fakultas Teknik dan Teknologi Kemaritiman  
  > Universitas Maritim Raja Ali Haji  
  > 2026

---

## DAFTAR ISI LAPORAN

- HALAMAN JUDUL
- DAFTAR ISI
- DAFTAR TABEL
- DAFTAR GAMBAR

---

### BAB I: BUSINESS UNDERSTANDING
*Bagian ini menjelaskan latar belakang masalah mitra riil (Bandara Dabo) dan mengapa butuh penambangan data.*

* **I.1 Latar Belakang**
  - Profil mitra: **Unit Penyelenggara Bandar Udara (UPBU) Kelas III Dabo Singkep**, Kabupaten Lingga, Kepulauan Riau.
  - Peran bandara: Menghubungkan wilayah kepulauan 3TP (Terdepan, Terluar, Tertinggal, Perbatasan) dengan kota-kota besar di Kepri, Riau, dan Jambi.
  - Karakteristik operasional: Menggunakan pesawat perintis **Cessna 208B Grand Caravan (Susi Air)** dengan kapasitas terbatas **12 kursi per penerbangan**.
* **I.2 Permasalahan**
  - Kapasitas kursi pesawat perintis sangat kecil (12 kursi), sehingga penambahan kursi tidak bisa mendadak.
  - Fluktuasi penumpang antar-rute sangat berbeda (rute Batam sangat padat, rute Karimun lebih sedikit).
  - Terjadi lonjakan musiman signifikan saat mudik Idul Fitri (Lebaran), di mana permintaan tiket melebihi kapasitas reguler.
  - Jika hanya mengandalkan tebakan rata-rata Excel, pengelola bandara tidak bisa mengantisipasi kapan lonjakan ekstrem terjadi dan berapa frekuensi penerbangan (*flight*) tambahan yang harus diajukan ke operator/kementerian.
* **I.3 Tujuan Penambangan Data**
  - Membangun model prediksi deret waktu (*time series forecasting*) per rute mingguan menggunakan algoritma **ARIMAX** (*Autoregressive Integrated Moving Average with Exogenous Variables*).
  - Memanfaatkan variabel eksogen penanda momentum **Lebaran** untuk menangkap lonjakan musiman.
  - Mengonversi hasil peramalan penumpang menjadi rekomendasi riil jumlah frekuensi penerbangan mingguan.
  - Mengimplementasikan model ke dalam **Dashboard Web Interaktif** untuk mempermudah pihak bandara.
* **I.4 Lini Waktu Pelaksanaan (Gantt Chart)**
  - Tabel jadwal kegiatan kelompok beserta PIC (Person in Charge) masing-masing anggota (detail tabel lengkap tersimpan di folder `laporan/GANTT_CHART_TIMELINE.md`):
    1. **Observasi & Pengumpulan Data Mentah** (24 Sep – 28 Sep 2026) | **PIC: Nikita Arzetty Siregar**
    2. **Data Preprocessing & Cleaning** (06 Okt – 13 Okt 2026) | **PIC: Erlinda Amira Putri Sudarmono**
    3. **Exploratory Data Analysis (EDA)** (14 Okt – 20 Okt 2026) | **PIC: Dhini Khairunnisa**
    4. **Pemodelan Deret Waktu ARIMAX** (21 Okt – 27 Okt 2026) | **PIC: Rismayanti**
    5. **Evaluasi Akurasi Data Uji Lebaran 2026** (25 Okt – 28 Okt 2026) | **PIC: Rismayanti**
    6. **Pengembangan Sistem Dashboard Web** (27 Okt – 31 Okt 2026) | **PIC: Rismayanti (Didukung Tim)**
    7. **Penyusunan Laporan Akhir & Dokumentasi** (01 Nov – 07 Nov 2026) | **PIC: Nikita, Erlinda, Dhini**

---

### BAB II: DATA UNDERSTANDING
*Bagian ini menjelaskan rincian data mentah yang didapatkan dan hasil analisis statistik awal.*

* **II.1 Teknik Pengumpulan Data**
  - Data log penerbangan riil diperoleh dari manifest/laporan operasional UPBU Bandara Dabo Singkep periode Januari 2025 hingga Agustus 2026.
* **II.2 Jenis Data**
  - Data tabular berformat Excel yang mencakup 5 rute utama pulang-pergi (PP):
    1. **BTH**: Dabo Singkep (SIQ) ↔ Batam (Hang Nadim)
    2. **PKU**: Dabo Singkep (SIQ) ↔ Pekanbaru (Sultan Syarif Kasim II)
    3. **DJB**: Dabo Singkep (SIQ) ↔ Jambi (Sultan Thaha)
    4. **TNJ**: Dabo Singkep (SIQ) ↔ Tanjungpinang (Raja Haji Fisabilillah)
    5. **TJB**: Dabo Singkep (SIQ) ↔ Tanjung Balai Karimun (Raja Haji Abdullah)
  - Atribut: Tanggal, Nomor Penerbangan, Rute Asal/Tujuan, Jumlah Penumpang Berangkat/Datang, Waktu Keberangkatan & Kedatangan (Jadwal vs Aktual).
* **II.3 Exploratory Data Analysis (EDA)**
  - **Pangsa Pasar Rute**: Batam (BTH) terbesar (30,1%), disusul Pekanbaru (19,5%), Tanjungpinang (18,3%), Jambi (18,2%), dan Karimun (13,9%).
  - **Hari Tersibuk**: Selasa (4.047 pax) dan Jumat (3.969 pax) karena jadwal utama penerbangan perintis.
  - **Tingkat Keterisian Kursi (*Load Factor*)**: Rata-rata 79,0% (hanya flight Cessna 12 kursi; dewasa + anak, bayi dipangku tidak dihitung; 18 flight ATR 72 dengan keterisian 34,9% dikeluarkan), tertinggi rute Batam (88,8%), disusul Pekanbaru (83,5%), terendah Karimun (60,8%).
  - **Kinerja Ketepatan Waktu**: 58,7% Tepat Waktu (*On-Time*) dan 41,3% *Delay* (>15 menit), penyebab terbanyak adalah faktor teknis operasional (600 flight), sedangkan cuaca tercatat pada 115 flight.
  *(Lampirkan grafik-grafik yang ada di folder `hasil/eda/`)*.

---

### BAB III: DATA PREPROCESSING
*Bagian ini menjelaskan langkah teknis pembersihan dan penyiapan data.*

* **III.1 Penanganan Missing Values & Tanggal Kosong**
  - Data log operasional harian diagregasi menjadi deret waktu mingguan (*Weekly frequency - Monday anchor*).
  - Lima minggu Januari 2026 (hanya 3 penerbangan, bukan operasi normal) dikosongkan lalu diinterpolasi secara linier agar kesinambungan deret waktu ARIMAX terpenuhi. Nilai hasil interpolasi hanya dipakai untuk melatih model, tidak dihitung dalam total atau ringkasan penumpang.
* **III.2 Seleksi Data (*Data Selection*)**
  - Memisahkan data ke dalam agregat bandara serta 5 dataset rute spesifik untuk pemodelan granular.
* **III.3 Feature Engineering (Variabel Eksogen Lebaran)**
  - Menambahkan kolom biner `lebaran` (nilai `1` pada minggu H-1 hingga H+1 Idul Fitri, dan `0` pada minggu biasa).
  - Variabel ini penting agar algoritma tidak salah menganggap lonjakan mudik tahunan sebagai anomali biasa.
* **III.4 Pembagian Data (*Train/Test Split*)**
  - Sesuai standar penambangan data: **71% Data Latih** (61 minggu, Januari 2025 – awal Maret 2026) dan **29% Data Uji** (25 minggu, mulai 9 Maret 2026 sampai Agustus 2026, yang mencakup momentum uji mudik Lebaran 2026).

---

### BAB IV: PEMODELAN (ARIMAX)
*Bagian ini menjelaskan algoritma dan hasil fitting model.*

* **IV.1 Konsep Teori ARIMAX**
  - Persamaan ARIMAX: Kombinasi *Autoregressive* (AR $p$), *Differencing* (I $d$), *Moving Average* (MA $q$), dan regresi variabel eksogen ($X$).
* **IV.2 Penentuan Orde Terbaik (Grid Search AIC)**
  - Menjelaskan hasil pencarian kombinasi parameter $(p, d, q)$ terbaik. Orde `d` ditentukan dari uji ADF pada data latih (p < 0,05 → d=0; hanya PKU yang tidak stasioner, p=0,083 → d=1; BTH tampak stasioner (p=0,026) karena lonjakan ATR 72, tanpa ATR p=0,461 → d=1, tulis ini sebagai catatan/keterbatasan), lalu `p` dan `q` (0–3) dipilih dengan *Akaike Information Criterion* (AIC) pada `d` yang sama. Catat sebagai keterbatasan: semua rute memilih q=3 (batas grid). Grid yang diperluas ke 0–5 membuat AIC/BIC terus turun tanpa memperbaiki akurasi data uji, sehingga batas q=3 dipertahankan demi model yang hemat parameter:
    - **Semua Rute (Agregat)**: ARIMAX(2, 0, 3) + Lebaran (AIC: 580,25)
    - **Rute BTH (Batam)**: ARIMAX(2, 0, 3) + Lebaran (AIC: 518,82)
    - **Rute PKU (Pekanbaru)**: ARIMAX(0, 1, 3) + Lebaran (AIC: 400,29)
    - **Rute DJB (Jambi)**: ARIMAX(3, 0, 3) + Lebaran (AIC: 413,98)
    - **Rute TNJ (Tanjungpinang)**: ARIMAX(3, 0, 3) + Lebaran (AIC: 371,96)
    - **Rute TJB (Karimun)**: ARIMAX(3, 0, 3) + Lebaran (AIC: 426,35)

---

### BAB V: EVALUASI MODEL
*Bagian ini membuktikan bahwa model akurat dan andal.*

* **V.1 Metrik Pengukuran Akurasi**
  - Menggunakan rumus:
    - **MAE** (*Mean Absolute Error*)
    - **RMSE** (*Root Mean Squared Error*)
    - **MAPE** (*Mean Absolute Percentage Error*)
* **V.2 Hasil Evaluasi pada Periode Uji (Lebaran 2026)**
  - Masukkan tabel perbandingan metrik evaluasi per rute (bisa disalin dari file `hasil/model/ringkasan_model.csv`):
    - Skenario rolling 1 minggu: MAPE per rute 11,7% (PKU, terbaik) sampai 31,6% (TNJ, terlemah); model agregat Semua Rute 6,9%.
    - Skenario 25 minggu sekaligus: MAPE per rute 10,8% (PKU) sampai 32,1% (TNJ); BTH 31,0%; model agregat 10,0%. Beri catatan bahwa MAPE model agregat tidak sebanding dengan MAPE per rute: fluktuasi antar rute saling menutupi sehingga MAPE-nya lebih kecil, sedangkan MAE/RMSE-nya lebih besar karena skala totalnya jauh lebih besar. MAPE BTH tinggi karena lonjakan ATR 72 Juni–Juli 2025 pada data latih (tanpa ATR: 22,5%).
    - Rute berpenumpang sedikit membuat MAPE tampak besar meski selisih absolutnya kecil (MAE 5–8 penumpang per minggu).
* **V.3 Pembahasan Validasi Prediksi vs Aktual**
  - Bandingkan prediksi dengan aktual pada minggu Lebaran 2026 (9, 16, 23 Maret) secara jujur: model mengikuti arah kenaikan pada sebagian rute, tetapi koefisien Lebaran pada model hanya signifikan (p < 0,05) di DJB (p < 0,001) dan PKU (p = 0,028), sedangkan BTH, TJB, dan TNJ tidak signifikan, dan prediksi jauh sebelum Lebaran (25 minggu sekaligus) kurang akurat.
  *(Lampirkan grafik `hasil/model/model1_prediksi_per_rute.png` dan `model2_multistep_per_rute.png`)*.

---

### BAB VI: PENERAPAN & KESIMPULAN
*Bagian ini menjelaskan produk sistem yang dibuat dan rekomendasi kebijakan.*

* **VI.1 Desain Implementasi (Dashboard Web Interaktif)**
  - Sistem dibangun dengan arsitektur web: Flask (Python backend), RESTful API, Vanilla CSS (Modern Aerospace Theme), dan Chart.js interaktif.
  - Fitur sistem:
    1. Pemilih rute dinamis (5 rute + agregat).
    2. Slider horizon proyeksi hingga 104 minggu ke depan.
    3. Kalkulator otomatis kebutuhan frekuensi *flight* armada Cessna 208B (12 kursi).
    4. Tab validasi historis dan penjelajah data.
* **VI.2 Rekomendasi Manajerial & Kesimpulan**
  - Kesimpulan: Model ARIMAX cukup baik untuk prediksi jangka pendek (rolling 1 minggu, MAPE 12–32% per rute), tetapi data baru sekitar 20 bulan dengan satu Lebaran pada data latih, sehingga prediksi jangka panjang dan efek Lebaran belum stabil.
  - Rekomendasi untuk UPBU Dabo Singkep:
    - Pada minggu Lebaran, jumlah flight per minggu pada data naik sekitar 1 flight per rute (mis. DJB 4,1 menjadi 5,0; TJB 4,0 menjadi 5,0) dan penumpang naik paling besar pada TJB, DJB, dan PKU. Usulkan flight tambahan pada minggu H-1 sampai H+1 Lebaran terutama untuk rute tersebut, dan gunakan dashboard (batas atas 95%) untuk menentukan jumlahnya.
    - Rute Batam tidak menunjukkan lonjakan Lebaran yang jelas, jadi tidak perlu penambahan khusus Lebaran.
    - Pada periode reguler, keterisian kursi rata-rata sekitar 79% (Cessna 12 kursi); Karimun (60,8%) masih longgar.

---

### LAMPIRAN
1. Cuplikan sampel data mentah log penerbangan.
2. Screenshot antarmuka Dashboard Web (Halaman Peramalan, Validasi, Evaluasi, dan Explorer).
3. Kode skrip utama pemodelan (`scripts/model_arimax.py`).

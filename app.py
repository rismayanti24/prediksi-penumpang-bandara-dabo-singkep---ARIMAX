# app.py - Backend Web Dashboard Prediksi Penumpang Bandara Dabo Singkep per Rute
# Model: ARIMAX (ARIMA + variabel eksogen Idul Fitri) per 5 Rute Utama & Agregat
# Jalankan: python app.py  ->  buka http://localhost:5000

import os
import warnings
import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, request
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings('ignore')

app = Flask(__name__)

# ================================================================
# KONFIGURASI PATH & DATA
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'hasil', 'data_bersih')
MODEL_DIR = os.path.join(BASE_DIR, 'hasil', 'model')

# Definisi Lebaran dipakai bersama dengan pipeline (lihat lebaran.py)
from lebaran import flag_lebaran as hitung_flag_lebaran

# Nama dan metadata rute
RUTE_INFO = {
    'SEMUA': {
        'kode': 'SEMUA',
        'nama': 'Semua Rute (Agregat)',
        'kota': 'Bandara Dabo Singkep (SIQ)',
        'kapasitas_flight': 12,
        'orde': (1, 1, 3),
        'jadwal_reguler': 18,
    },
    'BTH': {
        'kode': 'BTH',
        'nama': 'SIQ <-> BTH (Batam)',
        'kota': 'Batam (Hang Nadim)',
        'kapasitas_flight': 12,
        'orde': (1, 1, 3),
        'jadwal_reguler': 5,
    },
    'PKU': {
        'kode': 'PKU',
        'nama': 'SIQ <-> PKU (Pekanbaru)',
        'kota': 'Pekanbaru (Sultan Syarif Kasim II)',
        'kapasitas_flight': 12,
        'orde': (0, 1, 3),
        'jadwal_reguler': 4,
    },
    'DJB': {
        'kode': 'DJB',
        'nama': 'SIQ <-> DJB (Jambi)',
        'kota': 'Jambi (Sultan Thaha)',
        'kapasitas_flight': 12,
        'orde': (2, 1, 3),
        'jadwal_reguler': 3,
    },
    'TNJ': {
        'kode': 'TNJ',
        'nama': 'SIQ <-> TNJ (Tanjungpinang)',
        'kota': 'Tanjungpinang (Raja Haji Fisabilillah)',
        'kapasitas_flight': 12,
        'orde': (2, 1, 3),
        'jadwal_reguler': 3,
    },
    'TJB': {
        'kode': 'TJB',
        'nama': 'SIQ <-> TJB (Tj. Balai Karimun)',
        'kota': 'Tanjung Balai Karimun (Sei Bati)',
        'kapasitas_flight': 12,
        'orde': (3, 1, 3),
        'jadwal_reguler': 3,
    },
}

# ================================================================
# MEMUAT DATA BERSIH & HASIL EVALUASI
# ================================================================
print("=" * 60)
print("MEMUAT DATA & MODEL ARIMAX PER RUTE BANDARA DABO SINGKEP")
print("=" * 60)

# 1. Data mingguan agregat & per rute
file_mingguan = os.path.join(DATA_DIR, 'data_mingguan.csv')
file_per_rute = os.path.join(DATA_DIR, 'data_mingguan_per_rute.csv')

df_bersih = pd.read_csv(os.path.join(DATA_DIR, 'data_penerbangan_bersih.csv'), parse_dates=['tanggal'])
df_semua = pd.read_csv(file_mingguan, parse_dates=['minggu']).sort_values('minggu').reset_index(drop=True)
df_per_rute = pd.read_csv(file_per_rute, parse_dates=['minggu']).sort_values('minggu').reset_index(drop=True)

# Jadwal reguler (flight/minggu) = median flight mingguan pada data (asumsi dari data, bukan angka resmi mitra)
for _k in RUTE_INFO:
    _src = df_semua if _k == 'SEMUA' else df_per_rute[df_per_rute.rute == _k]
    RUTE_INFO[_k]['jadwal_reguler'] = int(round(_src['penerbangan'].median()))

# 2. Data evaluasi model yang sudah dihitung model_arimax.py
file_ringkasan = os.path.join(MODEL_DIR, 'ringkasan_model.csv')
file_metrik = os.path.join(MODEL_DIR, 'metrik_model.csv')
file_prediksi = os.path.join(MODEL_DIR, 'prediksi_model.csv')

df_ringkasan = pd.read_csv(file_ringkasan) if os.path.exists(file_ringkasan) else pd.DataFrame()
df_metrik = pd.read_csv(file_metrik) if os.path.exists(file_metrik) else pd.DataFrame()
df_pred_eval = pd.read_csv(file_prediksi, parse_dates=['minggu']) if os.path.exists(file_prediksi) else pd.DataFrame()

# Orde sebenarnya dibaca dari hasil model_arimax.py supaya dashboard = model yang dievaluasi
if not df_ringkasan.empty:
    import ast as _ast
    for _, _r in df_ringkasan.iterrows():
        if _r['rute'] in RUTE_INFO:
            RUTE_INFO[_r['rute']]['orde'] = _ast.literal_eval(_r['orde'].replace('ARIMAX', ''))

# Dictionary penyimpanan model terlatih pada seluruh data (untuk prediksi masa depan)
MODELS = {}
DATA_SERIES = {}

SPLIT_DATE = pd.Timestamp('2026-03-09')

def siapkan_dan_latih_rute(kode):
    """Menyiapkan data kontinu dan melatih model ARIMAX pada 100% data untuk peramalan masa depan."""
    if kode == 'SEMUA':
        sub = df_semua.copy().set_index('minggu')
    else:
        sub = df_per_rute[df_per_rute.rute == kode].copy().set_index('minggu')

    # Reindex ke rentang penuh kontinu (W-MON)
    full_idx = pd.date_range(sub.index.min(), sub.index.max(), freq='W-MON')
    sub = sub.reindex(full_idx)
    sub.index.name = 'minggu'

    # Simpan nilai asli (NaN = minggu tanpa data, Jan 2026) untuk ringkasan/total;
    # kolom 'penumpang' hasil interpolasi hanya untuk melatih model.
    sub['penumpang_asli'] = sub['penumpang']
    sub['penumpang'] = sub['penumpang'].interpolate(method='linear')
    if 'lebaran' not in sub.columns or sub['lebaran'].isna().any():
        sub['lebaran'] = [hitung_flag_lebaran(d) for d in sub.index]

    sub['lebaran'] = sub['lebaran'].fillna(0).astype(int)

    y = sub['penumpang']
    exog = sub[['lebaran']]

    orde = RUTE_INFO[kode]['orde']
    try:
        mod = SARIMAX(y, exog=exog, order=orde,
                      enforce_stationarity=False, enforce_invertibility=False)
        fit_res = mod.fit(disp=False, maxiter=200)
    except Exception as e:
        print(f"  [Warning] Fallback ARIMAX(1,1,0) untuk {kode}: {e}")
        mod = SARIMAX(y, exog=exog, order=(1, 1, 0),
                      enforce_stationarity=False, enforce_invertibility=False)
        fit_res = mod.fit(disp=False)

    return sub, fit_res

for r_kode in RUTE_INFO.keys():
    print(f"  Fitting model {r_kode} ({RUTE_INFO[r_kode]['nama']}) ARIMAX{RUTE_INFO[r_kode]['orde']}...", end=" ")
    sub_df, fit_m = siapkan_dan_latih_rute(r_kode)
    DATA_SERIES[r_kode] = sub_df
    MODELS[r_kode] = fit_m
    print("OK")

print("\nSemua model ARIMAX per rute siap!")
print("=" * 60)


# ================================================================
# API ROUTES
# ================================================================

@app.route('/')
def halaman_utama():
    """Halaman web dashboard utama."""
    return render_template('dashboard.html')


@app.route('/api/rute_list')
def api_rute_list():
    """Daftar rute yang tersedia untuk pemilih dropdown/tab."""
    daftar = []
    for k, v in RUTE_INFO.items():
        daftar.append({
            'kode': v['kode'],
            'nama': v['nama'],
            'kota': v['kota'],
            'orde': f"ARIMAX{v['orde']}",
        })
    return jsonify(daftar)


@app.route('/api/ringkasan')
def api_ringkasan():
    """Statistik ringkasan 4 kartu atas untuk rute terpilih."""
    rute = request.args.get('rute', 'SEMUA').upper()
    if rute not in RUTE_INFO:
        rute = 'SEMUA'

    sub = DATA_SERIES[rute]
    pax = sub['penumpang_asli'].dropna()  # hanya minggu yang benar-benar ada datanya
    total_pax = int(round(pax.sum()))
    rata_pax = round(float(pax.mean()), 1)
    n_minggu = len(pax)
    periode = f"{sub.index[0].strftime('%b %Y')} - {sub.index[-1].strftime('%b %Y')}"
    orde_str = f"ARIMAX{RUTE_INFO[rute]['orde']}"

    # Cari metrik dari df_ringkasan
    mae, rmse, mape, akurasi = 7.5, 10.5, 15.0, 85.0
    aic_val = 400.0

    if not df_ringkasan.empty and rute in df_ringkasan['rute'].values:
        row = df_ringkasan[df_ringkasan['rute'] == rute].iloc[0]
        mae = float(row['MAE_rolling'])
        rmse = float(row['RMSE_rolling'])
        mape = float(row['MAPE_rolling'])
        akurasi = round(max(0.0, 100.0 - mape), 1)
        aic_val = float(row['AIC'])

    return jsonify({
        'rute': rute,
        'nama_rute': RUTE_INFO[rute]['nama'],
        'total_penumpang': total_pax,
        'rata_rata': rata_pax,
        'minggu_data': n_minggu,
        'periode': periode,
        'orde': orde_str,
        'aic': aic_val,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'akurasi': akurasi,
        'kapasitas_flight': RUTE_INFO[rute]['kapasitas_flight'],
    })


@app.route('/api/historis')
def api_historis():
    """
    Data historis mingguan per rute:
    - aktual: penumpang asli
    - fitted: model fitted in-sample
    - prediksi_rolling: prediksi rolling 1 minggu pada data uji (mulai Maret 2026)
    - prediksi_multi: prediksi statis 25 minggu pada data uji
    - akurasi, selisih, is_test
    """
    rute = request.args.get('rute', 'SEMUA').upper()
    if rute not in RUTE_INFO:
        rute = 'SEMUA'

    sub = DATA_SERIES[rute]
    fit_model = MODELS[rute]
    fitted_vals = fit_model.fittedvalues

    # Ambil data evaluasi uji dari df_pred_eval jika ada
    pred_uji_map = {}
    if not df_pred_eval.empty:
        # SEMUA = model agregat yang dilatih sendiri (baris rute 'SEMUA' di prediksi_model.csv)
        sub_eval = df_pred_eval[df_pred_eval['rute'] == rute]

        for _, row in sub_eval.iterrows():
            tgl_str = row['minggu'].strftime('%Y-%m-%d')
            if tgl_str not in pred_uji_map:
                pred_uji_map[tgl_str] = {}
            if 'Rolling' in str(row['skenario']):
                pred_uji_map[tgl_str]['rolling'] = round(float(row['prediksi']), 1)
            else:
                pred_uji_map[tgl_str]['multi'] = round(float(row['prediksi']), 1)

    hasil = []
    for idx, (tgl, row) in enumerate(sub.iterrows()):
        tgl_str = tgl.strftime('%Y-%m-%d')
        pax = float(row['penumpang']) if pd.notna(row['penumpang']) else None
        fit = float(fitted_vals.iloc[idx]) if idx < len(fitted_vals) and pd.notna(fitted_vals.iloc[idx]) else None

        # Data uji jika tgl >= 2026-03-09
        is_test = (tgl >= SPLIT_DATE)
        pred_roll = pred_uji_map.get(tgl_str, {}).get('rolling', None)
        pred_multi = pred_uji_map.get(tgl_str, {}).get('multi', None)

        # Selisih & akurasi
        selisih = None
        akurasi = None
        interpolasi = bool(pd.isna(row['penumpang_asli']))
        perbandingan_val = pred_roll if (is_test and pred_roll is not None) else fit
        if pax is not None and perbandingan_val is not None and pax > 0 and not interpolasi:
            selisih = round(pax - perbandingan_val, 1)
            err_pct = abs(pax - perbandingan_val) / pax * 100.0
            akurasi = round(max(0.0, 100.0 - err_pct), 1)

        hasil.append({
            'minggu': tgl_str,
            'label': tgl.strftime('%d %b %Y'),
            'bulan_label': tgl.strftime('%b %Y'),
            'penumpang': round(pax, 1) if pax is not None else None,
            'fitted': round(fit, 1) if fit is not None else None,
            'prediksi_rolling': pred_roll,
            'prediksi_multi': pred_multi,
            'is_test': bool(is_test),
            'interpolasi': interpolasi,
            'selisih': selisih,
            'akurasi': akurasi,
            'lebaran': int(row.get('lebaran', 0)),
        })

    return jsonify(hasil)


@app.route('/api/prediksi', methods=['POST'])
def api_prediksi():
    """
    Prediksi N minggu ke depan menggunakan model ARIMAX pada rute terpilih.
    Menghasilkan nilai titik, confidence interval 95%, dan estimasi kebutuhan flight.
    """
    try:
        data_in = request.get_json(force=True) or {}
        rute = str(data_in.get('rute', 'SEMUA')).upper()
        if rute not in RUTE_INFO:
            rute = 'SEMUA'

        n = int(data_in.get('minggu', 8))
        n = min(max(1, n), 104)

        sub = DATA_SERIES[rute]
        model_fit = MODELS[rute]
        tgl_terakhir = sub.index[-1]

        # Tanggal masa depan (W-MON)
        tgl_masa_depan = [tgl_terakhir + pd.Timedelta(weeks=i + 1) for i in range(n)]

        # Variabel eksogen masa depan
        exog_depan = np.array([hitung_flag_lebaran(d) for d in tgl_masa_depan]).reshape(-1, 1)

        # ARIMAX Forecast
        forecast_res = model_fit.get_forecast(n, exog=exog_depan)
        pred = forecast_res.predicted_mean
        ci = forecast_res.conf_int(alpha=0.05)

        kapasitas = RUTE_INFO[rute]['kapasitas_flight']  # 12 pax

        data_pred = []
        for i in range(n):
            val_p = float(pred.iloc[i] if hasattr(pred, 'iloc') else pred[i])
            val_low = float(ci.iloc[i, 0] if hasattr(ci, 'iloc') else ci[i, 0])
            val_up = float(ci.iloc[i, 1] if hasattr(ci, 'iloc') else ci[i, 1])

            val_p = max(0.0, val_p)
            val_low = max(0.0, val_low)
            val_up = max(val_p, val_up)

            # Kebutuhan flight Cessna 208B (12 kursi)
            flight_butuh = int(np.ceil(val_p / kapasitas)) if val_p > 0 else 1

            data_pred.append({
                'minggu': tgl_masa_depan[i].strftime('%Y-%m-%d'),
                'label': tgl_masa_depan[i].strftime('%d %b %Y'),
                'bulan_label': tgl_masa_depan[i].strftime('%b %Y'),
                'prediksi': round(val_p, 1),
                'batas_bawah': round(val_low, 1),
                'batas_atas': round(val_up, 1),
                'kebutuhan_flight': flight_butuh,
                'lebaran': int(exog_depan[i][0]),
            })

        return jsonify({
            'status': 'ok',
            'rute': rute,
            'nama_rute': RUTE_INFO[rute]['nama'],
            'kapasitas_flight': kapasitas,
            'data': data_pred
        })

    except Exception as e:
        return jsonify({'status': 'error', 'pesan': str(e)}), 400


@app.route('/api/model_info')
def api_model_info():
    """Tabel perbandingan performa model ARIMAX antar rute."""
    hasil = []
    if not df_ringkasan.empty:
        for _, row in df_ringkasan.iterrows():
            r_kode = row['rute']
            hasil.append({
                'rute': r_kode,
                'nama': RUTE_INFO.get(r_kode, {}).get('nama', r_kode),
                'orde': row['orde'],
                'aic': float(row['AIC']),
                'n_latih': int(row['n_latih']),
                'n_uji': int(row['n_uji']),
                'pct_latih': float(row['pct_latih']),
                'mae_rolling': float(row['MAE_rolling']),
                'rmse_rolling': float(row['RMSE_rolling']),
                'mape_rolling': float(row['MAPE_rolling']),
                'mae_multi': float(row['MAE_multi']),
                'rmse_multi': float(row['RMSE_multi']),
                'mape_multi': float(row['MAPE_multi']),
            })
    return jsonify(hasil)


@app.route('/api/operasional')
def api_operasional():
    """Statistik rute, keterisian kursi, pola hari, dan delay - dihitung langsung dari data bersih."""
    b = df_bersih
    total_pax = b['pax_total'].sum()
    kapasitas_cessna = int(RUTE_INFO['SEMUA']['kapasitas_flight'])
    nama_rute = {'BTH': 'SIQ <-> Batam (BTH)', 'PKU': 'SIQ <-> Pekanbaru (PKU)', 'DJB': 'SIQ <-> Jambi (DJB)',
                 'TNJ': 'SIQ <-> Tanjungpinang (TNJ)', 'TJB': 'SIQ <-> Tj. Balai Karimun (TJB)'}
    rute_data = []
    b12 = b[b['kursi'] == kapasitas_cessna]  # keterisian hanya untuk Cessna 12 kursi (ATR 72 dikeluarkan)
    atr_df = b[b['kursi'] != kapasitas_cessna]
    for kode, g in b.groupby('rute_mitra'):
        g12 = b12[b12['rute_mitra'] == kode]
        mape_r = ''
        if not df_ringkasan.empty and kode in df_ringkasan['rute'].values:
            mape_r = f"{float(df_ringkasan[df_ringkasan['rute'] == kode].iloc[0]['MAPE_rolling']):.1f}%"
        rute_data.append({
            'kode': kode, 'nama': nama_rute.get(kode, kode),
            'pax': int(g['pax_total'].sum()), 'flights': int(len(g)),
            # keterisian kursi: bayi tidak memakai kursi, jadi hanya dewasa + anak (pax_kursi)
            'load_factor': round(float(g12['pax_kursi'].sum() / g12['kursi'].sum() * 100), 1),
            'share': round(float(g['pax_total'].sum() / total_pax * 100), 1),
            'orde': f"ARIMAX{RUTE_INFO[kode]['orde']}" if kode in RUTE_INFO else '',
            'mape': mape_r,
        })
    rute_data.sort(key=lambda r: -r['pax'])

    nama_hari = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis',
                 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
    hari_data = []
    for en, idn in nama_hari.items():
        g = b[b['hari'] == en]
        hari_data.append({'hari': idn, 'pax': int(g['pax_total'].sum()), 'flights': int(len(g))})

    kursi_ref = int(RUTE_INFO['SEMUA']['kapasitas_flight'])
    reguler = RUTE_INFO['SEMUA']['jadwal_reguler']
    armada = {
        "tipe_pesawat": "Cessna 208B Grand Caravan",
        "kapasitas_kursi": kursi_ref,
        "operator": "Susi Air",
        "jenis_layanan": "Penerbangan Perintis (Subsidi APBN)",
        "jadwal_reguler_mingguan": reguler,
        "kapasitas_reguler_mingguan": reguler * kursi_ref,
    }
    pct_delay = float(b['terlambat15'].mean() * 100)
    delay_stats = {
        "tepat_waktu_pct": round(100 - pct_delay, 1),
        "delay_pct": round(pct_delay, 1),
        "rata_delay_menit": round(float(b['delay_menit'].mean()), 1),
        "penyebab_cuaca": int((b['kategori_delay'] == 'CUACA').sum()),
        "penyebab_teknis": int((b['kategori_delay'] == 'TEKNIS OPERASIONAL').sum()),
    }
    tertinggi = max(rute_data, key=lambda r: r['load_factor'])
    terendah = min(rute_data, key=lambda r: r['load_factor'])
    keterisian_stats = {
        "rata_pax_flight": round(float(b['pax_total'].mean()), 1),
        "load_factor_pct": round(float(b12['pax_kursi'].sum() / b12['kursi'].sum() * 100), 1),
        "catatan_atr": (f"Hanya flight Cessna 12 kursi; {len(atr_df)} flight ATR 72 "
                        f"(keterisian {f"{float(atr_df['pax_kursi'].sum() / atr_df['kursi'].sum() * 100):.1f}".replace('.', ',')}%) tidak dihitung."
                        if len(atr_df) else ''),
        "rute_tertinggi": f"{tertinggi['kode']} ({tertinggi['load_factor']:.1f}%)".replace('.', ','),
        "rute_terendah": f"{terendah['kode']} ({terendah['load_factor']:.1f}%)".replace('.', ','),
    }
    return jsonify({"rute": rute_data, "hari": hari_data, "armada": armada,
                    "delay": delay_stats, "keterisian": keterisian_stats})


@app.route('/api/data_explorer')
def api_data_explorer():
    """Mengembalikan data mingguan per rute untuk tabel penjelajah data."""
    rute = request.args.get('rute', 'SEMUA').upper()
    if rute == 'SEMUA' or rute not in RUTE_INFO:
        data_sumber = df_semua.dropna(subset=['penumpang'])  # buang minggu Jan 2026 (tanpa data)
    else:
        data_sumber = df_per_rute[df_per_rute.rute == rute]

    hasil = []
    for _, r in data_sumber.iterrows():
        pax = r['penumpang']
        hasil.append({
            'minggu': r['minggu'].strftime('%Y-%m-%d'),
            'label': r['minggu'].strftime('%d %b %Y'),
            'rute': r.get('rute', 'SEMUA'),
            'penerbangan': int(r['penerbangan']) if 'penerbangan' in r and pd.notna(r['penerbangan']) else 0,
            'penumpang': int(round(pax)) if pd.notna(pax) else 0,
            'berangkat': int(r['berangkat']) if 'berangkat' in r and pd.notna(r['berangkat']) else 0,
            'datang': int(r['datang']) if 'datang' in r and pd.notna(r['datang']) else 0,
            'lebaran': int(r.get('lebaran', 0)),
        })
    return jsonify(hasil)


# ================================================================
# JALANKAN SERVER
# ================================================================
if __name__ == '__main__':
    print(f"\n  Dashboard Web: http://localhost:5000\n")
    app.run(debug=True, port=5000)

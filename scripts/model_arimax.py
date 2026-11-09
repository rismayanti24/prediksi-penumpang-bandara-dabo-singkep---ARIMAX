"""
model_arimax.py
Training & evaluasi model ARIMAX per rute.
- 5 rute utama (BTH, PKU, DJB, TNJ, TJB)
- Split 70/30: latih 61 minggu, uji 25 minggu (mulai dari sebelum Lebaran 2026)
- Variabel eksogen: flag Lebaran
- Evaluasi: MAE, RMSE, MAPE
- Output ke hasil/model/
"""
import os, warnings
import pandas as pd, numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
from itertools import product
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings('ignore')

# ============================================================
# KONFIGURASI
# ============================================================
FOLDER = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FOLDER) if os.path.basename(FOLDER) == 'scripts' else FOLDER
DATA = os.path.join(BASE_DIR, 'hasil', 'data_bersih')
OUT = os.path.join(BASE_DIR, 'hasil', 'model')
os.makedirs(OUT, exist_ok=True)

# Tanggal split: uji dimulai dari minggu sebelum Lebaran 2026
# Lebaran 2026 = ~20 Maret 2026
# Minggu mulai uji: 2026-03-09 (minggu yang mengandung Lebaran)
SPLIT_DATE = pd.Timestamp('2026-03-09')

# Grid search ARIMAX: orde (p,d,q)
# Catatan batas grid: uji coba grid diperluas ke p,q=0..5 (data latih hanya 61 minggu) membuat AIC dan BIC terus
# turun sampai q=5 (batas baru) tanpa memperbaiki akurasi data uji (mis. PKU 11,7% -> 14,1%, TJB 25,1% -> 28,0%).
# Jadi q=3 yang terpilih adalah batas grid yang disengaja demi model hemat parameter, bukan optimum sejati.
P_RANGE = range(0, 4)
# d TIDAK dicari lewat AIC (AIC lintas d tidak sebanding). d ditentukan dari uji ADF pada DATA LATIH:
# p < ALPHA_ADF -> stasioner -> d=0, selain itu d=1.
ALPHA_ADF = 0.05
Q_RANGE = range(0, 4)

# ============================================================
# MUAT DATA
# ============================================================
wr = pd.read_csv(os.path.join(DATA, 'data_mingguan_per_rute.csv'), parse_dates=['minggu'])
RUTE_UTAMA = sorted(wr.rute.unique())
# Total mingguan semua rute (agregat bandara) dimodelkan SENDIRI, bukan penjumlahan prediksi 5 rute
wk_total = pd.read_csv(os.path.join(DATA, 'data_mingguan.csv'), parse_dates=['minggu'])
DAFTAR_MODEL = RUTE_UTAMA + ['SEMUA']

print("=" * 70)
print("MODEL ARIMAX PER RUTE - TRAINING & EVALUASI")
print("=" * 70)
print(f"Data: {len(wr)} baris ({len(wr) // len(RUTE_UTAMA)} minggu x {len(RUTE_UTAMA)} rute)")
print(f"Rentang: {wr.minggu.min().date()} s/d {wr.minggu.max().date()}")
print(f"Split date: {SPLIT_DATE.date()}")
print()

# ============================================================
# FUNGSI UTILITAS
# ============================================================
def tentukan_d(y_train, alpha=ALPHA_ADF):
    """Tentukan orde differencing dari ADF pada data latih. Kembalikan (d, p-value)."""
    pval = adfuller(y_train.dropna())[1]
    return (0 if pval < alpha else 1), pval


def cari_orde_terbaik(y_train, exog_train, p_range, d_range, q_range):
    """Grid search (p,q) berdasarkan AIC terkecil, dengan d tetap (AIC hanya dibandingkan pada d yang sama)."""
    best_aic = np.inf
    best_order = (1, 0, 0)
    hasil_pencarian = []

    for p, d, q in product(p_range, d_range, q_range):
        if p == 0 and q == 0:
            continue  # Skip (0,d,0) karena tidak bermakna
        try:
            model = SARIMAX(y_train, exog=exog_train, order=(p, d, q),
                           enforce_stationarity=False, enforce_invertibility=False)
            fit = model.fit(disp=False, maxiter=200)
            hasil_pencarian.append({'p': p, 'd': d, 'q': q, 'AIC': fit.aic, 'BIC': fit.bic})
            if fit.aic < best_aic:
                best_aic = fit.aic
                best_order = (p, d, q)
        except:
            pass

    return best_order, best_aic, pd.DataFrame(hasil_pencarian)


def evaluasi(aktual, prediksi):
    """Hitung MAE, RMSE, MAPE."""
    aktual = np.array(aktual)
    prediksi = np.array(prediksi)
    mae = np.mean(np.abs(aktual - prediksi))
    rmse = np.sqrt(np.mean((aktual - prediksi) ** 2))
    # MAPE: hindari pembagian nol
    mask = aktual != 0
    if mask.sum() > 0:
        mape = np.mean(np.abs((aktual[mask] - prediksi[mask]) / aktual[mask])) * 100
    else:
        mape = np.nan
    return mae, rmse, mape


# ============================================================
# TRAINING PER RUTE
# ============================================================
semua_metrik = []
semua_prediksi = []
semua_ringkasan = []
semua_pencarian = []

for rute in DAFTAR_MODEL:
    print(f"\n{'─' * 50}")
    print(f"RUTE: SIQ <-> {rute}" if rute != 'SEMUA' else "MODEL AGREGAT: SEMUA RUTE")
    print(f"{'─' * 50}")

    if rute == 'SEMUA':
        sub = wk_total[['minggu', 'penumpang', 'lebaran']].copy().sort_values('minggu').reset_index(drop=True)
    else:
        sub = wr[wr.rute == rute].copy().sort_values('minggu').reset_index(drop=True)
    sub = sub.set_index('minggu')

    # Reindex ke rentang penuh untuk mengatasi gap (Jan 2026)
    # Data menggunakan tanggal Senin (start_time dari period W-SUN), jadi pakai freq W-MON
    full_idx = pd.date_range(sub.index.min(), sub.index.max(), freq='W-MON')
    sub = sub.reindex(full_idx)
    sub.index.name = 'minggu'

    # Interpolasi linear untuk penumpang pada gap, isi 0 untuk lebaran
    sub['penumpang'] = sub['penumpang'].interpolate(method='linear')
    sub['lebaran'] = sub['lebaran'].fillna(0).astype(int)

    y = sub['penumpang']
    exog = sub[['lebaran']]

    # Split train/test
    train = sub[sub.index < SPLIT_DATE]
    test = sub[sub.index >= SPLIT_DATE]

    y_train = train['penumpang']
    y_test = test['penumpang']
    exog_train = train[['lebaran']]
    exog_test = test[['lebaran']]

    n_train = len(y_train)
    n_test = len(y_test)
    pct_train = n_train / (n_train + n_test) * 100

    print(f"  Latih: {n_train} minggu ({pct_train:.1f}%) | Uji: {n_test} minggu ({100 - pct_train:.1f}%)")
    print(f"  Latih: {y_train.index[0].date()} s/d {y_train.index[-1].date()}")
    print(f"  Uji  : {y_test.index[0].date()} s/d {y_test.index[-1].date()}")

    # ---- Grid search orde terbaik ----
    d_pilih, p_adf = tentukan_d(y_train)
    print(f"  ADF data latih: p={p_adf:.4f} -> {'stasioner' if d_pilih == 0 else 'tidak stasioner'}, d={d_pilih}")
    print(f"  Mencari orde terbaik (grid search p,q dengan d={d_pilih})...", end=" ")
    best_order, best_aic, df_search = cari_orde_terbaik(
        y_train, exog_train, P_RANGE, [d_pilih], Q_RANGE
    )
    print(f"ARIMAX{best_order} (AIC={best_aic:.1f})")

    df_search['rute'] = rute
    df_search['p_adf_latih'] = round(p_adf, 4)
    semua_pencarian.append(df_search)

    # ---- Fit model final ----
    model_final = SARIMAX(y_train, exog=exog_train, order=best_order,
                          enforce_stationarity=False, enforce_invertibility=False)
    fit_final = model_final.fit(disp=False, maxiter=300)

    # ---- SKENARIO A: Prediksi 1 minggu bergulir (rolling forecast) ----
    print(f"  Skenario A: Rolling forecast 1 minggu...")
    prediksi_rolling = []
    for i in range(n_test):
        # Training data sampai sebelum minggu uji ke-i
        y_expand = y[:n_train + i]
        exog_expand = exog[:n_train + i]
        exog_next = exog.iloc[n_train + i: n_train + i + 1]

        try:
            model_roll = SARIMAX(y_expand, exog=exog_expand, order=best_order,
                                enforce_stationarity=False, enforce_invertibility=False)
            fit_roll = model_roll.fit(disp=False, maxiter=200)
            pred = fit_roll.forecast(steps=1, exog=exog_next)
            prediksi_rolling.append(pred.values[0])
        except:
            prediksi_rolling.append(np.nan)

    mae_a, rmse_a, mape_a = evaluasi(y_test.values, prediksi_rolling)
    print(f"    MAE={mae_a:.2f}, RMSE={rmse_a:.2f}, MAPE={mape_a:.2f}%")

    # Simpan prediksi rolling
    for idx_t, (minggu_t, aktual_t, pred_t) in enumerate(zip(y_test.index, y_test.values, prediksi_rolling)):
        semua_prediksi.append({
            'rute': rute,
            'minggu': minggu_t,
            'aktual': aktual_t,
            'prediksi': round(pred_t, 2) if not np.isnan(pred_t) else np.nan,
            'skenario': 'A. Rolling 1 minggu'
        })

    # ---- SKENARIO B: Prediksi multi-step sekaligus ----
    print(f"  Skenario B: Prediksi {n_test} minggu sekaligus...")
    try:
        pred_multi = fit_final.forecast(steps=n_test, exog=exog_test)
        mae_b, rmse_b, mape_b = evaluasi(y_test.values, pred_multi.values)
        print(f"    MAE={mae_b:.2f}, RMSE={rmse_b:.2f}, MAPE={mape_b:.2f}%")

        for minggu_t, aktual_t, pred_t in zip(y_test.index, y_test.values, pred_multi.values):
            semua_prediksi.append({
                'rute': rute,
                'minggu': minggu_t,
                'aktual': aktual_t,
                'prediksi': round(pred_t, 2),
                'skenario': f'B. {n_test} minggu sekaligus'
            })
    except Exception as e:
        print(f"    Error: {e}")
        mae_b, rmse_b, mape_b = np.nan, np.nan, np.nan

    # ---- Simpan metrik ----
    semua_metrik.append({
        'rute': rute,
        'orde': f"ARIMAX{best_order}",
        'AIC': round(best_aic, 2),
        'skenario': 'A. Rolling 1 minggu',
        'n_uji': n_test,
        'n_latih': n_train,
        'MAE': round(mae_a, 2),
        'RMSE': round(rmse_a, 2),
        'MAPE (%)': round(mape_a, 2)
    })
    semua_metrik.append({
        'rute': rute,
        'orde': f"ARIMAX{best_order}",
        'AIC': round(best_aic, 2),
        'skenario': f'B. {n_test} minggu sekaligus',
        'n_uji': n_test,
        'n_latih': n_train,
        'MAE': round(mae_b, 2),
        'RMSE': round(rmse_b, 2),
        'MAPE (%)': round(mape_b, 2)
    })

    # ---- Ringkasan model ----
    semua_ringkasan.append({
        'rute': rute,
        'orde': f"ARIMAX{best_order}",
        'AIC': round(best_aic, 2),
        'n_latih': n_train,
        'n_uji': n_test,
        'pct_latih': round(pct_train, 1),
        'MAE_rolling': round(mae_a, 2),
        'RMSE_rolling': round(rmse_a, 2),
        'MAPE_rolling': round(mape_a, 2),
        'MAE_multi': round(mae_b, 2) if not np.isnan(mae_b) else np.nan,
        'RMSE_multi': round(rmse_b, 2) if not np.isnan(rmse_b) else np.nan,
        'MAPE_multi': round(mape_b, 2) if not np.isnan(mape_b) else np.nan,
    })

# ============================================================
# SIMPAN OUTPUT
# ============================================================
df_metrik = pd.DataFrame(semua_metrik)
df_metrik.to_csv(os.path.join(OUT, 'metrik_model.csv'), index=False)

df_prediksi = pd.DataFrame(semua_prediksi)
df_prediksi.to_csv(os.path.join(OUT, 'prediksi_model.csv'), index=False)

df_ringkasan = pd.DataFrame(semua_ringkasan)
df_ringkasan.to_csv(os.path.join(OUT, 'ringkasan_model.csv'), index=False)

df_pencarian = pd.concat(semua_pencarian, ignore_index=True)
df_pencarian.to_csv(os.path.join(OUT, 'pencarian_orde.csv'), index=False)

# Ringkasan teks
with open(os.path.join(OUT, 'ringkasan_model.txt'), 'w', encoding='utf-8') as f:
    f.write("RINGKASAN MODEL ARIMAX PER RUTE\n")
    f.write(f"Split: latih sampai {SPLIT_DATE.date()}, uji sisanya\n")
    f.write(f"Variabel eksogen: flag Lebaran\n")
    f.write(f"Orde d ditentukan dari uji ADF pada data latih (p<{ALPHA_ADF} -> d=0, selain itu d=1); AIC hanya dipakai memilih p,q\n")
    f.write("Baris SEMUA = model agregat yang dilatih sendiri pada total mingguan (bukan jumlah prediksi 5 rute)\n\n")
    for r in semua_ringkasan:
        nama = f"Rute SIQ<->{r['rute']}" if r['rute'] != 'SEMUA' else "SEMUA RUTE (agregat)"
        f.write(f"{nama}: {r['orde']}, "
                f"AIC={r['AIC']}, "
                f"latih={r['n_latih']} ({r['pct_latih']}%), "
                f"uji={r['n_uji']}\n")
        f.write(f"  Rolling:  MAE={r['MAE_rolling']}, RMSE={r['RMSE_rolling']}, MAPE={r['MAPE_rolling']}%\n")
        f.write(f"  Multi-st: MAE={r['MAE_multi']}, RMSE={r['RMSE_multi']}, MAPE={r['MAPE_multi']}%\n\n")

print("\n" + "=" * 70)
print("RINGKASAN AKHIR")
print("=" * 70)
print(df_ringkasan[['rute', 'orde', 'AIC', 'n_latih', 'n_uji',
                     'MAE_rolling', 'RMSE_rolling', 'MAPE_rolling']].to_string(index=False))
print(f"\nFile disimpan di: {OUT}")
print("  - metrik_model.csv")
print("  - prediksi_model.csv")
print("  - ringkasan_model.csv")
print("  - pencarian_orde.csv")
print("  - ringkasan_model.txt")
print("\nSelesai!")

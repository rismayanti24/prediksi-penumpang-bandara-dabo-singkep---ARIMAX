"""
visualisasi_model.py
Menghasilkan grafik evaluasi model ARIMAX per rute.
Grafik disimpan ke folder hasil/model/:
1. model1_prediksi_per_rute.png     - Rolling forecast per rute (5 subplot)
2. model2_multistep_per_rute.png    - Multi-step forecast per rute
3. model3_perbandingan_metrik.png   - Perbandingan MAE/RMSE/MAPE antar rute
4. model4_error_per_rute.png        - Distribusi error per rute
"""
import os
import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============================================================
# KONFIGURASI
# ============================================================
FOLDER = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FOLDER) if os.path.basename(FOLDER) == 'scripts' else FOLDER
DATA = os.path.join(BASE_DIR, 'hasil', 'data_bersih')
MODEL = os.path.join(BASE_DIR, 'hasil', 'model')

# Cek file
for f in ['metrik_model.csv', 'prediksi_model.csv', 'ringkasan_model.csv']:
    if not os.path.exists(os.path.join(MODEL, f)):
        raise SystemExit(f'{f} tidak ditemukan di {MODEL}. Jalankan model_arimax.py dulu.')

# Muat data
wr = pd.read_csv(os.path.join(DATA, 'data_mingguan_per_rute.csv'), parse_dates=['minggu'])
df_pred = pd.read_csv(os.path.join(MODEL, 'prediksi_model.csv'), parse_dates=['minggu'])
df_metrik = pd.read_csv(os.path.join(MODEL, 'metrik_model.csv'))
df_ringkasan = pd.read_csv(os.path.join(MODEL, 'ringkasan_model.csv'))
# Grafik di file ini khusus 5 rute; baris model agregat 'SEMUA' tidak ikut digambar
df_pred = df_pred[df_pred.rute != 'SEMUA']
df_metrik = df_metrik[df_metrik.rute != 'SEMUA']
df_ringkasan = df_ringkasan[df_ringkasan.rute != 'SEMUA']

RUTE_UTAMA = sorted(wr.rute.unique())
NAMA_RUTE = {
    'BTH': 'Batam (BTH)', 'PKU': 'Pekanbaru (PKU)', 'DJB': 'Jambi (DJB)',
    'TNJ': 'Tanjungpinang (TNJ)', 'TJB': 'Tj. Balai Karimun (TJB)'
}
WARNA_RUTE = {
    'BTH': '#2a78d6', 'PKU': '#e85d3a', 'DJB': '#34a853',
    'TNJ': '#f4a742', 'TJB': '#9c27b0'
}

# Tema
SURF = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; GRID = '#e4e3df'
plt.rcParams.update({
    'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF,
    'text.color': INK, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.edgecolor': GRID, 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.family': 'DejaVu Sans'
})

print("=" * 60)
print("VISUALISASI MODEL ARIMAX PER RUTE")
print("=" * 60)

# ============================================================
# GRAFIK 1: Rolling Forecast per Rute (5 subplot)
# ============================================================
fig, axes = plt.subplots(3, 2, figsize=(15, 12))
axes_flat = axes.flatten()

pred_rolling = df_pred[df_pred.skenario == 'A. Rolling 1 minggu']

for i, rute in enumerate(RUTE_UTAMA):
    ax = axes_flat[i]
    
    # Data aktual lengkap
    aktual = wr[wr.rute == rute].sort_values('minggu')
    # Minggu Jan 2026 tidak punya data: sisipkan NaN agar garis terputus (bukan tampak seperti data nyata)
    aktual = aktual.set_index('minggu').penumpang
    aktual = aktual.reindex(pd.date_range(aktual.index.min(), aktual.index.max(), freq='W-MON'))
    ax.plot(aktual.index, aktual.values, color='#333', lw=1.5, label='Aktual', alpha=0.7)
    
    # Prediksi rolling
    pred = pred_rolling[pred_rolling.rute == rute].sort_values('minggu')
    ax.plot(pred.minggu, pred.prediksi, color=WARNA_RUTE[rute], lw=2, 
            marker='o', markersize=3, label='Prediksi ARIMAX')
    
    # Garis split
    split_date = pred.minggu.min()
    ax.axvline(split_date, color='#999', ls='--', lw=1)
    ax.text(split_date, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 100,
            '  Mulai uji', fontsize=8, color=INK2, va='top')
    
    # Jan 2026
    ax.axvspan(pd.Timestamp('2025-12-29'), pd.Timestamp('2026-02-01'),
               color='#d9d8d3', alpha=0.4, lw=0, label='Jan 2026: tanpa data (diinterpolasi hanya untuk melatih)')
    
    # Metrik
    r_info = df_ringkasan[df_ringkasan.rute == rute].iloc[0]
    ax.set_title(f'{NAMA_RUTE[rute]} | {r_info.orde}',
                 fontsize=11, fontweight='bold')
    ax.text(0.98, 0.95,
            f'MAE={r_info.MAE_rolling:.1f}\nMAPE={r_info.MAPE_rolling:.1f}%',
            transform=ax.transAxes, ha='right', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=GRID, alpha=0.9))
    
    ax.set_ylabel('Penumpang/minggu' if i % 2 == 0 else '')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.legend(fontsize=7.5, loc='upper left')

# Sembunyikan subplot kosong
axes_flat[-1].set_visible(False)

fig.suptitle('Prediksi Rolling 1 Minggu vs Aktual per Rute',
             fontsize=14, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(MODEL, 'model1_prediksi_per_rute.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] model1_prediksi_per_rute.png")

# ============================================================
# GRAFIK 2: Multi-step Forecast per Rute
# ============================================================
pred_multi = df_pred[df_pred.skenario != 'A. Rolling 1 minggu']

if len(pred_multi) > 0:
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    axes_flat = axes.flatten()

    for i, rute in enumerate(RUTE_UTAMA):
        ax = axes_flat[i]
        
        pred = pred_multi[pred_multi.rute == rute].sort_values('minggu')
        
        ax.plot(pred.minggu, pred.aktual, color='#333', lw=2, marker='o',
                markersize=4, label='Aktual')
        ax.plot(pred.minggu, pred.prediksi, color=WARNA_RUTE[rute], lw=2,
                marker='s', markersize=4, label='Prediksi ARIMAX', ls='--')
        
        # Area error
        ax.fill_between(pred.minggu, pred.aktual, pred.prediksi,
                        alpha=0.15, color=WARNA_RUTE[rute])
        
        r_info = df_ringkasan[df_ringkasan.rute == rute].iloc[0]
        ax.set_title(f'{NAMA_RUTE[rute]} | {r_info.orde}',
                     fontsize=11, fontweight='bold')
        ax.text(0.98, 0.95,
                f'MAE={r_info.MAE_multi:.1f}\nMAPE={r_info.MAPE_multi:.1f}%',
                transform=ax.transAxes, ha='right', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=GRID, alpha=0.9))
        
        ax.set_ylabel('Penumpang/minggu' if i % 2 == 0 else '')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=3))
        ax.legend(fontsize=8, loc='upper left')

    axes_flat[-1].set_visible(False)
    fig.suptitle('Prediksi Multi-step Sekaligus vs Aktual per Rute',
                 fontsize=14, fontweight='bold', y=1.01)
    fig.tight_layout()
    fig.savefig(os.path.join(MODEL, 'model2_multistep_per_rute.png'), dpi=160, bbox_inches='tight')
    plt.close()
    print("[OK] model2_multistep_per_rute.png")

# ============================================================
# GRAFIK 3: Perbandingan Metrik Antar Rute
# ============================================================
met_roll = df_metrik[df_metrik.skenario == 'A. Rolling 1 minggu'].copy()

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
metrik_cols = ['MAE', 'RMSE', 'MAPE (%)']
metrik_labels = ['MAE (penumpang/minggu)', 'RMSE (penumpang/minggu)', 'MAPE (%)']
colors = [WARNA_RUTE[r] for r in met_roll.rute]

for idx, (col, label) in enumerate(zip(metrik_cols, metrik_labels)):
    ax = axes[idx]
    rute_labels = [NAMA_RUTE.get(r, r) for r in met_roll.rute]
    bars = ax.barh(rute_labels, met_roll[col].values, color=colors, height=0.5)
    for bar, v in zip(bars, met_roll[col].values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{v:.1f}', va='center', fontsize=10, fontweight='bold', color=INK2)
    ax.set_xlabel(label, fontsize=10)
    ax.set_title(col, fontsize=12, fontweight='bold')
    ax.grid(axis='y', visible=False)
    ax.invert_yaxis()

fig.suptitle('Perbandingan Metrik ARIMAX per Rute (Rolling Forecast)',
             fontsize=14, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(MODEL, 'model3_perbandingan_metrik.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] model3_perbandingan_metrik.png")

# ============================================================
# GRAFIK 4: Distribusi Error per Rute
# ============================================================
fig, axes = plt.subplots(1, len(RUTE_UTAMA), figsize=(16, 4), sharey=True)

for i, rute in enumerate(RUTE_UTAMA):
    ax = axes[i]
    pred = pred_rolling[pred_rolling.rute == rute]
    error = pred.aktual - pred.prediksi
    
    ax.hist(error, bins=12, color=WARNA_RUTE[rute], edgecolor=SURF, alpha=0.85)
    ax.axvline(0, color='#333', lw=1.5, ls='--')
    ax.set_title(rute, fontsize=11, fontweight='bold')
    ax.set_xlabel('Error (aktual - prediksi)')
    if i == 0:
        ax.set_ylabel('Frekuensi')
    ax.grid(axis='x', visible=False)
    
    # Mean error
    me = error.mean()
    ax.text(0.95, 0.92, f'ME={me:.1f}', transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color=INK2,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=GRID, alpha=0.9))

fig.suptitle('Distribusi Error Prediksi per Rute (Rolling)',
             fontsize=13, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(MODEL, 'model4_error_per_rute.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] model4_error_per_rute.png")

print(f"\nSemua grafik disimpan di: {MODEL}")
print("Selesai!")

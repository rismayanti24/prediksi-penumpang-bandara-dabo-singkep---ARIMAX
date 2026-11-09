import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.dates as mdates
import os

# ============================================================
# KONFIGURASI
# ============================================================
FOLDER = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FOLDER) if os.path.basename(FOLDER) == 'scripts' else FOLDER
DATA = os.path.join(BASE_DIR, 'hasil', 'data_bersih')
OUT = os.path.join(BASE_DIR, 'hasil', 'eda')
os.makedirs(OUT, exist_ok=True)

# Cek ketersediaan data
for f in ['data_penerbangan_bersih.csv', 'data_mingguan_per_rute.csv', 'data_harian.csv']:
    if not os.path.exists(os.path.join(DATA, f)):
        raise SystemExit(f'File {f} tidak ditemukan di {DATA}. Jalankan clean.py dulu.')

fl = pd.read_csv(os.path.join(DATA, 'data_penerbangan_bersih.csv'), parse_dates=['tanggal'])
wr = pd.read_csv(os.path.join(DATA, 'data_mingguan_per_rute.csv'), parse_dates=['minggu'])
dy = pd.read_csv(os.path.join(DATA, 'data_harian.csv'), parse_dates=['tanggal'])
wk_total = pd.read_csv(os.path.join(DATA, 'data_mingguan.csv'), parse_dates=['minggu'])

RUTE_UTAMA = sorted(wr.rute.unique())
NAMA_RUTE = {
    'BTH': 'Batam (BTH)', 'PKU': 'Pekanbaru (PKU)', 'DJB': 'Jambi (DJB)',
    'TNJ': 'Tanjungpinang (TNJ)', 'TJB': 'Tj. Balai Karimun (TJB)'
}
WARNA_RUTE = {
    'BTH': '#2a78d6', 'PKU': '#e85d3a', 'DJB': '#34a853',
    'TNJ': '#f4a742', 'TJB': '#9c27b0'
}

# ============================================================
# TEMA GRAFIK
# ============================================================
SURF = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; GRID = '#e4e3df'
plt.rcParams.update({
    'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF,
    'text.color': INK, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.edgecolor': GRID, 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.family': 'DejaVu Sans'
})

def judul(ax, t, sub=None):
    ax.set_title(t, loc='left', fontsize=13, fontweight='bold', color=INK, pad=26 if sub else 12)
    if sub:
        ax.text(0, 1.03, sub, transform=ax.transAxes, fontsize=10, color=INK2, va='bottom')

print("=" * 60)
print("EXPLORATORY DATA ANALYSIS - PER RUTE")
print("=" * 60)

# ============================================================
# EDA 1: Tren penumpang mingguan SEMUA RUTE (overlay)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 5.5))
for rute in RUTE_UTAMA:
    sub = wr[wr.rute == rute].set_index('minggu').penumpang
    sub = sub.reindex(pd.date_range(sub.index.min(), sub.index.max(), freq='W-MON'))  # NaN di Jan 2026 -> garis terputus
    ax.plot(sub.index, sub.values, color=WARNA_RUTE[rute], lw=1.8, label=NAMA_RUTE[rute], alpha=0.85)
# Blok Januari 2026
ax.axvspan(pd.Timestamp('2025-12-29'), pd.Timestamp('2026-02-01'), color='#d9d8d3', alpha=0.5, lw=0)
ax.text(pd.Timestamp('2026-01-14'), ax.get_ylim()[1] * 0.92, 'Jan 2026:\ntidak ada\ndata',
        ha='center', va='top', fontsize=9, color=INK2)
ax.set_ylabel('Penumpang per minggu')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
judul(ax, 'Tren penumpang mingguan per rute', 'Datang + berangkat, dewasa + anak + bayi | minggu Senin-Minggu')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda1_tren_per_rute.png'), dpi=160)
plt.close()
print("[OK] eda1_tren_per_rute.png")

# ============================================================
# EDA 2: Perbandingan total penumpang per rute (bar chart)
# ============================================================
totals = wr.groupby('rute').agg(
    penumpang=('penumpang', 'sum'),
    penerbangan=('penerbangan', 'sum')
).sort_values('penumpang')

fig, ax = plt.subplots(figsize=(10, 4.6))
labels = [NAMA_RUTE.get(r, r) for r in totals.index]
colors = [WARNA_RUTE.get(r, '#2a78d6') for r in totals.index]
ax.barh(labels, totals.penumpang, color=colors, height=0.62)
for y, (v, c) in enumerate(zip(totals.penumpang, totals.penerbangan)):
    ax.text(v + 40, y, f"{int(v):,} penumpang | {int(c)} penerbangan".replace(',', '.'),
            va='center', fontsize=9, color=INK2)
ax.set_xlim(0, totals.penumpang.max() * 1.45)
ax.grid(axis='y', visible=False)
ax.set_xlabel(f'Total penumpang ({wr.minggu.nunique()} minggu penuh berdata, Jan 2025 - Agu 2026; tanpa Jan 2026 dan minggu parsial)')
judul(ax, 'Total penumpang per rute', f'{len(RUTE_UTAMA)} rute utama dari/ke Bandara Dabo Singkep (SIQ)')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda2_total_per_rute.png'), dpi=160)
plt.close()
print("[OK] eda2_total_per_rute.png")

# ============================================================
# EDA 3: Boxplot penumpang per minggu tiap rute
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))
data_box = [wr[wr.rute == r].penumpang.values for r in RUTE_UTAMA]
labels_box = [NAMA_RUTE.get(r, r) for r in RUTE_UTAMA]
bp = ax.boxplot(data_box, tick_labels=labels_box, patch_artist=True, widths=0.5,
                medianprops=dict(color=INK, lw=2))
for patch, r in zip(bp['boxes'], RUTE_UTAMA):
    patch.set_facecolor(WARNA_RUTE[r])
    patch.set_alpha(0.7)
ax.set_ylabel('Penumpang per minggu')
ax.grid(axis='x', visible=False)
# Tambahkan label mean
for i, r in enumerate(RUTE_UTAMA):
    m = wr[wr.rute == r].penumpang.mean()
    ax.text(i + 1, m, f'  {m:.0f}', va='center', ha='left', fontsize=9, color=INK2, fontweight='bold')
judul(ax, 'Sebaran penumpang mingguan per rute', 'Boxplot menunjukkan median, kuartil, dan pencilan')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda3_boxplot_per_rute.png'), dpi=160)
plt.close()
print("[OK] eda3_boxplot_per_rute.png")

# ============================================================
# EDA 4: Proporsi penumpang berangkat vs datang per rute
# ============================================================
fig, ax = plt.subplots(figsize=(10, 4.6))
rute_sort = sorted(RUTE_UTAMA)
brkt = [wr[wr.rute == r].penumpang_berangkat.sum() for r in rute_sort]
dtng = [wr[wr.rute == r].penumpang_datang.sum() for r in rute_sort]
labels_r = [NAMA_RUTE.get(r, r) for r in rute_sort]
x = np.arange(len(rute_sort))
w = 0.35
b1 = ax.bar(x - w/2, brkt, w, label='Berangkat (SIQ->Rute)', color='#2a78d6', alpha=0.85)
b2 = ax.bar(x + w/2, dtng, w, label='Datang (Rute->SIQ)', color='#e85d3a', alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(labels_r, fontsize=9)
ax.set_ylabel('Total penumpang')
ax.legend(fontsize=9)
ax.grid(axis='x', visible=False)
for bar_group in [b1, b2]:
    for bar in bar_group:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 20, f'{int(h):,}'.replace(',', '.'),
                ha='center', va='bottom', fontsize=8, color=INK2)
judul(ax, 'Penumpang berangkat vs datang per rute', f'Total kumulatif {wr.minggu.nunique()} minggu penuh berdata (tanpa Jan 2026 dan minggu parsial di ujung data)')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda4_berangkat_datang.png'), dpi=160)
plt.close()
print("[OK] eda4_berangkat_datang.png")

# ============================================================
# EDA 5: Distribusi delay per rute
# ============================================================
fig, axes = plt.subplots(1, len(RUTE_UTAMA), figsize=(16, 4), sharey=True)
for i, rute in enumerate(RUTE_UTAMA):
    ax = axes[i]
    sub = fl[fl.rute_mitra == rute]
    x = sub.delay_menit.clip(-30, 120)
    ax.hist(x, bins=np.arange(-30, 125, 5), color=WARNA_RUTE[rute], edgecolor=SURF, linewidth=0.5, alpha=0.85)
    ax.axvline(15, color='#333', lw=1.5, ls='--')
    ax.set_title(rute, fontsize=11, fontweight='bold')
    ax.set_xlabel('Delay (menit)')
    if i == 0:
        ax.set_ylabel('Jumlah penerbangan')
    persen = sub.terlambat15.mean() * 100
    ax.text(0.95, 0.92, f'{persen:.0f}% telat', transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color=INK2,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=GRID, alpha=0.9))
    ax.grid(axis='x', visible=False)
fig.suptitle('Sebaran keterlambatan per rute', fontsize=13, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda5_delay_per_rute.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] eda5_delay_per_rute.png")

# ============================================================
# EDA 6: Efek Lebaran per rute
#   - Warna batang Lebaran dibuat khusus (abu tua) supaya tidak sama dengan warna rute mana pun.
#   - BTH: minggu yang memuat penerbangan ATR 72 (lonjakan Jun-Jul 2025, bukan efek musiman)
#     mendongkrak rata-rata "normal", sehingga efek Lebaran tampak 0%. Untuk BTH ditampilkan
#     juga batang "Normal tanpa ATR" dan persentase kenaikan dihitung terhadap batang itu.
# ============================================================
WARNA_LEBARAN = '#3d3d3d'
fl_atr = fl[(fl.kursi == 72) | fl.tipe_pesawat.astype(str).str.startswith('ATR')]
# minggu ATR dihitung per rute (ATR hanya terbang di rute yang memuat penerbangan ATR)
minggu_atr_rute = {r: set((g.tanggal - pd.to_timedelta(g.tanggal.dt.weekday, unit='D')).unique())
                   for r, g in fl_atr.groupby('rute_mitra')}

fig, axes = plt.subplots(1, len(RUTE_UTAMA), figsize=(17, 4.8), sharey=False)
for i, rute in enumerate(RUTE_UTAMA):
    ax = axes[i]
    sub = wr[wr.rute == rute]
    normal = sub[sub.lebaran == 0].penumpang
    lebaran = sub[sub.lebaran == 1].penumpang
    minggu_atr = minggu_atr_rute.get(rute, set())
    ada_atr = len(minggu_atr) > 0
    if ada_atr:
        normal_bersih = sub[(sub.lebaran == 0) & ~sub.minggu.isin(minggu_atr)].penumpang
        labels = ['Normal', 'Normal\ntanpa ATR', 'Lebaran']
        means = [normal.mean(), normal_bersih.mean(), lebaran.mean()]
        warna = [WARNA_RUTE[rute], WARNA_RUTE[rute], WARNA_LEBARAN]
        alphas = [0.45, 0.9, 0.9]
        pembanding = means[1]
    else:
        labels = ['Normal', 'Lebaran']
        means = [normal.mean(), lebaran.mean()]
        warna = [WARNA_RUTE[rute], WARNA_LEBARAN]
        alphas = [0.9, 0.9]
        pembanding = means[0]
    bars = ax.bar(labels, means, color=warna, width=0.55)
    for bar, al in zip(bars, alphas):
        bar.set_alpha(al)
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.6, f'{val:.0f}',
                ha='center', va='bottom', fontsize=10, color=INK, fontweight='bold')
    ax.set_title(rute, fontsize=11, fontweight='bold')
    ax.set_ylabel('Rata-rata penumpang/minggu' if i == 0 else '')
    ax.grid(axis='x', visible=False)
    ax.margins(y=0.30)
    if pembanding > 0:
        pct = (means[-1] - pembanding) / pembanding * 100
        ket = f'{pct:+.0f}%' + (' (vs normal tanpa ATR)' if ada_atr else '')
        ax.text(0.5, 0.95, ket, transform=ax.transAxes, ha='center', va='top', fontsize=10,
                color='#b8452f' if pct > 0 else '#2a78d6', fontweight='bold')
fig.suptitle('Efek Lebaran pada penumpang per rute',
             fontsize=13, fontweight='bold', y=1.02)
fig.text(0.5, -0.03, 'Lebaran = minggu Idul Fitri ±1 minggu. "Tanpa ATR" = tanpa minggu yang memuat penerbangan ATR 72 (Jun-Jul 2025); '
         'lonjakan itu bukan efek musiman.', ha='center', fontsize=9, color=INK2)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda6_efek_lebaran.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] eda6_efek_lebaran.png")

# ============================================================
# EDA 7: Heatmap korelasi antar rute (penumpang mingguan)
# ============================================================
pivot = wr.pivot(index='minggu', columns='rute', values='penumpang')
corr = pivot.corr().round(2)

fig, ax = plt.subplots(figsize=(7, 5.5))
im = ax.imshow(corr.values, cmap='RdYlBu_r', vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.index)))
ax.set_xticklabels(corr.columns, fontsize=10)
ax.set_yticklabels(corr.index, fontsize=10)
for i in range(len(corr)):
    for j in range(len(corr)):
        txt_color = 'white' if abs(corr.values[i, j]) > 0.6 else INK
        ax.text(j, i, f'{corr.values[i, j]:.2f}', ha='center', va='center',
                fontsize=11, color=txt_color, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8, label='Korelasi Pearson')
judul(ax, 'Korelasi penumpang antar rute (mingguan)')
ax.set_aspect('equal')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda7_korelasi_antar_rute.png'), dpi=160)
plt.close()
print("[OK] eda7_korelasi_antar_rute.png")
print("\nMatriks korelasi antar rute:")
print(corr)

# ============================================================
# EDA 8: Stasioneritas & ACF per rute (teks + grafik)
# ============================================================
from statsmodels.tsa.stattools import adfuller, acf

print("\n" + "=" * 60)
print("UJI STASIONERITAS (ADF) & ACF PER RUTE")
print("=" * 60)

SPLIT_ADF = pd.Timestamp('2026-03-09')  # sama dengan model_arimax.py


def deret_latih(pax_per_minggu):
    """Deret yang dipakai model: reindex mingguan penuh, interpolasi Jan 2026, hanya data LATIH."""
    s = pax_per_minggu.reindex(pd.date_range(pax_per_minggu.index.min(), pax_per_minggu.index.max(), freq='W-MON'))
    s = s.interpolate(method='linear')
    return s[s.index < SPLIT_ADF]


# Deret BTH tanpa penerbangan ATR 72 (sama dengan model_bth_tanpa_atr.py)
is_atr = fl.tipe_pesawat.astype(str).str.startswith('ATR') | (fl.kursi == 72)
f_b = fl[(fl.rute_mitra == 'BTH') & ~is_atr].copy()
f_b['minggu'] = f_b.tanggal - pd.to_timedelta(f_b.tanggal.dt.weekday, unit='D')
bth_minggu = wr[wr.rute == 'BTH'].set_index('minggu').index
pax_bth_tanpa_atr = f_b.groupby('minggu').pax_total.sum().reindex(bth_minggu).fillna(0)

# 5 rute + panel ke-6: BTH tanpa ATR (lonjakan ATR membuat ADF BTH kurang bisa dipercaya)
daftar = [(r, wr[wr.rute == r].set_index('minggu').penumpang, WARNA_RUTE[r]) for r in RUTE_UTAMA]
daftar.append(('BTH tanpa ATR', pax_bth_tanpa_atr, WARNA_RUTE['BTH']))

print("(ADF dihitung pada DATA LATIH saja, deret yang sama dengan model: interpolasi Jan 2026)")
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes_flat = axes.flatten()

for i, (nama, pax, warna) in enumerate(daftar):
    ax = axes_flat[i]
    sub = deret_latih(pax)

    # ADF test
    adf_result = adfuller(sub, result_object=False)
    pval = adf_result[1]
    stasioner = "STASIONER (d=0)" if pval < 0.05 else "TIDAK STASIONER (d=1)"
    print(f"  {nama}: ADF p-value = {pval:.4f} -> {stasioner}  (n={len(sub)})")

    # ACF
    acf_vals = acf(sub, nlags=min(15, len(sub) - 1))
    ax.bar(range(len(acf_vals)), acf_vals, color=warna, alpha=0.8, width=0.6)
    # Confidence interval (95%)
    ci = 1.96 / np.sqrt(len(sub))
    ax.axhline(ci, color='#999', ls='--', lw=1)
    ax.axhline(-ci, color='#999', ls='--', lw=1)
    ax.axhline(0, color=INK, lw=0.5)
    ax.set_title(f'{nama} (ADF p={pval:.3f})', fontsize=11, fontweight='bold')
    ax.set_xlabel('Lag (minggu)')
    if i % 3 == 0:
        ax.set_ylabel('ACF')

fig.suptitle('ACF per rute (data latih, sampai Mar 2026)', fontsize=13, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'eda8_acf_per_rute.png'), dpi=160, bbox_inches='tight')
plt.close()
print("[OK] eda8_acf_per_rute.png")

# ============================================================
# Statistik ringkas per rute (teks)
# ============================================================
print("\n" + "=" * 60)
print("STATISTIK RINGKAS PER RUTE")
print("=" * 60)
for rute in RUTE_UTAMA:
    sub = wr[wr.rute == rute]
    sub_fl = fl[fl.rute_mitra == rute]
    print(f"\n--- {NAMA_RUTE[rute]} ---")
    print(f"  Minggu: {len(sub)} | Penerbangan total: {sub.penerbangan.sum()}")
    print(f"  Penumpang/minggu: mean={sub.penumpang.mean():.1f}, std={sub.penumpang.std():.1f}, "
          f"min={sub.penumpang.min()}, max={sub.penumpang.max()}")
    print(f"  Penumpang/penerbangan: mean={sub_fl.pax_total.mean():.1f}")
    print(f"  Delay rata-rata: {sub_fl.delay_menit.mean():.1f} menit | "
          f"Terlambat >15min: {sub_fl.terlambat15.mean()*100:.1f}%")
    print(f"  Lebaran effect: normal={sub[sub.lebaran==0].penumpang.mean():.1f} vs "
          f"lebaran={sub[sub.lebaran==1].penumpang.mean():.1f}")

print(f"\n\nSemua grafik disimpan di: {OUT}")
print("Selesai!")

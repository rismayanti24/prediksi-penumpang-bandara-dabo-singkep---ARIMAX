"""
model_bth_tanpa_atr.py
Analisis sensitivitas rute BTH: apakah lonjakan Juni-Juli 2025 (penerbangan ATR 72 milik Wings Abadi,
72 kursi) mengganggu model?

Dua versi deret BTH dibandingkan dengan prosedur yang sama persis seperti model_arimax.py
(grid search AIC pada data latih, rolling 1 minggu, dan 25 minggu sekaligus):
  A. Semua penerbangan (versi utama di model_arimax.py)
  B. Hanya Cessna 208B (tanpa ATR 72)
Data uji (Mar-Agu 2026) tidak memuat ATR 72, jadi metrik kedua versi sebanding.

Output (hasil/model/): perbandingan_bth_tanpa_atr.csv dan model5_bth_tanpa_atr.png
Hasil utama (ringkasan_model.csv dll.) TIDAK diubah.
"""
import os, warnings
from itertools import product
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "hasil", "data_bersih")
OUT = os.path.join(BASE, "hasil", "model")
SPLIT = pd.Timestamp("2026-03-09")

wr = pd.read_csv(os.path.join(DATA, "data_mingguan_per_rute.csv"), parse_dates=["minggu"])
fl = pd.read_csv(os.path.join(DATA, "data_penerbangan_bersih.csv"), parse_dates=["tanggal"])

bth_asli = wr[wr.rute == "BTH"].set_index("minggu")
minggu_ada = bth_asli.index

# Deret B: buang penerbangan ATR 72, agregasi mingguan dengan cara yang sama (minggu mulai Senin)
# ATR dikenali dari tipe ATAU kapasitas 72 kursi (jaga-jaga bila label tipe salah)
is_atr = fl.tipe_pesawat.str.startswith("ATR") | (fl.kursi == 72)
f = fl[(fl.rute_mitra == "BTH") & (~is_atr)].copy()
f["minggu"] = f.tanggal - pd.to_timedelta(f.tanggal.dt.weekday, unit="D")
pax_b = f.groupby("minggu").pax_total.sum().reindex(minggu_ada).fillna(0)

n_atr = int(fl[(fl.rute_mitra == "BTH") & is_atr].shape[0])
print(f"Penerbangan ATR 72 di rute BTH yang dikeluarkan pada versi B: {n_atr} flight")


def siapkan(pax):
    s = pd.DataFrame({"penumpang": pax, "lebaran": bth_asli["lebaran"]})
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="W-MON"))
    s["penumpang"] = s["penumpang"].interpolate(method="linear")
    s["lebaran"] = s["lebaran"].fillna(0).astype(int)
    return s


def metrik(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    return (np.mean(np.abs(a - p)), np.sqrt(np.mean((a - p) ** 2)), np.mean(np.abs(a - p) / a) * 100)


def jalankan(sub, nama):
    train, test = sub[sub.index < SPLIT], sub[sub.index >= SPLIT]
    nt, nu = len(train), len(test)
    # d ditentukan dari ADF pada data latih (sama dengan model_arimax.py); AIC hanya memilih p,q
    d_pilih = 0 if adfuller(train.penumpang.dropna())[1] < 0.05 else 1
    terbaik, orde = np.inf, (1, d_pilih, 0)
    for p, d, q in product(range(4), [d_pilih], range(4)):
        if p == 0 and q == 0:
            continue
        try:
            ft = SARIMAX(train.penumpang, exog=train[["lebaran"]], order=(p, d, q),
                         enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=200)
            if ft.aic < terbaik:
                terbaik, orde = ft.aic, (p, d, q)
        except Exception:
            pass
    final = SARIMAX(train.penumpang, exog=train[["lebaran"]], order=orde,
                    enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=300)
    multi = final.forecast(steps=nu, exog=test[["lebaran"]]).values
    roll = []
    for i in range(nu):
        try:
            m = SARIMAX(sub.penumpang[: nt + i], exog=sub[["lebaran"]][: nt + i], order=orde,
                        enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=200)
            roll.append(m.forecast(steps=1, exog=sub[["lebaran"]].iloc[nt + i: nt + i + 1]).values[0])
        except Exception:
            roll.append(np.nan)
    roll = np.array(roll)
    print(f"{nama}: ARIMAX{orde}, AIC={terbaik:.2f}")
    return orde, terbaik, test, roll, multi


hasil, seri = [], {}
for nama, pax in [("A. Semua penerbangan (versi utama)", bth_asli["penumpang"]),
                  ("B. Tanpa ATR 72 (hanya Cessna 208B)", pax_b)]:
    orde, aic, test, roll, multi = jalankan(siapkan(pax), nama)
    mr, mm = metrik(test.penumpang, roll), metrik(test.penumpang, multi)
    seri[nama] = (siapkan(pax), test, roll, multi)
    hasil.append({"versi": nama, "orde": f"ARIMAX{orde}", "AIC": round(aic, 2),
                  "MAE_rolling": round(mr[0], 2), "RMSE_rolling": round(mr[1], 2), "MAPE_rolling": round(mr[2], 2),
                  "MAE_multi": round(mm[0], 2), "RMSE_multi": round(mm[1], 2), "MAPE_multi": round(mm[2], 2)})

df = pd.DataFrame(hasil)
df.to_csv(os.path.join(OUT, "perbandingan_bth_tanpa_atr.csv"), index=False)
print(df.to_string(index=False))

# Grafik: deret + prediksi 25 minggu
fig, ax = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
(sa, ta, ra, ma), (sb, tb, rb, mb) = seri.values()
# Minggu tanpa data (Jan 2026, hanya diinterpolasi untuk melatih) tidak digambar agar garis terputus
ada = sa.index.isin(minggu_ada)
ax[0].plot(sa.index, sa.penumpang.where(ada), color="#9AA5B1", lw=1.8, label="Semua penerbangan")
ax[0].plot(sb.index, sb.penumpang.where(ada), color="#12355B", lw=2.2, label="Tanpa ATR 72")
ax[0].axvline(SPLIT, color="#8A97A5", ls="--", lw=1)
ax[0].text(SPLIT, ax[0].get_ylim()[1] * 0.97, " Mulai data uji", fontsize=9, color="#5B6B7B", va="top")
ax[0].set_title("Penumpang mingguan rute BTH", fontweight="bold", loc="left")
ax[0].set_ylabel("Penumpang per minggu"); ax[0].legend(frameon=False)
ax[1].plot(ta.index, ta.penumpang, color="#12355B", lw=2.2, label="Aktual")
ax[1].plot(ta.index, ma, color="#B8452F", ls="--", lw=2, label=f"Versi A, MAPE {hasil[0]['MAPE_multi']:.1f}%")
ax[1].plot(tb.index, mb, color="#2A7FBA", ls="--", lw=2, label=f"Versi B, MAPE {hasil[1]['MAPE_multi']:.1f}%")
ax[1].set_title("Prediksi 25 minggu sekaligus", fontweight="bold", loc="left"); ax[1].legend(frameon=False)
for a in ax:
    a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", color="#E3E8EE")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "model5_bth_tanpa_atr.png"), dpi=200, bbox_inches="tight")
print("Selesai. File: perbandingan_bth_tanpa_atr.csv, model5_bth_tanpa_atr.png")

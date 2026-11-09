# streamlit_app.py - Dashboard Prediksi Penumpang Bandara Dabo Singkep (versi Streamlit)
# Model: ARIMAX (ARIMA + variabel eksogen Idul Fitri) per rute dan agregat
# Jalankan: streamlit run streamlit_app.py

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Prediksi Penumpang Bandara Dabo Singkep",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================================
# KONFIGURASI
# ================================================================
BASE = Path(__file__).parent
DATA_DIR = BASE / "hasil" / "data_bersih"
MODEL_DIR = BASE / "hasil" / "model"
SPLIT_DATE = pd.Timestamp("2026-03-09")
KURSI = 12  # Cessna 208B Grand Caravan

# Definisi Lebaran dipakai bersama dengan pipeline (lihat lebaran.py)
from lebaran import flag_lebaran  # noqa: E402

RUTE = {
    "SEMUA": dict(nama="Semua rute (agregat)", orde=(1, 1, 3)),
    "BTH": dict(nama="Batam (BTH)", orde=(1, 1, 3)),
    "PKU": dict(nama="Pekanbaru (PKU)", orde=(0, 1, 3)),
    "DJB": dict(nama="Jambi (DJB)", orde=(2, 1, 3)),
    "TNJ": dict(nama="Tanjungpinang (TNJ)", orde=(2, 1, 3)),
    "TJB": dict(nama="Tj. Balai Karimun (TJB)", orde=(3, 1, 3)),
}
# Orde sebenarnya dibaca dari hasil model_arimax.py supaya dashboard = model yang dievaluasi
try:
    import ast as _ast
    for _, _r in pd.read_csv(MODEL_DIR / "ringkasan_model.csv").iterrows():
        if _r["rute"] in RUTE:
            RUTE[_r["rute"]]["orde"] = _ast.literal_eval(_r["orde"].replace("ARIMAX", ""))
except Exception:
    pass  # pakai orde bawaan di atas

HARI_ID = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
           "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}

# Palet: biru laut sebagai warna utama, kuning kunyit hanya untuk uji model / Lebaran
NAVY, SEA, SKY = "#12355B", "#2A7FBA", "#8FB8DE"
AMBER, BRICK, GRID = "#D9922B", "#B8452F", "#E3E8EE"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600&display=swap');
    html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
    #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }
    .judul { font-family: 'IBM Plex Serif', serif; font-size: 1.9rem; font-weight: 600;
             color: #12355B; line-height: 1.25; margin: 0; }
    .sub { color: #5B6B7B; font-size: 0.98rem; margin: .35rem 0 1.2rem 0; }
    [data-testid="stMetricLabel"] p { color: #5B6B7B; font-size: .85rem; }
    [data-testid="stMetricValue"] { color: #12355B; font-weight: 600; }
    div[data-baseweb="tab-list"] { gap: 1.5rem; border-bottom: 1px solid #E3E8EE; }
    button[data-baseweb="tab"] { padding: .6rem 0; font-weight: 500; }
    h3 { color: #12355B; font-weight: 600; font-size: 1.15rem !important; }
    .catatan { background: #F4F7FA; border-left: 3px solid #2A7FBA; padding: .75rem 1rem;
               border-radius: 4px; color: #35465A; font-size: .92rem; }
    .peringatan { background: #FBF3E6; border-left: 3px solid #D9922B; padding: .75rem 1rem;
               border-radius: 4px; color: #4A3a1c; font-size: .92rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ================================================================
# DATA & MODEL
# ================================================================
@st.cache_data(show_spinner=False)
def muat_data():
    mingguan = pd.read_csv(DATA_DIR / "data_mingguan.csv", parse_dates=["minggu"])
    per_rute = pd.read_csv(DATA_DIR / "data_mingguan_per_rute.csv", parse_dates=["minggu"])
    bersih = pd.read_csv(DATA_DIR / "data_penerbangan_bersih.csv", parse_dates=["tanggal"])
    ringkasan = pd.read_csv(MODEL_DIR / "ringkasan_model.csv")
    prediksi = pd.read_csv(MODEL_DIR / "prediksi_model.csv", parse_dates=["minggu"])
    orde = pd.read_csv(MODEL_DIR / "pencarian_orde.csv")
    return mingguan.sort_values("minggu"), per_rute.sort_values("minggu"), bersih, ringkasan, prediksi, orde


@st.cache_resource(show_spinner="Melatih model ARIMAX untuk setiap rute…")
def latih_semua():
    mingguan, per_rute, *_ = muat_data()
    hasil = {}
    for kode, info in RUTE.items():
        sub = mingguan.copy() if kode == "SEMUA" else per_rute[per_rute.rute == kode].copy()
        sub = sub.set_index("minggu")
        sub = sub.reindex(pd.date_range(sub.index.min(), sub.index.max(), freq="W-MON"))
        sub.index.name = "minggu"
        sub["penumpang_asli"] = sub["penumpang"]  # NaN = minggu tanpa data (Jan 2026); dipakai untuk total/ringkasan
        sub["penumpang"] = sub["penumpang"].interpolate(method="linear")  # hanya untuk melatih model
        sub["lebaran"] = [flag_lebaran(d) for d in sub.index]
        try:
            fit = SARIMAX(sub["penumpang"], exog=sub[["lebaran"]], order=info["orde"],
                          enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=200)
        except Exception:
            fit = SARIMAX(sub["penumpang"], exog=sub[["lebaran"]], order=(1, 1, 0),
                          enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        hasil[kode] = (sub, fit)
    return hasil


def metrik(aktual, pred):
    aktual, pred = np.asarray(aktual, float), np.asarray(pred, float)
    galat = aktual - pred
    return dict(MAE=np.mean(np.abs(galat)), RMSE=np.sqrt(np.mean(galat ** 2)),
                MAPE=np.mean(np.abs(galat) / aktual) * 100)


def evaluasi_rute(prediksi, kode):
    """Prediksi uji per skenario untuk satu rute (kode SEMUA = model agregat yang dilatih sendiri)."""
    return prediksi[prediksi.rute == kode]


def gaya(fig, tinggi=420):
    fig.update_layout(
        height=tinggi, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Sans, sans-serif", color="#35465A", size=13),
        legend=dict(orientation="h", y=1.12, x=0), hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def tandai_lebaran(fig, sub):
    for tgl in sub.index[sub["lebaran"] == 1]:
        fig.add_vrect(x0=tgl, x1=tgl + pd.Timedelta(days=7), fillcolor=AMBER, opacity=0.14, line_width=0)


# ================================================================
# MUAT
# ================================================================
try:
    mingguan, per_rute, bersih, ringkasan, prediksi, pencarian = muat_data()
except FileNotFoundError as e:
    st.error(f"File data tidak ditemukan: {e.filename}. Jalankan `python scripts/clean.py` dan "
             "`python scripts/model_arimax.py` dari folder project, lalu muat ulang halaman ini.")
    st.stop()

MODEL = latih_semua()

# Jumlah minggu uji dan rentang data diambil dari hasil, bukan ditulis tetap
N_UJI = int(ringkasan.n_uji.max())
BULAN_DATA = round((per_rute.minggu.max() - per_rute.minggu.min()).days / 30.44)

# Jadwal reguler bawaan = median jumlah flight mingguan di data (tahan terhadap lonjakan Lebaran)
REGULER = {r: int(round(per_rute[per_rute.rute == r].penerbangan.median())) for r in RUTE if r != "SEMUA"}
REGULER["SEMUA"] = int(round(mingguan.penerbangan.median()))

# ================================================================
# SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("### Pilih rute")
    kode = st.selectbox("Rute", list(RUTE), format_func=lambda k: RUTE[k]["nama"], label_visibility="collapsed")
    st.caption(f"Model: ARIMAX{RUTE[kode]['orde']}")
    reguler = st.number_input(
        "Jadwal reguler (flight per minggu)", 1, 80, REGULER[kode], key=f"reg_{kode}",
        help="Bawaan: median flight mingguan pada data. Ganti bila ada angka resmi dari UPBU. "
             "Berangkat dan datang dihitung sebagai flight terpisah.")
    st.divider()
    st.markdown("**Tentang data**")
    st.caption(
        "Log penerbangan perintis Susi Air (Cessna 208B, 12 kursi) di Bandara Dabo Singkep (SIQ), "
        "Januari 2025 – Agustus 2026, bersumber dari UPBU Dabo Singkep."
    )
    st.markdown("**Tentang model**")
    st.caption(
        f"Data latih sampai {(SPLIT_DATE - pd.Timedelta(days=7)).strftime('%d %b %Y')}, "
        f"data uji mulai {SPLIT_DATE.strftime('%d %b %Y')} (mencakup Lebaran 2026)."
    )
    st.divider()
    st.caption("Project Penambangan Data INF11121 · Teknik Informatika · UMRAH")

sub, fit = MODEL[kode]
info = RUTE[kode]

# ================================================================
# HEADER
# ================================================================
st.markdown('<p class="judul">Prediksi Penumpang Bandara Dabo Singkep</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="sub">{info["nama"]} · data {sub.index.min().strftime("%b %Y")} – '
    f'{sub.index.max().strftime("%b %Y")} · peramalan mingguan dengan ARIMAX</p>',
    unsafe_allow_html=True,
)

ev = evaluasi_rute(prediksi, kode)
roll = ev[ev.skenario.str.contains("Rolling")]
multi = ev[~ev.skenario.str.contains("Rolling")]
m_roll, m_multi = metrik(roll.aktual, roll.prediksi), metrik(multi.aktual, multi.prediksi)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Ringkasan", "Peramalan", "Evaluasi model", "Operasional", "Data"])

# ================================================================
# TAB 1 - RINGKASAN
# ================================================================
with tab1:
    pax = sub["penumpang_asli"].dropna()  # tanpa minggu hasil interpolasi
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total penumpang", f"{pax.sum():,.0f}".replace(",", "."),
              help=f"Jumlah penumpang pada {len(pax)} minggu penuh yang berdata. Tidak termasuk Jan 2026 dan minggu "
                   f"parsial di awal/akhir data, jadi lebih kecil dari total seluruh flight di tab Operasional.")
    k2.metric("Rata-rata per minggu", f"{pax.mean():.1f}")
    k3.metric("Puncak mingguan", f"{pax.max():.0f}", help=f"Minggu {pax.idxmax().strftime('%d %b %Y')}")
    k4.metric("Galat prediksi (MAPE)", f"{m_roll['MAPE']:.1f}%", help="Skenario rolling 1 minggu pada data uji")

    st.markdown("### Penumpang mingguan: aktual dan hasil model")
    fig = go.Figure()
    tandai_lebaran(fig, sub)
    fig.add_trace(go.Scatter(x=sub.index, y=sub["penumpang_asli"], name="Aktual", line=dict(color=NAVY, width=2.4)))
    fv = fit.fittedvalues.iloc[3:]
    fig.add_trace(go.Scatter(x=fv.index, y=fv.values, name="Model (data latih)", line=dict(color=SKY, width=1.8, dash="dot")))
    fig.add_trace(go.Scatter(x=roll.minggu, y=roll.prediksi, name="Prediksi rolling (data uji)",
                             line=dict(color=AMBER, width=2.4)))
    fig.add_shape(type="line", x0=SPLIT_DATE, x1=SPLIT_DATE, y0=0, y1=1, yref="paper",
                  line=dict(color="#8A97A5", width=1, dash="dash"))
    fig.add_annotation(x=SPLIT_DATE, y=1.0, yref="paper", text="Mulai data uji", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=12, color="#5B6B7B"))
    fig.update_yaxes(title="Penumpang per minggu")
    st.plotly_chart(gaya(fig), width="stretch")
    st.caption("Blok kuning menandai minggu Lebaran, yaitu ±1 minggu dari Idul Fitri. Garis aktual terputus pada "
               "Januari 2026 karena tidak ada penerbangan; total dan rata-rata hanya menghitung minggu yang ada datanya.")

    if kode == "SEMUA":
        st.markdown("### Kontribusi tiap rute")
        tot = per_rute.groupby("rute")["penumpang"].sum().sort_values()
        fig = go.Figure(go.Bar(x=tot.values, y=[RUTE[r]["nama"] for r in tot.index], orientation="h",
                               marker_color=SEA, text=[f"{v/tot.sum()*100:.1f}%" for v in tot.values],
                               textposition="outside"))
        fig.update_xaxes(title="Total penumpang")
        st.plotly_chart(gaya(fig, 300), width="stretch")

# ================================================================
# TAB 2 - PERAMALAN
# ================================================================
with tab2:
    c1, c2, c3 = st.columns([2, 2, 2])
    n = c1.slider("Horizon peramalan (minggu)", 4, 52, 12)
    dasar = c2.radio("Dasar kebutuhan flight", ["Prediksi", "Batas atas 95%"], horizontal=True,
                     help="Batas atas dipakai bila ingin perencanaan yang lebih aman.")
    lf = c3.slider("Target keterisian kursi (%)", 60, 100, 100, step=5,
                   help="100% berarti setiap flight diisi penuh 12 kursi.")

    tgl = [sub.index[-1] + pd.Timedelta(weeks=i + 1) for i in range(n)]
    ex = np.array([flag_lebaran(t) for t in tgl]).reshape(-1, 1)
    fc = fit.get_forecast(n, exog=ex)
    pm, ci = fc.predicted_mean.values, fc.conf_int(alpha=0.05).values
    f = pd.DataFrame({"minggu": tgl, "prediksi": np.maximum(pm, 0), "bawah": np.maximum(ci[:, 0], 0),
                      "atas": np.maximum(ci[:, 1], pm), "lebaran": ex.ravel()})
    basis = f["prediksi"] if dasar == "Prediksi" else f["atas"]
    f["butuh"] = np.maximum(1, np.ceil(basis / (KURSI * lf / 100))).astype(int)
    f["tambahan"] = np.maximum(0, f["butuh"] - reguler)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total prediksi", f"{f.prediksi.sum():,.0f}".replace(",", "."))
    m2.metric("Minggu puncak", f.loc[f.prediksi.idxmax(), "minggu"].strftime("%d %b %Y"),
              f"{f.prediksi.max():.0f} penumpang", delta_color="off")
    m3.metric("Minggu butuh flight tambahan", f"{(f.tambahan > 0).sum()} dari {n}",
              f"maks +{int(f.tambahan.max())} flight/minggu", delta_color="off")

    fig = go.Figure()
    riwayat = sub.iloc[-26:]
    fig.add_trace(go.Scatter(x=riwayat.index, y=riwayat.penumpang, name="Aktual", line=dict(color=NAVY, width=2.4)))
    fig.add_trace(go.Scatter(x=f.minggu, y=f.atas, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=f.minggu, y=f.bawah, fill="tonexty", fillcolor="rgba(42,127,186,0.16)",
                             line=dict(width=0), name="Rentang 95%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=f.minggu, y=f.prediksi, name="Prediksi", line=dict(color=SEA, width=2.4, dash="dash")))
    fig.add_shape(type="line", x0=sub.index[-1], x1=sub.index[-1], y0=0, y1=1, yref="paper",
                  line=dict(color="#8A97A5", width=1, dash="dash"))
    for t in f.minggu[f.lebaran == 1]:
        fig.add_vrect(x0=t, x1=t + pd.Timedelta(days=7), fillcolor=AMBER, opacity=0.14, line_width=0)
    fig.update_yaxes(title="Penumpang per minggu")
    st.plotly_chart(gaya(fig), width="stretch")

    if (f.tambahan > 0).any():
        st.markdown(
            f'<div class="peringatan"><b>Flight tambahan diperlukan.</b> Pada {int((f.tambahan > 0).sum())} dari {n} minggu, '
            f"kebutuhan flight melebihi jadwal reguler ({reguler} flight per minggu untuk {info['nama']}).</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="catatan"><b>Kapasitas cukup.</b> Jadwal reguler ({reguler} flight per minggu) '
                    "memenuhi kebutuhan pada seluruh minggu yang diprediksi.</div>", unsafe_allow_html=True)

    tabel = pd.DataFrame({
        "Minggu mulai": f.minggu.dt.strftime("%d %b %Y"),
        "Prediksi": f.prediksi.round(1), "Batas bawah": f.bawah.round(1), "Batas atas": f.atas.round(1),
        "Kebutuhan flight": f.butuh, "Jadwal reguler": reguler, "Flight tambahan": f.tambahan,
        "Lebaran": np.where(f.lebaran == 1, "Ya", ""),
    })
    st.dataframe(tabel, hide_index=True, width="stretch")
    st.download_button("Unduh hasil peramalan (CSV)", tabel.to_csv(index=False).encode("utf-8"),
                       f"peramalan_{kode}.csv", "text/csv")
    st.caption("Kebutuhan flight = penumpang dibagi (12 kursi × target keterisian), dibulatkan ke atas. "
               "Jadwal reguler diambil dari median flight mingguan pada data dan dapat diubah di sidebar. "
               "Tanggal Lebaran 2027 dan 2028 adalah estimasi.")

# ================================================================
# TAB 3 - EVALUASI MODEL
# ================================================================
with tab3:
    st.markdown("### Akurasi model pada data uji")
    st.markdown(
        '<div class="catatan"><b>Dua skenario uji.</b> <i>Rolling 1 minggu</i>: tiap minggu diprediksi setelah data minggu '
        f"sebelumnya diketahui. <i>{N_UJI} minggu sekaligus</i>: seluruh data uji diprediksi tanpa koreksi, sehingga jauh lebih "
        "sulit.</div>", unsafe_allow_html=True)
    st.write("")

    e1, e2, e3 = st.columns(3)
    e1.metric("MAE (rolling)", f"{m_roll['MAE']:.2f}", help="Rata-rata selisih dalam jumlah penumpang")
    e2.metric("RMSE (rolling)", f"{m_roll['RMSE']:.2f}")
    e3.metric(f"MAPE rolling / {N_UJI} minggu", f"{m_roll['MAPE']:.1f}% / {m_multi['MAPE']:.1f}%")
    if kode == "SEMUA":
        st.markdown(
            '<div class="peringatan"><b>Jangan dibandingkan langsung dengan rute.</b> Model agregat memprediksi total '
            "seluruh rute. Fluktuasi antar rute saling menutupi dan totalnya jauh lebih besar, sehingga MAPE-nya lebih kecil "
            "dan MAE/RMSE-nya lebih besar daripada per rute. Pembanding yang adil antar rute adalah lima model rute.</div>",
            unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roll.minggu, y=roll.aktual, name="Aktual", line=dict(color=NAVY, width=2.4)))
    fig.add_trace(go.Scatter(x=roll.minggu, y=roll.prediksi, name="Rolling 1 minggu", line=dict(color=AMBER, width=2.2)))
    fig.add_trace(go.Scatter(x=multi.minggu, y=multi.prediksi, name=f"{N_UJI} minggu sekaligus",
                             line=dict(color=BRICK, width=2.2, dash="dash")))
    fig.update_yaxes(title="Penumpang per minggu")
    st.plotly_chart(gaya(fig), width="stretch")

    st.markdown("### Perbandingan antar rute")
    rk = ringkasan[ringkasan.rute != "SEMUA"].copy()  # model agregat tidak sebanding dengan rute, tidak ikut di grafik
    rk_semua = ringkasan[ringkasan.rute == "SEMUA"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rk.rute, y=rk.MAPE_rolling, name="Rolling 1 minggu", marker_color=SEA))
    fig.add_trace(go.Bar(x=rk.rute, y=rk.MAPE_multi, name=f"{N_UJI} minggu sekaligus", marker_color=BRICK))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="MAPE (%)")
    st.plotly_chart(gaya(fig, 340), width="stretch")

    tabel = rk.rename(columns={
        "rute": "Rute", "orde": "Orde", "n_latih": "Minggu latih", "n_uji": "Minggu uji",
        "MAE_rolling": "MAE rolling", "RMSE_rolling": "RMSE rolling", "MAPE_rolling": "MAPE rolling (%)",
        f"MAE_multi": f"MAE {N_UJI} mgg", "RMSE_multi": f"RMSE {N_UJI} mgg", "MAPE_multi": f"MAPE {N_UJI} mgg (%)"
    }).drop(columns=["pct_latih"])
    st.dataframe(tabel, hide_index=True, width="stretch")
    st.caption("Baris SEMUA adalah model agregat pada total mingguan seluruh rute. MAPE-nya (lebih kecil) dan MAE/RMSE-nya "
               "(lebih besar) berskala berbeda, jadi tidak sebanding dengan baris rute.")

    rk5 = rk  # perbandingan antar rute, tanpa model agregat
    terburuk = rk5.loc[rk5.MAPE_multi.idxmax()]
    terburuk_roll = rk5.loc[rk5.MAPE_rolling.idxmax()]
    st.markdown(
        f'<div class="peringatan"><b>Keterbatasan.</b> Rute {terburuk.rute} memiliki MAPE {terburuk.MAPE_multi:.1f}% pada skenario '
        f"{N_UJI} minggu sekaligus, dan {terburuk_roll.rute} {terburuk_roll.MAPE_rolling:.1f}% pada skenario rolling (rute terlemah). "
        f"Data hanya mencakup sekitar {BULAN_DATA} bulan dengan satu "
        "Lebaran pada data latih, sehingga lonjakan Lebaran 2026 sulit ditangkap. Rute berpenumpang sedikit juga "
        "membuat MAPE tampak besar meski selisih absolutnya kecil.</div>", unsafe_allow_html=True)

    if kode != "SEMUA":
        with st.expander(f"Pencarian orde ARIMAX rute {kode} (lima AIC terendah)"):
            top = pencarian[pencarian.rute == kode].nsmallest(5, "AIC")[["p", "d", "q", "AIC", "BIC"]].round(2)
            st.dataframe(top, hide_index=True)
            st.caption("AIC makin kecil berarti model makin baik untuk kompleksitas yang sama.")
    else:
        st.caption("Metrik 'Semua rute' berasal dari model agregat yang dilatih sendiri pada total mingguan, "
                   "bukan dari penjumlahan prediksi kelima rute.")

# ================================================================
# TAB 4 - OPERASIONAL
# ================================================================
with tab4:
    b = bersih.copy()
    b["hari_id"] = b["hari"].map(HARI_ID)
    total_flight = len(b)
    # Keterisian dihitung hanya untuk Cessna 12 kursi (armada reguler). 18 flight ATR 72 (72 kursi, keterisian rendah)
    # dikeluarkan agar tidak menarik turun rute BTH; dilaporkan terpisah di catatan.
    b12 = b[b.kursi == KURSI]
    atr = b[b.kursi != KURSI]
    lf_all = b12.pax_kursi.sum() / b12.kursi.sum() * 100  # bayi tidak memakai kursi
    lf_atr = (atr.pax_kursi.sum() / atr.kursi.sum() * 100) if len(atr) else float("nan")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Total flight tercatat", f"{total_flight:,}".replace(",", "."),
              help=f"Seluruh flight pada data bersih ({b.pax_total.sum():,} penumpang, termasuk minggu parsial di ujung data). "
                   f"Total penumpang di tab Ringkasan hanya menghitung minggu penuh berdata.".replace(",", "."))
    o2.metric("Keterisian kursi", f"{lf_all:.1f}%",
              help=f"Hanya flight Cessna 208B (12 kursi), {len(b12):,} flight. {len(atr)} flight ATR 72 tidak dihitung "
                   f"(keterisian {lf_atr:.1f}%).".replace(",", "."))
    o3.metric("Terlambat ≥15 menit", f"{b.terlambat15.mean()*100:.1f}%")
    o4.metric("Penyebab terbanyak", "Teknis operasional",
              f"{(b.kategori_delay == 'TEKNIS OPERASIONAL').sum()} flight", delta_color="off")

    left, right = st.columns(2)
    with left:
        st.markdown("### Keterisian kursi per rute")
        lfr = b12.groupby("rute_mitra").apply(lambda x: x.pax_kursi.sum() / x.kursi.sum() * 100).sort_values()
        fig = go.Figure(go.Bar(x=lfr.values, y=lfr.index, orientation="h", marker_color=SEA,
                               text=[f"{v:.1f}%" for v in lfr.values], textposition="outside"))
        fig.update_xaxes(range=[0, 100], title="Keterisian (%)")
        st.plotly_chart(gaya(fig, 320), width="stretch")
    with right:
        st.markdown("### Penumpang menurut hari")
        urut = list(HARI_ID.values())
        ph = b.groupby("hari_id").pax_total.sum().reindex(urut)
        fig = go.Figure(go.Bar(x=ph.index, y=ph.values, marker_color=NAVY))
        fig.update_yaxes(title="Total penumpang")
        st.plotly_chart(gaya(fig, 320), width="stretch")

    st.markdown("### Penyebab keterlambatan")
    kd = b[b.kategori_delay != "TEPAT WAKTU/TANPA KETERANGAN"].kategori_delay.str.capitalize().value_counts()
    fig = go.Figure(go.Bar(x=kd.values, y=kd.index, orientation="h", marker_color=AMBER,
                           text=kd.values, textposition="outside"))
    fig.update_xaxes(title="Jumlah flight")
    st.plotly_chart(gaya(fig, 260), width="stretch")

    rt = b.groupby("rute_mitra").agg(Flight=("pax_total", "size"), Penumpang=("pax_total", "sum"), PaxKursi=("pax_kursi", "sum"),
                                      Kursi=("kursi", "sum"), Rata_delay=("delay_menit", "mean")).reset_index()
    _k12 = b12.groupby("rute_mitra").agg(PK12=("pax_kursi", "sum"), K12=("kursi", "sum"))
    rt["Keterisian (%)"] = (rt.rute_mitra.map(_k12.PK12 / _k12.K12) * 100).round(1)  # hanya Cessna 12 kursi
    rt["Penumpang/flight"] = (rt.Penumpang / rt.Flight).round(1)
    rt["Rata-rata delay (menit)"] = rt.Rata_delay.round(1)
    rt["Pangsa penumpang (%)"] = (rt.Penumpang / rt.Penumpang.sum() * 100).round(1)
    st.dataframe(rt[["rute_mitra", "Flight", "Penumpang", "Penumpang/flight", "Keterisian (%)",
                     "Pangsa penumpang (%)", "Rata-rata delay (menit)"]].rename(columns={"rute_mitra": "Rute"}),
                 hide_index=True, width="stretch")
    st.caption("Seluruh angka pada halaman ini dihitung langsung dari data_penerbangan_bersih.csv. "
               "Keterisian kursi = (dewasa + anak) dibagi jumlah kursi; bayi dipangku sehingga tidak dihitung. "
               f"Hanya flight Cessna 12 kursi yang dihitung; {len(atr)} flight ATR 72 di rute BTH (keterisian {lf_atr:.1f}%) dikeluarkan. "
               "Kolom Penumpang tetap memuat semua penumpang termasuk bayi.")

# ================================================================
# TAB 5 - DATA
# ================================================================
with tab5:
    st.markdown("### Data mingguan")
    sumber = mingguan if kode == "SEMUA" else per_rute[per_rute.rute == kode]
    kolom = {"minggu": "Minggu mulai", "penerbangan": "Flight", "penumpang": "Penumpang",
             "berangkat": "Berangkat", "datang": "Datang", "penumpang_berangkat": "Berangkat",
             "penumpang_datang": "Datang", "lebaran": "Lebaran"}
    d = sumber[[c for c in kolom if c in sumber.columns]].rename(columns=kolom).copy()
    d["Minggu mulai"] = d["Minggu mulai"].dt.strftime("%d %b %Y")
    if "Lebaran" in d:
        d["Lebaran"] = np.where(d["Lebaran"] == 1, "Ya", "")
    st.dataframe(d, hide_index=True, width="stretch", height=460)
    st.download_button("Unduh data (CSV)", d.to_csv(index=False).encode("utf-8"), f"data_mingguan_{kode}.csv", "text/csv")
    with st.expander("Log pembersihan data"):
        st.code((DATA_DIR / "log_pembersihan.txt").read_text(encoding="utf-8", errors="ignore"), language="text")

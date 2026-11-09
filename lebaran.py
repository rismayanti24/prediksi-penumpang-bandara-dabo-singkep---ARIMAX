"""
lebaran.py - Satu-satunya sumber definisi variabel eksogen Lebaran.

Dipakai oleh scripts/clean.py (pipeline & evaluasi model), streamlit_app.py, dan app.py,
supaya model yang dievaluasi sama persis dengan model yang dipakai di dashboard.

Definisi: sebuah minggu (Senin-Minggu) bernilai 1 bila berada dalam +/- 1 minggu
dari minggu yang memuat Idul Fitri (jadi 3 minggu berturut-turut: sebelum, saat, sesudah).
"""
import pandas as pd

# Tanggal 1 Syawal (Idul Fitri). Posisi dalam minggu tidak berpengaruh karena yang dipakai
# adalah Senin pada minggu tersebut.
LEBARAN = [
    pd.Timestamp("2025-03-31"),  # 1 Syawal 1446 H
    pd.Timestamp("2026-03-21"),  # 1 Syawal 1447 H
    pd.Timestamp("2027-03-10"),  # 1448 H (estimasi)
    pd.Timestamp("2028-02-28"),  # 1449 H (estimasi)
]


def flag_lebaran(minggu_mulai) -> int:
    """1 bila minggu yang diawali `minggu_mulai` (Senin) ada dalam +/- 1 minggu dari Idul Fitri."""
    minggu_mulai = pd.Timestamp(minggu_mulai)
    for hr in LEBARAN:
        senin_lebaran = hr - pd.Timedelta(days=hr.weekday())
        if abs((minggu_mulai - senin_lebaran).days) <= 7:
            return 1
    return 0

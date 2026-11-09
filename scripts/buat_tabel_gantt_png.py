import matplotlib.pyplot as plt
import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set style
fig, ax = plt.subplots(figsize=(14, 6.2), dpi=300)
ax.axis('off')

columns = [
    'No',
    'Tahapan Kegiatan Proyek',
    'Rentang\nTanggal',
    'Sep 26\n(M4)',
    'Okt 26\n(M1-2)',
    'Okt 26\n(M3)',
    'Okt 26\n(M4)',
    'Okt-Nov\n(M5)',
    'Nov 26\n(M1)',
    'Nov 26\n(M2)',
    'PIC (Penanggung Jawab)'
]

data = [
    [
        '1',
        'Observasi & Pengumpulan Data Mentah\n• Pengambilan log manifest UPBU Dabo Singkep\n• Identifikasi kendala armada perintis 12 kursi',
        '24 Sep –\n28 Sep 2026',
        '████', '', '', '', '', '', '',
        'Nikita Arzetty Siregar'
    ],
    [
        '2',
        'Penggabungan & Pembersihan Data (Preprocessing)\n• Integrasi file data mentah bulanan menjadi satu\n• Agregasi mingguan (W-MON) & interpolasi\n• Feature engineering penanda musiman Lebaran',
        '06 Okt –\n13 Okt 2026',
        '', '████', '', '', '', '', '',
        'Erlinda Amira Putri S.'
    ],
    [
        '3',
        'Exploratory Data Analysis (EDA)\n• Analisis pangsa rute, hari tersibuk & load factor\n• Visualisasi sebaran data & rasio on-time/delay',
        '14 Okt –\n20 Okt 2026',
        '', '', '████', '', '', '', '',
        'Dhini Khairunnisa'
    ],
    [
        '4',
        'Pemodelan Deret Waktu ARIMAX\n• Pembagian 71% data latih / 29% data uji\n• Optimasi parameter (p, d, q) via AIC 5 rute',
        '21 Okt –\n27 Okt 2026',
        '', '', '', '████', '', '', '',
        'Rismayanti'
    ],
    [
        '5',
        'Evaluasi Akurasi & Validasi Model\n• Pengujian periode uji mudik Lebaran 2026\n• Evaluasi MAE, RMSE, MAPE (rolling & multi-step)',
        '25 Okt –\n28 Okt 2026',
        '', '', '', '████', '', '', '',
        'Rismayanti'
    ],
    [
        '6',
        'Pengembangan & Finishing Web Dashboard\n• Backend Flask & API per rute\n• Antarmuka interaktif & simulator flight armada',
        '27 Okt –\n31 Okt 2026',
        '', '', '', '', '████', '', '',
        'Rismayanti (Didukung Tim)'
    ],
    [
        '7',
        'Penyusunan Laporan Akhir & Dokumentasi\n• Penulisan naskah laporan lengkap BAB I – BAB VI\n• Finalisasi lampiran & dokumen format FinPD',
        '01 Nov –\n13 Nov 2026',
        '', '', '', '', '', '████', '████',
        'Nikita, Erlinda, Dhini'
    ]
]

# Create table
table = ax.table(
    cellText=data,
    colLabels=columns,
    cellLoc='center',
    loc='center',
    colWidths=[0.04, 0.34, 0.11, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.17]
)

table.auto_set_font_size(False)
table.set_fontsize(9)

# Colors
header_bg = '#1e293b'
header_fg = '#ffffff'
row_even = '#f8fafc'
row_odd = '#ffffff'
accent_bar = '#2563eb'

for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor('#cbd5e1')
    cell.set_linewidth(0.8)
    if row == 0:
        cell.set_text_props(weight='bold', color=header_fg)
        cell.set_facecolor(header_bg)
        cell.set_height(0.08)
    else:
        # Alternating background
        bg = row_even if row % 2 == 0 else row_odd
        cell.set_facecolor(bg)
        cell.set_height(0.125)
        
        # Left align the task column
        if col == 1:
            cell.set_text_props(ha='left', weight='normal', color='#0f172a')
        elif col in [3, 4, 5, 6, 7, 8, 9]:
            # Highlight timeline block
            txt = cell.get_text().get_text()
            if '████' in txt:
                cell.set_facecolor('#dbeafe')
                cell.set_text_props(weight='bold', color=accent_bar)
        elif col == 10:
            cell.set_text_props(weight='bold', color='#1e3a8a')

plt.title('TABEL GANTT CHART LINI WAKTU PROYEK PENAMBANGAN DATA (INF11121)\nPrediksi Penumpang per Rute & Armada Pesawat ARIMAX - UPBU Kelas III Bandara Dabo Singkep', 
          fontsize=12, fontweight='bold', color='#0f172a', pad=15)

plt.tight_layout()
os.makedirs(os.path.join(BASE, 'laporan'), exist_ok=True)
out_file = os.path.join(BASE, 'laporan', 'tabel_gantt_chart.png')
plt.savefig(out_file, dpi=300, bbox_inches='tight')
print(f"SUKSES: Tabel Gantt Chart tersimpan di {out_file}")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ubah TODAY dan tanggal 'start'/'end' di bawah sesuai kondisi sebenarnya sebelum membuat ulang gambar
TODAY = '2026-11-09'
BLN = {'Jan':'Jan','Feb':'Feb','Mar':'Mar','Apr':'Apr','May':'Mei','Jun':'Jun','Jul':'Jul','Aug':'Agu','Sep':'Sep','Oct':'Okt','Nov':'Nov','Dec':'Des'}
def idn(ts, fmt='%d %b'):
    x = ts.strftime(fmt)
    for en, idd in BLN.items():
        x = x.replace(en, idd)
    return x

# Setup figure
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax = plt.subplots(figsize=(14.5, 7.5), dpi=300)

tasks = [
    {
        'task': '1. Pengumpulan Data Mentah & Observasi',
        'pic': 'Nikita Arzetty Siregar',
        'start': '2026-09-24',
        'end': '2026-09-28',
        'color': '#2563eb'
    },
    {
        'task': '2. Integrasi & Pembersihan Data (Preprocessing)',
        'pic': 'Erlinda Amira Putri S.',
        'start': '2026-10-06',
        'end': '2026-10-13',
        'color': '#0284c7'
    },
    {
        'task': '3. Exploratory Data Analysis (EDA)',
        'pic': 'Dhini Khairunnisa',
        'start': '2026-10-14',
        'end': '2026-10-20',
        'color': '#059669'
    },
    {
        'task': '4. Pemodelan Deret Waktu ARIMAX',
        'pic': 'Rismayanti',
        'start': '2026-10-21',
        'end': '2026-10-27',
        'color': '#7c3aed'
    },
    {
        'task': '5. Evaluasi Model (Uji Lebaran 2026)',
        'pic': 'Rismayanti',
        'start': '2026-10-25',
        'end': '2026-10-28',
        'color': '#db2777'
    },
    {
        'task': '6. Finishing Web Dashboard Prediksi',
        'pic': 'Rismayanti (Didukung Tim)',
        'start': '2026-10-27',
        'end': '2026-10-31',
        'color': '#d97706'
    },
    {
        'task': '7. Penyusunan Laporan Akhir (FinPD)',
        'pic': 'Nikita, Erlinda, Dhini',
        'start': '2026-11-01',
        'end': '2026-11-13',
        'color': '#1d4ed8'
    }
]

y_pos = list(range(len(tasks)))[::-1]

for i, t in enumerate(tasks):
    s = pd.to_datetime(t['start'])
    e = pd.to_datetime(t['end'])
    dur = (e - s).days + 1
    y = y_pos[i]
    
    # Horizontal bar
    ax.barh(y, dur, left=s, height=0.55, align='center', color=t['color'], alpha=0.92, edgecolor='none', zorder=3)
    

# Y-Axis labels
ax.set_yticks(y_pos)
labels = []
for t in tasks:
    s_, e_ = pd.to_datetime(t['start']), pd.to_datetime(t['end'])
    labels.append(f"{t['task']}\n{idn(s_)} - {idn(e_, '%d %b %Y')}  |  PIC: {t['pic']}")
ax.set_yticklabels(labels, fontsize=10, fontweight='600', color='#0f172a', linespacing=1.5)

# X-Axis date formatting
ax.xaxis_date()
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: idn(pd.Timestamp(mdates.num2date(v).replace(tzinfo=None)), '%d %b %Y')))
plt.xticks(rotation=15, ha='right', fontsize=9.5, fontweight='600', color='#475569')

# Today marker
today = pd.to_datetime(TODAY)
ax.axvline(today, color='#d97706', linestyle='--', linewidth=1.8, zorder=2)
ax.text(today - pd.Timedelta(days=0.4), len(tasks) - 0.35, f"Hari ini ({idn(today)})", color='#b45309',
        fontweight='bold', fontsize=9.5, ha='right', va='center')

# Deadline marker (14 Nov)
deadline = pd.to_datetime('2026-11-14')
ax.axvline(deadline, color='#dc2626', linestyle='--', linewidth=1.8, zorder=2)
ax.text(deadline + pd.Timedelta(days=0.4), len(tasks) - 0.35, 'Batas akhir RTM\n(14 Nov 2026)', color='#dc2626', fontweight='bold', fontsize=9.5, ha='left', va='center')

# Titles
fig.suptitle('GANTT CHART LINI WAKTU PROYEK PENAMBANGAN DATA', fontsize=15, fontweight='800', color='#0f172a', y=0.97)
ax.set_title('Prediksi Penumpang per Rute & Armada Pesawat ARIMAX - UPBU Dabo Singkep | Teknik Informatika UMRAH', fontsize=10.5, color='#64748b', pad=12)

# Grid & Spines
ax.grid(axis='x', color='#e2e8f0', linestyle='-', linewidth=0.9, zorder=1)
ax.grid(axis='y', linestyle='', alpha=0)
ax.set_xlim(pd.to_datetime('2026-09-21'), pd.to_datetime('2026-11-20'))
ax.set_ylim(-0.7, len(tasks) + 0.1)

for spine in ax.spines.values():
    spine.set_color('#cbd5e1')
ax.set_facecolor('#f8fafc')
fig.patch.set_facecolor('#ffffff')

plt.tight_layout()
os.makedirs(os.path.join(BASE, 'laporan'), exist_ok=True)
out_file = os.path.join(BASE, 'laporan', 'gantt_chart_lini_waktu.png')
plt.savefig(out_file, dpi=300, bbox_inches='tight')
print(f"SUKSES: Gantt Chart tersimpan di {out_file}")

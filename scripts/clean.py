import pandas as pd, numpy as np, re
import glob, os, sys

# ============================================================
# KONFIGURASI
# ============================================================
RUTE_UTAMA = ['BTH', 'PKU', 'DJB', 'TNJ', 'TJB']  # 5 rute reguler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lebaran import flag_lebaran

# Cari file Excel di folder data_mentah/ atau root proyek
FOLDER = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(FOLDER) if os.path.basename(FOLDER) == 'scripts' else FOLDER
cand = sorted(glob.glob(os.path.join(BASE_DIR, 'data_mentah', 'DATA_LLAU_SIQ*GABUNGAN*.xlsx'))) + \
       sorted(glob.glob(os.path.join(BASE_DIR, 'DATA_LLAU_SIQ*GABUNGAN*.xlsx'))) + \
       sorted(glob.glob(os.path.join(FOLDER, 'DATA_LLAU_SIQ*GABUNGAN*.xlsx')))
if not cand:
    raise SystemExit('File Excel DATA_LLAU_SIQ_...GABUNGAN.xlsx tidak ditemukan di folder data_mentah/ atau di root.')
P = cand[0]
OUT = os.path.join(BASE_DIR, 'hasil', 'data_bersih')
os.makedirs(OUT, exist_ok=True)
raw = pd.read_excel(P, header=None, skiprows=2)
cols=['No','tgl_sch','tgl_act','wkt_sch','wkt_act','kat_delay','asal','tujuan','operator','icao','kegiatan','tipe_rute','ket','no_flight','reg','tipe_pesawat','kursi','gerak','pax_dws','pax_anak','pax_bayi','tr_dws','tr_anak','tr_bayi','bagasi','kargo','pos','sumber']
raw.columns=cols
log=[]
log.append(f"Baris mentah: {len(raw)}")

# ============================================================
# 1. Pisahkan catatan 'no flight' dari penerbangan
# ============================================================
nf = raw[raw.asal.isna()].copy()
fl = raw[raw.asal.notna()].copy()
nf['tanggal']=pd.to_datetime(nf.tgl_act,format='%d-%m-%Y')
nf = nf[['tanggal']].drop_duplicates()
log.append(f"Catatan 'no flight' (hari tanpa penerbangan): {len(nf)} hari (tanggal asli di kolom tgl_act; kolom tgl_sch berisi placeholder 01-10-2026)")
log.append(f"Baris penerbangan: {len(fl)}")

# ============================================================
# 2. Tanggal & waktu
# ============================================================
fl['tanggal']=pd.to_datetime(fl.tgl_sch,format='%d-%m-%Y')
fl['tanggal_act']=pd.to_datetime(fl.tgl_act,format='%d-%m-%Y')

# ============================================================
# 3. Duplikat
# ============================================================
key=['tanggal','wkt_sch','no_flight','asal','tujuan','pax_dws','pax_anak','pax_bayi','bagasi']
dup=fl.duplicated(key,keep='first')
log.append(f"Duplikat dihapus: {dup.sum()} baris (kunci: tanggal, jam jadwal, no penerbangan, rute, penumpang, bagasi)")
fl=fl[~dup].copy()

# ============================================================
# 4. Standarisasi
# ============================================================
fl['asal']=fl.asal.str.strip().replace({'Dabo ( SIQ / Singkep ) ai':'SIQ'})
fl['tujuan']=fl.tujuan.str.strip().replace({'Dabo ( SIQ / Singkep ) ai':'SIQ'})
n_dabo=(raw.tujuan.astype(str).str.contains('Dabo')).sum()
log.append(f"Kode bandara 'Dabo ( SIQ / Singkep ) ai' diseragamkan jadi SIQ: {n_dabo} baris")
def op(x):
    x=str(x).upper()
    if 'WINGS' in x: return 'Wings Abadi'
    return 'Susi Air'
n_op_var=(~fl.operator.isin(['PT. Asi Pudjiastuti Aviation','PT. Wings Abadi'])).sum()
fl['operator']=fl.operator.map(op)
log.append(f"Nama operator diseragamkan (Susi Air / Wings Abadi); varian salah ketik: {n_op_var} baris")
def tp(x):
    x=re.sub(r'[\s-]','',str(x).lower())
    if x.startswith('atr72') and '500' in x: return 'ATR72-500'
    if x.startswith('atr72') and '600' in x: return 'ATR72-600'
    return 'C208B'
n_tp_var=(~fl.tipe_pesawat.isin(['c208b','atr 72-500','atr 72-600'])).sum()
fl['tipe_pesawat']=fl.tipe_pesawat.map(tp)
log.append(f"Tipe pesawat diseragamkan (C208B / ATR72-500 / ATR72-600); varian tulisan lain: {n_tp_var} baris")
fl['kategori_delay']=fl.kat_delay.replace({'-':'TEPAT WAKTU/TANPA KETERANGAN'})
fl['kursi']=fl.kursi.astype(int)
# Koreksi label tipe: pesawat 72 kursi pasti ATR 72, bukan C208B (12 kursi).
# Tipe ATR ditentukan dari registrasi pesawat yang sama pada penerbangan lain (mis. PK-WFG = ATR72-500).
atr_mask=fl.kursi.eq(72)&~fl.tipe_pesawat.str.startswith('ATR')
tipe_per_reg=(fl[fl.tipe_pesawat.str.startswith('ATR')].groupby('reg').tipe_pesawat.agg(lambda s:s.mode().iloc[0]))
fl.loc[atr_mask,'tipe_pesawat']=fl.loc[atr_mask,'reg'].map(tipe_per_reg).fillna('ATR72-500')
log.append(f"Label tipe pesawat dikoreksi: {atr_mask.sum()} baris berkursi 72 yang tertulis C208B diubah menjadi ATR72 (tipe diambil dari registrasi yang sama)")

# ============================================================
# 5. Keterlambatan (menit)
# ============================================================
def to_dt(d,t):
    t=pd.to_timedelta(t.astype(str))
    return d+t
sch=to_dt(fl.tanggal,fl.wkt_sch); act=to_dt(fl.tanggal_act,fl.wkt_act)
raw_dl=(act-sch).dt.total_seconds()/60
fl['delay_menit_mentah']=raw_dl
fix_lo=raw_dl<-180; fix_hi=raw_dl>720
dl=np.where(fix_lo,raw_dl+720,np.where(fix_hi,raw_dl-720,raw_dl))
fl['delay_dikoreksi']=(fix_lo|fix_hi).astype(int)
fl['delay_menit']=dl
log.append(f"Keterlambatan (menit) = jam aktual - jam jadwal. Terdapat {fix_lo.sum()} baris dengan selisih < -180 menit (mis. jadwal 11:10, aktual 02:40) dan {fix_hi.sum()} baris > +720 menit; diduga salah ketik AM/PM, dikoreksi +/-12 jam (nilai asli disimpan di delay_menit_mentah; penanda delay_dikoreksi=1)")
log.append(f"Setelah koreksi, delay negatif (lebih awal) tersisa: {(dl<0).sum()} baris, dibiarkan apa adanya")
fl['terlambat15']=(fl.delay_menit>15).astype(int)

# ============================================================
# 6. Penumpang & rute
# ============================================================
fl['pax_total']=fl.pax_dws+fl.pax_anak+fl.pax_bayi
# Penumpang yang memakai kursi = dewasa + anak (bayi dipangku, tidak memakai kursi). Dipakai untuk keterisian kursi.
fl['pax_kursi']=fl.pax_dws+fl.pax_anak
log.append(f"Penumpang transit semuanya 0 -> kolom transit dibuang; kolom pos (semua 0) dan tipe_rute (semua DOMESTIK) dibuang")
fl['arah']=fl.gerak.map({'A':'Datang','D':'Berangkat'})
fl['rute_mitra']=np.where(fl.gerak=='D',fl.tujuan,fl.asal)
fl['bulan']=fl.tanggal.dt.to_period('M').astype(str)
fl['hari']=fl.tanggal.dt.day_name()
fl['jam_jadwal']=pd.to_timedelta(fl.wkt_sch.astype(str)).dt.components.hours
keep=['tanggal','bulan','hari','wkt_sch','wkt_act','jam_jadwal','delay_menit','delay_menit_mentah','delay_dikoreksi','terlambat15','kategori_delay','arah','rute_mitra','asal','tujuan','operator','kegiatan','no_flight','reg','tipe_pesawat','kursi','pax_dws','pax_anak','pax_bayi','pax_total','pax_kursi','bagasi','kargo','sumber']
fl=fl[keep].sort_values(['tanggal','wkt_sch']).reset_index(drop=True)

# ============================================================
# 6b. Filter hanya rute utama
# ============================================================
n_before = len(fl)
fl = fl[fl.rute_mitra.isin(RUTE_UTAMA)].copy()
n_insidental = n_before - len(fl)
log.append(f"Rute utama yang dipertahankan: {', '.join(RUTE_UTAMA)}")
log.append(f"Penerbangan rute insidental dihapus: {n_insidental} baris (rute dengan < 10 penerbangan total)")
log.append(f"Baris penerbangan bersih (hanya rute utama): {len(fl)}")

over=fl[fl.pax_kursi>fl.kursi]
log.append(f"Penumpang berkursi (dewasa+anak) melebihi kapasitas kursi pada {len(over)} baris (diduga salah input, tidak diubah): "+", ".join(f"{r.tanggal:%d-%m-%Y} {r.rute_mitra} {r.arah} ({r.pax_kursi}/{r.kursi})" for r in over.itertuples()))
fl.to_csv(f'{OUT}/data_penerbangan_bersih.csv',index=False)

# ============================================================
# 7. Data harian (total, tetap dipertahankan sebagai referensi)
# ============================================================
cal=pd.DataFrame({'tanggal':pd.date_range('2025-01-01','2026-08-31')})
d=fl.groupby('tanggal').agg(penerbangan=('no_flight','size'),penumpang=('pax_total','sum'),
    berangkat=('pax_total',lambda s: s[fl.loc[s.index,'arah']=='Berangkat'].sum()),
    datang=('pax_total',lambda s: s[fl.loc[s.index,'arah']=='Datang'].sum())).reset_index()
cal=cal.merge(d,on='tanggal',how='left')
cal['no_flight_tercatat']=cal.tanggal.isin(nf.tanggal)
unrec=cal[cal.penerbangan.isna()&~cal.no_flight_tercatat]
log.append(f"Hari kalender 2025-01-01..2026-08-31: {len(cal)}; ada penerbangan: {cal.penerbangan.notna().sum()}; no flight tercatat: {cal.no_flight_tercatat.sum()}; tidak ada catatan sama sekali: {len(unrec)}")
log.append("Tanggal tak tercatat (kecuali Jan 2026): "+", ".join(unrec[unrec.tanggal.dt.strftime('%Y-%m')!='2026-01'].tanggal.dt.strftime('%d-%m-%Y').tolist()))
cal[['penerbangan','penumpang','berangkat','datang']]=cal[['penerbangan','penumpang','berangkat','datang']].fillna(0)
cal['status']=np.where(cal.tanggal.dt.strftime('%Y-%m')=='2026-01','PERIODE TANPA PENERBANGAN',np.where(cal.penerbangan>0,'ADA PENERBANGAN',np.where(cal.no_flight_tercatat,'NO FLIGHT TERCATAT','TIDAK TERCATAT')))
cal.to_csv(f'{OUT}/data_harian.csv',index=False)

# ============================================================
# 8. Mingguan TOTAL (Senin-Minggu), hanya minggu penuh
#    Tetap disimpan sebagai data_mingguan.csv untuk referensi
# ============================================================
cal['minggu']=cal.tanggal.dt.to_period('W-SUN').dt.start_time
wk=cal.groupby('minggu').agg(hari=('tanggal','size'),penerbangan=('penerbangan','sum'),penumpang=('penumpang','sum'),
    berangkat=('berangkat','sum'),datang=('datang','sum'),hilang=('status',lambda s:(s=='PERIODE TANPA PENERBANGAN').sum())).reset_index()
wk=wk[wk.hari==7].copy()

def jan(w):
    days=pd.date_range(w,periods=7)
    return any((d.year==2026 and d.month==1) for d in days)
mask=wk.minggu.map(jan)
log.append(f"Minggu penuh: {len(wk)}; minggu yang menyentuh Januari 2026: {mask.sum()}. Januari 2026 hanya memuat 3 penerbangan (dikonfirmasi benar adanya, bukan data hilang) sehingga bukan kondisi operasi normal; minggu-minggu ini dikeluarkan dari data model (NaN)")
wk['penumpang_nyata']=wk.penumpang; wk['penerbangan_nyata']=wk.penerbangan; wk['periode_henti']=mask.astype(int)
wk.loc[mask,['penerbangan','penumpang','berangkat','datang']]=np.nan

# delay & cuaca mingguan
fl['minggu']=fl.tanggal.dt.to_period('W-SUN').dt.start_time
w2=fl.groupby('minggu').agg(rata_delay=('delay_menit','mean'),persen_terlambat=('terlambat15','mean'),
    n_cuaca=('kategori_delay',lambda s:(s=='CUACA').sum()),n_teknis=('kategori_delay',lambda s:(s=='TEKNIS OPERASIONAL').sum())).reset_index()
wk=wk.merge(w2,on='minggu',how='left')
mask2=wk.minggu.map(jan)
wk.loc[mask2,['rata_delay','persen_terlambat','n_cuaca','n_teknis']]=np.nan
wk=wk.drop(columns=['hari','hilang'])
wk['lebaran']=wk.minggu.map(flag_lebaran)
wk.to_csv(f'{OUT}/data_mingguan.csv',index=False)

# ============================================================
# 9. Mingguan PER RUTE (output utama baru)
#    Setiap rute_mitra mendapat agregasi sendiri per minggu
# ============================================================
log.append("")
log.append("=" * 60)
log.append("AGREGASI MINGGUAN PER RUTE (5 rute utama)")
log.append("=" * 60)

# Buat kerangka lengkap: semua kombinasi minggu x rute
minggu_list = wk[wk.periode_henti == 0].minggu.tolist()  # hanya minggu non-henti
rute_list = sorted(RUTE_UTAMA)
idx = pd.MultiIndex.from_product([minggu_list, rute_list], names=['minggu', 'rute'])
kerangka = pd.DataFrame(index=idx).reset_index()

# Agregasi penerbangan per rute per minggu
agg_rute = fl.groupby(['minggu', 'rute_mitra']).agg(
    penerbangan=('no_flight', 'size'),
    penumpang=('pax_total', 'sum'),
    penumpang_berangkat=('pax_total', lambda s: s[fl.loc[s.index, 'arah'] == 'Berangkat'].sum()),
    penumpang_datang=('pax_total', lambda s: s[fl.loc[s.index, 'arah'] == 'Datang'].sum()),
    bagasi_total=('bagasi', 'sum'),
    kargo_total=('kargo', 'sum'),
    rata_delay=('delay_menit', 'mean'),
    persen_terlambat=('terlambat15', 'mean'),
    n_cuaca=('kategori_delay', lambda s: (s == 'CUACA').sum()),
    n_teknis=('kategori_delay', lambda s: (s == 'TEKNIS OPERASIONAL').sum()),
).reset_index().rename(columns={'rute_mitra': 'rute'})

# Gabungkan dengan kerangka
wk_rute = kerangka.merge(agg_rute, on=['minggu', 'rute'], how='left')

# Minggu yang tidak ada penerbangan untuk rute tertentu -> isi 0
for col in ['penerbangan', 'penumpang', 'penumpang_berangkat', 'penumpang_datang',
            'bagasi_total', 'kargo_total', 'n_cuaca', 'n_teknis']:
    wk_rute[col] = wk_rute[col].fillna(0).astype(int)
for col in ['rata_delay', 'persen_terlambat']:
    wk_rute[col] = wk_rute[col].fillna(0)

# Penanda Lebaran: definisi tunggal di lebaran.py (+/- 1 minggu dari Idul Fitri),
# dipakai juga oleh dashboard supaya model yang dievaluasi = model yang dipakai.
wk_rute['lebaran'] = wk_rute.minggu.map(flag_lebaran)

# Sortir
wk_rute = wk_rute.sort_values(['rute', 'minggu']).reset_index(drop=True)

# Statistik per rute
for rute in rute_list:
    sub = wk_rute[wk_rute.rute == rute]
    log.append(f"  Rute SIQ<->{rute}: {len(sub)} minggu, "
               f"rata-rata {sub.penumpang.mean():.1f} penumpang/minggu, "
               f"min {sub.penumpang.min()}, max {sub.penumpang.max()}")

wk_rute.to_csv(f'{OUT}/data_mingguan_per_rute.csv', index=False)
log.append(f"Total baris data_mingguan_per_rute.csv: {len(wk_rute)} ({len(wk_rute)//len(rute_list)} minggu × {len(rute_list)} rute)")

# ============================================================
# 10. Statistik ringkas per rute
# ============================================================
stats = wk_rute.groupby('rute').agg(
    minggu=('minggu', 'count'),
    penumpang_mean=('penumpang', 'mean'),
    penumpang_std=('penumpang', 'std'),
    penumpang_min=('penumpang', 'min'),
    penumpang_max=('penumpang', 'max'),
    penerbangan_mean=('penerbangan', 'mean'),
    penerbangan_std=('penerbangan', 'std'),
).round(2)
stats.to_csv(f'{OUT}/statistik_ringkas.csv')
log.append(f"\nStatistik ringkas per rute disimpan ke statistik_ringkas.csv")

log.append(f"\nRentang minggu: {wk_rute.minggu.min().date()} s/d {wk_rute.minggu.max().date()}")

# ============================================================
# Simpan log
# ============================================================
open(f'{OUT}/log_pembersihan.txt','w', encoding='utf-8').write("\n".join(log))
print("\n".join(log))
print("\n=== PREVIEW data_mingguan_per_rute.csv ===")
print(wk_rute.head(15))
print(f"\n=== STATISTIK PER RUTE ===")
print(stats)

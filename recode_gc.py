import pandas as pd
import re

STOPWORDS = [
    "pt", "cv", "tbk", "cabang", "branch", "ud", "pd",
    "toko", "warung", "ruko", "kop", "koperasi",
    "jalan", "jl", "no", "blok", "block"
]

code = {
    "Tidak Ditemukan": 99,
    "Aktif": 1,
    "Duplikat": 4,
    "Tutup Sementara": 3,
    "Tutup": 3,
    "Aktif Nonrespons": 1,
    "Alih Usaha": 1,
    "Salah Kode Wilayah": 99,
    "Perlu Konfirmasi": 1,
    "Belum Berproduksi": 3

}

def check_kurung(text):
    pattern = re.compile(r'<[^<>]+>')
    return 1 if pattern.search(text) else 0

def is_usaha_perorangan(u):
    if pd.isna(u):
        return 0
    usaha_lower = u.lower()
    for stopword in STOPWORDS:
        if stopword in usaha_lower:
            return 0
        else: return 1

with open('advanced_pairing_dfkecil_2.csv', 'r') as f:
    p = pd.read_csv(f, sep=";", encoding="cp1252")
    df = pd.DataFrame(p)

df['hasilgc_recode'] = ''
df['flag_shadow'] = ''
df['is_perorangan'] = ''
df['id_duplikat'] = df["id_duplikat"].fillna("")

df['flag_shadow'] = (
    df.groupby('id_duplikat')['id_duplikat']
      .transform('count')
      .apply(lambda x: 1 if x == 1 else 0)
)

df['is_kurung'] = df['nama_usaha'].apply(check_kurung)
df['is_perorangan'] = df['nama_usaha'].apply(is_usaha_perorangan)

for idx, row in df.iterrows():
    if df.loc[idx, 'sumber_data'] == "OSS - Perorangan": df.loc[idx, 'is_perorangan'] == 1
    elif df.loc[idx, 'sumber_data'] == "OSS - Badan Usaha": df.loc[idx, 'is_perorangan'] == 0

for idx, row in df.iterrows():
    status = df.loc[idx, 'status_perusahaan']

    if df.loc[idx, 'flag_shadow'] == 1: #Kalau gak ada pairing, tidak termasuk duplikat, hasilgc mengikuti status usaha
        df.loc[idx, 'is_duplicate'] = 0
        df.loc[idx, 'hasilgc_recode'] = code.get(status)
        
    elif df.loc[idx,'flag_shadow'] == 0:                               # Kalau ada pairing :
        if df.loc[idx, 'is_duplicate'] == 1:
            if df.loc[idx, 'is_kurung'] == True:
                if df.loc[idx, 'is_perorangan'] == 1:                    # Jika duplikat tapi ada terindikasi nama perorangan,
                    df.loc[idx, 'hasilgc_recode'] = code.get(status)
                else:  df.loc[idx, 'hasilgc_recode'] = 4     # Hasilgc ikuti status usaha
            elif df.loc[idx, 'is_kurung'] == False:
                if df.loc[idx, 'gc_flag_duplikat'] == 4:
                    df.loc[idx, 'hasilgc_recode'] = 4
                elif df.loc[idx, 'gc_flag_duplikat'] == 1:
                    df.loc[idx, 'hasilgc_recode'] = code.get(status)
        elif df.loc[idx, 'is_duplicate'] == 0:
            df.loc[idx, 'hasilgc_recode'] = code.get(status)
            
df.to_excel('dfkecil_recoded_2.xlsx')
import pandas as pd
import re

STOPWORDS_USAHA = [
    "pt", "cv", "tbk", "cabang", "branch", "ud", "pd",
    "toko", "warung", "ruko", "kop", "koperasi", "kpn",
    "bumdes", "sd", "sdn", "smp", "smpn", "bolum", "jaya",
    "abadi", "mandiri", "perkasa", "berkah", "desa", "bumdes", "kud",
    "kpb", "kelompok", "group", "borneo", "kalimantan", "berlian", "paser",
    "dinas", "komunitas", "unit", "kop", "koperasi", "komite", "majelis",
    "bengkel", "spm", "sumber", "taman", "apotek", "karya", "utama", "lapak",
    "subur", "lestari", "guna", "taka", "kesong", "buen", "yayasan", "bersama",
    "tech", "indonesia", "katering", "catering", "ptpn"
]

USAHA_WORDS = r'\b(JUAL|MENJUAL|DAGANG|USAHA|TOKO|WARUNG|BENGKEL|KELONTONG|MEMBUAT)\b'
SIMBOL_ISI = r'[\(<]\s*[^<>()]{2,30}\s*[\)>]'
PATTERN_USAHA_NAMA = re.compile(
    rf'{USAHA_WORDS}|{SIMBOL_ISI}',
    flags=re.IGNORECASE
)

def extract_kbli_2d(text):
    if pd.isna(text):
        return "00"
    m = re.search(r'KBLI\s*[:=]\s*(\d{2})\d*', str(text))
    return m.group(1) if m else "00"

def extract_kbli_5d(text):
    if pd.isna(text):
        return "00"
    m = re.search(r'KBLI\s*[:=]\s*(\d{5})\d*', str(text))
    return m.group(1) if m else "00000"

def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tandai_usaha(text):
    text = text.lower()
    pattern = r"\b(" + "|".join(map(re.escape, STOPWORDS_USAHA)) + r")\b"
    return 1 if re.search(pattern, text) else 0

def flag_usaha_dengan_nama(text):
    if PATTERN_USAHA_NAMA.search(text):
        return 1
    else: return 0

with open('recheck file\\remaining-data-part-2.csv', 'r') as f:
    dp = pd.read_csv(f, sep=";", encoding="cp1252")
    df = pd.DataFrame(dp)

df['nama_usaha_cleaned'] = df['nama_usaha'].apply(normalize)
df['flag_nama_org_w_usaha'] = ''

df['flag_nama_usaha'] = df['nama_usaha_cleaned'].apply(tandai_usaha)
df['flag_nama_org_w_usaha'] = df['nama_usaha'].apply(flag_usaha_dengan_nama)

df.to_csv('remaining_data_tagged_1.csv', sep=";")
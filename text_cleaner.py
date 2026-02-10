import re
import pandas as pd

jln_stopwords = [ "jalan", "jl", "jln", "jln"]
deskel_stopwords = [ "kelurahan", "kel", "kl", "desa", "ds"]
pasar_stopwords = [ "pasar", "psr", "ps"]
perumahan_stopwords = [ "perumahan", "perum", "prm", "prmh"]

def clean_text(text):
    text = re.sub(r'[^\w\s]', '', str(text))  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    return text.strip()

# capture number after RT or RW
def extract_rt_rw(text):
    rt_match = re.search(r'RT\s*(\d+)', str(text), re.IGNORECASE) # check if RT [space] number
    rw_match = re.search(r'RW\s*(\d+)', str(text), re.IGNORECASE)
    rt = rt_match.group(1) if rt_match else ''
    rw = rw_match.group(1) if rw_match else ''
    return rt, rw


def recognize_if_desa_only(alamat):
    if pd.isna(alamat):
        return ''
    alamat_lower = alamat.lower()
    for stopword in deskel_stopwords:
        if stopword in alamat_lower:
            return 1
    return ''

def is_in_perumahan(alamat):
    if pd.isna(alamat):
        return ''
    alamat_lower = alamat.lower()
    for stopword in perumahan_stopwords:
        if stopword in alamat_lower:
            return 1
    return ''

def is_in_pasar(alamat):
    if pd.isna(alamat):
        return ''
    alamat_lower = alamat.lower()
    for stopword in pasar_stopwords:
        if stopword in alamat_lower:
            return 1
    return ''

with open('dfkecil_recoded_2.csv', 'r', encoding="cp1252") as file:
    data = pd.read_csv(file, sep=";")
    df = pd.DataFrame(data)

    df['alamat_normalized'] = df['alamat_usaha'].apply(clean_text)
    df[['rt', 'rw']] = df['alamat_usaha'].apply(lambda x: pd.Series(extract_rt_rw(x)))
    df['is_desa_only'] = df['alamat_normalized'].apply(recognize_if_desa_only)
    df['is_in_perumahan'] = df['alamat_normalized'].apply(is_in_perumahan)
    df['is_in_pasar'] = df['alamat_normalized'].apply(is_in_pasar)

#print(df.head(50))
df.to_csv('dfkecil_recoded_with_rtrw.csv', index=False, sep=';')

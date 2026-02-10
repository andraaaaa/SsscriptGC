# Cek Duplikat 1.2 by Dhyandra Raka
# get the repo at https://github.com/andraaaaa

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import re
from collections import Counter

dup_global = 1
STOPWORDS = [
    "pt", "cv", "tbk", "cabang", "branch", "ud", "pd",
    "toko", "warung", "ruko", "kop", "koperasi",
    "jalan", "jl", "no", "blok", "block"
]

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

def remove_stopwords(text):
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOPWORDS]
    return " ".join(tokens)

def normalize(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess(text):
    text = normalize(text)
    text = remove_stopwords(text)
    return text

with open("recheck file\\data_tahap_2.csv", "r") as f:
    p = pd.read_csv(f, dtype=str, sep=";", encoding="cp1252")
    df = pd.DataFrame(p)
    #df = df_awal.head(1000).copy()

def extract_kbli_2d(text):
    if pd.isna(text):
        return "00"
    m = re.search(r'KBLI\s*[:=]\s*(\d{2})\d*', str(text))
    return m.group(1) if m else "00"

def extract_kbli_5d(text):
    if pd.isna(text):
        return "00000"
    m = re.search(r'KBLI\s*[:=]\s*(\d{5})\d*', str(text))
    return m.group(1) if m else "00000"


def split_group(df, size):  # Jika ingin split grup dataframe untuk mempercepat proses cek duplikat, misal split dataframe ke kode wilayah yang jumlahnya kurang dan lebih dari 500
    grup_size = df.groupby('kode_wilayah').size()
    grup_besar = grup_size[grup_size > size].index
    grup_kecil = grup_size[grup_size <= size].index
    df_besar = df[df['kode_wilayah'].isin(grup_besar)]
    df_kecil = df[df['kode_wilayah'].isin(grup_kecil)]

    return df_besar, df_kecil


print("Total data usaha:", len(df))
# live report row processed in terminal
print("Preprocessing nama usaha...")
df['cleaned_nama_usaha'] = df['nama_usaha'].apply(preprocess)
df['cleaned_alamat'] = df['alamat_usaha'].apply(normalize)
df['sim_score'] = 0
df["is_duplicate"] = 0
df['gc_flag_duplikat'] = 0
df['id_duplikat'] = ''
df['kbli5d'] = ''

#dup = 1
df['kbli5d'] = df['kegiatan_usaha'].apply(extract_kbli_5d)
df['nama_usaha_with_alamat_and_kbli'] = df['cleaned_nama_usaha'] + " " + df['cleaned_alamat'] + " kbli" + df['kbli5d']

print("Jumlah usaha dalam grup :", len(df))
print("Cek duplikat nama usaha berdasarkan kode wilayah...")
for wid, usaha in df.groupby('kode_wilayah'):
    if wid == "6401": continue                  # Filter yang isinya kode kabupaten aja karena terlalu umum untuk cek duplikat
    else:
        uf = UnionFind()
        u = usaha['nama_usaha_with_alamat_and_kbli'].to_list()
        idxs = usaha.index.to_list()

        vct = TfidfVectorizer(
            max_features=8000,
            analyzer='char_wb',
            ngram_range=(1,2),                 # Ideal untuk data nama alamat sampai kbli
            min_df=1
        )

        X = vct.fit_transform(u)
        print("Terdapat", len(u), "data di kode wilayah", wid)

        k = min(2, len(u))
        knn = NearestNeighbors(
            n_neighbors=k,
            metric='cosine',
            algorithm='brute',
            n_jobs=-1
        ).fit(X)

        distances, indices = knn.kneighbors(X)
        similarity = 1 - distances

        # SET untuk tracking flag
        flagged_idx = set()
        sim_map = {}

        for row_i, (neigh_idxs, sims) in enumerate(zip(indices, similarity)):
            idx_asli = idxs[row_i]

            for n_idx, sim in zip(neigh_idxs[1:], sims[1:]):
                idx_match = idxs[n_idx]

                if df.loc[idx_asli, 'kbli5d'] != df.loc[idx_match, 'kbli5d']:
                    continue

                if sim >= 0.8:      # Bisa diubah, makin tinggi sim score makin disinyalir duplikat
                    uf.union(idx_asli, idx_match)
                    key = tuple(sorted((idx_asli, idx_match)))
                    sim_map[key] = max(sim_map.get(key, 0), sim)

                    # HITUNG UKURAN CLUSTER
                    root_count = Counter(uf.find(i) for i in idxs)

                    # ASSIGN ID DUPLIKAT
                    cluster_id = {}

                    for idx in idxs:
                        root = uf.find(idx)

                        # skip singleton (bukan duplikat)
                        if root_count[root] == 1:
                            continue

                        if root not in cluster_id:
                            cluster_id[root] = dup_global
                            dup_global += 1

                        df.loc[idx, 'id_duplikat'] = cluster_id[root]
                        df.loc[idx, 'is_duplicate'] = 1

                    # OPTIONAL: sim_score
                    for (a, b), sim in sim_map.items():
                        if (
                            df.loc[a, 'id_duplikat']
                            == df.loc[b, 'id_duplikat']
                        ):
                            df.loc[a, 'sim_score'] = sim
                            df.loc[b, 'sim_score'] = sim

print("Assigning id duplikat setiap kluster ...")
for dup_id, g in df.groupby('id_duplikat'):

    if pd.isna(dup_id):
        continue
    # pilih master
    master_idx = g.index.min()
    df.loc[master_idx, 'gc_flag_duplikat'] = 1

    # sisanya duplikat
    dup_idxs = g.index.difference([master_idx])
    df.loc[dup_idxs, 'gc_flag_duplikat'] = 4

print("Mengurutkan data ...")
df.sort_values(by=['is_duplicate', 'id_duplikat'], ascending=True)
print("Menyimpan data ke CSV ...")
df.to_csv("data_tahap_2_dupcheck.csv", sep=";", index=False)
print("Data disimpan.")

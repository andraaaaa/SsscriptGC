from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import re
from collections import Counter




buffer = []
c = 0
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
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess(text):
    text = normalize(text)
    text = remove_stopwords(text)
    return text

with open("direktori_usaha_full_all_columns_2026.csv", "r") as f:
    p = pd.read_csv(f, dtype=str, sep=";", encoding="utf-8")
    df = pd.DataFrame(p)
    #df = df_awal.head(1000).copy()

def extract_kbli_2d(text):
    if pd.isna(text):
        return "00"
    m = re.search(r'KBLI\s*[:=]\s*(\d{2})\d*', str(text))
    return m.group(1) if m else "00"

def split_group(df, size):
    grup_size = df.groupby('kode_wilayah').size()
    grup_besar = grup_size[grup_size > size].index
    grup_kecil = grup_size[grup_size <= size].index
    df_besar = df[df['kode_wilayah'].isin(grup_besar)]
    df_kecil = df[df['kode_wilayah'].isin(grup_kecil)]

    return df_besar, df_kecil

df_b, df_k = split_group(df, 750)
df_besar = df_k.copy()

print("Total data usaha:", len(df_besar))
# live report row processed in terminal
print("Preprocessing nama usaha...")
df_besar['cleaned_nama_usaha'] = df_besar['nama_usaha'].apply(preprocess)
df_besar['cleaned_alamat'] = df_besar['alamat_usaha'].apply(normalize)
df_besar['sim_score'] = 0
df_besar["is_duplicate"] = 0
df_besar['gc_flag_duplikat'] = 0
df_besar['match_with'] = ''
df_besar['alamat_cek'] = ''
df_besar['id_duplikat'] = ''
df_besar['kbli2d'] = ''


dup = 1
df_besar['kbli2d'] = df_besar['kegiatan_usaha'].apply(extract_kbli_2d)
df_besar['nama_usaha_with_alamat_and_kbli'] = df_besar['cleaned_nama_usaha'] + " " + df_besar['cleaned_alamat'] + " kbli" + df_besar['kbli2d']

print("Jumlah usaha dalam grup :", len(df_besar))
print("Cek duplikat nama usaha berdasarkan kode wilayah...")
for wid, usaha in df_besar.groupby('kode_wilayah'):
    if wid == "6401": continue
    else:

        uf = UnionFind()

        u = usaha['nama_usaha_with_alamat_and_kbli'].to_list()
        idxs = usaha.index.to_list()

        vct = TfidfVectorizer(
            max_features=8000,
            analyzer='char_wb',
            ngram_range=(3, 8),
            min_df=1
        )

        X = vct.fit_transform(u)
        print(len(u), "data di kode wilayah", wid)

        k = min(2, len(u))
        knn = NearestNeighbors(
            n_neighbors=k,
            metric='cosine',
            algorithm='brute',
            n_jobs=-1
        ).fit(X)

        distances, indices = knn.kneighbors(X)
        similarity = 1 - distances

        # =========================
        # SET untuk tracking flag
        # =========================
        flagged_idx = set()
        sim_map = {}

        for row_i, (neigh_idxs, sims) in enumerate(zip(indices, similarity)):
            idx_asli = idxs[row_i]

            for n_idx, sim in zip(neigh_idxs[1:], sims[1:]):
                idx_match = idxs[n_idx]

                if df_besar.loc[idx_asli, 'kbli2d'] != df_besar.loc[idx_match, 'kbli2d']:
                    continue

                if sim >= 0.8:
                    uf.union(idx_asli, idx_match)
                    key = tuple(sorted((idx_asli, idx_match)))
                    sim_map[key] = max(sim_map.get(key, 0), sim)

        # =====================
        # HITUNG UKURAN CLUSTER
        # =====================
        
                    root_count = Counter(uf.find(i) for i in idxs)

        # =====================
        # ASSIGN ID DUPLIKAT
        # =====================
                    cluster_id = {}

                    for idx in idxs:
                        root = uf.find(idx)

                        # skip singleton (bukan duplikat)
                        if root_count[root] == 1:
                            continue

                        if root not in cluster_id:
                            cluster_id[root] = dup_global
                            dup_global += 1

                        df_besar.loc[idx, 'id_duplikat'] = cluster_id[root]
                        df_besar.loc[idx, 'is_duplicate'] = 1

                    # =====================
                    # OPTIONAL: sim_score
                    # =====================
                    for (a, b), sim in sim_map.items():
                        if (
                            df_besar.loc[a, 'id_duplikat']
                            == df_besar.loc[b, 'id_duplikat']
                        ):
                            df_besar.loc[a, 'sim_score'] = sim
                            df_besar.loc[b, 'sim_score'] = sim

print("Assigning id duplikat setiap kluster ...")
for dup_id, g in df_besar.groupby('id_duplikat'):

    if pd.isna(dup_id):
        continue
    # pilih master
    master_idx = g.index.min()
    df_besar.loc[master_idx, 'gc_flag_duplikat'] = 1

    # sisanya duplikat
    dup_idxs = g.index.difference([master_idx])
    df_besar.loc[dup_idxs, 'gc_flag_duplikat'] = 4

print("Mengurutkan data ...")
df_besar.sort_values(by=['is_duplicate', 'id_duplikat', 'gc_flag_duplikat'], ascending=True)
print("Menyimpan data ke CSV ...")
df_besar.to_csv("advanced_pairing_dfkecil_2.csv", sep=";", index=False)
print("Data disimpan.")

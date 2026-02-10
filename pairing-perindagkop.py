from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import hstack
import re
import numpy as np
import pandas as pd

THRES = 0.85
jln_stopwords = [ "jalan", "jl", "jln", "jln"]
deskel_stopwords = [ "kelurahan", "kel", "desa", "ds"]

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

def clean_text(text):
    if not isinstance(text, str):
        return ""
    
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)   # satu regex saja
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def rid_kbli(text):
    text_wo_kbli = re.sub(r'\bkbli\s*\d{2}\b', '', text)
    text_wo_kbli = re.sub(r'\s+', ' ', text_wo_kbli).strip()
    return text_wo_kbli

def clean_alamat(text):
    text = clean_text(text)
    for stp in jln_stopwords:
        text = re.sub(rf'\b{stp}\b', '', text)

    for stp2 in deskel_stopwords:
        text = re.sub(rf'\b{stp2}\b', '', text)
    
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

with open('SsscriptGC\data-parent.csv', 'r') as f1:
    df_p = pd.read_csv(f1, sep=";", encoding="cp1252")

with open('SsscriptGC\data-pivot.csv', 'r') as f2:
    df_v = pd.read_csv(f2, sep=";", encoding="cp1252")

parent_data = pd.DataFrame(df_p)
pivot_data = pd.DataFrame(df_v)

for wid, usaha in parent_data.groupby('kode_wilayah'):
    if wid == "6401": continue                  # Filter yang isinya kode kabupaten aja karena terlalu umum untuk cek duplikat
    else:

        u = usaha['nama_usaha'].to_list()
        #uf = UnionFind()
        vectorizer = TfidfVectorizer(
            ngram_range=(1,2),
            max_features=8000
        )

        tfidf_pivot = vectorizer.fit_transform(pivot_data['nama'])
        tfidf_parent = vectorizer.transform(u)

        nn = NearestNeighbors(
            n_neighbors=1,
            metric='cosine',
            algorithm='brute'
        )
        nn.fit(tfidf_pivot)

        dist, idxs = nn.kneighbors(tfidf_parent)

        parent_data['sim_score'] = 1 - dist.flatten()
        parent_data['pivot_idx'] = idxs.flatten()
        parent_data['lat_match'] = None
        parent_data['long_match'] = None

        mask = parent_data['sim_score'] >= THRES
        parent_data.loc[mask, 'lat_match'] = (
            pivot_data.iloc[parent_data.loc[mask, 'pivot_idx']]['latitude_pivot'].values
        )
        parent_data.loc[mask, 'long_match'] = (
            pivot_data.iloc[parent_data.loc[mask, 'pivot_idx']]['longitude_pivot'].values
        )

        parent_data['match_flag'] = np.where(parent_data['sim_score'] >= THRES, 'MATCH', 'NO_MATCH')
        parent_data.to_csv('test_perindagkop.csv', sep=";")

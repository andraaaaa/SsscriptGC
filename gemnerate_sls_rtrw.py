import pandas as pd
import re

def extract_rt_rw(text):
    rt_match = re.search(r'RT\s*(\d+)', str(text), re.IGNORECASE) # check if RT [space] number
    rw_match = re.search(r'RW\s*(\d+)', str(text), re.IGNORECASE)
    rt = rt_match.group(1) if rt_match else ''
    rw = rw_match.group(1) if rw_match else ''
    return rt, rw

with open('centroids-data\\sls-ccentroid-with-code.csv', 'r') as f:
    cdata = pd.read_csv(f, sep=";", encoding="cp1252")
    df = pd.DataFrame(cdata)

df[['rt', 'rw']] = df['nmsls'].apply(lambda x: pd.Series(extract_rt_rw(x)))
df.to_excel('sls_rtrw_centroids.xlsx')


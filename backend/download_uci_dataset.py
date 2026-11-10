"""Optional downloader for the UCI Online Retail benchmark (not kitchen-specific).
Requires: pip install ucimlrepo
The UCI dataset is CC BY 4.0; see the project README for attribution.
"""
from ucimlrepo import fetch_ucirepo
from pathlib import Path
import pandas as pd

repo = fetch_ucirepo(id=352)
df = repo.data.features.copy()
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
df = df.dropna(subset=['Description','InvoiceDate','Quantity'])
df = df[df['Quantity'] > 0]
if 'InvoiceNo' in df.columns:
    df = df[~df['InvoiceNo'].astype(str).str.startswith('C')]
out = df.assign(date=df['InvoiceDate'].dt.date.astype(str), item_name=df['Description'].astype(str).str.strip(), quantity=df['Quantity'])[['date','item_name','quantity']]
path = Path(__file__).resolve().parent / 'data' / 'uci_online_retail_daily.csv'
out.to_csv(path, index=False)
print(f'Saved {len(out):,} transaction rows to {path}')
print('Important: UCI Online Retail is general gift/novelty retail, not a food/kitchen dataset. Use it only as a generic retail forecasting benchmark.')

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from joblib import dump, load

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'demo_sales.csv'
MODEL = ROOT / 'data' / 'demand_model.joblib'
METRICS = ROOT / 'data' / 'model_metrics.json'
FEATURES = ['lag_1','lag_7','lag_14','rolling_7','rolling_14','dayofweek','month','dayofyear']

def make_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({'y': series.astype(float)})
    idx = pd.DatetimeIndex(df.index)
    df['lag_1'] = df.y.shift(1); df['lag_7'] = df.y.shift(7); df['lag_14'] = df.y.shift(14)
    df['rolling_7'] = df.y.shift(1).rolling(7).mean(); df['rolling_14'] = df.y.shift(1).rolling(14).mean()
    df['dayofweek'] = idx.dayofweek; df['month'] = idx.month; df['dayofyear'] = idx.dayofyear
    return df.dropna()

def train_all():
    raw = pd.read_csv(DATA, parse_dates=['date'])
    raw['quantity'] = pd.to_numeric(raw.quantity, errors='coerce').clip(lower=0)
    results = {}
    trained = {}
    for item, grp in raw.groupby('item_name'):
        s = grp.groupby('date').quantity.sum().sort_index()
        if len(s) < 35: continue
        full_idx = pd.date_range(s.index.min(), s.index.max(), freq='D')
        s = s.reindex(full_idx, fill_value=0)
        f = make_features(s); X, y = f[FEATURES], f.y
        split = max(int(len(f)*0.8), 1)
        Xtr, Xte, ytr, yte = X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]
        candidates = {
            'Random Forest': RandomForestRegressor(n_estimators=180, max_depth=10, min_samples_leaf=2, random_state=42, n_jobs=-1),
            'Extra Trees': ExtraTreesRegressor(n_estimators=180, max_depth=10, min_samples_leaf=2, random_state=42, n_jobs=-1),
            'Hist Gradient Boosting': HistGradientBoostingRegressor(max_iter=120, l2_regularization=1.0, random_state=42)
        }
        scored=[]
        for name, model in candidates.items():
            pipe=make_pipeline(SimpleImputer(strategy='median'), model)
            pipe.fit(Xtr,ytr); pred=np.maximum(0,pipe.predict(Xte))
            mae=float(mean_absolute_error(yte,pred)); rmse=float(np.sqrt(mean_squared_error(yte,pred)))
            scored.append((mae,name,pipe,rmse,float(r2_score(yte,pred)) if len(yte)>1 else 0.0))
        scored.sort(key=lambda x:x[0]); best=scored[0]
        final=make_pipeline(SimpleImputer(strategy='median'), candidates[best[1]])
        final.fit(X,y)
        trained[item]={'model':final,'history':s.tail(60).tolist(),'last_date':s.index[-1].strftime('%Y-%m-%d'),'model_name':best[1], 'metrics':{'mae':best[0],'rmse':best[3],'r2':best[4],'test_days':len(yte)}}
        results[item]={'model':best[1],**trained[item]['metrics']}
    dump(trained, MODEL)
    METRICS.write_text(json.dumps(results,indent=2))
    return results

def predict_item(item_name: str, days: int=7):
    if not MODEL.exists(): train_all()
    models=load(MODEL)
    if item_name not in models: raise ValueError('No training history for this item. Import sales history or use a demo item.')
    obj=models[item_name]; hist=pd.Series(obj['history'], index=pd.date_range(end=obj['last_date'], periods=len(obj['history']), freq='D'),dtype=float)
    preds=[]
    for _ in range(days):
        next_date=hist.index[-1]+pd.Timedelta(days=1)
        temp=pd.concat([hist,pd.Series([np.nan],index=[next_date])])
        # Build exactly the features from prior observations.
        row=pd.DataFrame([{'lag_1':hist.iloc[-1], 'lag_7':hist.iloc[-7] if len(hist)>=7 else hist.mean(), 'lag_14':hist.iloc[-14] if len(hist)>=14 else hist.mean(), 'rolling_7':hist.tail(7).mean(), 'rolling_14':hist.tail(14).mean(), 'dayofweek':next_date.dayofweek,'month':next_date.month,'dayofyear':next_date.dayofyear}])
        value=max(0.0,float(obj['model'].predict(row[FEATURES])[0])); preds.append({'date':next_date.strftime('%Y-%m-%d'),'quantity':round(value,2)})
        hist.loc[next_date]=value
    return {'item_name':item_name,'model':obj['model_name'],'metrics':obj['metrics'],'predictions':preds,'total_demand':round(sum(x['quantity'] for x in preds),2)}

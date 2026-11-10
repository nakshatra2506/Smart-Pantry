from datetime import date, datetime, timedelta
from pathlib import Path
import csv, io, random
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from .db import Base, engine, get_db, SessionLocal
from .models import Item, Batch, Sale, Waste, Movement
from .ml import train_all, predict_item, METRICS

app = FastAPI(title='SmartPantry API', version='2.0.0', description='Kitchen inventory and demand forecasting API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
Base.metadata.create_all(bind=engine)

class ItemIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = 'Other'; unit: str = 'unit'
    quantity: float = Field(default=0, ge=0); min_stock: float = Field(default=5, ge=0)
    unit_cost: float = Field(default=0, ge=0); supplier: str = ''
class StockIn(BaseModel):
    quantity: float = Field(gt=0); expiry_date: date | None = None; note: str = ''
class SaleIn(BaseModel):
    quantity: float = Field(gt=0); unit_price: float = Field(default=0, ge=0); note: str = ''
class WasteIn(BaseModel):
    quantity: float = Field(gt=0); reason: str = 'Expired'


def serialize_item(x):
    return {'id':x.id,'name':x.name,'category':x.category,'unit':x.unit,'quantity':round(x.quantity,2),'min_stock':x.min_stock,'unit_cost':x.unit_cost,'supplier':x.supplier,'stock_value':round(x.quantity*x.unit_cost,2)}
def consume_batches(db, item_id, qty):
    batches=db.query(Batch).filter(Batch.item_id==item_id, Batch.quantity>0).order_by(Batch.expiry_date.asc().nullslast(), Batch.received_at.asc()).all()
    remaining=qty
    for b in batches:
        take=min(b.quantity,remaining); b.quantity-=take; remaining-=take
        if remaining<=1e-8: break
    # Batches may not exist for legacy/manual stock; item quantity remains authoritative.

def seed():
    db=SessionLocal()
    try:
        if db.query(Item).count(): return
        rng=random.Random(19)
        products=[('Tomatoes','Vegetables','kg',24,8,38),('Onions','Vegetables','kg',32,10,28),('Potatoes','Vegetables','kg',40,12,24),('Milk','Dairy','litre',18,8,32),('Eggs','Dairy','dozen',15,5,72),('Rice','Grains','kg',55,15,62),('Chicken','Meat','kg',12,5,210),('Spinach','Vegetables','bunch',10,4,18),('Paneer','Dairy','kg',8,3,260)]
        for name,cat,unit,q,m,cost in products:
            it=Item(name=name,category=cat,unit=unit,quantity=q,min_stock=m,unit_cost=cost,supplier='Demo Supplier')
            db.add(it); db.flush(); db.add(Batch(item_id=it.id,quantity=q,expiry_date=date.today()+timedelta(days=rng.randint(2,24))))
        db.commit()
    finally: db.close()
seed()

@app.get('/api/health')
def health(): return {'status':'ok','service':'SmartPantry API'}
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db)):
    items=db.query(Item).all(); today=datetime.now().date(); batches=db.query(Batch).all()
    expiring=[b for b in batches if b.expiry_date and 0 <= (b.expiry_date-today).days <= 7 and b.quantity>0]
    expired=[b for b in batches if b.expiry_date and b.expiry_date<today and b.quantity>0]
    low=[i for i in items if i.quantity<=i.min_stock]
    sales_today=db.query(func.coalesce(func.sum(Sale.quantity*Sale.unit_price),0)).filter(func.date(Sale.sold_at)==today.isoformat()).scalar() or 0
    waste_cost=db.query(func.coalesce(func.sum(Waste.quantity*Item.unit_cost),0)).join(Item).scalar() or 0
    return {'item_count':len(items),'inventory_value':round(sum(i.quantity*i.unit_cost for i in items),2),'low_stock_count':len(low),'expiring_count':len(expiring),'expired_count':len(expired),'sales_today':round(float(sales_today),2),'waste_cost':round(float(waste_cost),2),'low_stock':[serialize_item(i) for i in low], 'expiring':[{'item':b.item.name,'quantity':b.quantity,'expiry_date':b.expiry_date.isoformat()} for b in expiring[:8]],'recent_sales':sale_list(db,5)}

def sale_list(db,limit=100):
    rows=db.query(Sale).order_by(Sale.sold_at.desc()).limit(limit).all()
    return [{'id':s.id,'item_id':s.item_id,'item_name':s.item.name,'quantity':s.quantity,'unit_price':s.unit_price,'total':round(s.quantity*s.unit_price,2),'sold_at':s.sold_at.isoformat(),'note':s.note} for s in rows]
@app.get('/api/items')
def list_items(db:Session=Depends(get_db)): return [serialize_item(i) for i in db.query(Item).order_by(Item.name).all()]
@app.post('/api/items')
def create_item(data:ItemIn,db:Session=Depends(get_db)):
    if db.query(Item).filter(func.lower(Item.name)==data.name.lower()).first(): raise HTTPException(409,'An item with this name already exists.')
    it=Item(**data.model_dump()); db.add(it); db.flush()
    if it.quantity: db.add(Batch(item_id=it.id,quantity=it.quantity))
    db.commit(); db.refresh(it); return serialize_item(it)
@app.put('/api/items/{item_id}')
def update_item(item_id:int,data:ItemIn,db:Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,'Item not found')
    old_qty = it.quantity
    new_data = data.model_dump()
    for k,v in new_data.items(): setattr(it,k,v)
    delta = it.quantity - old_qty
    if delta > 0:
        db.add(Batch(item_id=item_id, quantity=delta))
    elif delta < 0:
        consume_batches(db, item_id, -delta)
    db.commit(); db.refresh(it); return serialize_item(it)
@app.delete('/api/items/{item_id}')
def delete_item(item_id:int,db:Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,'Item not found')
    if db.query(Sale).filter_by(item_id=item_id).first() or db.query(Waste).filter_by(item_id=item_id).first(): raise HTTPException(409,'Cannot delete an item with sales or waste history.')
    db.delete(it); db.commit(); return {'message':'Item deleted'}
@app.post('/api/items/{item_id}/stock-in')
def stock_in(item_id:int,data:StockIn,db:Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,'Item not found')
    it.quantity+=data.quantity; db.add(Batch(item_id=item_id,quantity=data.quantity,expiry_date=data.expiry_date)); db.add(Movement(item_id=item_id,movement_type='IN',quantity=data.quantity,note=data.note)); db.commit(); return serialize_item(it)
@app.post('/api/items/{item_id}/sales')
def record_sale(item_id:int,data:SaleIn,db:Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,'Item not found')
    if it.quantity<data.quantity: raise HTTPException(400,f'Insufficient stock. Available: {it.quantity:g} {it.unit}.')
    it.quantity-=data.quantity; consume_batches(db,item_id,data.quantity)
    s=Sale(item_id=item_id,quantity=data.quantity,unit_price=data.unit_price,note=data.note); db.add(s); db.add(Movement(item_id=item_id,movement_type='SALE',quantity=data.quantity,note=data.note)); db.commit(); db.refresh(s)
    return {'message':'Sale recorded','sale':{'id':s.id,'item_name':it.name,'quantity':s.quantity,'total':s.quantity*s.unit_price}}
@app.get('/api/sales')
def sales(db:Session=Depends(get_db)): return sale_list(db,200)
@app.post('/api/items/{item_id}/waste')
def record_waste(item_id:int,data:WasteIn,db:Session=Depends(get_db)):
    it=db.get(Item,item_id)
    if not it: raise HTTPException(404,'Item not found')
    if it.quantity<data.quantity: raise HTTPException(400,'Waste quantity exceeds available stock.')
    it.quantity-=data.quantity; consume_batches(db,item_id,data.quantity); db.add(Waste(item_id=item_id,quantity=data.quantity,reason=data.reason)); db.add(Movement(item_id=item_id,movement_type='WASTE',quantity=data.quantity,note=data.reason)); db.commit(); return {'message':'Waste recorded'}
@app.get('/api/waste')
def waste(db:Session=Depends(get_db)):
    rows=db.query(Waste).order_by(Waste.wasted_at.desc()).limit(200).all()
    return [{'id':w.id,'item_name':w.item.name,'quantity':w.quantity,'reason':w.reason,'cost':round(w.quantity*w.item.unit_cost,2),'wasted_at':w.wasted_at.isoformat()} for w in rows]
@app.get('/api/expiry')
def expiry(db:Session=Depends(get_db)):
    rows=db.query(Batch).filter(Batch.quantity>0).order_by(Batch.expiry_date.asc().nullslast()).all()
    return [{'id':b.id,'item_id':b.item_id,'item_name':b.item.name,'quantity':b.quantity,'expiry_date':b.expiry_date.isoformat() if b.expiry_date else None,'days_left':(b.expiry_date-date.today()).days if b.expiry_date else None} for b in rows]
@app.get('/api/forecast')
def forecasts(db:Session=Depends(get_db)):
    result=[]
    for it in db.query(Item).order_by(Item.name).all():
        try:
            f=predict_item(it.name,7); demand=f['total_demand']; target=max(it.min_stock,demand*1.15); reorder=max(0,round(target-it.quantity,2))
            result.append({'item_id':it.id,'item_name':it.name,'unit':it.unit,'current_stock':it.quantity,'predicted_7_day_demand':demand,'recommended_reorder':reorder,'model':f['model'],'mae':f['metrics']['mae'],'rmse':f['metrics']['rmse'],'predictions':f['predictions']})
        except Exception as e: result.append({'item_id':it.id,'item_name':it.name,'error':str(e),'current_stock':it.quantity,'recommended_reorder':max(0,it.min_stock-it.quantity)})
    return result
@app.get('/api/model/metrics')
def model_metrics():
    if not METRICS.exists(): return {'message':'Model has not been trained yet.'}
    import json
    return json.loads(METRICS.read_text())
@app.post('/api/model/train')
def model_train():
    try: return {'message':'Training completed using a chronological 80/20 split.','results':train_all()}
    except Exception as e: raise HTTPException(500,f'Model training failed: {e}')
@app.post('/api/import/sales-csv')
async def import_sales_csv(file:UploadFile=File(...)):
    if not file.filename.lower().endswith('.csv'): raise HTTPException(400,'Upload a CSV file.')
    content=(await file.read()).decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(content)); required={'date','item_name','quantity'}
    if not reader.fieldnames or not required.issubset({x.strip().lower() for x in reader.fieldnames}): raise HTTPException(400,'CSV must contain date, item_name, quantity columns.')
    # Append normalized rows to the training history file; this is training history, not transactional DB sales.
    path=Path(__file__).resolve().parents[1]/'data'/'demo_sales.csv'
    normalized=[]
    for row in reader:
        r={k.strip().lower():v for k,v in row.items() if k}
        try: normalized.append({'date':pd_date(r['date']),'item_name':r['item_name'].strip(),'quantity':float(r['quantity'])})
        except Exception: continue
    if not normalized: raise HTTPException(400,'No valid rows found.')
    with path.open('a',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['date','item_name','quantity']); w.writerows(normalized)
    return {'message':f'Imported {len(normalized)} historical rows. Retrain the model to use them.'}

def pd_date(v):
    return datetime.fromisoformat(v).date().isoformat()
@app.get('/api/reports/inventory.csv')
def export_inventory(db:Session=Depends(get_db)):
    out=io.StringIO(); w=csv.writer(out); w.writerow(['id','name','category','quantity','unit','min_stock','unit_cost','stock_value'])
    for i in db.query(Item).all(): w.writerow([i.id,i.name,i.category,i.quantity,i.unit,i.min_stock,i.unit_cost,i.quantity*i.unit_cost])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=smartpantry_inventory.csv'})

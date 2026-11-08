"""Cross-file quality checks for generated source tables."""
from pathlib import Path
import argparse, json
import pandas as pd

def validate(data: Path):
    read=lambda f: pd.read_csv(data/f)
    sku,store,supplier,supplier_sku,sales,inv,lead=map(read,['sku.csv','store.csv','supplier.csv','supplier_sku.csv','sales_history.csv','inventory_snapshot.csv','lead_time_observation.csv'])
    checks={}
    checks['sku_primary_key_unique']=bool(sku.sku_id.is_unique)
    checks['store_primary_key_unique']=bool(store.store_id.is_unique)
    checks['supplier_primary_key_unique']=bool(supplier.supplier_id.is_unique)
    checks['sales_grain_unique']=bool(not sales.duplicated(['store_id','sku_id','sale_date']).any())
    checks['sales_store_fk_valid']=bool(sales.store_id.isin(store.store_id).all())
    checks['sales_sku_fk_valid']=bool(sales.sku_id.isin(sku.sku_id).all())
    checks['supplier_sku_fk_valid']=bool(supplier_sku.supplier_id.isin(supplier.supplier_id).all() and supplier_sku.sku_id.isin(sku.sku_id).all())
    checks['inventory_fk_valid']=bool(inv.store_id.isin(store.store_id).all() and inv.sku_id.isin(sku.sku_id).all())
    checks['pack_and_moq_positive']=bool((supplier_sku.pack_size>0).all() and (supplier_sku.moq_units>0).all())
    checks['valid_lead_times_positive']=bool((lead.loc[lead.is_valid.astype(bool),'observed_days']>0).all())
    checks['stockouts_separately_flagged']=bool('stockout_flag' in sales and sales.stockout_flag.notna().all())
    return {'passed':all(checks.values()),'checks':checks,'row_counts':{'sku':len(sku),'store':len(store),'sales':len(sales),'inventory':len(inv),'supplier_sku':len(supplier_sku)}}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data',default='data/sample'); a=p.parse_args()
    result=validate(Path(a.data)); print(json.dumps(result,indent=2))
    if not result['passed']: raise SystemExit(1)

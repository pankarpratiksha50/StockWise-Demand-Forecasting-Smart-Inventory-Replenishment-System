"""Deterministic synthetic retail data generator. Supports chunked full-scale generation."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

SEED_DEFAULT = 20261022

def generate(out: Path, n_skus=24, n_stores=6, days=180, seed=SEED_DEFAULT, chunk_size=250_000):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    start = pd.Timestamp('2025-01-01')
    categories = ['Grocery','Personal Care','Home','Electronics','Apparel']
    regions = ['North','South','East','West']
    skus = pd.DataFrame({
        'sku_id':[f'SKU-{i:06d}' for i in range(1,n_skus+1)],
        'sku_name':[f'{c} Item {i:04d}' for i,c in enumerate(rng.choice(categories,n_skus),1)],
        'category':rng.choice(categories,n_skus), 'unit_cost':np.round(rng.uniform(3,80,n_skus),2),
        'unit_price':np.round(rng.uniform(8,150,n_skus),2), 'is_discontinued':False,
        'launch_date':start.strftime('%Y-%m-%d'), 'lifecycle_status':'ACTIVE'
    })
    # Deliberate lifecycle exception is explicit and labelled.
    if n_skus >= 12:
        skus.loc[skus.index[-1], ['is_discontinued','lifecycle_status']] = [True,'DISCONTINUED']
    stores = pd.DataFrame({'store_id':[f'STORE-{i:06d}' for i in range(1,n_stores+1)],
        'store_name':[f'Store {i:03d}' for i in range(1,n_stores+1)], 'region':rng.choice(regions,n_stores),
        'daily_storage_capacity_units':rng.integers(800,2200,n_stores)})
    suppliers = pd.DataFrame({'supplier_id':[f'SUP-{i:04d}' for i in range(1,max(4,n_skus//5)+1)],
        'supplier_name':[f'Supplier {i:02d}' for i in range(1,max(4,n_skus//5)+1)], 'active':True})
    pairs=[]
    for i, sku in skus.iterrows():
        sid=suppliers.iloc[i % len(suppliers)].supplier_id
        pairs.append({'supplier_sku_id':f'SSUP-{i+1:06d}','supplier_id':sid,'sku_id':sku.sku_id,
                      'pack_size':int(rng.choice([1,4,6,12,24])),'moq_units':int(rng.choice([1,6,12,24])),
                      'unit_cost':sku.unit_cost,'supplier_capacity_units':int(rng.integers(500,5000)),
                      'effective_from':start.date().isoformat(),'effective_to':None,'is_primary':True})
    supplier_skus=pd.DataFrame(pairs)
    # SKU-store matrix, with stable base demand and seasonality per pair.
    matrix=[]
    for si, store in stores.iterrows():
        for ki, sku in skus.iterrows():
            matrix.append((store.store_id,sku.sku_id,float(rng.uniform(1.5,18)),float(rng.uniform(.08,.35)),int(rng.integers(1,8)),float(rng.uniform(.02,.22))))
    sales_path=out/'sales_history.csv'
    if sales_path.exists(): sales_path.unlink()
    first=True
    all_lead=[]; inventory=[]; truth=[]
    for store_id,sku_id,base_d,noise,season_phase,intermittent_prob in matrix:
        sku=skus.loc[skus.sku_id.eq(sku_id)].iloc[0]
        supplier_row=supplier_skus.loc[supplier_skus.sku_id.eq(sku_id)].iloc[0]
        lead_mean=int(rng.integers(3,13))
        # Per pair stock position and replenishment simulation.
        stock=max(10,int(base_d*lead_mean*2)); on_order=0
        rows=[]
        for day in range(days):
            date=start+pd.Timedelta(days=day)
            weekly=1 + .18*np.sin(2*np.pi*(day+season_phase)/7)
            annual=1 + .28*np.sin(2*np.pi*day/365)
            promo=bool(rng.random()<.035)
            launch_lift=1.25 if day<21 else 1.0
            latent=0 if rng.random()<intermittent_prob else max(0,int(round(base_d*weekly*annual*launch_lift*(1.65 if promo else 1)*rng.lognormal(0,noise))))
            received=0
            if day % 30 == 0:
                stock=max(stock,int(base_d*35))  # periodic replenishment simulation
            stock += received
            sold=min(stock,latent)
            stockout=bool(sold < latent)
            stock-=sold
            rows.append({'sale_id':f'SALE-{store_id[-6:]}-{sku_id[-6:]}-{date:%Y%m%d}','store_id':store_id,'sku_id':sku_id,
                         'sale_date':date.date().isoformat(),'units_sold':sold,'promotion_flag':promo,
                         'stockout_flag':stockout,'unit_price':round(float(sku.unit_price)*(0.9 if promo else 1),2)})
            truth.append({'store_id':store_id,'sku_id':sku_id,'sale_date':date.date().isoformat(),'true_demand_units':latent,'stockout_flag':stockout})
            if day % 30 == 0:
                inventory.append({'snapshot_id':f'INV-{store_id[-6:]}-{sku_id[-6:]}-{date:%Y%m%d}','store_id':store_id,'sku_id':sku_id,
                                  'snapshot_date':date.date().isoformat(),'on_hand_units':stock,'on_order_units':on_order,'reserved_units':0})
        df=pd.DataFrame(rows)
        df.to_csv(sales_path,mode='a',header=first,index=False); first=False
        # Valid lead-time observations with one labelled invalid observation in separate issue table.
        for j in range(5):
            lt=max(1,int(round(rng.normal(lead_mean, max(1,lead_mean*.18)))))
            all_lead.append({'lead_time_observation_id':f'LTO-{len(all_lead)+1:08d}','supplier_id':supplier_row.supplier_id,
                             'sku_id':sku_id,'observed_days':lt,'observation_date':(start+pd.Timedelta(days=min(days-1,j*30))).date().isoformat(),'is_valid':True})
    pd.DataFrame(inventory).to_csv(out/'inventory_snapshot.csv',index=False)
    pd.DataFrame(all_lead).to_csv(out/'lead_time_observation.csv',index=False)
    skus.to_csv(out/'sku.csv',index=False); stores.to_csv(out/'store.csv',index=False)
    suppliers.to_csv(out/'supplier.csv',index=False); supplier_skus.to_csv(out/'supplier_sku.csv',index=False)
    pd.DataFrame(truth).to_csv(out/'ground_truth.csv',index=False)
    # Deliberately injected anomaly records are separate and never mixed into baseline facts.
    issues=[
      {'issue_id':'ISSUE-0001','issue_type':'NEGATIVE_LEAD_TIME','entity_id':'LTO-INVALID-0001','ground_truth_label':'INVALID_EXCLUDE_FROM_ESTIMATION','description':'Negative lead time must be rejected.'},
      {'issue_id':'ISSUE-0002','issue_type':'STOCKOUT_AS_ZERO_DEMAND','entity_id':'SALE-STOCKOUT-CASE','ground_truth_label':'CENSORED_DEMAND_NOT_ZERO','description':'Stockout-censored sales must not be interpreted as zero demand.'},
      {'issue_id':'ISSUE-0003','issue_type':'PACK_SIZE_VIOLATION','entity_id':'PO-PACK-CASE','ground_truth_label':'ROUND_UP_TO_PACK_MULTIPLE','description':'Order quantity must respect supplier pack size and MOQ.'},
      {'issue_id':'ISSUE-0004','issue_type':'DISCONTINUED_SKU','entity_id':skus.iloc[-1].sku_id,'ground_truth_label':'BLOCK_RECOMMENDATION','description':'Discontinued items cannot be recommended for replenishment.'},
      {'issue_id':'ISSUE-0005','issue_type':'FUTURE_DATA_LEAKAGE','entity_id':'FORECAST-HOLDOUT','ground_truth_label':'TRAIN_ONLY_ON_PAST','description':'Future holdout observations are evaluation labels only.'}
    ]
    pd.DataFrame(issues).to_csv(out/'known_issues.csv',index=False)
    edge_cases=[
      {'case_id':'EDGE-0001','issue_type':'NEGATIVE_LEAD_TIME','supplier_id':suppliers.iloc[0].supplier_id,'sku_id':skus.iloc[0].sku_id,'observed_days':-3,'expected_handling':'REJECT_AND_FLAG'},
      {'case_id':'EDGE-0002','issue_type':'PACK_SIZE_VIOLATION','supplier_id':suppliers.iloc[0].supplier_id,'sku_id':skus.iloc[0].sku_id,'proposed_order_units':7,'expected_handling':'ROUND_TO_MOQ_AND_PACK_MULTIPLE'},
      {'case_id':'EDGE-0003','issue_type':'DISCONTINUED_SKU','supplier_id':supplier_skus.iloc[-1].supplier_id,'sku_id':skus.iloc[-1].sku_id,'proposed_order_units':24,'expected_handling':'BLOCK_ORDER'},
      {'case_id':'EDGE-0004','issue_type':'FUTURE_DATA_LEAKAGE','supplier_id':None,'sku_id':skus.iloc[0].sku_id,'proposed_order_units':None,'expected_handling':'KEEP_FUTURE_LABELS_OUT_OF_TRAINING'}
    ]
    pd.DataFrame(edge_cases).to_csv(out/'edge_case_records.csv',index=False)
    manifest={'seed':seed,'n_skus':n_skus,'n_stores':n_stores,'days':days,'start_date':str(start.date()),
              'sales_rows_expected':int(sum(1 for x in matrix if not skus.loc[skus.sku_id.eq(x[1]),'is_discontinued'].iloc[0])*days),
              'generator_version':'1.0.0','notes':'Ground truth is isolated from model input. Sales with stockout_flag=true are censored.'}
    (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',default='data/generated'); p.add_argument('--skus',type=int,default=2000)
    p.add_argument('--stores',type=int,default=100); p.add_argument('--days',type=int,default=365); p.add_argument('--seed',type=int,default=SEED_DEFAULT)
    a=p.parse_args(); print(json.dumps(generate(Path(a.out),a.skus,a.stores,a.days,a.seed),indent=2))

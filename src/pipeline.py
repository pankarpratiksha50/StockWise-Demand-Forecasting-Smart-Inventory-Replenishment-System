"""Forecast evaluation and constraint-aware replenishment decision engine."""
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd


def wape(actual, predicted):
    denom=np.abs(actual).sum()
    return float(np.abs(actual-predicted).sum()/denom*100) if denom else 0.0

def run(data_dir: Path, out_dir: Path, horizon=14, holdout_days=28):
    out_dir.mkdir(parents=True,exist_ok=True)
    read=lambda f: pd.read_csv(data_dir/f)
    sku,store,sales,inv,supsku,lead=map(read,['sku.csv','store.csv','sales_history.csv','inventory_snapshot.csv','supplier_sku.csv','lead_time_observation.csv'])
    sales['sale_date']=pd.to_datetime(sales.sale_date)
    # Exclude stockout-censored days from demand estimation; never turn them into zero demand.
    clean=sales.loc[~sales.stockout_flag.astype(bool)].copy()
    cutoff=clean.sale_date.max()-pd.Timedelta(days=holdout_days)
    train=clean.loc[clean.sale_date<=cutoff]
    truth=read('ground_truth.csv'); truth['sale_date']=pd.to_datetime(truth.sale_date)
    test=sales.loc[sales.sale_date>cutoff].merge(truth,on=['store_id','sku_id','sale_date'],how='left',suffixes=('','_truth'))
    # Last valid inventory snapshot for each pair.
    inv['snapshot_date']=pd.to_datetime(inv.snapshot_date)
    inv=inv.sort_values('snapshot_date').groupby(['store_id','sku_id'],as_index=False).tail(1)
    lead=lead.loc[(lead.observed_days>0)&lead.is_valid.astype(bool)]
    lead_avg=lead.groupby(['supplier_id','sku_id']).observed_days.mean().to_dict()
    records=[]; eval_rows=[]
    for (store_id,sku_id),hist in train.groupby(['store_id','sku_id']):
        hist=hist.sort_values('sale_date'); vals=hist.units_sold.astype(float)
        if len(vals)<14: continue
        # Simple explainable hybrid: weighted recent average and weekly seasonal profile.
        recent=float(vals.tail(28).mean()); weekly=float(vals.tail(56).groupby(hist.tail(56).sale_date.dt.dayofweek).mean().mean())
        forecast=max(0,0.7*recent+0.3*weekly)
        residual=vals.tail(56).to_numpy()-recent
        daily_std=float(np.std(residual,ddof=1)) if len(residual)>1 else 0.0
        pair_test=test.loc[(test.store_id==store_id)&(test.sku_id==sku_id)]
        if len(pair_test):
            actual=float(pair_test.true_demand_units.mean()); eval_rows.append({'store_id':store_id,'sku_id':sku_id,'actual_mean':actual,'forecast_daily':forecast,'n_test_days':len(pair_test)})
        records.append({'store_id':store_id,'sku_id':sku_id,'forecast_daily_units':forecast,'daily_demand_std':daily_std,
                        'forecast_horizon_units':forecast*horizon,'training_rows':len(hist),'forecast_as_of':cutoff.date().isoformat()})
    fc=pd.DataFrame(records)
    if fc.empty: raise ValueError('No SKU/store pairs had enough uncensored training history. Increase generated days.')
    fc=fc.merge(inv[['store_id','sku_id','on_hand_units','on_order_units','reserved_units']],on=['store_id','sku_id'],how='left')
    fc[['on_hand_units','on_order_units','reserved_units']]=fc[['on_hand_units','on_order_units','reserved_units']].fillna(0)
    fc=fc.merge(sku[['sku_id','unit_cost','is_discontinued','lifecycle_status']],on='sku_id',how='left')
    fc=fc.merge(supsku[['sku_id','supplier_id','pack_size','moq_units','supplier_capacity_units']],on='sku_id',how='left')
    fc=fc.merge(store[['store_id','daily_storage_capacity_units']],on='store_id',how='left')
    fc['lead_time_days']=[lead_avg.get((r.supplier_id,r.sku_id),7.0) for r in fc.itertuples()]
    fc['safety_stock_units']=np.ceil(1.65*fc.daily_demand_std*np.sqrt(fc.lead_time_days)).astype(int)
    fc['reorder_point_units']=np.ceil(fc.forecast_daily_units*fc.lead_time_days+fc.safety_stock_units).astype(int)
    fc['inventory_position']=fc.on_hand_units+fc.on_order_units-fc.reserved_units
    fc['target_stock_units']=np.ceil(fc.forecast_daily_units*(fc.lead_time_days+horizon)+fc.safety_stock_units).astype(int)
    raw=(fc.target_stock_units-fc.inventory_position).clip(lower=0)
    # Round to MOQ and pack multiple; then apply supplier and store capacity.
    pack=fc.pack_size.fillna(1).clip(lower=1); moq=fc.moq_units.fillna(1).clip(lower=1)
    rounded=np.ceil(np.maximum(raw,moq)/pack)*pack
    capacity=np.minimum(fc.supplier_capacity_units.fillna(0),fc.daily_storage_capacity_units.fillna(0)).clip(lower=0)
    feasible_capacity=np.floor(capacity/pack)*pack
    proposed=np.minimum(rounded,feasible_capacity)
    fc['recommended_order_units']=np.where(proposed>=moq,proposed,0).astype(int)
    fc['exception_code']='NONE'
    fc.loc[fc.is_discontinued.astype(bool),'exception_code']='DISCONTINUED_SKU_BLOCKED'
    fc.loc[fc.inventory_position>fc.reorder_point_units,'exception_code']='ABOVE_REORDER_POINT'
    fc.loc[(fc.inventory_position<=fc.reorder_point_units)&(fc.recommended_order_units<raw)&(fc.recommended_order_units>0),'exception_code']='CAPACITY_LIMITED'
    fc.loc[(fc.inventory_position<=fc.reorder_point_units)&(raw>0)&(capacity<=0),'exception_code']='NO_AVAILABLE_CAPACITY'
    fc.loc[fc.is_discontinued.astype(bool),'exception_code']='DISCONTINUED_SKU_BLOCKED'
    fc.loc[fc.is_discontinued.astype(bool),'recommended_order_units']=0
    fc['decision']=np.where(fc.recommended_order_units>0,'REPLENISH','NO_ORDER')
    fc['estimated_order_value']=fc.recommended_order_units*fc.unit_cost
    fc['stockout_risk']=np.where(fc.inventory_position<=fc.reorder_point_units,'HIGH','NORMAL')
    fc.to_csv(out_dir/'forecast_replenishment.csv',index=False)
    ev=pd.DataFrame(eval_rows)
    if not ev.empty:
        # Mean-of-test actual is compared with daily forecast; pair-level aggregation.
        metrics={'evaluated_pairs':int(len(ev)),'MAE':float(np.mean(np.abs(ev.actual_mean-ev.forecast_daily))),
                 'RMSE':float(np.sqrt(np.mean((ev.actual_mean-ev.forecast_daily)**2))),
                 'WAPE_percent':wape(ev.actual_mean.to_numpy(),ev.forecast_daily.to_numpy()),
                 'holdout_days':holdout_days,'cutoff_date':cutoff.date().isoformat()}
    else: metrics={'evaluated_pairs':0,'MAE':None,'RMSE':None,'WAPE_percent':None,'holdout_days':holdout_days}
    (out_dir/'evaluation_metrics.json').write_text(json.dumps(metrics,indent=2))
    summary={'pairs_forecast':len(fc),'replenishment_recommendations':int((fc.recommended_order_units>0).sum()),
             'high_risk_pairs':int((fc.stockout_risk=='HIGH').sum()),'blocked_discontinued':int((fc.exception_code=='DISCONTINUED_SKU_BLOCKED').sum()),
             'estimated_order_value':round(float(fc.estimated_order_value.sum()),2)}
    (out_dir/'run_summary.json').write_text(json.dumps(summary,indent=2))
    return fc,metrics,summary

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--data',default='data/sample'); p.add_argument('--out',default='outputs'); p.add_argument('--horizon',type=int,default=14); p.add_argument('--holdout-days',type=int,default=28)
    a=p.parse_args(); _,m,s=run(Path(a.data),Path(a.out),a.horizon,a.holdout_days); print(json.dumps({'metrics':m,'summary':s},indent=2))

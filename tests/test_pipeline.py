from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd

def test_sample_files_exist():
    data=Path(__file__).resolve().parents[1]/'data/sample'
    for name in ['sku.csv','store.csv','sales_history.csv','inventory_snapshot.csv','supplier.csv','supplier_sku.csv','lead_time_observation.csv','ground_truth.csv','known_issues.csv']:
        assert (data/name).exists(), name

def test_sales_keys_unique_and_stockouts_explicit():
    p=Path(__file__).resolve().parents[1]/'data/sample/sales_history.csv'
    d=pd.read_csv(p)
    assert not d.duplicated(['store_id','sku_id','sale_date']).any()
    assert d.stockout_flag.isin([True,False,0,1]).all()

def test_supplier_constraints_positive():
    p=Path(__file__).resolve().parents[1]/'data/sample/supplier_sku.csv'
    d=pd.read_csv(p)
    assert (d.pack_size>0).all() and (d.moq_units>0).all()

def test_recommendations_obey_pack_and_discontinued_rules():
    root=Path(__file__).resolve().parents[1]
    out=pd.read_csv(root/'outputs/forecast_replenishment.csv')
    assert (out.loc[out.is_discontinued.astype(bool),'recommended_order_units']==0).all()
    positive=out.loc[out.recommended_order_units>0]
    assert ((positive.recommended_order_units % positive.pack_size)==0).all()
    assert (positive.recommended_order_units>=positive.moq_units).all()

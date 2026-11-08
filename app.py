from pathlib import Path
import json, subprocess, sys
import pandas as pd
import streamlit as st

ROOT=Path(__file__).parent; DATA=ROOT/'data/sample'; OUT=ROOT/'outputs'
st.set_page_config(page_title='StockWise | Demand & Replenishment',page_icon='📦',layout='wide')
st.title('📦 StockWise — Demand Forecasting & Smart Replenishment')
st.caption('SKU × Store planning | Explainable forecasts | Constraint-aware purchase recommendations')
if not (OUT/'forecast_replenishment.csv').exists():
    with st.spinner('Running the forecasting and replenishment pipeline...'):
        subprocess.run([sys.executable,str(ROOT/'src/pipeline.py'),'--data',str(DATA),'--out',str(OUT)],check=True)
df=pd.read_csv(OUT/'forecast_replenishment.csv'); metrics=json.loads((OUT/'evaluation_metrics.json').read_text()); summary=json.loads((OUT/'run_summary.json').read_text())
with st.sidebar:
    st.header('Planning controls')
    store_filter=st.selectbox('Store',['All']+sorted(df.store_id.unique().tolist()))
    status=st.selectbox('Decision',['All','REPLENISH','NO_ORDER'])
    risk=st.selectbox('Stockout risk',['All','HIGH','NORMAL'])
    st.divider(); st.caption('Demo data is synthetic and reproducible. Use the CLI to generate full-scale data.')
view=df.copy()
if store_filter!='All': view=view[view.store_id==store_filter]
if status!='All': view=view[view.decision==status]
if risk!='All': view=view[view.stockout_risk==risk]
c1,c2,c3,c4=st.columns(4)
c1.metric('SKU–store pairs',f"{summary['pairs_forecast']:,}"); c2.metric('Order recommendations',f"{summary['replenishment_recommendations']:,}")
c3.metric('High-risk pairs',f"{summary['high_risk_pairs']:,}"); c4.metric('Estimated order value',f"₹{summary['estimated_order_value']:,.0f}")
st.subheader('Forecast & inventory position')
st.dataframe(view[['store_id','sku_id','forecast_daily_units','on_hand_units','on_order_units','reorder_point_units','safety_stock_units','recommended_order_units','decision','exception_code']],use_container_width=True,hide_index=True)
st.download_button('Download filtered recommendations (CSV)',view.to_csv(index=False).encode(),file_name='purchase_recommendations.csv',mime='text/csv')
left,right=st.columns(2)
with left:
    st.subheader('Forecast evaluation — temporal holdout')
    st.metric('MAE',f"{metrics['MAE']:.2f}" if metrics.get('MAE') is not None else 'N/A')
    st.metric('RMSE',f"{metrics['RMSE']:.2f}" if metrics.get('RMSE') is not None else 'N/A')
    st.metric('WAPE',f"{metrics['WAPE_percent']:.1f}%" if metrics.get('WAPE_percent') is not None else 'N/A')
with right:
    st.subheader('Exception breakdown')
    st.bar_chart(view.exception_code.value_counts())
st.info('Stockout-censored days are excluded from demand estimation. Ground-truth demand is stored separately and used only for evaluation. Recommendations are rounded to supplier MOQ/pack size and capped by capacity.')

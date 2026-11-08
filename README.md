
# StockWise – Demand Forecasting & Smart Inventory Replenishment

An end-to-end retail inventory optimization system that forecasts demand at the SKU-store level and recommends smart replenishment quantities by considering supplier lead time, safety stock, minimum order quantity (MOQ), pack size, and storage capacity.

## Business Problem

Retail businesses often face two major challenges:

- **Overstocking:** Excess inventory increases storage and holding costs.
- **Stockouts:** Insufficient inventory results in lost sales and dissatisfied customers.

StockWise solves this problem by forecasting product demand and generating intelligent inventory replenishment recommendations.

## Project Objectives

- Forecast demand for each SKU-store combination.
- Calculate safety stock and reorder points.
- Recommend optimal purchase quantities.
- Consider supplier lead time, MOQ, pack size, and capacity constraints.
- Identify stockouts and unusual inventory conditions.
- Evaluate forecasting performance using meaningful metrics.
- Provide an interactive dashboard for inventory monitoring.

## Key Features

1. **Synthetic Data Generation**
   - 2,000 SKUs
   - 100 Stores
   - 365 Days of sales and inventory history
   - Promotions, seasonality, intermittent demand, and product launches.

2. **Demand Forecasting**
   - SKU-store level demand forecasting.
   - Historical sales analysis.
   - Weekly demand patterns.
   - Temporal holdout evaluation.

3. **Inventory Optimization**
   - Safety stock calculation.
   - Reorder point calculation.
   - Target inventory calculation.
   - Purchase quantity recommendations.

4. **Supplier Management**
   - Supplier lead-time analysis.
   - Minimum Order Quantity (MOQ).
   - Pack-size constraints.
   - Supplier capacity validation.

5. **Exception Handling**
   - Stockout detection.
   - Discontinued SKU protection.
   - Negative lead-time detection.
   - Invalid replenishment quantity detection.
   - Forecast data leakage prevention.

6. **Interactive Dashboard**
   - Demand forecast visualization.
   - Inventory monitoring.
   - Replenishment recommendations.
   - Exception analysis.
   - Forecast evaluation metrics.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core business logic |
| Pandas | Data processing |
| NumPy | Numerical calculations |
| Streamlit | Interactive dashboard |
| SQL | Relational database design |
| Pytest | Automated testing |
| Git & GitHub | Version control |

## Project Architecture

```text
Data Generation
      |
      v
Master Data Creation
(SKU, Store, Supplier)
      |
      v
Sales & Inventory Generation
      |
      v
Data Validation
      |
      v
Demand Forecasting
      |
      v
Safety Stock & Reorder Point
      |
      v
Replenishment Optimization
      |
      v
Supplier & Capacity Constraints
      |
      v
Forecast Evaluation
      |
      v
Interactive Dashboard
```

## Business Logic

### 1. Inventory Position

Inventory Position = On-Hand + On-Order - Reserved

### 2. Safety Stock

Safety Stock = Z × Demand Standard Deviation × √Lead Time

### 3. Reorder Point

Reorder Point = Forecast Daily Demand × Lead Time + Safety Stock

### 4. Target Stock

Target Stock = Forecast Daily Demand × (Lead Time + Review Period) + Safety Stock

### 5. Replenishment Quantity

Reorder Quantity = Maximum(0, Target Stock - Inventory Position)

The final quantity is adjusted according to supplier MOQ, pack size, and capacity constraints.

## Database Entities

The project includes the following core entities:

- SKU
- Store
- SalesHistory
- InventorySnapshot
- Supplier
- SupplierSKU
- LeadTimeObservation
- Forecast
- ReorderPolicy
- PurchaseRecommendation

Primary keys, foreign keys, relationships, and validation rules maintain data integrity.

## Evaluation Metrics

Forecasting performance is evaluated using:

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| WAPE | Weighted Absolute Percentage Error |

A chronological holdout is used to evaluate forecasts without using future information during training.

## Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/StockWise-Demand-Forecasting.git
```

### Step 2: Navigate to Project

```bash
cd StockWise-Demand-Forecasting
```

### Step 3: Create Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Run the Project

### Validate Dataset

```bash
python src/validate.py --data data/sample
```

### Execute Forecasting Pipeline

```bash
python src/pipeline.py --data data/sample --out outputs
```

### Launch Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your browser, usually at:

```text
http://localhost:8501
```

## Generate Full Synthetic Dataset

To generate the full dataset containing 2,000 SKUs, 100 stores, and 365 days:

```bash
python src/generator.py --out data/full --skus 2000 --stores 100 --days 365 --seed 20261022
```

Run the pipeline:

```bash
python src/pipeline.py --data data/full --out outputs_full
```

A fixed random seed ensures reproducibility.

## Testing

Run automated tests:

```bash
pytest -q
```

The project validates:

- Primary key uniqueness.
- Foreign key integrity.
- Valid supplier relationships.
- Allowed values and data types.
- Date ordering.
- Inventory calculations.
- Replenishment constraints.

## Future Enhancements

- Machine Learning-based demand forecasting.
- LSTM-based time-series forecasting.
- Advanced supplier optimization.
- Real-time inventory tracking.
- PostgreSQL integration.
- Automated purchase order generation.
- Cloud deployment using Microsoft Azure.

## Project Outcomes

StockWise demonstrates how data analytics, demand forecasting, and business rules can work together to improve inventory planning.

The solution aims to:

- Reduce stockout risks.
- Minimize excess inventory.
- Improve replenishment decisions.
- Increase supply-chain visibility.
- Support data-driven business decisions.

## Author

**Pratiksha Pankar**

GitHub: [pankarpratiksha50](https://github.com/pankarpratiksha50)

---

**StockWise – Turning Demand Forecasts into Smarter Inventory Decisions.**

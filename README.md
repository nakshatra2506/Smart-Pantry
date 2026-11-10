# SmartPantry — Kitchen Inventory & Demand Forecasting

A standalone full-stack project with a React frontend, FastAPI backend, SQLite database, inventory/expiry/sales/waste workflows, and an ML demand-forecasting pipeline. This is a clean independent implementation; it is not a fork or copy of the earlier Flask prototype.

## Features

- Dashboard with stock value, low-stock alerts, expiry watch and recent sales
- Ingredient CRUD, stock receiving and inventory CSV export
- Batch expiry tracking; sales/waste consume batches using FEFO ordering
- Sales entry automatically reduces stock and stores transaction history
- Food-waste log with estimated ingredient cost
- 7-day demand forecasting for nine demo ingredients
- Trains Random Forest, Extra Trees and HistGradientBoosting regressors per item
- Chronological 80/20 holdout evaluation with MAE, RMSE and R²; selects the lowest-test-MAE model
- Import historical daily sales CSV and retrain
- SQLite persistence; local-only development setup

## Requirements

- Windows 10/11
- Python 3.11 or 3.12 recommended
- Node.js 20 or newer (npm included)

## Run on Windows

1. Extract the entire ZIP.
2. Double-click `run_all.bat`.
3. Wait for the two terminal windows to finish installing dependencies and start.
4. Open **http://127.0.0.1:5173** in your browser.
5. Backend API docs are at **http://127.0.0.1:8000/docs**.

If you prefer separate terminals:

**Terminal 1 — backend**
```powershell
cd backend
.\run_backend.bat
```

**Terminal 2 — frontend**
```powershell
cd frontend
.\run_frontend.bat
```

Do not run `run_all.bat` from inside the backend or frontend folder; run it from the extracted project root.

## ML dataset and honest limitations

`backend/data/demo_sales.csv` is a deterministic synthetic dataset (540 days × 9 kitchen ingredients). It is bundled so the application and training pipeline work offline on first launch. It is **not a public dataset and not real restaurant data**. Its purpose is to demonstrate the end-to-end ML workflow and populate the demo forecast screen.

For your own project evaluation, collect or import historical daily sales from the target kitchen/restaurant. On the Demand Forecast page, use **Import sales CSV**. Required columns are `date,item_name,quantity`, with dates formatted `YYYY-MM-DD`. Item names should match the names in the inventory/training data. After import, the app retrains the models. Keep a separate test period and report metrics honestly; synthetic-data metrics are not evidence of real-world performance.

An optional downloader is included at `backend/download_uci_dataset.py`. It retrieves the UCI Online Retail dataset (CC BY 4.0), but that dataset represents a UK online gift/novelty retailer, **not a kitchen or food business**. It can be used as a generic retail forecasting benchmark, not as proof of kitchen-specific performance. Dataset source and citation:

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33. License: CC BY 4.0. Dataset details: https://archive.ics.uci.edu/dataset/352/online+retail.

To download it (optional):
```powershell
cd backend
.venv\Scripts\activate
pip install ucimlrepo
python download_uci_dataset.py
```

The optional UCI download is not wired into the default app training flow because its products are not kitchen ingredients. Use the app's CSV importer with appropriately prepared records if you want to experiment with it.

## CSV format example

```csv
date,item_name,quantity
2026-01-01,Tomatoes,4.5
2026-01-01,Onions,2.0
2026-01-02,Tomatoes,5.0
```

## Project structure

```text
SmartPantry-Complete/
├── run_all.bat
├── README.md
├── backend/
│   ├── app/                 # FastAPI routes, SQLAlchemy models, ML pipeline
│   ├── data/                # SQLite DB is created here; demo sales CSV bundled
│   ├── requirements.txt
│   ├── run_backend.bat
│   ├── train_model.py
│   └── download_uci_dataset.py
└── frontend/
    ├── src/                 # React UI
    ├── package.json
    ├── index.html
    └── run_frontend.bat
```

## Troubleshooting

- If port 8000 is already in use, stop the other process or change the port in `backend/run_backend.bat` and `frontend/src/main.jsx` (`API` constant).
- If the browser says it cannot reach the API, make sure the backend terminal is still running and visit http://127.0.0.1:8000/api/health.
- If the frontend does not start, use Node.js 20+ and run `npm install` from `frontend`.
- If the Python install fails, use Python 3.11/3.12 and rerun `backend/run_backend.bat`.
- Local data is stored in `backend/smartpantry.db`. Back it up before deleting or resetting the database.

## Security and deployment

This project is configured for local development, not public internet deployment. It does not currently include user authentication, CSRF protection, role-based access, production hosting configuration, or automated backups. Add these before using real business or personal data or deploying publicly.

## Third-party software

Python and JavaScript dependencies are installed from their package managers and retain their own licences. This repository does not relicense those dependencies. Review the package licence notices before redistribution.

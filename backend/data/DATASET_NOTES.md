# Dataset notes

`demo_sales.csv` is a deterministic **synthetic demonstration dataset** generated for this application. It contains 540 daily observations for nine kitchen ingredients covering the 540 days up to the date the package was built. It is included so the forecasting pipeline can run offline immediately. It is not a public dataset and must not be described as real customer or restaurant sales.

For meaningful evaluation, replace/import your own historical daily sales. The CSV importer expects these columns:

- `date` — ISO date (`YYYY-MM-DD`)
- `item_name` — ingredient/product name
- `quantity` — non-negative quantity sold that day

The app compares three regressors using a chronological 80/20 split and selects the lowest test MAE per item. Metrics from synthetic demo data only verify that the pipeline executes; they do not establish real-world accuracy.

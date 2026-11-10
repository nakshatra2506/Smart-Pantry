from app.ml import train_all
if __name__ == '__main__':
    result = train_all()
    for item, metrics in result.items():
        print(f"{item}: {metrics['model']} | MAE={metrics['mae']:.3f} | RMSE={metrics['rmse']:.3f} | R2={metrics['r2']:.3f}")

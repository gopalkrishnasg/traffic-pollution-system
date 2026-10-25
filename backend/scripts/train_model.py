import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.dataset_loader import load_active_dataset
from app.ml.trainer import train_random_forest_model


def main():
    df, meta = load_active_dataset()
    print(
        f"[INFO] Loaded dataset '{meta['dataset_name']}' "
        f"(rows={meta['row_count']}, is_synthetic={meta['is_synthetic']})"
    )
    artifact = train_random_forest_model(
        df=df, is_synthetic=meta["is_synthetic"], dataset_name=meta["dataset_name"]
    )
    print(f"[SUCCESS] Trained model version: {artifact['model_version']}")
    print(f"[METRICS] MAE={artifact['metrics']['mae']} | RMSE={artifact['metrics']['rmse']} | R2={artifact['metrics']['r2']}")


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.dataset_loader import generate_synthetic_bengaluru_dataset
from app.config import settings


def main():
    output_file = generate_synthetic_bengaluru_dataset(
        output_path=settings.SYNTHETIC_CSV_PATH, num_days=18, seed=42
    )
    print(f"[SUCCESS] Generated synthetic Bengaluru dataset at: {output_file}")


if __name__ == "__main__":
    main()

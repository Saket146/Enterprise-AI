import json
from pathlib import Path
import pandas as pd


def save_csv(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(path, index=False)


def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, default=str)
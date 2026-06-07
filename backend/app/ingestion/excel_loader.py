from pathlib import Path
from typing import Optional

import pandas as pd


def load_excel_if_exists(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_excel(path)


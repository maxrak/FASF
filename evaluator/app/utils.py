import pandas as pd
import os


def load_csv_safe(path):
    try:
        df = pd.read_csv(path)
        if len(df) == 0:
            return None
        return df
    except:
        return None


def get_generated_files(directory):
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".csv") and "target" not in f
    ]
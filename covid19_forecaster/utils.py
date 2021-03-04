import hashlib
import json

import numpy as np
import pandas as pd


def aggregate_to_quarters(df, cols=None, key=None):
    """Aggregate monthly data to quarters."""
    grouped = df.groupby(pd.Grouper(freq="QS", key=key))
    if cols is not None:
        out = grouped[cols].sum()
    else:
        out = grouped.sum()

    # Set quarters w/o three to missing
    size = grouped.size()
    missing = size != 3
    out.loc[missing, :] = np.nan

    return out.dropna(axis=0, how="all")


def get_unique_id(d, n=5):
    """Generate a unique hash string from a dictionary."""

    unique_id = hashlib.sha1(
        json.dumps(d, sort_keys=True).encode()
    ).hexdigest()

    return unique_id[:n]


def get_fiscal_year(dt):
    """Get fiscal year from a date."""
    if dt.month >= 7:
        return dt.year + 1
    else:
        return dt.year

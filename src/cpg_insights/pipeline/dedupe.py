"""
Dedupe stage — removes duplicate transaction IDs.

In a real CPG environment, POS systems retry failed writes and at-least-once
delivery semantics mean the same transaction can appear multiple times.
We keep the first occurrence and drop the rest.
"""

import pandas as pd


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Returns (deduped_df, n_duplicates_removed)."""
    before = len(df)
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    return df, before - len(df)

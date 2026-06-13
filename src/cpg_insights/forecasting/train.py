"""
CLI entry point for Phase 3 — train forecasting model and detect anomalies.

Usage:
    python -m cpg_insights.forecasting.train
    make train
"""

from cpg_insights.config import settings
from cpg_insights.db.connection import get_connection
from cpg_insights.forecasting.anomaly import detect_anomalies
from cpg_insights.forecasting.model import train


def main() -> None:
    print("=== Phase 3 — Forecasting ===")
    conn = get_connection()

    print("\nStep 1/2 — Training Ridge regression model …")
    metrics = train(conn, holdout_months=4, model_path=settings.model_path_abs)
    print(f"  MAE  : {metrics['mae']:,.2f}")
    print(f"  MAPE : {metrics['mape']:.1f}%")
    print(f"  Train: {metrics['n_train']} group-months  |  "
          f"Holdout: {metrics['n_test']} group-months")
    print(f"  Model saved → {settings.model_path_abs}")

    print("\nStep 2/2 — Detecting revenue anomalies (z-score ≥ 2.0) …")
    flagged = detect_anomalies(conn, z_threshold=2.0)
    if flagged.empty:
        print("  No anomalies detected.")
    else:
        print(f"  {len(flagged)} anomalies found and written to anomalies table:")
        for _, row in flagged.iterrows():
            print(f"    [{row['severity'].upper()}] {row['description']}")

    conn.close()
    print("\nTraining complete.")


if __name__ == "__main__":
    main()

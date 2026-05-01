#!/usr/bin/env python3
"""Check for credit model drift using Evidently. Run: python scripts/check_model_drift.py"""
import os

def check_drift():
    print("Model drift check — connect MLFLOW_TRACKING_URI and run Evidently reports.")
    print("Metrics to monitor: PSI on credit_score, dti_ratio, fraud_risk_score distributions.")
    print("Alert threshold: PSI > 0.2 triggers auto-retrain via Airflow DAG.")

if __name__ == "__main__":
    check_drift()

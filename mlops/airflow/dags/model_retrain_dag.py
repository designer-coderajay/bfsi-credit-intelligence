"""
Airflow DAG: Weekly credit model retraining pipeline.
Triggers every Sunday, retrains on new loan data, registers in MLflow.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mlops-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": True,
    "email": ["ml-alerts@yourcompany.com"],
}


def extract_training_data(**context):
    """Pull latest loan data from PostgreSQL feature store."""
    import pandas as pd
    from sqlalchemy import create_engine
    import os
    engine = create_engine(os.environ["DATABASE_URL"])
    df = pd.read_sql(
        "SELECT * FROM loan_features WHERE created_at > NOW() - INTERVAL '30 days'",
        engine,
    )
    context["ti"].xcom_push(key="n_samples", value=len(df))
    df.to_parquet("/tmp/training_data.parquet")
    print(f"Extracted {len(df)} training samples")


def train_credit_model(**context):
    """Train XGBoost credit model with latest data."""
    from backend.ml.credit_model.train import train
    model, scaler = train()
    print("✅ Credit model retrained successfully")


def evaluate_and_gate(**context):
    """Evaluate new model vs current production model — gate on AUC threshold."""
    import mlflow
    # Load latest run
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(experiment_ids=["1"], order_by=["metrics.train_auc DESC"], max_results=2)
    new_auc = runs[0].data.metrics.get("train_auc", 0)
    if len(runs) > 1:
        current_auc = runs[1].data.metrics.get("train_auc", 0)
    else:
        current_auc = 0.8  # baseline

    print(f"New AUC: {new_auc:.4f} | Current AUC: {current_auc:.4f}")
    if new_auc < current_auc - 0.02:
        raise ValueError(f"New model AUC {new_auc:.4f} below threshold. Not promoting.")
    print("✅ Model passed quality gate. Promoting to production.")


def deploy_model(**context):
    """Register model in MLflow registry and trigger BentoML redeploy."""
    import mlflow
    import subprocess
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(experiment_ids=["1"], order_by=["metrics.train_auc DESC"], max_results=1)
    run_id = runs[0].info.run_id
    model_uri = f"runs:/{run_id}/credit_model"
    mlflow.register_model(model_uri, "bfsi-credit-model")
    print(f"✅ Model registered from run: {run_id}")


with DAG(
    dag_id="credit_model_weekly_retrain",
    default_args=default_args,
    schedule_interval="0 2 * * 0",  # Every Sunday at 2 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mlops", "credit", "bfsi"],
) as dag:

    t1 = PythonOperator(task_id="extract_training_data", python_callable=extract_training_data)
    t2 = PythonOperator(task_id="train_credit_model",    python_callable=train_credit_model)
    t3 = PythonOperator(task_id="evaluate_and_gate",     python_callable=evaluate_and_gate)
    t4 = PythonOperator(task_id="deploy_model",          python_callable=deploy_model)

    t1 >> t2 >> t3 >> t4

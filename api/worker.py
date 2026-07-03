# api/worker.py
import os
from celery import Celery
from core.era_loop import run_experiment, run_dataset_experiment

celery_app = Celery(
    "era_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@celery_app.task(name="run_dsa_task", soft_time_limit=1200)
def run_dsa_task(problem: str, function_name: str):
    try:
        exp_id = run_experiment(problem, function_name)
        return {"status": "SUCCESS", "experiment_id": exp_id}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

@celery_app.task(name="run_ml_task", soft_time_limit=1200)
def run_ml_task(problem: str, metric: str, data_path: str, dataset_preview: str, db_problem: str, iterations: int = 5):
    try:
        exp_id = run_dataset_experiment(problem, metric, data_path, dataset_preview, db_problem, iterations)
        return {"status": "SUCCESS", "experiment_id": exp_id}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
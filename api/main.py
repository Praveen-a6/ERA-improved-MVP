# api/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Any
from db.storage import (init_db, get_experiment_history, get_best_node, get_experiment_tree, 
                        get_all_experiments, get_node_details, get_experiment_details, delete_experiment, 
                        update_experiment_status)
from api.worker import celery_app
import shutil
import os
import pandas as pd
import io

app = FastAPI(title="ERA-Lite API")

@app.on_event("startup")
def startup():
    init_db()
    os.makedirs("/app/datasets", exist_ok=True)
    os.makedirs("/app/experiments", exist_ok=True)

class ExperimentRequest(BaseModel):
    problem: str
    function_name: str

@app.post("/api/run")
def run_experiment_endpoint(req: ExperimentRequest):
    task = celery_app.send_task(
        "run_dsa_task",
        kwargs={"problem": req.problem, "function_name": req.function_name}
    )
    return {"status": "queued", "task_id": task.id, "message": "Experiment is queued in Celery."}

@app.post("/api/run_dataset")
def run_dataset_endpoint(
    problem: str = Form(...),
    metric: str = Form(...),
    iterations: int = Form(5), # Accept iterations
    file: UploadFile = File(...)
):
    container_file_path = f"/app/datasets/{file.filename}"
    with open(container_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    preview_str = ""
    try:
        df = pd.read_csv(container_file_path)
        preview_str = df.head(5).to_string(index=False)
        
        buffer = io.StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        null_counts = df.isnull().sum().to_string()
        
        enhanced_problem = f"{problem}\n\nDataset Preview (First 5 rows):\n{preview_str}\n\nDataset Info:\n{info_str}\n\nMissing Values Per Column:\n{null_counts}"
    except Exception:
        enhanced_problem = problem

    host_dir = os.getenv("HOST_PROJECT_DIR", os.getcwd())
    host_file_path = os.path.join(host_dir, "datasets", file.filename).replace("\\", "/")

    task = celery_app.send_task(
        "run_ml_task",
        kwargs={
            "problem": enhanced_problem, 
            "metric": metric, 
            "data_path": host_file_path, 
            "dataset_preview": preview_str,
            "db_problem": problem,
            "iterations": iterations
        }
    )
    return {"status": "queued", "task_id": task.id, "message": "Dataset experiment is queued in Celery."}

@app.get("/api/experiments")
def list_experiments():
    return {"experiments": get_all_experiments()}

@app.get("/api/experiments/{experiment_id}")
def get_experiment_status(experiment_id: int):
    history = get_experiment_history(experiment_id)
    details = get_experiment_details(experiment_id)
    if not details:
        raise HTTPException(status_code=404, detail="Experiment not found")
    best_node = get_best_node(experiment_id)
    return {
        "experiment_id": experiment_id,
        "details": details,
        "iterations": len(history),
        "best_score": best_node["score"] if best_node else 0.0,
        "best_code": best_node["code"] if best_node else "",
        "history": history
    }

@app.get("/api/tree/{experiment_id}")
def get_tree(experiment_id: int):
    tree = get_experiment_tree(experiment_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"nodes": tree}

@app.get("/api/node/{node_id}")
def get_node_details_endpoint(node_id: int):
    node = get_node_details(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

@app.delete("/api/experiments/{experiment_id}")
def delete_experiment_endpoint(experiment_id: int):
    delete_experiment(experiment_id)
    return {"status": "deleted"}

@app.post("/api/stop/{experiment_id}")
def stop_experiment_endpoint(experiment_id: int):
    update_experiment_status(experiment_id, "STOPPED")
    return {"status": "stopped", "message": "Experiment will stop after current iteration."}
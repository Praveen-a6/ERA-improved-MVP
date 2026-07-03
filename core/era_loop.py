# core/era_loop.py
from dotenv import load_dotenv
from db.storage import init_db, create_experiment, retrieve_memory, update_experiment_status
from core.memory_agent import extract_tags, format_memory_context
from core.rag_agent import build_research_context
from core.agents import DSAManagerAgent, DatasetManagerAgent
import os

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "z-ai/glm-5.1")
RESEARCH_TAGS = {"dynamic_programming", "graph", "backtracking", "binary_search", "monotonic_stack", "prefix_sum", "tree"}

def should_run_rag(tags: list[str]) -> bool:
    return any(tag in RESEARCH_TAGS for tag in tags)

def run_experiment(problem: str, function_name: str):
    init_db()
    exp_id = create_experiment(problem, MODEL, metric="PASS/FAIL")
    try:
        problem_tags = extract_tags(problem)
        past_memories = retrieve_memory(problem_tags, limit=2)
        memory_context = format_memory_context(past_memories)
        research_context = build_research_context(problem, problem_tags) if should_run_rag(problem_tags) else ""
        base_context = "\n\n".join(filter(None, [memory_context, research_context]))
        
        manager = DSAManagerAgent(exp_id, problem, function_name, problem_tags, base_context)
        manager.run()
        update_experiment_status(exp_id, "COMPLETED")

    except Exception as e:
        print(f"Experiment failed: {e}")
        update_experiment_status(exp_id, "FAILED")
        
    return exp_id

def run_dataset_experiment(problem: str, metric: str, data_path: str, dataset_preview: str, db_problem: str = None, iterations: int = 5):
    init_db()
    filename = os.path.basename(data_path)
    actual_db_problem = db_problem if db_problem else problem
    
    actual_metric = metric
    db_metric = metric
    if "Auto-Detect" in metric:
        db_metric = "Auto-Detect"
        actual_metric = "the most appropriate metric for this task (e.g., accuracy for classification, r2_score for regression)"
    
    exp_id = create_experiment(actual_db_problem, MODEL, metric=db_metric, dataset_filename=filename, dataset_preview=dataset_preview)
    try:
        problem_tags = ["machine_learning", "tabular_data"]
        past_memories = retrieve_memory(problem_tags, limit=2)
        memory_context = format_memory_context(past_memories)
        base_context = memory_context if memory_context else ""
    
        manager = DatasetManagerAgent(exp_id, problem, actual_metric, data_path, problem_tags, base_context, iterations=iterations)
        manager.run()
        update_experiment_status(exp_id, "COMPLETED")
    
    except Exception as e:
        print(f"Experiment failed: {e}")
        update_experiment_status(exp_id, "FAILED")
    return exp_id
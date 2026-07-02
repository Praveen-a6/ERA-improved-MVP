import os
import subprocess
import uuid
from core.llm_utils import llm_call, MODEL
from core.critic import critique
from db.storage import save_node, save_memory, get_experiment_status
from core.memory_agent import summarize_problem

class GeneratorAgent:
    def generate_dsa(self, problem: str, func_name: str, test_runner: str, context: str) -> str:
        prompt = f"""You are an expert Python engineer.
Problem:
{problem}

Requirements:
- Write a function named exactly: {func_name}
- Do NOT use any imports unless absolutely necessary.
- Do NOT print anything inside the function.
- Do NOT add test code.

{f"Context/Feedback: {context}" if context else ""}

Return ONLY raw Python code. No markdown."""
        response = llm_call(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2048)
        raw_code = response.choices[0].message.content.strip()
        if raw_code.startswith("```"):
            lines = raw_code.splitlines()
            raw_code = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        return raw_code + "\n" + test_runner

    def mutate_dsa(self, code: str, score: float, feedback: str, func_name: str, test_runner: str, context: str) -> str:
        prompt = f"""You are reviewing a solution that scored {score:.2f}.
{f"Context: {context}" if context else ""}

Current code:
{code.split('# ── TEST RUNNER')[0].strip()}

Failures/Metrics:
{feedback}

Rewrite ONLY the {func_name} function to fix errors and improve the score.
Return ONLY raw Python code. No markdown."""
        response = llm_call(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=2048)
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        try:
            compile(raw, "<mutant>", "exec")
            return raw + "\n" + test_runner
        except SyntaxError:
            return code

    def generate_ml_pipeline(self, problem: str, metric: str, context: str) -> str:
        prompt = f"""You are an expert ML/Data Science engineer.
Task: {problem}
Evaluation Metric to MAXIMIZE: {metric}

Requirements:
- Write a COMPLETE, standalone Python script.
- The script MUST read the dataset from '/app/data.csv' using pandas.
- The script MUST train a model and evaluate it.
- CRITICAL: Wrap your entire script in a try/except block. If any error occurs, print exactly "SCORE: 0.0" and then print the error message.
- The script MUST print the final score EXACTLY in this format: print(f"SCORE: {{score}}")
- You may use numpy, pandas, scikit-learn, xgboost, lightgbm, scipy, and statsmodels.
- Do NOT write any functions. Just write the script top-to-bottom.

{f"Context/Feedback from previous attempt: {context}" if context else ""}

Return ONLY raw Python code. No markdown. No explanations."""
        response = llm_call(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2048)
        raw_code = response.choices[0].message.content.strip()
        if raw_code.startswith("```"):
            lines = raw_code.splitlines()
            raw_code = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        return raw_code

    def mutate_ml_pipeline(self, code: str, score: float, feedback: str, metric: str, context: str) -> str:
        prompt = f"""You are reviewing an ML pipeline that achieved a {metric} score of {score:.4f}.
{f"Context: {context}" if context else ""}

Current code:
{code}

Execution Feedback/Errors:
{feedback}

Your job:
- Identify why the score is low or why it failed.
- Rewrite the script to improve the {metric}. Try feature engineering, hyperparameter tuning, or a different model.
- CRITICAL: Wrap your entire script in a try/except block. If any error occurs, print exactly "SCORE: 0.0" and then print the error message.
- The script MUST still read from '/app/data.csv' and print exactly `print(f"SCORE: {{score}}")`.

Return ONLY raw Python code. No markdown."""
        response = llm_call(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=2048)
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        try:
            compile(raw, "<mutant>", "exec")
            return raw
        except SyntaxError:
            return code


class ExecutorAgent:
    def execute(self, code: str, data_path: str = None) -> tuple[str, str, int]:
        container_exp_dir = "/app/experiments"
        os.makedirs(container_exp_dir, exist_ok=True)
        
        filename = f"cand_{uuid.uuid4().hex}.py"
        container_fpath = os.path.join(container_exp_dir, filename)
        
        with open(container_fpath, "w", encoding="utf-8") as f:
            f.write(code)
            
        host_dir = os.getenv("HOST_PROJECT_DIR", os.getcwd())
        host_fpath = os.path.join(host_dir, "experiments", filename).replace("\\", "/")
        
        try:
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "1g",       
                "--cpus", "2.0",        
                "-v", f"{host_fpath}:/app/candidate.py"
            ]
            
            if data_path:
                docker_cmd.append("-v")
                docker_cmd.append(f"{data_path}:/app/data.csv")
                
            docker_cmd.append("era-sandbox")
            
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=120)
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "TIMEOUT", 1

    def evaluate_dsa(self, stdout: str) -> tuple[float, str]:
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        results = [l for l in lines if l in ("PASS", "FAIL")]
        if not results:
            return 0.0, "No valid output or SCORE found"
        score = round(results.count("PASS") / len(results), 2)
        failures = "\n".join([l for l in lines if l.startswith("FAIL")])
        return score, failures

    def evaluate_ml(self, stdout: str) -> tuple[float, str]:
        lines = [l.strip() for l in stdout.splitlines() if l.strip()]
        for line in lines:
            if line.startswith("SCORE:"):
                try:
                    score = float(line.split(":")[1].strip())
                    # Capture any error messages printed after the score
                    error_lines = [l for l in lines if l.startswith("Error:") or l.startswith("Traceback")]
                    feedback = "ML Metric captured" if score > 0 else "\n".join(error_lines) if error_lines else "Score is 0.0"
                    return score, feedback
                except ValueError:
                    pass
        return 0.0, "No SCORE found in output.\n" + "\n".join(lines[-5:])
    
class CriticAgent:
    def review(self, problem: str, code: str, stdout: str, score: float) -> dict:
        if score < 0.9:
            return {"verdict": "SKIP", "reason": "Score too low to review", "penalised_score": score}
        result = critique(problem, code, stdout)
        return result

class DSAManagerAgent:
    def __init__(self, exp_id: int, problem: str, func_name: str, tags: list[str], base_context: str, test_runner: str, iterations=5, beam_width=3):
        self.exp_id = exp_id
        self.problem = problem
        self.func_name = func_name
        self.tags = tags
        self.base_context = base_context
        self.test_runner = test_runner
        self.iterations = iterations
        self.beam_width = beam_width
        self.node_pool = []
        self.top_nodes = []
        
        self.generator = GeneratorAgent()
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()

    def run(self):
        for i in range(1, self.iterations + 1):
            current_status = get_experiment_status(self.exp_id)
            if current_status == "STOPPED":
                print("\n  Experiment cancelled by user. Stopping search.")
                break
                
            print(f"\n[Iteration {i}/{self.iterations}]")
            candidates = []
            
            if not self.node_pool:
                for _ in range(self.beam_width):
                    code = self.generator.generate_dsa(self.problem, self.func_name, self.test_runner, self.base_context)
                    candidates.append(("generate", code, "Initial generation based on problem description."))
            else:
                self.node_pool.sort(key=lambda x: x[0], reverse=True)
                self.top_nodes = self.node_pool[:self.beam_width]
                for idx, (prev_score, prev_code, prev_node_id, prev_feedback) in enumerate(self.top_nodes):
                    if idx == 0:
                        feedback = f"Previous best score: {prev_score:.2f}. Try a completely different algorithm."
                        full_context = f"{self.base_context}\n\n{feedback}" if self.base_context else feedback
                        code = self.generator.generate_dsa(self.problem, self.func_name, self.test_runner, full_context)
                        candidates.append(("generate", code, f"Exploring new branch. Reason: {feedback}"))
                    else:
                        code = self.generator.mutate_dsa(prev_code, prev_score, prev_feedback, self.func_name, self.test_runner, self.base_context)
                        candidates.append(("mutate", code, f"Mutating Node {prev_node_id}. Reason: {prev_feedback.splitlines()[0]}"))

            for idx, (source, code, reasoning) in enumerate(candidates):
                stdout, stderr, exit_code = self.executor.execute(code)
                score, feedback = self.executor.evaluate_dsa(stdout) if exit_code == 0 else (0.0, stderr)
                
                parent_id = self.top_nodes[idx][2] if idx < len(self.top_nodes) else None
                node_id = save_node(self.exp_id, i, code, score, stdout, stderr, exit_code, parent_id, reasoning)

                critic_result = self.critic.review(self.problem, code, stdout, score)
                if critic_result["verdict"] == "FAIL":
                    score = critic_result["penalised_score"]
                    feedback += f"\nCritic: {critic_result['reason']}"
                elif critic_result["verdict"] == "PASS" and score >= 0.99:
                    summary = summarize_problem(self.problem)
                    save_memory(self.exp_id, node_id, summary, ",".join(self.tags), code.split("# ── TEST RUNNER")[0].strip(), score)

                status = "✓" if exit_code == 0 else "✗"
                feedback_line = feedback.splitlines()[0] if feedback.strip() else "No feedback"
                print(f"  [{source}] Node {node_id}: {status} Score={score:.2f} | {feedback_line}")
                self.node_pool.append((score, code, node_id, feedback))

            self.node_pool.sort(key=lambda x: x[0], reverse=True)
            best_score = self.node_pool[0][0]
            print(f"  ★ Best in pool: {best_score:.2f} (Total nodes: {len(self.node_pool)})")

            if best_score >= 0.99:
                print("\n  ✓ Perfect score reached. Stopping early.")
                break


class DatasetManagerAgent:
    def __init__(self, exp_id: int, problem: str, metric: str, data_path: str, tags: list[str], base_context: str, iterations=5, beam_width=3):
        self.exp_id = exp_id
        self.problem = problem
        self.metric = metric
        self.data_path = data_path
        self.tags = tags
        self.base_context = base_context
        self.iterations = iterations
        self.beam_width = beam_width
        self.node_pool = []
        self.top_nodes = []
        
        self.generator = GeneratorAgent()
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()

    def run(self):
        for i in range(1, self.iterations + 1):
            current_status = get_experiment_status(self.exp_id)
            if current_status == "STOPPED":
                print("\n  Experiment cancelled by user. Stopping search.")
                break
                
            print(f"\n[Iteration {i}/{self.iterations}]")
            print(f"\n[Iteration {i}/{self.iterations}]")
            candidates = []
            
            if not self.node_pool:
                for _ in range(self.beam_width):
                    code = self.generator.generate_ml_pipeline(self.problem, self.metric, self.base_context)
                    candidates.append(("generate", code, "Initial ML pipeline generation based on problem and data preview."))
            else:
                self.node_pool.sort(key=lambda x: x[0], reverse=True)
                self.top_nodes = self.node_pool[:self.beam_width]
                for idx, (prev_score, prev_code, prev_node_id, prev_feedback) in enumerate(self.top_nodes):
                    if idx == 0:
                        feedback = f"Previous best score: {prev_score:.4f}. Try a completely different model approach."
                        full_context = f"{self.base_context}\n\n{feedback}" if self.base_context else feedback
                        code = self.generator.generate_ml_pipeline(self.problem, self.metric, full_context)
                        candidates.append(("generate", code, f"Exploring new model. Reason: {feedback}"))
                    else:
                        code = self.generator.mutate_ml_pipeline(prev_code, prev_score, prev_feedback, self.metric, self.base_context)
                        candidates.append(("mutate", code, f"Mutating Node {prev_node_id}. Reason: {prev_feedback.splitlines()[0]}"))

            for idx, (source, code, reasoning) in enumerate(candidates):
                stdout, stderr, exit_code = self.executor.execute(code, self.data_path)
                score, feedback = self.executor.evaluate_ml(stdout) if exit_code == 0 else (0.0, stderr[-500:])
                
                parent_id = self.top_nodes[idx][2] if idx < len(self.top_nodes) else None
                node_id = save_node(self.exp_id, i, code, score, stdout, stderr, exit_code, parent_id, reasoning)

                critic_result = self.critic.review(self.problem, code, stdout, score)
                if critic_result["verdict"] == "FAIL":
                    score = critic_result["penalised_score"]
                    feedback += f"\nCritic: {critic_result['reason']}"
                elif critic_result["verdict"] == "PASS" and score >= 0.85:
                    summary = summarize_problem(self.problem)
                    save_memory(self.exp_id, node_id, summary, ",".join(self.tags), code, score)

                status = "✓" if exit_code == 0 else "✗"
                feedback_line = feedback.splitlines()[0] if feedback.strip() else "No feedback"
                print(f"  [{source}] Node {node_id}: {status} Score={score:.4f} | {feedback_line}")
                self.node_pool.append((score, code, node_id, feedback))

            self.node_pool.sort(key=lambda x: x[0], reverse=True)
            best_score = self.node_pool[0][0]
            print(f"  ★ Best in pool: {best_score:.4f} (Total nodes: {len(self.node_pool)})")

            if best_score >= 0.999:
                print("\n  ✓ Perfect score reached. Stopping early.")
                break
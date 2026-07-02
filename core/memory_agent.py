from core.llm_utils import llm_call, MODEL

def extract_tags(problem: str) -> list[str]:
    """
    Ask the LLM to identify algorithm/data-structure tags for a problem.
    Returns a list like ["sliding_window", "hashmap", "two_pointer"]
    """
    prompt = f"""You are an algorithm classifier.

Given this problem description, identify the 1 to 3 MOST relevant algorithm or data-structure tags.

Problem:
{problem}

Rules:
- Return only the strongest, most essential tags
- Do NOT include broad or weak tags unless absolutely necessary
- Prefer concrete algorithm/data-structure tags over generic categories
- For simple hashmap counting problems, return hashmap, array, string, etc. only if truly central
- Avoid noisy tags like math unless the problem genuinely requires mathematics

Choose from:
sliding_window, two_pointer, dynamic_programming, binary_search,
hashmap, stack, queue, recursion, greedy, sorting, graph, tree, math, string,
array, linked_list, backtracking, prefix_sum, monotonic_stack

Return ONLY a comma-separated list of 1 to 3 lowercase tags with underscores.
Nothing else."""

    response = llm_call(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=64,
        stream=False
    )
    
    raw = response.choices[0].message.content.strip()
    tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return tags[:3]  # cap at 3 tags


def summarize_problem(problem: str) -> str:
    """
    Create a short 1-sentence summary of the problem for memory storage.
    """
    prompt = f"""Summarize this problem in one sentence (max 20 words):

{problem}

Return ONLY the summary sentence."""

    response = llm_call(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=64,
        stream=False
    )
    
    return response.choices[0].message.content.strip()


def format_memory_context(memories: list[dict]) -> str:
    """
    Format retrieved memories into a prompt-injectable string.
    """
    if not memories:
        return ""

    lines = ["Relevant patterns from past successful experiments:"]
    for i, mem in enumerate(memories, 1):
        lines.append(f"\n[Pattern {i}]")
        lines.append(f"Problem type: {mem['problem_summary']}")
        lines.append(f"Tags: {mem['algorithm_tags']}")
        lines.append(f"Winning approach:")
        lines.append(mem['code_snippet'])
        lines.append(f"Score achieved: {mem['score']:.0%}")

    return "\n".join(lines)
from core.llm_utils import llm_call, MODEL


CRITIC_PROMPT = """You are a senior code reviewer and adversarial tester.

A solution has been generated for the following problem:

PROBLEM:
{problem}

SOLUTION CODE:
{code}

TEST RESULTS:
{test_results}

Your job is to detect if this solution is:
1. Hardcoded — returns answers that only work for the exact test cases given
2. Cheating — imports test data or reads from external sources
3. Logically flawed — happens to pass tests but breaks on unseen inputs
4. Genuinely correct — implements the algorithm properly for ALL inputs

Respond in this EXACT format:
VERDICT: PASS or FAIL
REASON: one sentence explanation
CONFIDENCE: HIGH, MEDIUM, or LOW

Examples of FAIL verdicts:
- Solution hardcodes return values matching test inputs
- Solution uses a lookup table of known answers
- Solution passes tests but has off-by-one errors on boundary conditions
- Solution works only for the specific input sizes in the tests

Examples of PASS verdicts:
- Solution implements a correct general algorithm (sliding window, DP, hash map, etc.)
- Solution handles edge cases (empty input, single element, all same values)
- Logic is sound and would work on inputs not in the test suite
"""

def critique(problem: str, code: str, stdout: str) -> dict:
    """
    Returns:
        {
            "verdict": "PASS" or "FAIL",
            "reason": str,
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "penalised_score": float  (1.0 if PASS, 0.7 if FAIL)
        }
    """
    prompt = CRITIC_PROMPT.format(
        problem=problem,
        code=code,
        test_results=stdout.strip()
    )

    response = llm_call(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,    # low temp — critic must be consistent
        max_tokens=256,
        stream=False
    )
    
    raw = response.choices[0].message.content.strip()

    # Parse structured response
    verdict = "PASS"
    reason = "No reason provided"
    confidence = "LOW"

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("VERDICT:"):
            verdict = "PASS" if "PASS" in line else "FAIL"
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()
        elif line.startswith("CONFIDENCE:"):
            conf = line.replace("CONFIDENCE:", "").strip().upper()
            if conf in ("HIGH", "MEDIUM", "LOW"):
                confidence = conf

    # Penalise score if critic flags the solution
    penalised_score = 1.0 if verdict == "PASS" else 0.7

    return {
        "verdict": verdict,
        "reason": reason,
        "confidence": confidence,
        "penalised_score": penalised_score,
        "raw_response": raw
    }
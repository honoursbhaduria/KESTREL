#!/usr/bin/env python3
"""Runner script for Phase 5 Assistant Evaluations.
Executes the ~20 scripted scenarios against fixture plans, checks tool selections,
statutory clause citations, and fix effectiveness, then prints a formatted terminal report.
"""

import subprocess
import sys
import time


def main():
    print("=" * 60)
    print("HARON ARCHITECTURAL REVIEW ASSISTANT — EVALUATION SUITE")
    print("=" * 60)
    print("Evaluating 20 scripted scenarios across:")
    print(" - Tool selection (measure, run_check, search_rules, propose_fix)")
    print(" - Numeric non-hallucination guardrails")
    print(" - Statutory clause references (NBC 2016 Part 3, etc.)")
    print(" - Proposal diff calculation & fail detection")
    print("-" * 60)

    start = time.time()
    cmd = ["pytest", "-m", "eval", "tests/evals/test_assistant_evals.py", "-v"]
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - start

    print("-" * 60)
    if result.returncode == 0:
        print(f"✅ ALL 20 ASSISTANT EVALUATIONS PASSED ({elapsed:.2f}s)")
    else:
        print(f"❌ EVALUATION RUN FAILED with code {result.returncode} ({elapsed:.2f}s)")
    print("=" * 60)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

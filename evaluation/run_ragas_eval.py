"""
Automated RAGAS evaluation — the LLMOps quality gate.
Run in CI; exits with code 1 if any metric drops below threshold.

Usage:
    python -m evaluation.run_ragas_eval
    python -m evaluation.run_ragas_eval --dataset evaluation/eval_dataset.json
"""
import json
import sys
import argparse
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from src.rag.graph import rag_app

THRESHOLDS = {
    "faithfulness":       0.80,
    "answer_relevancy":   0.80,
    "context_precision":  0.70,
}


def run(dataset_path: str = "evaluation/eval_dataset.json"):
    with open(dataset_path) as f:
        cases = json.load(f)

    rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    for c in cases:
        print(f"  Evaluating: {c['question'][:60]}...")
        state = rag_app.invoke(
            {"question": c["question"], "documents": [], "generation": "", "retries": 0}
        )
        rows["question"].append(c["question"])
        rows["answer"].append(state["generation"])
        rows["contexts"].append(state["documents"])
        rows["ground_truth"].append(c["ground_truth"])

    ds     = Dataset.from_dict(rows)
    result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
    print("\nRAGAS results:")
    print(result)

    failed = [
        f"{metric}={result[metric]:.3f} < threshold {threshold}"
        for metric, threshold in THRESHOLDS.items()
        if result[metric] < threshold
    ]

    if failed:
        print("\n❌ Evaluation gate FAILED:")
        for f in failed:
            print(f"   {f}")
        sys.exit(1)

    print("\n✅ Evaluation gate PASSED — all metrics above thresholds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/eval_dataset.json")
    args = parser.parse_args()
    run(args.dataset)

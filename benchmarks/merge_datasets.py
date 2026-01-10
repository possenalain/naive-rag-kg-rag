"""
Merge benchmark datasets into single file for RAG evaluation.
"""
import json
from pathlib import Path

def load_dataset(filepath):
    """Load a JSON dataset file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_datasets():
    """Merge all benchmark datasets into a single file."""
    datasets_dir = Path("benchmarks/datasets")
    
    # Load all datasets
    factual = load_dataset(datasets_dir / "factual_questions.json")
    multihop_part1 = load_dataset(datasets_dir / "multihop_part1.json")
    multihop_part2 = load_dataset(datasets_dir / "multihop_part2.json")
    multihop_part3 = load_dataset(datasets_dir / "multihop_part3.json")
    multihop_questions_part1 = load_dataset(datasets_dir / "multihop_questions_part1.json")
    analytical = load_dataset(datasets_dir / "analytical_questions.json")
    
    # Combine all questions
    all_questions = []
    all_questions.extend(factual["questions"])
    all_questions.extend(multihop_part1["questions"])
    all_questions.extend(multihop_part2["questions"])
    all_questions.extend(multihop_part3["questions"])
    all_questions.extend(multihop_questions_part1["questions"])
    all_questions.extend(analytical["questions"])
    
    # Create merged dataset
    merged_dataset = {
        "dataset_name": "big_tech_curated",
        "description": "Curated benchmark dataset from big_tech_docs for evaluating RAG systems. Includes factual, multi-hop, and analytical questions.",
        "version": "1.0",
        "created_date": "2026-01-10",
        "total_questions": len(all_questions),
        "question_types": {
            "factual": len(factual["questions"]),
            "multihop": (len(multihop_part1["questions"]) + len(multihop_part2["questions"]) + 
                        len(multihop_part3["questions"]) + len(multihop_questions_part1["questions"])),
            "analytical": len(analytical["questions"])
        },
        "source_documents": "data/big_tech_docs/ (21 documents covering AI industry, investments, companies, executives, technology, regulations)",
        "questions": all_questions
    }
    
    # Save merged dataset
    output_path = datasets_dir / "big_tech_curated.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_dataset, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Merged dataset created: {output_path}")
    print(f"  Total questions: {len(all_questions)}")
    print(f"  - Factual: {len(factual['questions'])}")
    print(f"  - Multi-hop: {merged_dataset['question_types']['multihop']}")
    print(f"  - Analytical: {len(analytical['questions'])}")
    
    return merged_dataset

if __name__ == "__main__":
    merge_datasets()

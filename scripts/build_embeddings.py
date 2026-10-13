"""Generate actual optional BioBERT embeddings from canonical records."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.clinical_trial_intelligence.nlp.biobert import BioBERTEncoder
from src.clinical_trial_intelligence.research import _features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--revision", required=True, help="Exact model commit hash")
    parser.add_argument("--model", default="dmis-lab/biobert-base-cased-v1.2")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    source, directory = Path(args.input), Path(args.output)
    if directory.exists() and any(directory.iterdir()):
        parser.error("Use a new, empty embedding output directory.")
    df = pd.read_parquet(source) if source.suffix == ".parquet" else pd.read_csv(source)
    if "nct_id" not in df or df.nct_id.isna().any() or df.nct_id.duplicated().any():
        parser.error("Embedding rows require nonmissing unique nct_id values.")
    embeddings = BioBERTEncoder(model_name=args.model, revision=args.revision, local_files_only=not args.allow_download).fit_transform(_features(df)["protocol_text"])
    directory.mkdir(parents=True, exist_ok=True)
    np.save(directory / "biobert_embeddings.npy", embeddings, allow_pickle=False)
    df[["nct_id"]].to_csv(directory / "embedding_rows.csv", index=False)
    (directory / "embedding_manifest.json").write_text(json.dumps({"model": args.model, "revision": args.revision, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "rows": len(df), "dimensions": embeddings.shape[1], "pooling": "attention-mask mean", "max_length": 256, "fine_tuned": False}, indent=2), encoding="utf-8")
    print(f"Wrote actual frozen embeddings: {embeddings.shape}")


if __name__ == "__main__":
    main()

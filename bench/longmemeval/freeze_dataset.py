"""S2 dataset-only preparation. No inference, endpoint credentials or scoring."""
import argparse
import hashlib
import json
from pathlib import Path

from .runner import freeze

DATASET_REV = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_SIZE = 277383467
DATASET_URL = ("https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/"
               + DATASET_REV + "/longmemeval_s_cleaned.json")


def freeze_verified(path):
    path = Path(path)
    if path.stat().st_size != DATASET_SIZE:
        raise ValueError("official dataset byte size mismatch")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    if sha.hexdigest() != DATASET_SHA256:
        raise ValueError("official dataset SHA256 mismatch")
    manifest = freeze(path)
    if manifest["dataset_sha256"] != DATASET_SHA256:
        raise ValueError("dataset changed during preparation")
    if len(manifest["eval_ids"]) != 50 or len(manifest["dev_ids"]) != 50 or set(manifest["eval_ids"]) & set(manifest["dev_ids"]):
        raise ValueError("invalid frozen ID sets")
    return manifest


def publish(path, output):
    manifest = freeze_verified(path)
    with Path(output).open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="Pinned data: " + DATASET_URL)
    parser.add_argument("--dataset", required=True, help="Local copy of the official pinned release")
    parser.add_argument("--output", required=True, help="New IDs manifest; existing files never overwritten")
    args = parser.parse_args()
    publish(args.dataset, args.output)
    print("Dataset IDs frozen; model/judge configuration remains separate. No scoring performed.")


if __name__ == "__main__":
    main()

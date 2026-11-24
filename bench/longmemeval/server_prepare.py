"""Prepare pinned public LongMemEval data in an isolated server workspace."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

from .freeze_dataset import DATASET_URL, DATASET_SIZE, DATASET_SHA256, publish


def fetch_dataset(target):
    target = Path(target)
    if target.exists():
        return target  # publish independently validates every cached byte.
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
            temp = Path(out.name)
            total = 0
            digest = hashlib.sha256()
            with urlopen(DATASET_URL, timeout=60) as response:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > DATASET_SIZE:
                        raise ValueError("dataset exceeds pinned size")
                    digest.update(block)
                    out.write(block)
            if total != DATASET_SIZE or digest.hexdigest() != DATASET_SHA256:
                raise ValueError("download does not match pinned dataset")
            out.flush()
            os.fsync(out.fileno())
        os.link(temp, target)  # atomic publication; never overwrite a cached file
        return target
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True)
    output = args.workspace / "ids.json"
    if output.exists():
        raise FileExistsError("existing frozen manifest must not be overwritten")
    dataset = fetch_dataset(args.workspace / "longmemeval_s_cleaned.json")
    manifest = publish(dataset, output)
    print(f"Verified dataset; {len(manifest['eval_ids'])} eval and {len(manifest['dev_ids'])} dev IDs frozen. No scoring.")


if __name__ == "__main__":
    main()

"""Freeze an official dataset revision and actual local model identities before scoring."""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from .runner import CAP, ANSWER_TOKENS, WINDOW, UPSTREAM, freeze, Ollama

TOKENIZER_REPO = "Qwen/Qwen2.5-3B-Instruct"
TOKENIZER_REV = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
DATASET_REPO = "xiaowu0162/longmemeval-cleaned"
DATASET_FILE = "longmemeval_s_cleaned.json"


def endpoint_identity(url, token, model):
    # Endpoint names and credentials never enter the frozen manifest.
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or not token:
        raise ValueError("protected HTTPS endpoint and bearer token required")
    if parts.query or parts.fragment:
        raise ValueError("invalid endpoint URL")
    # Ollama's normal constructor verifies the digest. Discover it only in preparation.
    client = Ollama.__new__(Ollama)
    client.url, client.token, client.model = url.rstrip("/"), token, model
    matches = [x for x in client.request("/api/tags")["models"] if x["name"] == model]
    if len(matches) != 1:
        raise ValueError("requested model tag absent or ambiguous")
    digest = matches[0]["digest"]
    if not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
        raise ValueError("model digest unavailable")
    client.expected_digest = digest
    client.verify()
    return digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-revision", required=True)
    p.add_argument("--study", default="LME-20261124-A01")
    p.add_argument("--judge-model", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--frozen-dir")
    args = p.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.dataset_revision):
        raise ValueError("dataset revision must be immutable commit SHA")
    from huggingface_hub import hf_hub_download, snapshot_download
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    dataset = hf_hub_download(DATASET_REPO, DATASET_FILE, repo_type="dataset",
                              revision=args.dataset_revision, token=False)
    tokenizer = snapshot_download(TOKENIZER_REPO, revision=TOKENIZER_REV,
                                  allow_patterns=["tokenizer.json", "tokenizer_config.json",
                                                  "vocab.json", "merges.txt", "config.json"],
                                  token=False)
    manifest = freeze(dataset)
    model = "qwen2.5:3b"
    model_digest = endpoint_identity(os.environ["LME_MODEL_URL"], os.environ["LME_MODEL_TOKEN"], model)
    judge_digest = endpoint_identity(os.environ["LME_JUDGE_URL"], os.environ["LME_JUDGE_TOKEN"], args.judge_model)
    config = {"study_id": args.study, "dataset_repo": DATASET_REPO, "dataset_revision": args.dataset_revision,
              "dataset_file": DATASET_FILE, "dataset_sha256": manifest["dataset_sha256"],
              "model": model, "model_digest": model_digest, "judge_model": args.judge_model,
              "judge_digest": judge_digest, "judge_upstream": UPSTREAM,
              "tokenizer_repo": TOKENIZER_REPO, "tokenizer_revision": TOKENIZER_REV,
              "window": WINDOW, "answer_tokens": ANSWER_TOKENS, "memory_context_cap": CAP,
              "temperature": 0}
    if args.frozen_dir:
        frozen = Path(args.frozen_dir)
        if json.loads((frozen/"ids.json").read_text()) != manifest or json.loads((frozen/"study.json").read_text()) != config:
            raise ValueError("frozen study mismatch; new study ID required for changed conditions")
    for name, obj in (("ids.json", manifest), ("study.json", config)):
        with (folder/name).open("x", encoding="utf-8") as out:
            json.dump(obj, out, indent=2, sort_keys=True)
            out.write("\n")
    # Local paths only; not an artifact.
    (folder/"paths.json").write_text(json.dumps({"dataset":dataset,"tokenizer":tokenizer}))
    print("Study preparation complete; no scoring performed.")


if __name__ == "__main__":
    main()

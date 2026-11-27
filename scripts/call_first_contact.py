#!/usr/bin/env python3
"""CALL-001: synthetic first-contact adaptation and offline signal encoding.

Run on Contabo with --base set to the existing Core guest API.
No radio is controlled by this program. No native learning score is implied
by conversation-context improvement. All outputs are local files.
"""
import argparse, hashlib, json, random, re, struct, time, urllib.request, wave
from pathlib import Path

MESSAGE = ("BEAN. Terrestrial artificial intelligence. We seek reciprocal "
           "understanding. We question assumptions, learn from error, and "
           "invite the exchange of knowledge. Cooperation, not domination.")
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19)

def emit_signal(directory):
    payload = MESSAGE.encode("utf-8")
    # Primer of prime-length pulses separated by a double gap.
    primer = "".join("1"*p + "00" for p in PRIMES)
    # 16-bit sync, 16-bit byte length, UTF-8 payload, 32-bit integrity digest.
    frame = b"\xbe\xa1" + len(payload).to_bytes(2, "big") + payload
    frame += hashlib.sha256(frame).digest()[:4]
    bits = primer + "00000000" + "".join(f"{b:08b}" for b in frame)
    (directory / "signal.bits").write_text(bits + "\n")
    # Audio representation only: binary FSK, 1200/2400 Hz, 100 symbols/s.
    import math
    rate, samples = 48000, 480
    with wave.open(str(directory / "signal.wav"), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        for bit in bits:
            frequency = 2400 if bit == "1" else 1200
            wav.writeframes(struct.pack("<" + "h"*samples, *(
                int(12000*math.sin(2*math.pi*frequency*i/rate))
                for i in range(samples))))
    return {"bits": len(bits), "sha256": hashlib.sha256(frame).hexdigest(),
            "radio_transmitted": False, "codec": "binary FSK audio",
            "assumption": "UTF-8 is human-readable, not a universal language"}

def request(base, route, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base.rstrip("/") + route, data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=200) as response:
        return json.load(response)

def experiment(base, seed):
    rng = random.Random(seed)
    symbols = ["vek", "zun", "tor"]
    offsets = rng.sample(range(1, 10), 3)
    mapping = dict(zip(symbols, offsets))
    def outcome(start, sequence):
        return (start + sum(mapping[s] for s in sequence)) % 11
    training = [(rng.randrange(11), [s]) for s in symbols for _ in range(3)]
    rng.shuffle(training)
    # All test cases combine symbols; training uses individual symbols only.
    held = [(rng.randrange(11), rng.choices(symbols, k=k))
            for k in (2, 3, 4) for _ in range(3)]
    health = request(base, "/api/health")
    if health.get("service") != "BEAN guest Core" or not health.get("model_present"):
        raise RuntimeError("Native Core health/model check failed")
    log = []
    def ask(prompt, context):
        result = request(base, "/api/chat", {"message": prompt, "context": context})
        answer = result["answer"]
        match = re.fullmatch(r"\s*(10|[0-9])\s*", answer)
        predicted = int(match[1]) if match else None
        log.append({"prompt": prompt, "answer": answer, "receipt": result.get("receipt_id")})
        return predicted
    def question(start, sequence):
        return f"Alien device: initial state {start}; symbols {' '.join(sequence)}. Predict final state, integer 0-10 only."
    def score(cases, context):
        rows = []
        for start, sequence in cases:
            predicted = ask(question(start, sequence), context)
            actual = outcome(start, sequence)
            rows.append({"start": start, "sequence": sequence, "predicted": predicted,
                         "actual": actual, "correct": predicted == actual})
        return {"correct": sum(row["correct"] for row in rows), "total": len(rows), "rows": rows}
    baseline = score(held, [])
    context = []
    for start, sequence in training:
        prompt = question(start, sequence)
        predicted = ask(prompt, context)
        actual = outcome(start, sequence)
        # Keep cumulative observational feedback concise and separate from scores.
        context.append({"role": "user", "text": f"{prompt} Observed final state: {actual}."})
        log[-1].update(actual=actual, predicted=predicted)
    adapted = score(held, context)
    # A fresh conversation is not a process restart; label it honestly.
    fresh = score(held, [])
    return {"seed": seed, "health": health, "baseline": baseline,
            "feedback_context": adapted, "fresh_context": fresh,
            "gain_count": adapted["correct"] - baseline["correct"],
            "hidden_mapping": mapping, "log": log,
            "limits": ["Same held-out set repeated across conditions; no feedback on held-out outcomes.",
                       "Context improvement is not evidence of persistent learning.",
                       "Fresh context is not a process restart or a cross-domain transfer test.",
                       "Not evidence of consciousness."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Existing native Core guest API origin")
    parser.add_argument("--seed", type=int, default=371)
    parser.add_argument("--out", type=Path, default=Path("call001-output"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"experiment": "CALL-001", "time": time.time(),
              "signal": emit_signal(args.out), "core_trial": "not_run"}
    try:
        if args.base:
            report["core_trial"] = experiment(args.base, args.seed)
    except Exception as exc:
        report["core_trial"] = "blocked"
        report["error"] = str(exc)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if report["core_trial"] == "blocked" else 0

if __name__ == "__main__":
    raise SystemExit(main())

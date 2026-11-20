# Local Qwen smoke verdict correction

The existing actual-model smoke conflated arithmetic value with compliance with
“a single numeral.” PR #440 run 44733875027 returned `2 + 2 = 4`, which is
mathematically correct and violates that format. Earlier main run 44664703649 and
candidate run 44733378717 returned `2`, a genuine arithmetic failure. Those
failed runs remain evidence; this correction does not reinterpret `2` as correct.

The smoke now records both verdicts, retaining the complete answer and journal.
The bounded parser accepts only a complete integer or the exact requested
addition equation, and independently computes the sum. Prose, unrelated digits,
wrong operands and incorrect sums fail conservatively. An unrecognized answer
means the parser could not establish correctness, not necessarily mathematical
incorrectness. Temperature zero and seed zero are confined to this smoke server.

`diagnostic.json` retains three predeclared local diagnostics through the actual
NativeReasoningService and LocalLlamaCppProvider, llama.cpp revision
620d2225cc436ab0b001e3200e590e3b286ef9ab, Apache-2.0 Qwen model revision and SHA256
recorded in the report. No external paid provider or learned-answer stub ran.
The first case answered `2 + 2 = 4` (correct value, wrong format). The second
answered `Seven plus five is eight.` (wrong). The third answered
`Nine plus six is 15.` (correct prose, conservatively unrecognized by the bounded
parser). These are diagnostics, not held-out learning evidence or an AGI rank.
They demonstrate that this tiny model is not a reliable arithmetic reasoner.
The dependency source/model were used locally without modification.

Validation: 39 focused tests and 8 subtests; whole Core 1491 passed, 44 skipped,
374 subtests passed on Python 3.12 Linux. Exact remote-head CI is recorded in the
associated PR; these local totals do not substitute for that execution.

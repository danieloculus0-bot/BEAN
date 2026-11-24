"""Non-scoring token-accounting checks for the fixed answer model."""


def chat_tokens(tokenizer, prompt):
    return len(tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=True,
        add_generation_prompt=True))


def verify_answer_accounting(tokenizer, answer, window, answer_tokens):
    """Use synthetic probes only; require identical local/server prompt counts."""
    prompts = (
        "Answer with one word: blue.",
        "History:\nDate: 2026-01-01\nuser: café, 東京, 12.5 kg.\nQuestion: What unit?\nAnswer:",
        "History:\n" + "user: unrelated synthetic text 123.\n" * 200 + "Question: What number?\nAnswer:",
    )
    observations = []
    for prompt in prompts:
        expected = chat_tokens(tokenizer, prompt)
        actual = answer(prompt, 1)["tokens_in"]
        if expected != actual or expected + answer_tokens > window:
            raise ValueError("answer tokenizer/server prompt-token mismatch")
        observations.append({"expected": expected, "actual": actual})
    return observations

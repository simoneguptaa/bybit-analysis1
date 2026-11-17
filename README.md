# INTE2629-A2

Assignment 2 in Blockchain Innovations INTE2629 at RMIT — the Bybit Hack: initial
investigation and fund-tracing.

## Team

- S4051222
- S4269637

## Task split

| Owner | Coding (`bybit_skeleton.py`) | Report |
|-------|-------------------------------|--------|
| Christian | `q1`-`q3` | Part 1, Part 3, Teamwork discussion (page 4) |
| Simone | `q4`-`q6` | Part 2 |
| Both | — | References (added inline while writing own part(s)); Contribution Table (filled in together before submission) |

## Contents

The course-provided package plus our work:

| File | What it is |
|------|-----------|
| `bybit_skeleton.py` | The fund tracer. We implement the six `q1`–`q6` question functions; everything else is provided and must not change. |
| `bybit_answer_key_student.json` | Answers for the 2 public example wallets, used by the built-in self-test. |
| `STUDENT_GUIDE.md` / `.pdf` | How the code is structured, how to run it, and how it's marked. |
| `Assignment2_BybitHack_Initial_Investigation.pdf` | The written-report brief (Parts 1–3 + references + teamwork page). |

## Running the self-test

```bash
python bybit_skeleton.py
```
or
```bash
python3 bybit_skeleton.py
```

Requires the `requests` package (`pip install requests`) and a free Etherscan API key
(https://etherscan.io/apis).

**This repo is private, but still do not commit a real API key.** Set `API_KEY` in
`bybit_skeleton.py` locally to test, then revert that line (e.g.
`git checkout -- bybit_skeleton.py` if it's the only change, or hand-revert just that
line) before committing or pushing.

## Working together

The assignment brief requires using this GitHub repo to evidence individual
contribution — commit your own work under your own GitHub account rather than one
person pushing for both.

## Academic Integrity
Use of AI tools: AI was used to assist in code implementation to ensure syntactic correctness only.

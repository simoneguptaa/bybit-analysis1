# Assignment 2 - Bybit Hack Fund Tracer: Student Guide

Everything you need to work on the code component, in two parts:

- **Part 1 - Program structure and flow.** How the script fits together: what runs
  when, where each of your functions is called from, where its inputs come from.
  **Read this first**, before you write any code.
- **Part 2 - Working the assignment.** Your package, how to run the self-test, the
  expected results, and how the code is marked.

The full task background (the Bybit hack, what each question means forensically) is in
the separate **Assignment 2 PDF**.

---
---

# PART 1 - PROGRAM STRUCTURE AND FLOW

The short version: **the program is already fully wired.** You fill in six function
bodies. Nothing calls your code that you have to write yourself, and you never touch
`main`, `build_report`, or `grade`.

## 1.1 The flow in one picture

```
python3 bybit_skeleton.py
   |
   v
main()                                        [PROVIDED]
   |  loads bybit_answer_key_student.json
   |  loops over the 2 example addresses in TEST_ADDRESSES
   |
   +--> build_report(address)                 [PROVIDED]  <-- the orchestrator
   |      |
   |      | 1. txs = get_normal_transactions(address, API_KEY)   [PROVIDED]
   |      |       ONE API call. Returns the wallet's full normal-tx history
   |      |       as a list of dicts. THIS is the `txs` your functions receive.
   |      |
   |      | 2. passes that same list into your five list-based functions:
   |      |       q1_bybit_inflow(txs, address, BYBIT_EXPLOITER_1)     [YOU]
   |      |       q2_exploiter_network(txs, address, known)            [YOU]
   |      |       q3_eth_outflows(txs, address)                        [YOU]
   |      |       q4_net_flow(txs, address)                            [YOU]
   |      |       q5_activity_window(txs)                              [YOU]
   |      |
   |      | 3. for Q6 it does something different:
   |      |       bfs_start = _first_outflow_block(txs, ...)           [PROVIDED]
   |      |       bfs_n_hops(address, q6_get_value_neighbors, ...)     [PROVIDED]
   |      |            |
   |      |            +--> calls YOUR q6_get_value_neighbors(...)     [YOU]
   |      |                 once per wallet it visits, each time with a
   |      |                 different block range. Your Q6 makes its own
   |      |                 API call - it is the one exception.
   |      |
   |      | 4. collects everything into one report dict
   |      | 5. save_json(report, "bybit_tracer_<addr>.json")           [PROVIDED]
   |      v
   +--> grade(report, answer_key, ...)         [PROVIDED]
   |      compares your report against the answer key, prints one line per check
   |      plus a PASS/FAIL verdict per question
   v
prints "SELF-CHECK RESULT: N/12 question x wallet cases passed"
```

**The key idea:** `build_report` fetches the data **once** and hands the same list to
Q1-Q5. That is why those five functions take `txs` as their first parameter and must
not call the API themselves.

## 1.2 Every function in the file

16 functions. **You implement 6.** The other 10 are complete and must not be changed.

| Line | Function | Who | Role in the program |
|------|----------|-----|---------------------|
| 99 | `_http_get_json` | provided | Low-level HTTP GET with self-throttling and retries so the many Q6 calls stay inside Etherscan's 5-per-second limit |
| 120 | `get_normal_transactions` | provided | The Week-2 fetcher. Calls Etherscan `txlist` and returns a list of tx dicts |
| 151 | `save_json` | provided | Writes the finished report to disk |
| 160 | `_norm` | provided | Lowercases an address. Use it on **both sides** of every address comparison |
| 164 | `sum_eth_amount` | provided | Sums the `value` field of a tx list and returns ETH. Useful in Q4 |
| 181 | `bfs_n_hops` | provided | The graph traversal for Q6. Walks the value-transfer graph layer by layer and returns the wallets at exactly `hops` distance. Calls your Q6 callback at each step |
| 226 | `_first_outflow_block` | provided | Finds the block where the wallet first sends real ETH. Anchors the Q6 search window |
| **249** | **`q1_bybit_inflow`** | **YOU** | Q1: find the inflow(s) from Exploiter 1 |
| **283** | **`q2_exploiter_network`** | **YOU** | Q2: find interactions with other known cluster wallets |
| **311** | **`q3_eth_outflows`** | **YOU** | Q3: list the distinct addresses this wallet sent ETH to |
| **335** | **`q4_net_flow`** | **YOU** | Q4: total ETH in, out, and net |
| **361** | **`q5_activity_window`** | **YOU** | Q5: first and last block of activity |
| **384** | **`q6_get_value_neighbors`** | **YOU** | Q6: given a wallet and a block range, return the wallets it exchanged ETH with. This is the callback `bfs_n_hops` uses |
| 421 | `build_report` | provided | **The orchestrator.** Fetches the data, calls all six of your functions, saves the JSON |
| 462 | `grade` | provided | Checks your report against the answer key and prints verdicts |
| 569 | `main` | provided | Entry point. Loops the example addresses, calls `build_report` then `grade` |

*(Line numbers are from the skeleton as shipped. They shift as you type - the function
names are the reliable anchor.)*

## 1.3 Per question: implement it here, it runs there, verify it with this

| Q | You implement | It gets called from | It produces this JSON key | You verify it by |
|---|---------------|---------------------|---------------------------|------------------|
| Q1 | `q1_bybit_inflow` (line 249) | `build_report` | `q1_bybit_inflow` | 4 check lines: total ETH, transfer count, timestamp, asset |
| Q2 | `q2_exploiter_network` (283) | `build_report` | `q2_exploiter_network` | 1 check line: interaction count |
| Q3 | `q3_eth_outflows` (311) | `build_report` | `q3_eth_outflows` | 2 check lines: recipient count, recipient set |
| Q4 | `q4_net_flow` (335) | `build_report` | `q4_net_flow` | 2 check lines: ETH in, ETH out |
| Q5 | `q5_activity_window` (361) | `build_report` | `q5_activity_window` | 1 check line: the `[begin, end]` list |
| Q6 | `q6_get_value_neighbors` (384) | `bfs_n_hops`, which `build_report` invokes | `q6_bfs_n_hops` | 2 check lines: hop-2 count, hop-2 set |

To run all of it: `python3 bybit_skeleton.py`. There is nothing else to execute, and
no separate test file. A question passes on a wallet only when **every** check line
for that question passes - that is exactly how the marker awards marks.

## 1.4 Where your inputs come from

This is the most common confusion, so it is worth stating plainly.

**Q1 to Q5 receive `txs` as a parameter. You do not fetch it.** `build_report` calls
`get_normal_transactions(address, API_KEY)` once, then passes the resulting list to
each of your functions. Your job inside those functions is purely to **filter and
summarise a list you already have**. You do not need to write a wrapper - the
orchestration already exists.

Each item in `txs` is a dict from Etherscan. The fields you need:

| Field | Meaning | Note |
|-------|---------|------|
| `from` | sender address | mixed case, always `_norm` it |
| `to` | recipient address | mixed case; empty on contract creation |
| `value` | amount in wei | a **string**, so `int(t["value"])` first |
| `timeStamp` | unix seconds | a **string** |
| `blockNumber` | block number | a **string** |

To see one for yourself, add `print(txs[0])` temporarily inside your Q1.

**Q6 is the exception.** It takes an `address` and a block range, not a list, because
`bfs_n_hops` calls it repeatedly for different wallets and different ranges. So Q6
calls `get_normal_transactions(address, API_KEY, start_block=..., end_block=...)`
itself - exactly once per invocation, and the dust filter and hub guard both work off
that single fetch.

## 1.5 What you should see when you run it

```
[INFO] Fetching transactions for 0x0e8c1e28...
[INFO] 167 transactions returned                 <- this is len(txs)
[INFO] Running 2-hop BFS in blocks [21938776, 21938876]...
[INFO] BFS found 3 hop-2 wallets
[INFO] Wrote 7 records to bybit_tracer_0x0e8c1e28.json
  [PASS]       Q1  ETH from Exploiter 1
  ...
  Question verdicts: Q1 PASS   Q2 PASS   ...
  Questions passed: 6/6
```

Failed checks print `got=...  expected=...` so you can compare directly. The written
report is in `bybit_tracer_<address>.json` if you want to inspect the full output.

---
---

# PART 2 - WORKING THE ASSIGNMENT

## 2.1 What's in your package (3 files)

| File | What it is |
|------|-----------|
| `bybit_skeleton.py` | Your working file. Implement the **6 question functions** (`q1`-`q6`). Everything else (HTTP helpers, `bfs_n_hops`, `build_report`, `grade`, `main`) is pre-built - **do not modify anything outside the 6 function bodies.** |
| `bybit_answer_key_student.json` | The correct answers for the **2 public example wallets**, used by the built-in self-test. Includes the full recipient lists (Q3) and hop-2 wallet lists (Q6) so you can diff your output. |
| `STUDENT_GUIDE.md` | This file (Part 1 = program structure, Part 2 = how to run, expected results, marking). |

You also need your **own free Etherscan API key** (https://etherscan.io/apis) - put it
in `API_KEY` at the top of the skeleton.

## 2.2 The two-tier test setup (read this before you start)

- Your skeleton ships with **2 public example wallets** and their answers. Running the
  file tests your code against them - that is your **self-test**, worth **0 marks**.
- Your actual marks come from the marker running your submitted code on
  **3 hidden wallets that you never see**. They are wallets of the same type
  (Bybit hop-1 wallets that each received 10,000 ETH from Exploiter 1), but their
  per-wallet values - timestamps, recipient sets, activity windows, hop-2 sets -
  are all different.
- **Consequence:** hard-coding the two public answers scores ~0 on the hidden
  wallets. Write general code that computes the answers from the fetched data.

## 2.3 How to run the self-test

```bash
python3 bybit_skeleton.py
```

For each of the 2 public wallets the harness:
1. Fetches the wallet's transactions (plus extra fetches during the Q6 BFS),
2. Runs your `q1`-`q6` via `build_report` and writes `bybit_tracer_<addr>.json`,
3. Prints one `[PASS]` / `[WRONG]` / `[WRONG_TYPE]` line per check - failed checks
   show `got=... expected=...`,
4. Prints a **`Question verdicts:`** line - a question passes on a wallet only if
   **every** one of its checks passes on that wallet,
5. Ends with `SELF-CHECK RESULT: N/12 question x wallet cases passed`
   (6 questions x 2 wallets).

Target before you submit: **12/12**.

> **Runtime note:** Q6 triggers ~5-20 extra API calls per wallet (the BFS). A full
> self-test run takes ~30-60 seconds on the free tier. If you see
> `Max rate limit reached`, wait a minute and re-run - your code is not broken.

## 2.4 Expected results - the 2 public examples

Summary of what a correct implementation produces (full recipient / hop-2 lists are
in `bybit_answer_key_student.json`):

### Input 1 - `0x0e8c1e2881f35ef20343264862a242fb749d6b35`

| Q | Checks | Expected |
|---|--------|----------|
| Q1 | 4 | 10000.0 ETH, 1 transfer, `2025-02-21T15:50:47Z`, asset `ETH` |
| Q2 | 1 | 0 other-exploiter interactions (empty list) |
| Q3 | 2 | 62 unique recipients (set-compared, order doesn't matter) |
| Q4 | 2 | eth_in `10042.571775`, eth_out `10042.56899` (+/-1.0 tolerance) |
| Q5 | 1 | `[21895721, 21965191]` (exact) |
| Q6 | 2 | 3 hop-2 wallets (set-compared) |

### Input 2 - `0x3a21f4e6bbe527d347ca7c157f4233c935779847`

| Q | Checks | Expected |
|---|--------|----------|
| Q1 | 4 | 10000.0 ETH, 1 transfer, `2025-02-21T15:48:11Z`, asset `ETH` |
| Q2 | 1 | **2** other-exploiter interactions |
| Q3 | 2 | 77 unique recipients |
| Q4 | 2 | eth_in `10003.615974`, eth_out `10003.612706` (+/-1.0 tolerance) |
| Q5 | 1 | `[21895708, 21948952]` (exact) |
| Q6 | 2 | 14 hop-2 wallets |

> **Note on Q2 and these two examples.** Input 1 has **0** interactions and Input 2 has
> **2**, so between them they exercise both paths. That matters, because a Q2 that
> always returns an empty list would still "pass" on Input 1 - it only shows up as
> wrong on Input 2. The two interactions on Input 2 also run in **opposite
> directions** (one wallet sent ETH to this address, the other received ETH from it),
> so a Q2 that only checks one side of each transaction finds 1 instead of 2. If your
> Q2 passes on both inputs, it is genuinely working.

Numeric tolerances: Q1 total +/-0.001 ETH; Q4 +/-1.0 ETH; everything else exact.
All ETH values rounded to 6 decimals - round only the **final** value, never
intermediate sums (see the precision rules at the top of the skeleton).

## 2.5 How the code component is marked - 15 marks

> These 15 marks cover the **code component only** - they are one part of your
> Assignment 2 grade. The full assignment description, the written report, and the
> overall grade breakdown are delivered separately in the **Assignment 2 PDF**.

The marker pastes your `q1`-`q6` into the marking harness and runs it on the
**3 hidden wallets**. Each question earns **1 mark per hidden wallet where every
check for that question passes** (all-or-nothing per question per wallet - e.g.
61 of 62 recipients on a wallet earns 0 for Q3 on that wallet):

| Question | Graded on | Marks |
|----------|-----------|-------|
| Q1 inflow | 3 hidden wallets | **3** |
| Q2 exploiter network | 2 hidden wallets | **2** |
| Q3 outflow recipients | 2 hidden wallets | **2** |
| Q4 net flow | 3 hidden wallets | **3** |
| Q5 activity window | 2 hidden wallets | **2** |
| Q6 BFS hop-2 | 3 hidden wallets | **3** |
| **Total** | | **15** |

If your self-test shows 12/12 and your code contains no hard-coded answers or
address-specific branches, you should expect full marks on the hidden wallets.

## 2.6 Rules

- Implement **only** the 6 question function bodies. Do not change signatures,
  return types, the helpers, `bfs_n_hops`, `build_report`, `grade`, `main`, or any
  config constant.
- Do not call the API inside Q1-Q5. Five questions share one fetch (see 1.4).
- Do not write your own wrapper or `main` - the orchestration already exists.
- Do not hard-code answers or branch on specific wallet addresses - the hidden
  wallets are designed to catch this, including one where Q2 is **not** empty.
- Normalise addresses on both sides of every comparison with `_norm`.
- Allowed data source: `txlist` via the provided `get_normal_transactions` only
  (no `eth_call`, receipts, event logs, or `tokentx`).
- Submit your completed `bybit_skeleton.py` for this code component. All other
  deliverables (including the written report) are described in the Assignment 2 PDF.

Good luck - and remember you are tracing real stolen funds; every number your code
produces is verifiable on Etherscan.

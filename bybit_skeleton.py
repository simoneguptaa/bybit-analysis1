"""
Assignment 2 - Bybit Hack Fund Tracer (Student Skeleton)

Implement the SIX question functions (q1 through q6). Everything else -
HTTP helpers, bfs_n_hops, build_report, grade, main - is already done.
See the Assignment 2 PDF for the full task description.

SELF-CHECK: this skeleton ships with 2 example input addresses and their answers
(bybit_answer_key_student.json), so you can run it and see a per-check verdict plus
a PASS/FAIL verdict per question on each example.

MARKING (done by the marker on HIDDEN wallets you never see): each question earns
1 mark per hidden wallet where EVERY check for that question passes - Q1, Q4, Q6
are graded on 3 hidden wallets (3 marks each); Q2, Q3, Q5 on 2 (2 marks each);
15 marks total. Hard-coding the two example answers scores 0 on the hidden
wallets - write GENERAL code.
"""

import json
import time
import requests
import datetime
from typing import List, Dict, Any

# ============================================================
# CONFIGURATION
# ============================================================
API_KEY = "NZQZ5HR2WUUKDXHCVMB9NAVWWB4ET7YK21"

# The primary Bybit exploit distribution hub - given to all students, do not change.
BYBIT_EXPLOITER_1 = "0x47666fab8bd0ac7003bce3f5c3585383f09486e2"

# Publicly attributed Bybit exploiter cluster.
KNOWN_EXPLOITER_ADDRESSES = {
    "0x47666fab8bd0ac7003bce3f5c3585383f09486e2",  # Bybit Exploiter Hub 1 (seed)
    "0x36ed3c0213565530c35115d93a80f9c04d94e4cb",  # received 10,000 ETH from seed
    "0xaf620e6d32b1c67f3396ef5d2f7d7642dc2e6ce9",  # received 10,000 ETH from seed
    "0x3a21f4e6bbe527d347ca7c157f4233c935779847",  # received 10,000 ETH from seed
    "0xfa3fcccb897079fd83bfba690e7d47eb402d6c49",  # received 10,000 ETH from seed
    "0xfc926659dd8808f6e3e0a8d61b20b871f3fa6465",  # received 10,000 ETH from seed
    "0x83c7678492d623fb98834f0fbcb2e7b7f5af8950",  # received 10,000 ETH from seed
    "0x96244d83dc15d36847c35209bbdc5bdde9bec3d8",  # received 10,000 ETH from seed
    "0x83ef5e80fad88288f770152875ab0bb16641a09e",  # received 10,000 ETH from seed
}

# Your 2 self-check examples (answers in bybit_answer_key_student.json).
# Each run prints a per-check verdict + a PASS/FAIL verdict per question.
# Failed checks show got + expected. The marker runs your code on 3 HIDDEN
# wallets (where the marks live) - keep your code general.
TEST_ADDRESSES = [
    {"address": "0x0e8c1e2881f35ef20343264862a242fb749d6b35", "visibility": "public"},  # Input 1 (Bybit Exploiter 14)
    {"address": "0x3a21f4e6bbe527d347ca7c157f4233c935779847", "visibility": "public"},  # Input 2 (Bybit Exploiter 34)
]

ETHERSCAN_API_URL = "https://api.etherscan.io/v2/api"

# Q6 BFS window - the 2-hop BFS spans this many blocks starting from the wallet's
# FIRST OUTFLOW block (where its fan-out begins), not the inflow block. Anchoring on
# the fan-out is what makes the BFS trace real downstream movement; a narrow window
# keeps Etherscan API calls within the free tier.
Q6_HOP2_WINDOW_BLOCKS = 100

# BFS traversal filters (Assignment 2).
MIN_ETH_VALUE = 0.5               # ignore transfers below this many ETH (dust)
MAX_NODE_TX_COUNT = 250           # skip nodes with more txs than this in the window (hubs)
# Placeholder for known CEX/bridge exit endpoints. Kept EMPTY here so Assignment 2's
# q6 hop-2 discovery is unfiltered (its verified answers assume no service filter).
# The real CEX/bridge list is defined and used in Assignment 3 (ASSIGNMENT3/).
PUBLIC_SERVICE_ADDRESSES = set()
# ============================================================


# ============================================================
# NUMERICAL PRECISION RULES (must follow exactly for tests to pass)
# ============================================================
# 1. wei → ETH conversion uses 1e18:  eth = int(wei_str) / 1e18
# 2. All ETH amounts returned in JSON are rounded to 6 decimal places (ETH_DECIMALS).
# 3. Round ONLY the final value you return - never round intermediate sums.
# 4. Block numbers, tx counts, transfer counts: plain int (no rounding).
# 5. Timestamps: ISO-8601 UTC via
#       datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%dT%H:%M:%SZ")
# ============================================================
ETH_DECIMALS = 6
# ============================================================


# ============================================================
# HELPER FUNCTIONS (REUSED FROM WEEK 2 + WEEK 4)
# ============================================================

# Q6 runs a BFS that issues many sequential calls, so the fetch RETRIES on
# transient failures (timeouts, rate-limit responses). Without this, a dropped
# call mid-BFS silently shrinks the hop-2 set and makes results non-deterministic
# on the Etherscan free tier.
_LAST_CALL = [0.0]   # self-throttle clock (module-level)
_MIN_INTERVAL = 0.25  # >= 0.2s keeps us under the 5 req/sec free-tier limit


def _http_get_json(params, timeout=20, tries=6):
    for i in range(tries):
        wait = _MIN_INTERVAL - (time.time() - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.time()
        try:
            response = requests.get(ETHERSCAN_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            time.sleep(min(2.0 * (i + 1), 8.0))
            continue
        result = data.get("result")
        if data.get("status") == "0" and isinstance(result, str) and "rate limit" in result.lower():
            time.sleep(min(2.0 * (i + 1), 8.0))
            continue
        return data
    return {}


def get_normal_transactions(address, api_key,
                             start_block=0,
                             end_block=99999999,
                             sort="asc"):
    params = {
        "module": "account",
        "action": "txlist",
        "chainid": 1,
        "address": address,
        "startblock": start_block,
        "endblock": end_block,
        "sort": sort,
        "apikey": api_key,
    }

    data = _http_get_json(params)
    status = data.get("status")
    message = data.get("message")
    transactions = data.get("result")

    if status == "1":
        return transactions or []

    if status == "0" and message == "No transactions found":
        print("[INFO] No transactions found for this address.")
        return []

    print(f"[ERROR] Etherscan API error: status={status}, message={message}")
    return []


def save_json(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[INFO] Wrote {len(data)} records to {filename}")
    except OSError as e:
        print(f"[ERROR] Failed to write file: {e}")


def _norm(addr):
    return addr.lower()


def sum_eth_amount(txs):
    total = 0
    for t in txs:
        total += int(t["value"])
    return total / 1e18

# ============================================================


# ============================================================
# HELPER FUNCTIONS (NEW IN ASSIGNMENT 2) - Graph traversal
# ============================================================
# bfs_n_hops is PROVIDED - do not modify. You only implement the
# q6_get_value_neighbors callback. The BFS is generic and reused in later
# assignments. For Q6 build_report calls it with hops=2.
# ============================================================

def bfs_n_hops(seed_address: str,
               get_neighbors_fn,
               start_block: int,
               end_block: int,
               hops: int,
               min_eth_value: float = MIN_ETH_VALUE,
               max_node_tx_count: int = MAX_NODE_TX_COUNT,
               public_service_addresses: set = PUBLIC_SERVICE_ADDRESSES) -> List[str]:
    """
    Generic BFS returning the wallets at exactly `hops` distance from the seed.

    Filters applied during traversal:
      - min_eth_value:      transfers below this many ETH are ignored (dust).
      - max_node_tx_count:  a node busier than this in the window is treated as
                            a hub and not traversed into (the callback returns []).
      - public_service_addresses: addresses in this set are never traversed
                            into nor returned (known exchanges/bridges/mixers).

    get_neighbors_fn signature:
        get_neighbors_fn(address, start_block, end_block,
                         min_eth_value, max_node_tx_count) -> List[str]

    Returns a sorted List[str] of lowercase addresses at depth `hops`.
    """
    seed_lower = seed_address.lower()
    service_set = {a.lower() for a in public_service_addresses}
    visited: set = {seed_lower}
    frontier: set = {seed_lower}

    for _ in range(hops):
        next_frontier: set = set()
        for node in frontier:
            if node in service_set:
                continue  # never traverse into a public service
            for addr in get_neighbors_fn(node, start_block, end_block,
                                         min_eth_value, max_node_tx_count):
                a = addr.lower()
                if a and a not in visited and a not in service_set:
                    next_frontier.add(a)
        visited |= next_frontier
        frontier = next_frontier

    return sorted(frontier)


def _first_outflow_block(txs, address, min_eth_value):
    """First block where `address` sends >= min_eth_value ETH - i.e. where its
    fan-out begins. Used to anchor the Q6 BFS window. Falls back to the earliest
    tx block if the wallet has no qualifying outflow; None if txs is empty."""
    a = _norm(address)
    outflow_blocks = [
        int(t["blockNumber"]) for t in txs
        if _norm(t["from"]) == a and int(t["value"]) / 1e18 >= min_eth_value
    ]
    if outflow_blocks:
        return min(outflow_blocks)
    if txs:
        return min(int(t["blockNumber"]) for t in txs)
    return None

# ============================================================


# ============================================================
# ASSIGNMENT QUESTIONS
# ============================================================

# Q1 - 3 marks: graded on 3 hidden wallets, 1 mark per wallet where ALL Q1 checks pass.
def q1_bybit_inflow(txs: List[Dict[str, Any]], address: str, exploiter1: str) -> Dict[str, Any]:
    """
    Q1: What Bybit scam money was transferred to this address, when, and in what asset?

    Parameters:
        txs        - list from get_normal_transactions()
        address    - the wallet being analysed
        exploiter1 - BYBIT_EXPLOITER_1 address (the expected sender)

    Returns:
        {
          "transfers": [{amount_eth (6dp), timestamp (ISO UTC), asset "ETH", block (int)}],
          "total_eth_received_from_exploiter1": float (6dp)
        }

    Example output:
        {
          "transfers": [
            {"amount_eth": 10000.0, "timestamp": "2025-02-21T15:50:47Z",
             "asset": "ETH", "block": 21895721}
          ],
          "total_eth_received_from_exploiter1": 10000.0
        }
    """
    a = _norm(address)
    e1 = _norm(exploiter1)

    matches = []
    total_wei = 0
    for transaction in txs:
        if _norm(transaction["from"]) == e1 and _norm(transaction["to"]) == a and int(transaction["value"]) > 0:
            value_wei = int(transaction["value"])
            timestamp = datetime.datetime.utcfromtimestamp(int(transaction["timeStamp"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            matches.append({
                "amount_eth": round(value_wei / 1e18, ETH_DECIMALS),
                "timestamp": timestamp,
                "asset": "ETH",
                "block": int(transaction["blockNumber"])
            })
            total_wei += value_wei

    matches.sort(key=lambda m: m["timestamp"])

    result: Dict[str, Any] = {
        "transfers": matches,
        "total_eth_received_from_exploiter1": round(total_wei / 1e18, ETH_DECIMALS),
    }

    return result

# Q2 - 2 marks: graded on 2 hidden wallets, 1 mark per wallet where ALL Q2 checks pass.
def q2_exploiter_network(txs: List[Dict[str, Any]], address: str,
                         known_exploiters: set) -> List[Dict[str, Any]]:
    """
    Q2: Which other known Bybit cluster accounts (besides Exploiter 1) did this
        address interact with, how many times, and for how much total ETH?

    Parameters:
        txs              - list from get_normal_transactions()
        address          - the wallet being analysed
        known_exploiters - set of known Bybit exploiter addresses
                           (already excludes `address`; you must also exclude
                           BYBIT_EXPLOITER_1 - Q1 covers that one)

    Returns:
        [{address, tx_count (int), total_eth (6dp), direction}]
        An empty list [] if there are no matches - that IS the correct answer for
        many addresses, so return [] once your filter finds nothing (do not leave
        the placeholder entry in).

    Example output:
        [{"address": "0x36ed3c0213565530c35115d93a80f9c04d94e4cb",
          "tx_count": 1, "total_eth": 10000.0, "direction": "outbound"}]
    """
    a = _norm(address)
    e1 = _norm(BYBIT_EXPLOITER_1)
    known = {_norm(addr) for addr in known_exploiters if _norm(addr) != e1}

    groups: Dict[tuple, Dict[str, int]] = {}

    for transaction in txs:
        value_wei = int(transaction["value"])
        if value_wei <= 0:
            continue
        from_addr = _norm(transaction["from"])
        to_addr = _norm(transaction["to"])

        if from_addr == a and to_addr in known:
            key = (to_addr, "outbound")
        elif to_addr == a and from_addr in known:
            key = (from_addr, "inbound")
        else:
            continue

        g = groups.setdefault(key, {"tx_count": 0, "total_wei": 0})
        g["tx_count"] += 1
        g["total_wei"] += value_wei

    interactions: List[Dict[str, Any]] = [
        {
            "address": addr,
            "tx_count": g["tx_count"],
            "total_eth": round(g["total_wei"] / 1e18, ETH_DECIMALS),
            "direction": direction,
        }
        for (addr, direction), g in groups.items()
    ]

    return interactions

# Q3 - 2 marks: graded on 2 hidden wallets, 1 mark per wallet where ALL Q3 checks pass.
def q3_eth_outflows(txs: List[Dict[str, Any]], address: str) -> List[str]:
    """
    Q3: Which addresses received ETH from this address?

    Parameters:
        txs     - list from get_normal_transactions()
        address - the wallet being analysed

    Returns:
        List[str] of distinct recipient addresses (lowercase) from txs where
        from == address AND value > 0. Order does NOT matter (compared as a set).

    Example output:
        ["0xe8e8035dbb36a3faf41ecf8888de4032ac8203a3",
         "0xc4679d63183f67046f1778cc13ff24458a031cc5"]
    """
    a = _norm(address)
    recipients_set = set()

    for transaction in txs:
        if _norm(transaction["from"]) != a:
            continue
        if not transaction["to"]:
            continue 
        if int(transaction["value"]) <= 0:
            continue
        recipients_set.add(_norm(transaction["to"]))

    return sorted(recipients_set)


# Q4 - 3 marks: graded on 3 hidden wallets, 1 mark per wallet where ALL Q4 checks pass.
def q4_net_flow(txs: List[Dict[str, Any]], address: str) -> Dict[str, float]:
    """
    Q4: How much ETH flowed in vs out, and what is the net?

    Parameters:
        txs     - list from get_normal_transactions()
        address - the wallet being analysed

    Returns:
        {"eth_in": float (6dp), "eth_out": float (6dp), "net_eth": float (6dp)}
        net_eth = eth_in - eth_out.

    Example output:
        {"eth_in": 10042.571775, "eth_out": 10042.56899, "net_eth": 0.002785}
    """
    result: Dict[str, float] = {
        "eth_in": 0.0,
        "eth_out": 0.0,
        "net_eth": 0.0,
    }

    a = _norm(address)
    eth_in_wei = 0
    eth_out_wei = 0

    for transaction in txs:
        value_wei = int(transaction["value"])
        if value_wei <= 0:
            continue

        asset = str(transaction.get("asset") or "ETH").upper()
        if asset != "ETH":
            continue

        from_addr = _norm(transaction.get("from", ""))
        to_addr = _norm(transaction.get("to", ""))

        if to_addr == a:
            eth_in_wei += value_wei
        if from_addr == a:
            eth_out_wei += value_wei

    eth_in = round(eth_in_wei / 1e18, ETH_DECIMALS)
    eth_out = round(eth_out_wei / 1e18, ETH_DECIMALS)
    net_eth = round(eth_in - eth_out, ETH_DECIMALS)

    result["eth_in"] = eth_in
    result["eth_out"] = eth_out
    result["net_eth"] = net_eth

    return result

# Q5 - 2 marks: graded on 2 hidden wallets, 1 mark per wallet where ALL Q5 checks pass.
def q5_activity_window(txs: List[Dict[str, Any]]) -> List[int]:
    """
    Q5: Over what block range was this address active?

    Parameters:
        txs - list from get_normal_transactions()

    Returns:
        [begin_block, end_block] - block numbers of the first and last txs
        (sorted chronologically by timeStamp), both ints. [] if txs is empty.

    Example output:
        [21895721, 21965191]
    """
    activity_window: List[int] = []

    if not txs:
        return activity_window

    sorted_txs = sorted(
        txs,
        key=lambda tx: (int(tx["timeStamp"]), int(tx["blockNumber"]))
    )
    first_block = int(sorted_txs[0]["blockNumber"])
    last_block = int(sorted_txs[-1]["blockNumber"])

    activity_window = [first_block, last_block]
    return activity_window


# Q6 - 3 marks: graded on 3 hidden wallets, 1 mark per wallet where ALL Q6 checks pass.
# (The dust/hub thresholds apply to the ETH transfers fetched in the block window.)
def q6_get_value_neighbors(address: str, start_block: int, end_block: int,
                           min_eth_value: float, max_node_tx_count: int) -> List[str]:
    """
    Q6 - neighbour-extraction callback used by bfs_n_hops (you do NOT write the BFS).

    Return the unique addresses that exchanged ETH with `address` in
    [start_block, end_block].

    Rules:
      - Fetch txs once with the given block range.
      - If the address has MORE than max_node_tx_count txs in the window, return
        [] (it is a hub - bfs_n_hops will not traverse into it). Use the same
        fetched list - do NOT make an extra API call to count.
      - Ignore transfers below min_eth_value ETH (this also drops value==0 txs).
      - Skip contract-creation txs (`to` empty/null). Exclude `address` itself.
      - Return lowercase addresses. Order does not matter.

    Parameters:
        address           - wallet to look up
        start_block       - inclusive lower block bound
        end_block         - inclusive upper block bound
        min_eth_value     - dust threshold in ETH
        max_node_tx_count - hub threshold (window tx count)

    Example output (test address, 20-block window):
        ["0x47666fab8bd0ac7003bce3f5c3585383f09486e2",
         "0xe8e8035dbb36a3faf41ecf8888de4032ac8203a3"]
    """
    params = {
        "module": "account",
        "action": "txlist",
        "chainid": 1,
        "address": address,
        "startblock": start_block,
        "endblock": end_block,
        "sort": "asc",
        "apikey": API_KEY,
    }

    data = _http_get_json(params)
    status = data.get("status")
    message = data.get("message")
    txs = data.get("result") or []

    if status == "0" and message == "No transactions found":
        return []
    if status != "1":
        print(f"[ERROR] Etherscan API error: status={status}, message={message}")
        return []

    if len(txs) > max_node_tx_count:
        return []

    a = _norm(address)
    neighbors: set[str] = set()

    for tx in txs:
        from_addr = str(tx.get("from") or "")
        to_addr = str(tx.get("to") or "")
        value_wei = int(tx.get("value", 0))

        if value_wei < min_eth_value * 1e18:
            continue
        if not to_addr:
            continue

        from_norm = _norm(from_addr)
        to_norm = _norm(to_addr)

        if from_norm == a and to_norm == a:
            continue

        if from_norm == a and to_norm != a:
            neighbors.add(to_norm)
        elif to_norm == a and from_norm != a:
            neighbors.add(from_norm)

    return sorted(neighbors)


# ── Runner + tester (pre-implemented, do not modify) ────────────────────────

def build_report(address):
    """Fetch txs, run all 6 question functions, save the JSON report."""
    print(f"[INFO] Fetching transactions for {address}...")
    txs = get_normal_transactions(address, API_KEY)
    print(f"[INFO] {len(txs)} transactions returned")

    # Exclude the address being tested from the known list so Q2 doesn't
    # compare the address against itself.
    known = {a for a in KNOWN_EXPLOITER_ADDRESSES if _norm(a) != _norm(address)}

    q5_result = q5_activity_window(txs)

    # Q6: 2-hop BFS over the wallet's fan-out. Anchor the window at the first block
    # where the wallet sends >= MIN_ETH_VALUE ETH (its first real outflow) - that is
    # where downstream laundering starts, not the inflow block. Thresholds come from
    # the module constants (MIN_ETH_VALUE, MAX_NODE_TX_COUNT, PUBLIC_SERVICE_ADDRESSES).
    bfs_start = _first_outflow_block(txs, address, MIN_ETH_VALUE)
    if bfs_start is not None:
        bfs_end = bfs_start + Q6_HOP2_WINDOW_BLOCKS
        print(f"[INFO] Running 2-hop BFS in blocks [{bfs_start}, {bfs_end}]...")
        q6_result = bfs_n_hops(address, q6_get_value_neighbors, bfs_start, bfs_end, hops=2)
        print(f"[INFO] BFS found {len(q6_result)} hop-2 wallets")
    else:
        q6_result = []

    report = {
        "address": address,
        "q1_bybit_inflow":      q1_bybit_inflow(txs, address, BYBIT_EXPLOITER_1),
        "q2_exploiter_network": q2_exploiter_network(txs, address, known),
        "q3_eth_outflows":      q3_eth_outflows(txs, address),
        "q4_net_flow":          q4_net_flow(txs, address),
        "q5_activity_window":   q5_result,
        "q6_bfs_n_hops":        q6_result,
    }
    save_json(report, f"bybit_tracer_{address[:10]}.json")
    return report


ALL_QUESTIONS = ("q1", "q2", "q3", "q4", "q5", "q6")


def grade(report, answer_key, visibility="public", graded_questions=ALL_QUESTIONS):
    """Compare report against answer_key, print verdict per check.

    Checks are grouped per question. A question PASSES on this wallet only if
    EVERY one of its checks passes (all-or-nothing - marks are awarded as
    1 mark per question per graded wallet).

    visibility="public" → on failure, print got and expected values.
    visibility="hidden" → print only PASS / WRONG / WRONG_TYPE (no values revealed).
    graded_questions   → which questions are checked on this wallet (the marker
                         grades q2/q3/q5 on 2 wallets and q1/q4/q6 on 3).

    Returns {question_name: bool} for the graded questions.
    """
    hide = (visibility == "hidden")

    def check(label, got, expected, tol=None):
        if got is None:
            verdict, ok = "WRONG_TYPE", False
        elif tol is not None:
            if not isinstance(got, (int, float)) or isinstance(got, bool):
                verdict, ok = "WRONG_TYPE", False
            else:
                ok = abs(got - expected) <= tol
                verdict = "PASS" if ok else "WRONG"
        else:
            if not isinstance(got, type(expected)):
                verdict, ok = "WRONG_TYPE", False
            else:
                ok = got == expected
                verdict = "PASS" if ok else "WRONG"

        if hide:
            print(f"  [{verdict:10}] {label}")
        elif ok:
            print(f"  [PASS]       {label}")
        else:
            print(f"  [{verdict:10}] {label}  got={got!r}  expected={expected!r}")
        return ok

    q1 = report.get("q1_bybit_inflow") or {}
    transfers = q1.get("transfers") or []
    t0 = transfers[0] if transfers else {}
    q2 = report.get("q2_exploiter_network")
    q3 = report.get("q3_eth_outflows")
    q4 = report.get("q4_net_flow") or {}
    q5 = report.get("q5_activity_window")
    q6 = report.get("q6_bfs_n_hops")

    # Q3/Q6 are order-independent: compare as sorted lists (set semantics)
    q3_sorted = sorted(_norm(a) for a in q3) if isinstance(q3, list) else None
    q6_sorted = sorted(_norm(a) for a in q6) if isinstance(q6, list) else None

    def q1_checks(ak):
        return [
            check("Q1  ETH from Exploiter 1",  q1.get("total_eth_received_from_exploiter1"), ak["total_eth_received_from_exploiter1"], tol=0.001),
            check("Q1  Transfer count",        len(transfers),                               ak["transfer_count"]),
            check("Q1  Arrival timestamp",     t0.get("timestamp"),                          ak["timestamp"]),
            check("Q1  Asset type",            t0.get("asset"),                              ak["asset"]),
        ]

    def q2_checks(ak):
        return [
            check("Q2  Other exploiter interactions", len(q2) if isinstance(q2, list) else None, ak["interaction_count"]),
        ]

    def q3_checks(ak):
        ak3_sorted = sorted(_norm(a) for a in ak["recipients"])
        return [
            check("Q3  Recipient count",       len(q3) if isinstance(q3, list) else None,   ak["recipient_count"]),
            check("Q3  Recipients match",      q3_sorted,                                    ak3_sorted),
        ]

    def q4_checks(ak):
        return [
            check("Q4  ETH in",                q4.get("eth_in"),                             ak["eth_in"],  tol=1.0),
            check("Q4  ETH out",               q4.get("eth_out"),                            ak["eth_out"], tol=1.0),
        ]

    def q5_checks(ak):
        return [
            check("Q5  Activity window",       q5,                                           ak["activity_window"]),
        ]

    def q6_checks(ak):
        ak6_sorted = sorted(_norm(a) for a in ak["hop2_wallets"])
        return [
            check("Q6  Hop-2 wallet count",    len(q6) if isinstance(q6, list) else None,   ak["hop2_count"]),
            check("Q6  Hop-2 wallets match",   q6_sorted,                                    ak6_sorted),
        ]

    checkers = {"q1": q1_checks, "q2": q2_checks, "q3": q3_checks,
                "q4": q4_checks, "q5": q5_checks, "q6": q6_checks}

    verdicts = {}
    for qname in ALL_QUESTIONS:
        if qname not in graded_questions:
            continue
        oks = checkers[qname](answer_key[qname])
        verdicts[qname] = all(oks)

    summary = "   ".join(f"{q.upper()} {'PASS' if ok else 'FAIL'}" for q, ok in verdicts.items())
    print(f"\n  Question verdicts: {summary}")
    print(f"  Questions passed: {sum(verdicts.values())}/{len(verdicts)}")
    return verdicts


def main():
    import os
    ak_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bybit_answer_key_student.json")
    if not os.path.exists(ak_path):
        print("[ERROR] bybit_answer_key_student.json not found - cannot grade.")
        return
    with open(ak_path) as f:
        all_keys = json.load(f)

    passed_cases = 0
    total_cases  = 0
    for entry in TEST_ADDRESSES:
        addr = entry["address"]
        vis  = entry["visibility"]

        print(f"\n{'=' * 60}")
        print(f"SELF-CHECK [{vis.upper()}]: {addr}")
        print(f"{'=' * 60}")

        report = build_report(addr)

        answer_key = all_keys.get(_norm(addr))
        if answer_key is None:
            print(f"[WARNING] No answer key entry for {addr} - skipping grading.")
            continue

        verdicts = grade(report, answer_key, visibility=vis)
        passed_cases += sum(verdicts.values())
        total_cases  += len(verdicts)

    print(f"\n{'=' * 60}")
    print(f"SELF-CHECK RESULT: {passed_cases}/{total_cases} question×wallet cases passed")
    print("Marking (marker-side, on HIDDEN wallets): 1 mark per question per hidden")
    print("wallet where EVERY check for that question passes. Q1/Q4/Q6 are graded on")
    print("3 hidden wallets (3 marks each); Q2/Q3/Q5 on 2 (2 marks each) → 15 marks.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

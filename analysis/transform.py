#!/usr/bin/env python3
"""
Transform raw .sca outputs into a wide-format CSV ready for plot_figures.py.

Pulls throughput/loss from the `scalar` table and delay from the `statistic`
table (endToEndDelay histogram stats). Adds derived columns:
  - scheme           : "Standard EDCA" / "QAD-EDCA"
  - hi_priority_ratio: (numVo + numVi) / (numVo+numVi+numBe+numBk)
  - jains_index      : Jain's fairness across 4 ACs (per run, by throughput)
"""

import argparse
import glob
import os
import re
import sqlite3
import sys

import numpy as np
import pandas as pd

SIM_TIME_S = 30.0
AC_ORDER = ["AC_VO", "AC_VI", "AC_BE", "AC_BK"]
SERVER_APP_AC = {0: "AC_VO", 1: "AC_VI", 2: "AC_BE", 3: "AC_BK"}
STA_PREFIX_AC = {"voSta": "AC_VO", "viSta": "AC_VI",
                 "beSta": "AC_BE", "bkSta": "AC_BK"}


def _run_attrs(con: sqlite3.Connection) -> dict:
    return dict(con.execute("SELECT attrName, attrValue FROM runAttr").fetchall())


def _server_rx(con: sqlite3.Connection) -> dict:
    """Per-AC received {count,bytes} at server.app[N]."""
    rx = {}
    rows = con.execute("""
        SELECT moduleName, scalarName, scalarValue FROM scalar
        WHERE moduleName LIKE 'EdcaFairnessNetwork.server.app[%]'
          AND scalarName IN ('packetReceived:count', 'packetReceived:sum(packetBytes)')
    """).fetchall()
    for mod, name, val in rows:
        m = re.search(r"app\[(\d+)\]", mod)
        if not m or int(m.group(1)) not in SERVER_APP_AC:
            continue
        ac = SERVER_APP_AC[int(m.group(1))]
        key = "count" if name.endswith(":count") else "bytes"
        rx.setdefault(ac, {"count": 0.0, "bytes": 0.0})[key] = val
    return rx


def _sta_tx(con: sqlite3.Connection) -> dict:
    """Per-AC sent {count,bytes} summed over the AC's stations."""
    tx = {}
    rows = con.execute("""
        SELECT moduleName, scalarName, scalarValue FROM scalar
        WHERE moduleName LIKE 'EdcaFairnessNetwork.%Sta[%].app[0]'
          AND scalarName IN ('packetSent:count', 'packetSent:sum(packetBytes)')
    """).fetchall()
    for mod, name, val in rows:
        m = re.search(r"(voSta|viSta|beSta|bkSta)\[", mod)
        if not m:
            continue
        ac = STA_PREFIX_AC[m.group(1)]
        key = "count" if name.endswith(":count") else "bytes"
        tx.setdefault(ac, {"count": 0.0, "bytes": 0.0})
        tx[ac][key] += val
    return tx


def _delay_stats(con: sqlite3.Connection) -> dict:
    """endToEndDelay histogram stats at server.app[N], converted to ms."""
    out = {}
    rows = con.execute("""
        SELECT moduleName, statCount, statMean, statStddev, statMin, statMax
        FROM statistic
        WHERE moduleName LIKE 'EdcaFairnessNetwork.server.app[%]'
          AND statName = 'endToEndDelay:histogram'
    """).fetchall()
    for mod, n, mn, sd, mi, mx in rows:
        m = re.search(r"app\[(\d+)\]", mod)
        if not m or int(m.group(1)) not in SERVER_APP_AC:
            continue
        out[SERVER_APP_AC[int(m.group(1))]] = {
            "delay_n": int(n),
            "avg_delay_ms": (mn or 0) * 1000,
            "delay_stddev_ms": (sd or 0) * 1000,
            "delay_min_ms": (mi or 0) * 1000,
            "delay_max_ms": (mx or 0) * 1000,
        }
    return out


def _parse_iter_vars(itv: str) -> dict:
    """Parse iterationvarsd string like 'numVo=1/numVi=1/numBe=4/numBk=4'."""
    out = {}
    for token in (itv or "").split("/"):
        if "=" in token:
            k, v = token.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _scheme_of(config: str) -> str:
    if config.startswith("QadEdca"):
        return "QAD-EDCA"
    if config.startswith("TunedStatic"):
        return "Tuned Static EDCA"
    if config.startswith("Baseline"):
        return "Standard EDCA"
    return config


def jains(values: np.ndarray) -> float:
    arr = values[values > 0]
    if arr.size == 0:
        return float("nan")
    return float(arr.sum() ** 2 / (arr.size * (arr ** 2).sum()))


def process_sca(sca_path: str) -> list[dict]:
    con = sqlite3.connect(sca_path)
    try:
        attrs = _run_attrs(con)
        rx = _server_rx(con)
        tx = _sta_tx(con)
        dly = _delay_stats(con)
    finally:
        con.close()

    config = attrs.get("configname", "")
    itv = attrs.get("iterationvarsd", "")
    rep = int(attrs.get("repetition", "0") or 0)
    iter_dict = _parse_iter_vars(itv)
    nvo, nvi, nbe, nbk = (int(iter_dict.get(k, "0") or 0)
                          for k in ("numVo", "numVi", "numBe", "numBk"))
    n_total = nvo + nvi + nbe + nbk
    hi_ratio = (nvo + nvi) / n_total if n_total else float("nan")

    rows = []
    for ac in AC_ORDER:
        tx_c = tx.get(ac, {}).get("count", 0.0)
        tx_b = tx.get(ac, {}).get("bytes", 0.0)
        rx_c = rx.get(ac, {}).get("count", 0.0)
        rx_b = rx.get(ac, {}).get("bytes", 0.0)
        loss = ((tx_c - rx_c) / tx_c * 100) if tx_c > 0 else 0.0
        throughput = rx_b * 8 / SIM_TIME_S / 1e6
        row = {
            "scheme": _scheme_of(config),
            "configName": config,
            "iterationVars": itv,
            "repetition": rep,
            "numVo": nvo, "numVi": nvi, "numBe": nbe, "numBk": nbk,
            "n_stations": n_total,
            "hi_priority_ratio": hi_ratio,
            "ac": ac,
            "sent_count": tx_c, "sent_bytes": tx_b,
            "received_count": rx_c, "received_bytes": rx_b,
            "throughput_mbps": throughput,
            "loss_rate_pct": loss,
        }
        row.update(dly.get(ac, {
            "delay_n": 0, "avg_delay_ms": 0.0, "delay_stddev_ms": 0.0,
            "delay_min_ms": 0.0, "delay_max_ms": 0.0,
        }))
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results_dir")
    p.add_argument("--out", default="metrics_per_ac.csv")
    args = p.parse_args()

    files = sorted(glob.glob(os.path.join(args.results_dir, "*.sca")))
    if not files:
        print(f"No .sca files in {args.results_dir}", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    for sca in files:
        all_rows.extend(process_sca(sca))
    df = pd.DataFrame(all_rows)

    # Jain's index per (config, iter, rep) across the 4 ACs' throughput
    jdf = (df.groupby(["configName", "iterationVars", "repetition"])
             .apply(lambda g: jains(g["throughput_mbps"].to_numpy()))
             .reset_index(name="jains_index"))
    df = df.merge(jdf, on=["configName", "iterationVars", "repetition"])
    df.to_csv(args.out, index=False)
    print(f"-> {args.out}: {len(df)} rows, {df['configName'].nunique()} configs")


if __name__ == "__main__":
    main()

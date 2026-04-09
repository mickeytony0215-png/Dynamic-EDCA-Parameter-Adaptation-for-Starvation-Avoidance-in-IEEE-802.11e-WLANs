#!/usr/bin/env python3
"""
Parse OMNeT++ simulation results (.sca and .vec files) for EDCA fairness analysis.

Usage:
    python parse_results.py <results_dir> [--output <output_csv>]
"""

import argparse
import glob
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

AC_MAP = {
    "vosta": "AC_VO", "vista": "AC_VI", "besta": "AC_BE", "bksta": "AC_BK",
    "voice": "AC_VO", "video": "AC_VI", "background": "AC_BK",
}


def _query_sqlite(db_path: str, query: str) -> pd.DataFrame:
    """Execute a SQL query against an OMNeT++ SQLite result file."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def parse_scalar_results(sca_file: str) -> pd.DataFrame:
    """Parse scalar results from an OMNeT++ .sca SQLite file."""
    return _query_sqlite(sca_file, """
        SELECT r.runId, r.runAttr AS configName,
               s.moduleName, s.scalarName, s.scalarValue
        FROM scalar s JOIN run r ON s.runId = r.runId
        WHERE s.scalarName LIKE '%throughput%'
           OR s.scalarName LIKE '%delay%'  OR s.scalarName LIKE '%jitter%'
           OR s.scalarName LIKE '%loss%'   OR s.scalarName LIKE '%packetSent%'
           OR s.scalarName LIKE '%packetReceived%' OR s.scalarName LIKE '%packetDrop%'
    """)


def parse_vec_for_timeseries(vec_file: str, signal_name: str) -> pd.DataFrame:
    """Parse vector results for time-series analysis."""
    return _query_sqlite(vec_file, f"""
        SELECT v.vectorName, v.moduleName, vd.simtimeRaw AS time, vd.value
        FROM vector v JOIN vectorData vd ON v.vectorId = vd.vectorId
        WHERE v.vectorName LIKE '%{signal_name}%'
        ORDER BY vd.simtimeRaw
    """)


def extract_ac(module_name: str) -> str:
    """Extract Access Category from module path."""
    lower = module_name.lower()
    for keyword, ac in AC_MAP.items():
        if keyword in lower:
            return ac
    return "AC_BE"


def compute_jains_fairness(throughputs: np.ndarray) -> float:
    """J = (sum x_i)^2 / (n * sum x_i^2). Returns 0 if empty."""
    n = len(throughputs)
    sq_sum = np.sum(throughputs ** 2)
    if n == 0 or sq_sum == 0:
        return 0.0
    return np.sum(throughputs) ** 2 / (n * sq_sum)


def summarize_results(results_dir: str) -> pd.DataFrame | None:
    """Parse all .sca files and return aggregated per-AC metrics."""
    frames = [df for f in glob.glob(os.path.join(results_dir, "*.sca"))
              if not (df := parse_scalar_results(f)).empty]
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)
    combined["ac"] = combined["moduleName"].apply(extract_ac)
    return combined.groupby(["runId", "ac", "scalarName"]).agg(
        mean_value=("scalarValue", "mean"),
        std_value=("scalarValue", "std"),
        count=("scalarValue", "count"),
    ).reset_index()


def main():
    parser = argparse.ArgumentParser(description="Parse EDCA simulation results")
    parser.add_argument("results_dir")
    parser.add_argument("--output", "-o", default="results_summary.csv")
    args = parser.parse_args()

    if not os.path.isdir(args.results_dir):
        print(f"Error: {args.results_dir} is not a directory")
        sys.exit(1)

    metrics = summarize_results(args.results_dir)
    if metrics is not None:
        metrics.to_csv(args.output, index=False)
        print(f"Results saved to {args.output}")
    else:
        print("No scalar results found.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""CLI wrapper around the ingestion job body.

Usage:
    uv run python scripts/ingest_bondlens.py 0002110410
"""

from __future__ import annotations

import sys

from vichara_portfolio.bondlens.ingestion_job import run_ingestion_job


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: ingest_bondlens.py <CIK>", file=sys.stderr)
        raise SystemExit(2)

    cik = sys.argv[1]
    result = run_ingestion_job(cik)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

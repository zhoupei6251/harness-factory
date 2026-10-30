#!/usr/bin/env python3
"""Small CLI over the pinned UI UX Pro Max engine; no downloads or file writes."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "upstream/uiux/scripts"))
from core import AVAILABLE_STACKS, CSV_CONFIG, search, search_stack

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("query", help="English UI/UX keywords")
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--domain", choices=list(CSV_CONFIG))
mode.add_argument("--stack", choices=AVAILABLE_STACKS)
parser.add_argument("--max-results", type=int, choices=range(1, 21), default=3)
args = parser.parse_args()
if not args.query.strip():
    parser.error("query must not be empty")

result = (search_stack(args.query, args.stack, args.max_results) if args.stack
          else search(args.query, args.domain, args.max_results))
if "error" in result:
    print(result["error"], file=sys.stderr)
    sys.exit(1)
print(json.dumps(result, ensure_ascii=True))
if not result["count"]:
    print("No matches; refine the query before using general guidance.", file=sys.stderr)

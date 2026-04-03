#!/usr/bin/env python3
"""Read-only function tester for a deployed GenLayer intelligent contract.

Usage:
    python scripts/test_read_functions.py \
      --contract 0x... \
      --endpoint https://studio.genlayer.com/api \
      --sample-address 0x...
"""

from __future__ import annotations

import argparse
import collections.abc
import json
import sys
from typing import Any

# genlayer-py currently targets Python >=3.12 where collections.abc.Buffer exists.
# In Python 3.10/3.11 environments, this shim allows import to proceed.
if not hasattr(collections.abc, "Buffer"):
    collections.abc.Buffer = bytes  # type: ignore[attr-defined]

from genlayer_py import create_client  # noqa: E402


DEFAULT_ENDPOINT = "https://studio.genlayer.com/api"
DEFAULT_CONTRACT = "0x089BAD15ABF412083A51badc891Da97c3583cdA5"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call every read-only method discovered from contract schema."
    )
    parser.add_argument("--contract", default=DEFAULT_CONTRACT, help="Contract address")
    parser.add_argument(
        "--endpoint", default=DEFAULT_ENDPOINT, help="GenLayer RPC endpoint URL"
    )
    parser.add_argument(
        "--sample-address",
        default=ZERO_ADDRESS,
        help="Address used as placeholder for address/string method params",
    )
    parser.add_argument(
        "--raw-return",
        action="store_true",
        help="Pass raw_return=True to read_contract",
    )
    return parser.parse_args()


def build_method_args(method_name: str, params: list[list[str]], sample_address: str) -> list[Any]:
    args: list[Any] = []
    for param_name, param_type in params:
        lowered_name = param_name.lower()
        lowered_type = str(param_type).lower()

        if "address" in lowered_name or "address" in lowered_type:
            args.append(sample_address)
        elif lowered_type in {"int", "u256", "u64", "u32", "u16", "u8"}:
            args.append(0)
        elif lowered_type == "bool":
            args.append(False)
        elif lowered_type in {"list", "array", "dynarray"}:
            args.append([])
        else:
            # Most schemas expose strings for IDs and addresses; sample address is a good
            # placeholder for address-like names, empty string otherwise.
            args.append(sample_address if "player" in lowered_name else "")

    if method_name == "get_player_points" and len(args) == 1:
        args[0] = sample_address

    return args


def main() -> int:
    args = parse_args()

    print(f"Connecting to endpoint: {args.endpoint}")
    print(f"Contract: {args.contract}")

    try:
        client = create_client(endpoint=args.endpoint)
        schema = client.get_contract_schema(address=args.contract)
    except Exception as exc:  # noqa: BLE001
        print("❌ Could not connect to GenLayer endpoint or fetch schema.")
        print(f"Reason: {exc}")
        print("Tip: try a reachable endpoint, e.g. local Studio http://127.0.0.1:4000/api")
        return 2

    methods: dict[str, dict[str, Any]] = schema.get("methods", {})
    readonly_methods = {
        name: meta
        for name, meta in methods.items()
        if isinstance(meta, dict) and meta.get("readonly") is True
    }

    if not readonly_methods:
        print("No read-only methods found in schema.")
        return 0

    print(f"Found {len(readonly_methods)} read-only method(s): {', '.join(readonly_methods)}")

    results: dict[str, Any] = {}
    failures: dict[str, str] = {}

    for method_name, meta in readonly_methods.items():
        method_args = build_method_args(
            method_name=method_name,
            params=meta.get("params", []),
            sample_address=args.sample_address,
        )
        print(f"\n→ Calling {method_name}({method_args})")

        try:
            value = client.read_contract(
                address=args.contract,
                function_name=method_name,
                args=method_args,
                raw_return=args.raw_return,
            )
            results[method_name] = value
            print(f"✅ {method_name} returned: {json.dumps(value, default=str)[:800]}")
        except Exception as exc:  # noqa: BLE001
            failures[method_name] = str(exc)
            print(f"❌ {method_name} failed: {exc}")

    print("\n=== Summary ===")
    print(f"Successful calls: {len(results)}")
    print(f"Failed calls: {len(failures)}")

    if results:
        print("\nResults JSON:")
        print(json.dumps(results, indent=2, default=str))

    if failures:
        print("\nFailures:")
        print(json.dumps(failures, indent=2))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

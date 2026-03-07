#!/usr/bin/env python3
"""
Query Bitcoin Core RPC for fee estimates and mempool info.

Connects to a local Bitcoin Core node via JSON-RPC. Requires a running
bitcoind with RPC enabled.

Configuration:
    Set RPC_USER, RPC_PASSWORD, RPC_HOST, RPC_PORT via environment variables
    or modify the defaults below. Alternatively, point COOKIE_FILE to your
    .cookie file for cookie-based authentication.

Usage:
    python fee-estimate.py
    RPC_PORT=18443 python fee-estimate.py  # regtest
"""

import json
import os
import sys
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RPC_HOST = os.environ.get("RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.environ.get("RPC_PORT", "8332"))
RPC_USER = os.environ.get("RPC_USER", "")
RPC_PASSWORD = os.environ.get("RPC_PASSWORD", "")

# Cookie file path (auto-detected if RPC_USER is empty)
# Default locations by network:
#   mainnet: ~/.bitcoin/.cookie
#   testnet: ~/.bitcoin/testnet3/.cookie
#   regtest: ~/.bitcoin/regtest/.cookie
COOKIE_FILE = os.environ.get("COOKIE_FILE", "")


def get_auth() -> tuple:
    """Get RPC authentication credentials."""
    if RPC_USER and RPC_PASSWORD:
        return RPC_USER, RPC_PASSWORD

    # Try cookie file
    cookie_paths = [
        COOKIE_FILE,
        os.path.expanduser("~/.bitcoin/.cookie"),
        os.path.expanduser("~/.bitcoin/regtest/.cookie"),
        os.path.expanduser("~/.bitcoin/testnet3/.cookie"),
        os.path.expanduser("~/.bitcoin/signet/.cookie"),
    ]

    for path in cookie_paths:
        if path and os.path.exists(path):
            with open(path, "r") as f:
                cookie = f.read().strip()
            user, password = cookie.split(":")
            return user, password

    print("ERROR: No RPC credentials found.")
    print("Set RPC_USER and RPC_PASSWORD environment variables,")
    print("or ensure Bitcoin Core is running with a .cookie file.")
    sys.exit(1)


def rpc_call(method: str, params: list = None) -> dict:
    """Make a JSON-RPC call to Bitcoin Core."""
    if params is None:
        params = []

    user, password = get_auth()
    url = f"http://{RPC_HOST}:{RPC_PORT}/"

    payload = json.dumps({
        "jsonrpc": "1.0",
        "id": "fee-estimate",
        "method": method,
        "params": params,
    }).encode()

    # Build request with Basic auth
    import base64
    auth_string = base64.b64encode(f"{user}:{password}".encode()).decode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "text/plain",
            "Authorization": f"Basic {auth_string}",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot connect to Bitcoin Core at {url}")
        print(f"  {e}")
        print("\nMake sure bitcoind is running with RPC enabled.")
        sys.exit(1)

    if result.get("error"):
        raise RuntimeError(f"RPC error: {result['error']}")

    return result["result"]


def format_btc_per_kvb_to_sat_per_vb(btc_per_kvb: float) -> float:
    """Convert BTC/kvB to sat/vB."""
    # BTC/kvB * 100,000,000 sats/BTC / 1,000 vB/kvB = sats * 100,000 / kvB
    return btc_per_kvb * 100_000


def main():
    print("=" * 60)
    print("BITCOIN FEE ESTIMATION")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # Blockchain info
    # -----------------------------------------------------------------------
    info = rpc_call("getblockchaininfo")
    print(f"\nChain:    {info['chain']}")
    print(f"Height:   {info['blocks']}")
    print(f"IBD:      {'Yes (SYNCING)' if info['initialblockdownload'] else 'No (synced)'}")

    # -----------------------------------------------------------------------
    # Mempool info
    # -----------------------------------------------------------------------
    mempool = rpc_call("getmempoolinfo")

    print(f"\n--- Mempool ---")
    print(f"Transactions:  {mempool['size']:,}")
    print(f"Size:          {mempool['bytes'] / 1_000_000:.2f} MB")
    print(f"Memory usage:  {mempool['usage'] / 1_000_000:.2f} MB")
    print(f"Max mempool:   {mempool['maxmempool'] / 1_000_000:.0f} MB")
    print(f"Min fee:       {format_btc_per_kvb_to_sat_per_vb(mempool['mempoolminfee']):.1f} sat/vB")
    print(f"Min relay fee: {format_btc_per_kvb_to_sat_per_vb(mempool['minrelaytxfee']):.1f} sat/vB")

    if mempool.get("fullrbf") is not None:
        print(f"Full RBF:      {'Enabled' if mempool['fullrbf'] else 'Disabled'}")

    # -----------------------------------------------------------------------
    # Fee estimates for different confirmation targets
    # -----------------------------------------------------------------------
    print(f"\n--- Fee Estimates ---")
    print(f"{'Target':>10s}  {'Rate (sat/vB)':>15s}  {'P2WPKH 1-in-2-out':>20s}  {'P2TR 1-in-2-out':>18s}")
    print("-" * 70)

    targets = [1, 2, 3, 6, 12, 24, 144, 504, 1008]

    estimates = {}
    for target in targets:
        result = rpc_call("estimatesmartfee", [target])

        if "feerate" in result:
            sat_per_vb = format_btc_per_kvb_to_sat_per_vb(result["feerate"])
            estimates[target] = sat_per_vb

            # Estimate fees for common transaction types
            p2wpkh_fee = int(sat_per_vb * 141)   # ~141 vB for 1-in-2-out P2WPKH
            p2tr_fee = int(sat_per_vb * 112)      # ~112 vB for 1-in-2-out P2TR

            target_label = f"{target} block{'s' if target > 1 else ''}"
            print(f"{target_label:>10s}  {sat_per_vb:>12.1f}     {p2wpkh_fee:>15,} sats    {p2tr_fee:>13,} sats")
        else:
            target_label = f"{target} block{'s' if target > 1 else ''}"
            errors = result.get("errors", ["insufficient data"])
            print(f"{target_label:>10s}  {'N/A':>15s}  ({errors[0]})")

    # -----------------------------------------------------------------------
    # Recommendation
    # -----------------------------------------------------------------------
    print(f"\n--- Recommendation ---")

    if not estimates:
        print("Insufficient data for fee estimation.")
        print("This is normal if the node just started or is on regtest.")
        return

    next_block = estimates.get(1, estimates.get(2, 0))
    medium = estimates.get(6, estimates.get(12, 0))
    economy = estimates.get(144, estimates.get(1008, 0))

    congestion = "unknown"
    if mempool["size"] < 5_000:
        congestion = "LOW (mempool nearly empty)"
    elif mempool["size"] < 20_000:
        congestion = "MODERATE"
    elif mempool["size"] < 50_000:
        congestion = "HIGH"
    else:
        congestion = "VERY HIGH (consider waiting)"

    print(f"Mempool congestion: {congestion}")
    print()

    if next_block and medium:
        savings_pct = ((next_block - medium) / next_block * 100) if next_block > 0 else 0
        print(f"  Next-block rate:  {next_block:.1f} sat/vB")
        print(f"  ~6 block rate:    {medium:.1f} sat/vB (save {savings_pct:.0f}%)")
        if economy:
            print(f"  Economy rate:     {economy:.1f} sat/vB")
        print()

        if savings_pct > 50:
            print("  TIP: Large gap between next-block and medium priority.")
            print("  If your transaction is not urgent, use the medium rate to save significantly.")
        elif mempool["size"] < 5_000:
            print("  TIP: Mempool is nearly empty. Even the minimum relay fee may confirm quickly.")


if __name__ == "__main__":
    main()

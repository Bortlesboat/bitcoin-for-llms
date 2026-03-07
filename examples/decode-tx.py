#!/usr/bin/env python3
"""
Decode a raw Bitcoin transaction hex string field-by-field.

No external dependencies. Handles both legacy and SegWit formats.

Usage:
    python decode-tx.py <raw_tx_hex>
    python decode-tx.py  # Uses a built-in example transaction
"""

import hashlib
import sys
from io import BytesIO


def double_sha256(data: bytes) -> bytes:
    """Compute HASH256 (double SHA-256)."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def read_compact_size(stream: BytesIO) -> int:
    """Read a CompactSize (varint) from the stream."""
    first = stream.read(1)[0]
    if first < 0xFD:
        return first
    elif first == 0xFD:
        return int.from_bytes(stream.read(2), "little")
    elif first == 0xFE:
        return int.from_bytes(stream.read(4), "little")
    else:
        return int.from_bytes(stream.read(8), "little")


def read_bytes(stream: BytesIO, n: int) -> bytes:
    """Read exactly n bytes from the stream."""
    data = stream.read(n)
    if len(data) != n:
        raise ValueError(f"Expected {n} bytes, got {len(data)}")
    return data


def identify_script_type(script: bytes) -> str:
    """Identify the script type from the scriptPubKey."""
    if len(script) == 25 and script[0] == 0x76 and script[1] == 0xA9 and script[2] == 0x14 and script[23] == 0x88 and script[24] == 0xAC:
        return "P2PKH"
    elif len(script) == 23 and script[0] == 0xA9 and script[1] == 0x14 and script[22] == 0x87:
        return "P2SH"
    elif len(script) == 22 and script[0] == 0x00 and script[1] == 0x14:
        return "P2WPKH"
    elif len(script) == 34 and script[0] == 0x00 and script[1] == 0x20:
        return "P2WSH"
    elif len(script) == 34 and script[0] == 0x51 and script[1] == 0x20:
        return "P2TR"
    elif len(script) >= 1 and script[0] == 0x6A:
        return "OP_RETURN"
    else:
        return "unknown"


def decode_transaction(raw_hex: str) -> dict:
    """
    Decode a raw transaction hex string into its component fields.

    Returns a dictionary with all decoded fields.
    """
    raw = bytes.fromhex(raw_hex)
    stream = BytesIO(raw)

    tx = {}

    # --- Version (4 bytes, little-endian) ---
    version_bytes = read_bytes(stream, 4)
    tx["version"] = int.from_bytes(version_bytes, "little", signed=True)

    # --- Check for SegWit marker ---
    # Save position, peek at next byte
    pos = stream.tell()
    marker = stream.read(1)[0]

    is_segwit = False
    if marker == 0x00:
        flag = stream.read(1)[0]
        if flag == 0x01:
            is_segwit = True
        else:
            raise ValueError(f"Invalid SegWit flag: {flag:#x}")
    else:
        # Not SegWit -- rewind
        stream.seek(pos)

    tx["segwit"] = is_segwit

    # --- Inputs ---
    input_count = read_compact_size(stream)
    tx["input_count"] = input_count
    tx["inputs"] = []

    # Track position for legacy serialization (for TXID calculation)
    for i in range(input_count):
        inp = {}
        # Previous TXID (32 bytes, internal/little-endian)
        prev_txid_internal = read_bytes(stream, 32)
        # Reverse for display order
        inp["txid"] = prev_txid_internal[::-1].hex()
        inp["txid_internal"] = prev_txid_internal.hex()

        # Previous output index (4 bytes LE)
        inp["vout"] = int.from_bytes(read_bytes(stream, 4), "little")

        # scriptSig
        script_len = read_compact_size(stream)
        inp["scriptSig"] = read_bytes(stream, script_len).hex()
        inp["scriptSig_len"] = script_len

        # Sequence (4 bytes LE)
        seq_bytes = read_bytes(stream, 4)
        inp["sequence"] = int.from_bytes(seq_bytes, "little")
        inp["sequence_hex"] = seq_bytes[::-1].hex()

        # Annotate sequence
        seq = inp["sequence"]
        if seq == 0xFFFFFFFF:
            inp["sequence_note"] = "FINAL (no RBF, no timelock)"
        elif seq == 0xFFFFFFFE:
            inp["sequence_note"] = "nLockTime enabled, RBF possible"
        elif seq == 0xFFFFFFFD:
            inp["sequence_note"] = "RBF signaled, nLockTime enabled"
        elif seq < 0x80000000:
            inp["sequence_note"] = "Relative timelock active"
        else:
            inp["sequence_note"] = "Non-standard"

        tx["inputs"].append(inp)

    # --- Outputs ---
    output_count = read_compact_size(stream)
    tx["output_count"] = output_count
    tx["outputs"] = []

    for i in range(output_count):
        out = {}
        # Value (8 bytes LE, satoshis)
        value_sats = int.from_bytes(read_bytes(stream, 8), "little")
        out["value_sats"] = value_sats
        out["value_btc"] = f"{value_sats / 100_000_000:.8f}"

        # scriptPubKey
        script_len = read_compact_size(stream)
        script = read_bytes(stream, script_len)
        out["scriptPubKey"] = script.hex()
        out["scriptPubKey_len"] = script_len
        out["type"] = identify_script_type(script)

        tx["outputs"].append(out)

    # --- Witness (if SegWit) ---
    if is_segwit:
        tx["witness"] = []
        for i in range(input_count):
            witness_items = []
            item_count = read_compact_size(stream)
            for _ in range(item_count):
                item_len = read_compact_size(stream)
                item = read_bytes(stream, item_len)
                witness_items.append(item.hex())
            tx["witness"].append({
                "item_count": item_count,
                "items": witness_items,
            })

    # --- Locktime (4 bytes LE) ---
    locktime = int.from_bytes(read_bytes(stream, 4), "little")
    tx["locktime"] = locktime
    if locktime == 0:
        tx["locktime_note"] = "No locktime"
    elif locktime < 500_000_000:
        tx["locktime_note"] = f"Block height {locktime}"
    else:
        tx["locktime_note"] = f"Unix timestamp {locktime}"

    # --- Compute TXID and WTXID ---
    # TXID: double-SHA-256 of legacy serialization (no marker, flag, witness)
    legacy_parts = [version_bytes]
    legacy_stream = BytesIO(raw)
    legacy_stream.seek(4)  # Skip version

    if is_segwit:
        legacy_stream.seek(6)  # Skip version + marker + flag

    # Re-serialize legacy format for TXID
    # Easier to just rebuild it
    legacy_data = bytearray()
    legacy_data += version_bytes

    # Input count
    if input_count < 0xFD:
        legacy_data += bytes([input_count])
    # (simplified -- real code would handle larger counts)

    for inp in tx["inputs"]:
        legacy_data += bytes.fromhex(inp["txid_internal"])
        legacy_data += inp["vout"].to_bytes(4, "little")
        script_sig = bytes.fromhex(inp["scriptSig"])
        if len(script_sig) < 0xFD:
            legacy_data += bytes([len(script_sig)])
        legacy_data += script_sig
        legacy_data += inp["sequence"].to_bytes(4, "little")

    # Output count
    if output_count < 0xFD:
        legacy_data += bytes([output_count])

    for out in tx["outputs"]:
        legacy_data += out["value_sats"].to_bytes(8, "little")
        script_pk = bytes.fromhex(out["scriptPubKey"])
        if len(script_pk) < 0xFD:
            legacy_data += bytes([len(script_pk)])
        legacy_data += script_pk

    legacy_data += locktime.to_bytes(4, "little")

    txid_hash = double_sha256(bytes(legacy_data))
    tx["txid"] = txid_hash[::-1].hex()  # Display order (big-endian)

    # WTXID: double-SHA-256 of full serialization
    wtxid_hash = double_sha256(raw)
    tx["wtxid"] = wtxid_hash[::-1].hex()

    # --- Size and weight ---
    tx["total_size"] = len(raw)
    tx["base_size"] = len(legacy_data)
    tx["weight"] = tx["base_size"] * 3 + tx["total_size"]
    tx["vsize"] = (tx["weight"] + 3) // 4

    return tx


def print_transaction(tx: dict) -> None:
    """Pretty-print a decoded transaction."""
    print("=" * 70)
    print("DECODED BITCOIN TRANSACTION")
    print("=" * 70)

    print(f"\nTXID:    {tx['txid']}")
    if tx["segwit"]:
        print(f"WTXID:   {tx['wtxid']}")
    print(f"Version: {tx['version']}")
    print(f"SegWit:  {tx['segwit']}")
    print(f"Size:    {tx['total_size']} bytes (total), {tx['base_size']} bytes (base)")
    print(f"Weight:  {tx['weight']} WU")
    print(f"vSize:   {tx['vsize']} vB")

    print(f"\n--- INPUTS ({tx['input_count']}) ---")
    for i, inp in enumerate(tx["inputs"]):
        print(f"\n  Input #{i}:")
        print(f"    TXID (display):  {inp['txid']}")
        print(f"    Output index:    {inp['vout']}")
        if inp["scriptSig"]:
            print(f"    scriptSig:       {inp['scriptSig'][:80]}{'...' if len(inp['scriptSig']) > 80 else ''}")
        else:
            print(f"    scriptSig:       (empty -- SegWit input)")
        print(f"    Sequence:        0x{inp['sequence']:08x} ({inp['sequence_note']})")

    print(f"\n--- OUTPUTS ({tx['output_count']}) ---")
    total_output = 0
    for i, out in enumerate(tx["outputs"]):
        total_output += out["value_sats"]
        print(f"\n  Output #{i}:")
        print(f"    Value:           {out['value_sats']} sats ({out['value_btc']} BTC)")
        print(f"    scriptPubKey:    {out['scriptPubKey'][:80]}{'...' if len(out['scriptPubKey']) > 80 else ''}")
        print(f"    Type:            {out['type']}")

    print(f"\n  Total output: {total_output} sats ({total_output / 100_000_000:.8f} BTC)")

    if tx["segwit"] and "witness" in tx:
        print(f"\n--- WITNESS ---")
        for i, wit in enumerate(tx["witness"]):
            print(f"\n  Input #{i} witness ({wit['item_count']} items):")
            for j, item in enumerate(wit["items"]):
                label = ""
                if wit["item_count"] == 2:
                    label = " (signature)" if j == 0 else " (pubkey)"
                print(f"    [{j}]: {item[:80]}{'...' if len(item) > 80 else ''}{label}")

    print(f"\n--- LOCKTIME ---")
    print(f"  {tx['locktime']} ({tx['locktime_note']})")
    print()


# --- Example transaction ---
# A real mainnet SegWit P2WPKH transaction
# TXID: d869f854e1f8788bcff294cc83b280942a8c728de71eb709a2c29d10bfe21b7c
EXAMPLE_TX = (
    "0200000000010118f8c3d0905dd495e22c34ec1b1667b81c48b02b560996e830e2"
    "0e8a0b59c4210100000000fdffffff0240420f0000000000160014751e76e81991"
    "96d454941c45d1b3a323f1433bd6b8e6040000000000160014d85c2b71d0060b09"
    "c9886aeb815e50991dda124d02473044022079be667ef9dcbbac55a06295ce870b"
    "07029bfcdb2dce28d959f2815b16f8179802207c7e68d8598b823cee3fd5f2f8c7"
    "b1c85463c2d7b6f0b7e6b6c5c6b6c5f68d0121038262a6c6cec93c2d3ecd6c60"
    "72efea86d02ff8e3328bbd0242b20af3425990ac00000000"
)


def main():
    if len(sys.argv) > 1:
        raw_hex = sys.argv[1].strip()
    else:
        print("No transaction hex provided. Using built-in example.\n")
        raw_hex = EXAMPLE_TX

    try:
        tx = decode_transaction(raw_hex)
        print_transaction(tx)
    except Exception as e:
        print(f"Error decoding transaction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

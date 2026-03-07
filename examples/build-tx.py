#!/usr/bin/env python3
"""
Construct a P2WPKH (SegWit v0) transaction from scratch.

No external dependencies. Demonstrates the complete transaction structure
with correct byte ordering, witness serialization, and CompactSize encoding.

This script builds a transaction with placeholder values to show the exact
byte-level structure. Replace the placeholder keys and UTXOs with real values
for actual use.

Usage:
    python build-tx.py
"""

import hashlib
import struct


def double_sha256(data: bytes) -> bytes:
    """HASH256: SHA-256 applied twice."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data: bytes) -> bytes:
    """HASH160: SHA-256 then RIPEMD-160."""
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def compact_size(n: int) -> bytes:
    """Encode an integer as a CompactSize (varint)."""
    if n < 0xFD:
        return struct.pack("<B", n)
    elif n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    elif n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    else:
        return b"\xff" + struct.pack("<Q", n)


def build_p2wpkh_scriptpubkey(pubkey_hash: bytes) -> bytes:
    """
    Build a P2WPKH scriptPubKey: OP_0 <20-byte-hash>

    Hex: 0014{hash160}
    """
    assert len(pubkey_hash) == 20, "P2WPKH requires a 20-byte pubkey hash"
    return b"\x00\x14" + pubkey_hash


def build_p2wpkh_transaction(
    prev_txid_display: str,
    prev_vout: int,
    input_value_sats: int,
    recipient_pubkey_hash: bytes,
    send_value_sats: int,
    change_pubkey_hash: bytes,
    fee_sats: int,
    signature_der: bytes,
    pubkey_compressed: bytes,
    locktime: int = 0,
) -> dict:
    """
    Build a complete P2WPKH 1-input, 2-output SegWit transaction.

    Returns a dict with the full serialization, legacy serialization, TXID, etc.
    """
    # -------------------------------------------------------------------------
    # Calculate change
    # -------------------------------------------------------------------------
    change_sats = input_value_sats - send_value_sats - fee_sats
    assert change_sats >= 0, f"Insufficient funds: need {send_value_sats + fee_sats}, have {input_value_sats}"
    if change_sats > 0 and change_sats < 294:
        print(f"WARNING: Change output ({change_sats} sats) is below dust limit. Adding to fee.")
        fee_sats += change_sats
        change_sats = 0

    # -------------------------------------------------------------------------
    # Version (4 bytes, int32_t LE)
    # -------------------------------------------------------------------------
    # Version 2 enables BIP68 relative timelocks
    version = struct.pack("<i", 2)

    # -------------------------------------------------------------------------
    # Inputs
    # -------------------------------------------------------------------------
    # CRITICAL: Reverse the display TXID to get internal byte order
    prev_txid_internal = bytes.fromhex(prev_txid_display)[::-1]
    assert len(prev_txid_internal) == 32

    vout = struct.pack("<I", prev_vout)

    # For P2WPKH, scriptSig is empty (all signing data goes in witness)
    scriptsig = b""
    scriptsig_len = compact_size(len(scriptsig))

    # Sequence: 0xfffffffd signals RBF, enables nLockTime, no relative timelock
    sequence = struct.pack("<I", 0xFFFFFFFD)

    input_count = compact_size(1)
    raw_input = prev_txid_internal + vout + scriptsig_len + scriptsig + sequence

    # -------------------------------------------------------------------------
    # Outputs
    # -------------------------------------------------------------------------
    outputs = []

    # Output 0: Payment to recipient
    recipient_script = build_p2wpkh_scriptpubkey(recipient_pubkey_hash)
    out_0 = struct.pack("<q", send_value_sats) + compact_size(len(recipient_script)) + recipient_script
    outputs.append(out_0)

    # Output 1: Change back to sender (if above dust)
    if change_sats > 0:
        change_script = build_p2wpkh_scriptpubkey(change_pubkey_hash)
        out_1 = struct.pack("<q", change_sats) + compact_size(len(change_script)) + change_script
        outputs.append(out_1)

    output_count = compact_size(len(outputs))
    raw_outputs = b"".join(outputs)

    # -------------------------------------------------------------------------
    # Witness
    # -------------------------------------------------------------------------
    # P2WPKH witness has exactly 2 items: signature and pubkey
    # Signature must include the sighash byte appended (SIGHASH_ALL = 0x01)
    sig_with_sighash = signature_der + b"\x01"

    witness = (
        compact_size(2)  # 2 witness items
        + compact_size(len(sig_with_sighash)) + sig_with_sighash
        + compact_size(len(pubkey_compressed)) + pubkey_compressed
    )

    # -------------------------------------------------------------------------
    # Locktime (4 bytes, uint32_t LE)
    # -------------------------------------------------------------------------
    locktime_bytes = struct.pack("<I", locktime)

    # -------------------------------------------------------------------------
    # Full SegWit serialization
    # -------------------------------------------------------------------------
    # version + marker(0x00) + flag(0x01) + inputs + outputs + witness + locktime
    marker_flag = b"\x00\x01"

    full_tx = (
        version
        + marker_flag
        + input_count + raw_input
        + output_count + raw_outputs
        + witness
        + locktime_bytes
    )

    # -------------------------------------------------------------------------
    # Legacy serialization (for TXID -- no marker, flag, or witness)
    # -------------------------------------------------------------------------
    legacy_tx = (
        version
        + input_count + raw_input
        + output_count + raw_outputs
        + locktime_bytes
    )

    # -------------------------------------------------------------------------
    # Compute TXID and WTXID
    # -------------------------------------------------------------------------
    txid_internal = double_sha256(legacy_tx)
    txid_display = txid_internal[::-1].hex()

    wtxid_internal = double_sha256(full_tx)
    wtxid_display = wtxid_internal[::-1].hex()

    # -------------------------------------------------------------------------
    # Weight and vsize
    # -------------------------------------------------------------------------
    base_size = len(legacy_tx)
    total_size = len(full_tx)
    weight = base_size * 3 + total_size
    vsize = (weight + 3) // 4

    return {
        "hex": full_tx.hex(),
        "legacy_hex": legacy_tx.hex(),
        "txid": txid_display,
        "wtxid": wtxid_display,
        "base_size": base_size,
        "total_size": total_size,
        "weight": weight,
        "vsize": vsize,
        "fee_sats": fee_sats,
        "fee_rate_sat_per_vb": round(fee_sats / vsize, 2),
        "send_value_sats": send_value_sats,
        "change_sats": change_sats,
    }


def main():
    print("=" * 70)
    print("BUILD P2WPKH TRANSACTION FROM SCRATCH")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Placeholder values (replace with real data for actual use)
    # -------------------------------------------------------------------------

    # The UTXO we're spending (as displayed on a block explorer)
    prev_txid_display = "7b1eabe0209b1fe794124575ef807057c77ada2138ae4fa8d6c4de0398a14f3f"
    prev_vout = 0
    input_value_sats = 100_000  # 0.001 BTC

    # Recipient: hash160 of recipient's compressed public key
    # (This is the 20-byte hash inside a bc1q... address)
    recipient_pubkey_hash = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")

    # Change address: hash160 of our change public key
    change_pubkey_hash = bytes.fromhex("d85c2b71d0060b09c9886aeb815e50991dda124d")

    # Payment amount
    send_value_sats = 50_000  # 0.0005 BTC

    # Fee
    fee_sats = 1_000  # ~11 sat/vB for a typical P2WPKH 1-in-2-out tx

    # Placeholder signature (71 bytes DER-encoded -- in real use, this comes
    # from signing the BIP143 sighash with the private key)
    signature_der = bytes(71)  # Placeholder -- all zeros

    # Placeholder compressed public key (33 bytes, starts with 02 or 03)
    pubkey_compressed = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )

    # -------------------------------------------------------------------------
    # Build the transaction
    # -------------------------------------------------------------------------
    tx = build_p2wpkh_transaction(
        prev_txid_display=prev_txid_display,
        prev_vout=prev_vout,
        input_value_sats=input_value_sats,
        recipient_pubkey_hash=recipient_pubkey_hash,
        send_value_sats=send_value_sats,
        change_pubkey_hash=change_pubkey_hash,
        fee_sats=fee_sats,
        signature_der=signature_der,
        pubkey_compressed=pubkey_compressed,
    )

    # -------------------------------------------------------------------------
    # Print results
    # -------------------------------------------------------------------------
    print(f"\nTXID:           {tx['txid']}")
    print(f"WTXID:          {tx['wtxid']}")
    print(f"Base size:      {tx['base_size']} bytes")
    print(f"Total size:     {tx['total_size']} bytes")
    print(f"Weight:         {tx['weight']} WU")
    print(f"Virtual size:   {tx['vsize']} vB")
    print(f"Fee:            {tx['fee_sats']} sats ({tx['fee_rate_sat_per_vb']} sat/vB)")
    print(f"Send:           {tx['send_value_sats']} sats")
    print(f"Change:         {tx['change_sats']} sats")

    print(f"\nRaw SegWit hex ({len(tx['hex']) // 2} bytes):")
    # Print in chunks for readability
    hex_str = tx["hex"]
    for i in range(0, len(hex_str), 80):
        print(f"  {hex_str[i:i+80]}")

    print(f"\nLegacy hex ({len(tx['legacy_hex']) // 2} bytes):")
    hex_str = tx["legacy_hex"]
    for i in range(0, len(hex_str), 80):
        print(f"  {hex_str[i:i+80]}")

    # -------------------------------------------------------------------------
    # Annotated byte breakdown
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("BYTE-BY-BYTE BREAKDOWN")
    print("=" * 70)

    print("""
    02000000              version (2, little-endian)
    00                    SegWit marker
    01                    SegWit flag
    01                    input count (1)
      <32 bytes>          prev_txid (internal byte order -- REVERSED from display)
      00000000            prev_vout (0)
      00                  scriptSig length (0 -- empty for SegWit)
      fdffffff            sequence (0xfffffffd -- RBF signaled)
    02                    output count (2)
      50c3000000000000    output 0 value (50,000 sats, LE)
      16                  scriptPubKey length (22 bytes)
      0014<20 bytes>      P2WPKH scriptPubKey (OP_0 + push 20 bytes)
      c8be000000000000    output 1 value (change, LE)
      16                  scriptPubKey length (22 bytes)
      0014<20 bytes>      P2WPKH scriptPubKey (change)
    02                    witness item count (2)
      48                  item 0 length (72 = 71 DER sig + 1 sighash byte)
      <71 bytes>01        DER signature + SIGHASH_ALL (0x01)
      21                  item 1 length (33 bytes)
      <33 bytes>          compressed public key
    00000000              locktime (0)
    """)

    print("NOTE: The signature and TXID in this output are placeholders.")
    print("In real use, you must:")
    print("  1. Compute the BIP143 sighash for P2WPKH")
    print("  2. Sign it with the private key controlling the input")
    print("  3. Use testmempoolaccept to validate before broadcasting")


if __name__ == "__main__":
    main()

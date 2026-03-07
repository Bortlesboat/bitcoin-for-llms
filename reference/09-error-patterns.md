# Common Mistakes LLMs Make When Writing Bitcoin Code

The top 10 error patterns that cause incorrect Bitcoin transaction construction, with wrong vs right examples for each.

## 1. TXID Byte Order

The most frequent mistake. TXIDs are displayed in big-endian (reversed) but serialized in little-endian (internal byte order) when used as an input reference.

**WRONG:**
```python
# Using the TXID as shown on a block explorer directly in serialization
prev_txid = bytes.fromhex("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16")
raw_input = prev_txid + vout + ...
```

**RIGHT:**
```python
# Reverse the bytes for serialization
display_txid = "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
prev_txid = bytes.fromhex(display_txid)[::-1]  # Reverse!
raw_input = prev_txid + vout + ...
```

**Why:** Internally, Bitcoin stores hashes in little-endian. Block explorers display them in big-endian for human readability. When constructing a raw transaction, the `prev_txid` field must be in little-endian (internal) byte order.

## 2. Witness Serialization

Forgetting the marker and flag bytes, or including witness data in the TXID hash.

**WRONG:**
```python
# Missing marker and flag for SegWit tx
raw_tx = version + input_count + inputs + output_count + outputs + witness + locktime

# Including witness in TXID calculation
txid = double_sha256(raw_tx_with_witness)
```

**RIGHT:**
```python
# Full SegWit serialization includes marker (0x00) and flag (0x01)
raw_tx = version + b'\x00\x01' + input_count + inputs + output_count + outputs + witness + locktime

# TXID uses legacy serialization (NO marker, flag, or witness)
legacy_tx = version + input_count + inputs + output_count + outputs + locktime
txid = double_sha256(legacy_tx)
```

**Why:** The SegWit marker (0x00) and flag (0x01) must appear between version and input_count. The TXID is always computed from the legacy serialization to maintain backward compatibility and fix transaction malleability.

## 3. Sighash Flags

Using the wrong sighash type or forgetting to append it to the signature.

**WRONG:**
```python
# Signing without specifying sighash type
signature = sign(private_key, sighash_preimage)
witness = [signature, pubkey]  # Missing sighash byte!
```

**RIGHT:**
```python
# SIGHASH_ALL (0x01) is appended to the DER signature
signature = sign(private_key, sighash_preimage)
witness = [signature + b'\x01', pubkey]  # Append SIGHASH_ALL
```

| Sighash | Value | Meaning |
|---------|-------|---------|
| SIGHASH_ALL | 0x01 | Sign all inputs and outputs (most common) |
| SIGHASH_NONE | 0x02 | Sign all inputs, no outputs |
| SIGHASH_SINGLE | 0x03 | Sign all inputs, only the output at same index |
| SIGHASH_ANYONECANPAY | 0x80 | Combinable flag: only sign this input |
| SIGHASH_ALL\|ANYONECANPAY | 0x81 | Sign this input and all outputs |
| SIGHASH_DEFAULT (Taproot) | 0x00 | Equivalent to SIGHASH_ALL for Schnorr sigs |

**For Taproot/Schnorr:** SIGHASH_DEFAULT (0x00) means SIGHASH_ALL, and the sighash byte is **omitted** from the signature (signature is 64 bytes, not 65). If a non-default sighash is used, the byte IS appended (65 bytes).

## 4. Value Encoding

Using BTC floats instead of integer satoshis, causing precision errors.

**WRONG:**
```python
# Floating point BTC -- DANGEROUS
value = 0.1  # This is 0.1000000000000000055511151231257827021181583404541015625 in IEEE 754
value_sats = int(value * 100_000_000)  # Might not be exactly 10,000,000!

# Even worse: adding floats
total = 0.1 + 0.2  # = 0.30000000000000004
```

**RIGHT:**
```python
# Always work in integer satoshis
value_sats = 10_000_000  # 0.1 BTC
value_bytes = value_sats.to_bytes(8, 'little')

# For display only:
btc_display = value_sats / 100_000_000  # Only at the presentation layer

# If parsing BTC strings, use Decimal:
from decimal import Decimal
btc = Decimal("0.1")
sats = int(btc * 100_000_000)  # Exactly 10,000,000
```

**Why:** IEEE 754 floating point cannot represent most decimal fractions exactly. Bitcoin values must be exact -- a 1-satoshi error can invalidate a transaction or lose funds.

## 5. Script Length Prefix

Forgetting the CompactSize length prefix before scripts, or using the wrong encoding.

**WRONG:**
```python
# Missing length prefix
scriptPubKey = bytes.fromhex("76a914751e76e8199196d454941c45d1b3a323f1433bd688ac")
output = value_bytes + scriptPubKey  # No length prefix!
```

**RIGHT:**
```python
# Include CompactSize length prefix
scriptPubKey = bytes.fromhex("76a914751e76e8199196d454941c45d1b3a323f1433bd688ac")
script_len = len(scriptPubKey)  # 25 bytes

# CompactSize: 25 < 253, so single byte
output = value_bytes + bytes([script_len]) + scriptPubKey
```

**CompactSize encoding function:**
```python
def compact_size(n):
    if n < 0xfd:
        return bytes([n])
    elif n <= 0xffff:
        return b'\xfd' + n.to_bytes(2, 'little')
    elif n <= 0xffffffff:
        return b'\xfe' + n.to_bytes(4, 'little')
    else:
        return b'\xff' + n.to_bytes(8, 'little')
```

## 6. Fee Calculation

Using total serialized size instead of virtual size (vbytes) for fee rate calculation.

**WRONG:**
```python
# Using total byte size for SegWit transactions
tx_bytes = serialize_segwit_tx(tx)
fee_rate = fee / len(tx_bytes)  # WRONG for SegWit -- this is sat/byte, not sat/vB
```

**RIGHT:**
```python
# Calculate weight, then vbytes
base_size = len(serialize_legacy(tx))      # Without witness
total_size = len(serialize_segwit(tx))     # With witness
weight = base_size * 3 + total_size
vbytes = (weight + 3) // 4                 # Round up

fee_rate = fee / vbytes  # Correct: sat/vB
```

**Why:** SegWit gives witness bytes a 75% discount. Using total size overpays fees by 20-40% for typical SegWit transactions.

## 7. Sequence Number Defaults

Accidentally enabling timelocks or disabling RBF by using the wrong sequence number.

**WRONG:**
```python
# Using 0 -- enables relative timelock of 0 blocks AND signals RBF
sequence = 0x00000000

# Using max -- disables nLockTime enforcement and RBF
sequence = 0xffffffff
```

**RIGHT:**
```python
# For standard transactions with RBF signaling (most common):
sequence = 0xfffffffd  # Signals RBF, no relative timelock, nLockTime active

# For finalized transactions (no RBF, no timelock):
sequence = 0xffffffff

# For RBF + nLockTime:
sequence = 0xfffffffe
```

| Sequence Value | RBF | nLockTime | Relative Timelock |
|---------------|-----|-----------|-------------------|
| 0xffffffff | No | Disabled | No |
| 0xfffffffe | Yes* | Enabled | No |
| 0xfffffffd | Yes | Enabled | No |
| < 0x80000000 | Yes | Enabled | **Yes** (value encodes lock) |

*0xfffffffe is technically < 0xffffffff so it opts into BIP125 RBF, but many implementations treat only < 0xfffffffe as explicit RBF signaling. With full RBF (Core 28+), this distinction is less important.

## 8. OP_PUSHDATA Confusion

Using OP_PUSHDATA1 when a direct push is correct, or vice versa.

**WRONG:**
```python
# Using OP_PUSHDATA1 for a 20-byte hash push
script = b'\x4c\x14' + hash160  # OP_PUSHDATA1 + length 20 -- non-standard!
```

**RIGHT:**
```python
# Direct push for data <= 75 bytes
script = b'\x14' + hash160  # Push 20 bytes (0x14 = 20)
```

| Data Size | Correct Push Method |
|-----------|-------------------|
| 0 bytes | OP_0 (0x00) |
| 1 byte, value 1-16 | OP_1 through OP_16 (0x51-0x60) |
| 1 byte, value 0x81 | OP_1NEGATE (0x4f) |
| 1-75 bytes | Direct push: `<length_byte> <data>` |
| 76-255 bytes | OP_PUSHDATA1: `0x4c <1-byte-length> <data>` |
| 256-65535 bytes | OP_PUSHDATA2: `0x4d <2-byte-length-LE> <data>` |

Using a larger push opcode than necessary creates a non-standard transaction that nodes will reject.

## 9. Address Validation

Not validating checksums, mixing mainnet/testnet, or confusing Bech32/Bech32m.

**WRONG:**
```python
# Accepting any string that starts with "bc1" as valid
if address.startswith("bc1"):
    # Assume it's valid -- NO!
    pass

# Using Bech32 for Taproot (witness v1)
address = bech32_encode("bc", 1, program)  # WRONG -- must use Bech32m!
```

**RIGHT:**
```python
# Validate checksum, witness version, and program length
def validate_segwit_address(address):
    hrp, version, program = decode_bech32(address)

    if hrp not in ("bc", "tb", "bcrt"):
        return False

    # Check encoding type matches witness version
    if version == 0:
        # Must be Bech32, program must be 20 or 32 bytes
        if not is_bech32(address) or len(program) not in (20, 32):
            return False
    elif version == 1:
        # Must be Bech32m, program must be 32 bytes
        if not is_bech32m(address) or len(program) != 32:
            return False
    elif 2 <= version <= 16:
        # Must be Bech32m, program 2-40 bytes
        if not is_bech32m(address):
            return False

    return True
```

**Key rules:**
- Witness v0 uses Bech32 encoding
- Witness v1+ uses Bech32m encoding
- P2WPKH program is exactly 20 bytes
- P2WSH program is exactly 32 bytes
- P2TR program is exactly 32 bytes
- Never mix mainnet/testnet prefixes

## 10. Missing Change Output

Forgetting to include a change output, sending the entire difference to miners as fee.

**WRONG:**
```python
# Input: 1.0 BTC, want to send 0.01 BTC
inputs = [{"txid": "...", "vout": 0, "value": 100_000_000}]
outputs = [{"address": recipient, "value": 1_000_000}]  # 0.01 BTC

# Missing change output!
# Fee = 1.0 - 0.01 = 0.99 BTC = $60,000+ donated to miners
```

**RIGHT:**
```python
# Input: 1.0 BTC, want to send 0.01 BTC
input_value = 100_000_000  # 1.0 BTC in sats
send_value = 1_000_000     # 0.01 BTC in sats

# Estimate fee first
estimated_vbytes = 141  # Typical P2WPKH 1-in-2-out
fee_rate = 10  # sat/vB
fee = estimated_vbytes * fee_rate  # 1,410 sats

change_value = input_value - send_value - fee  # 98,998,590 sats

# Safety check
assert change_value > 0, "Insufficient funds"
assert change_value > 294, "Change would be dust -- add to fee or find better inputs"

outputs = [
    {"address": recipient, "value": send_value},
    {"address": change_address, "value": change_value},
]
```

**Safety checklist before broadcasting:**
1. Sum of outputs + fee == sum of inputs
2. Fee is reasonable (not > 1% of total value for large txs)
3. No output is below the dust limit (294 sats for P2WPKH)
4. Change output exists if input value significantly exceeds send value

# Bitcoin Protocol Quick Reference for LLMs

Drop this file into your project's CLAUDE.md or system prompt to give an LLM accurate Bitcoin protocol knowledge. Covers the critical patterns and pitfalls in ~15K tokens.

---

## Byte Order (THE #1 SOURCE OF BUGS)

Bitcoin uses TWO byte orders:

- **Internal (little-endian):** Used in serialized data. All integers, and TXIDs when stored as input references.
- **Display (big-endian):** Used on block explorers and in human-readable output. TXIDs and block hashes are shown reversed.

**To convert a display TXID to serialized form, reverse the entire 32-byte sequence:**
```python
display = "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
serialized = bytes.fromhex(display)[::-1]  # Reverse all 32 bytes
```

NEVER use a display-order TXID directly in raw transaction construction.

## Transaction Format

### Legacy
```
version(4) | input_count(varint) | inputs | output_count(varint) | outputs | locktime(4)
```

### SegWit
```
version(4) | marker(0x00) | flag(0x01) | input_count(varint) | inputs | output_count(varint) | outputs | witness | locktime(4)
```

### Input
```
prev_txid(32, LE!) | prev_vout(4) | scriptSig_len(varint) | scriptSig | sequence(4)
```

### Output
```
value(8, sats LE) | scriptPubKey_len(varint) | scriptPubKey
```

### TXID Calculation
TXID = double-SHA-256 of **legacy serialization** (no marker, flag, or witness). Reverse the hash for display.

## CompactSize (Varint)

| Value | Encoding |
|-------|----------|
| 0-252 | 1 byte: value directly |
| 253-65535 | 0xfd + 2 bytes LE |
| 65536-4294967295 | 0xfe + 4 bytes LE |
| larger | 0xff + 8 bytes LE |

```python
def compact_size(n):
    if n < 0xfd: return bytes([n])
    elif n <= 0xffff: return b'\xfd' + n.to_bytes(2, 'little')
    elif n <= 0xffffffff: return b'\xfe' + n.to_bytes(4, 'little')
    else: return b'\xff' + n.to_bytes(8, 'little')
```

## Address Types

| Type | Prefix | scriptPubKey | Encoding |
|------|--------|-------------|----------|
| P2PKH | 1... | `76a914{hash160}88ac` | Base58Check |
| P2SH | 3... | `a914{hash160}87` | Base58Check |
| P2WPKH | bc1q... (20B prog) | `0014{hash160}` | Bech32 |
| P2WSH | bc1q... (32B prog) | `0020{sha256}` | Bech32 |
| P2TR | bc1p... | `5120{tweaked_pubkey}` | Bech32m |

**Critical:** P2WPKH/P2WSH (witness v0) use Bech32. P2TR (witness v1) uses Bech32**m**.
**Critical:** P2WSH uses SHA-256 (32 bytes), not HASH160 (20 bytes).

## Script Patterns

### Common Opcodes

| Hex | Name | Action |
|-----|------|--------|
| 0x00 | OP_0 | Push empty (false) |
| 0x51-0x60 | OP_1-OP_16 | Push 1-16 |
| 0x75 | OP_DROP | Remove top |
| 0x76 | OP_DUP | Duplicate top |
| 0x87 | OP_EQUAL | Check equality |
| 0x88 | OP_EQUALVERIFY | Check equality + verify |
| 0xa9 | OP_HASH160 | SHA256 then RIPEMD160 |
| 0xac | OP_CHECKSIG | Verify signature |
| 0xae | OP_CHECKMULTISIG | M-of-N multisig |
| 0xb1 | OP_CLTV | Absolute timelock |
| 0xb2 | OP_CSV | Relative timelock |
| 0x6a | OP_RETURN | Provably unspendable |

### Data Push Rules

| Size | Method |
|------|--------|
| 1-75 bytes | `<length_byte> <data>` (direct push) |
| 76-255 bytes | `0x4c <1-byte-len> <data>` (OP_PUSHDATA1) |
| 256-65535 bytes | `0x4d <2-byte-len-LE> <data>` (OP_PUSHDATA2) |

ALWAYS use minimal push. Using OP_PUSHDATA1 for data < 76 bytes is non-standard.

## Sighash Types

| Type | Value | Meaning |
|------|-------|---------|
| SIGHASH_ALL | 0x01 | Sign all inputs and outputs |
| SIGHASH_NONE | 0x02 | Sign inputs, no outputs |
| SIGHASH_SINGLE | 0x03 | Sign inputs, only matching output |
| ANYONECANPAY | 0x80 | Combine: only sign current input |
| SIGHASH_DEFAULT (Taproot) | 0x00 | Same as ALL, but omit byte from sig |

For legacy/SegWit v0: append sighash byte to DER signature. For Taproot with SIGHASH_DEFAULT: signature is 64 bytes (no appended byte). Non-default Taproot sighash: 65 bytes.

## Sequence Numbers

| Value | RBF | nLockTime | Relative Timelock |
|-------|-----|-----------|-------------------|
| 0xffffffff | No | Disabled | No |
| 0xfffffffe | Yes | Enabled | No |
| 0xfffffffd | Yes | Enabled | No |
| < 0x80000000 | Yes | Enabled | YES |

Default for most wallets: 0xfffffffd (RBF enabled).

## Fees and Weight

```
weight = base_size * 3 + total_size
vbytes = ceil(weight / 4)
fee_rate = fee_sats / vbytes  (sat/vB)
```

- Non-witness byte = 4 WU
- Witness byte = 1 WU
- Max block weight = 4,000,000 WU

**Dust limits:** P2WPKH: 294 sats, P2TR: 330 sats, P2PKH: 546 sats.

## Values: ALWAYS Use Integer Satoshis

```python
# WRONG - floating point error
value = 0.1 + 0.2  # 0.30000000000000004

# RIGHT - integer satoshis
value = 10_000_000 + 20_000_000  # 30,000,000 sats exactly

# If parsing BTC strings:
from decimal import Decimal
sats = int(Decimal("0.1") * 100_000_000)
```

1 BTC = 100,000,000 satoshis. Never use float for BTC values.

## Hash Functions

| Name | Algorithm | Used For |
|------|-----------|----------|
| HASH256 | SHA256(SHA256(x)) | TXIDs, block hashes, merkle nodes |
| HASH160 | RIPEMD160(SHA256(x)) | P2PKH/P2SH/P2WPKH addresses |
| SHA-256 | SHA256(x) | P2WSH witness programs, Taproot tagged hashes |
| Tagged hash | SHA256(SHA256(tag)\|\|SHA256(tag)\|\|x) | Taproot (TapTweak, TapLeaf, etc.) |

## Block Structure

Header: version(4) + prev_hash(32) + merkle_root(32) + timestamp(4) + bits(4) + nonce(4) = 80 bytes.

Subsidy: `50 * 100_000_000 >> (height // 210_000)` satoshis. Current (2024+): 3.125 BTC.

## Top 10 LLM Error Patterns

### 1. TXID byte order
WRONG: Use display TXID directly in serialization. RIGHT: Reverse the 32 bytes.

### 2. Missing SegWit marker/flag
WRONG: Omit 0x00 0x01 after version. RIGHT: Insert marker+flag between version and input_count.

### 3. Sighash byte missing
WRONG: Witness = [raw_signature, pubkey]. RIGHT: Witness = [signature + 0x01, pubkey].

### 4. Floating point BTC
WRONG: `value = 0.1 * 100_000_000`. RIGHT: `value = 10_000_000`.

### 5. Missing script length prefix
WRONG: `output = value + scriptPubKey`. RIGHT: `output = value + compact_size(len(script)) + scriptPubKey`.

### 6. Fee uses total size, not vbytes
WRONG: `fee_rate = fee / len(segwit_tx)`. RIGHT: `fee_rate = fee / vbytes`.

### 7. Wrong sequence number
WRONG: `sequence = 0x00000000` (enables relative timelock!). RIGHT: `sequence = 0xfffffffd` for standard RBF.

### 8. OP_PUSHDATA for short data
WRONG: `0x4c 0x14 <20 bytes>`. RIGHT: `0x14 <20 bytes>` (direct push for <= 75 bytes).

### 9. Bech32 vs Bech32m
WRONG: Bech32 for P2TR. RIGHT: Bech32m for witness v1+.

### 10. Missing change output
WRONG: Only create payment output; miners get the rest. RIGHT: Always include change output = input - payment - fee.

## Most-Used RPC Commands

```bash
# Info
getblockchaininfo                              # Chain state
getblockcount                                  # Current height
getblock "hash" 1                              # Block data (JSON)
getblockhash 0                                 # Hash at height

# Transactions
getrawtransaction "txid" true                  # Decode tx (needs txindex)
decoderawtransaction "hex"                     # Decode raw hex
testmempoolaccept '["signed_hex"]'             # Validate without broadcast
sendrawtransaction "signed_hex"                # Broadcast

# Mempool
getmempoolinfo                                 # Mempool stats
getrawmempool                                  # All mempool TXIDs

# Fees
estimatesmartfee 6                             # Fee rate for ~6 block confirm

# UTXO
gettxout "txid" 0                              # Check if output is unspent
scantxoutset start '["addr(bc1q...)"]'         # Find UTXOs for address

# Construction
createrawtransaction '[{"txid":"...","vout":0}]' '[{"addr":0.01}]'
signrawtransactionwithkey "hex" '["privkey"]'

# Network
getpeerinfo                                    # Connected peers
getnetworkinfo                                 # Network state

# Validation
validateaddress "bc1q..."                      # Check address validity
decodescript "hex"                             # Decode script hex
```

**estimatesmartfee returns BTC/kvB.** Convert: `sat_per_vb = feerate * 100_000`

## Testing Checklist

Before broadcasting any transaction:

1. `testmempoolaccept` passes
2. TXID byte order is reversed from display
3. All values are integer satoshis (no floats)
4. Change output exists (input - payment - fee)
5. No output below dust limit
6. Fee rate is reasonable (check `estimatesmartfee`)
7. Signature includes sighash byte
8. SegWit tx has marker (0x00) + flag (0x01)
9. CompactSize prefixes are present and minimal
10. Test on regtest first: `bitcoind -regtest`, mine 101 blocks, then test

## Regtest Quick Start

```bash
bitcoind -regtest -daemon
bitcoin-cli -regtest createwallet "test"
ADDR=$(bitcoin-cli -regtest getnewaddress "" bech32m)
bitcoin-cli -regtest generatetoaddress 101 "$ADDR"
bitcoin-cli -regtest getbalance  # 50.00000000
```

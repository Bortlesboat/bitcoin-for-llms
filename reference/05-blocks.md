# Bitcoin Block Structure

Block headers, coinbase transactions, merkle trees, weight limits, and difficulty adjustment.

## Block Header

Exactly 80 bytes. This is what gets hashed to produce the block hash.

```
+----------+-----------+-------------+-----------+------+-------+
| version  | prev_hash | merkle_root | timestamp | bits | nonce |
| 4 bytes  | 32 bytes  | 32 bytes    | 4 bytes   | 4B   | 4B    |
+----------+-----------+-------------+-----------+------+-------+
```

All fields are little-endian.

### Field Details

| Field | Size | Description |
|-------|------|-------------|
| version | int32_t (4B) | Block version. Encodes BIP9 signaling bits. Current blocks typically use 0x20000000 or higher. |
| prev_hash | 32 bytes | Double-SHA-256 hash of the previous block header, in internal (LE) byte order. |
| merkle_root | 32 bytes | Root of the merkle tree of all transaction TXIDs in the block, in internal byte order. |
| timestamp | uint32_t (4B) | Unix epoch time. Must be greater than median of last 11 blocks. |
| bits | uint32_t (4B) | Compact encoding of the target threshold. |
| nonce | uint32_t (4B) | Miner-adjusted value to find a valid hash. |

### Real Block Header: Genesis Block (Block 0)

```
Block hash (display): 000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f

Raw header (hex):
01000000                                 version: 1
0000000000000000000000000000000000000000
00000000000000000000000000000000         prev_hash: all zeros (no previous)
3ba3edfd7a7b12b27ac72c3e67768f617fc81b
c3888a51323a9fb8aa4b1e5e4a             merkle_root (internal byte order)
29ab5f49                                 timestamp: 1231006505 (Jan 3, 2009 18:15:05 UTC)
ffff001d                                 bits: 0x1d00ffff (difficulty 1)
1dac2b7c                                 nonce: 2083236893
```

To get the block hash:
1. Double-SHA-256 the 80-byte header
2. Result is in internal byte order; reverse to get display order

### Bits (Compact Target Encoding)

The `bits` field encodes the target as: `target = coefficient * 256^(exponent - 3)`

```
bits = 0x1d00ffff

exponent = 0x1d = 29
coefficient = 0x00ffff

target = 0x00ffff * 256^(29-3) = 0x00ffff0000000000000000000000000000000000000000000000000000

A valid block hash must be <= target (when interpreted as a 256-bit number).
```

## Coinbase Transaction

The first transaction in every block. Special rules:

- **prev_txid**: Must be `0x00` * 32 (all zeros)
- **prev_vout**: Must be `0xffffffff`
- **scriptSig**: Arbitrary data (used for extra nonce space, miner messages). Must start with the block height (BIP34, since block 227,836).
- **sequence**: Typically `0xffffffff`
- **Outputs**: Block reward (subsidy + fees) sent to miner's address(es)

### Block Height in Coinbase (BIP34)

The scriptSig must begin with the block height encoded as a Script number:

```
Height 800000 (0x0C3500):
scriptSig starts with: 03 00350c
                        ^  ^^^^^^^
                        |  height in LE (3 bytes)
                        push 3 bytes
```

### Block Subsidy Schedule

```
Blocks 0 - 209,999:        50 BTC
Blocks 210,000 - 419,999:  25 BTC
Blocks 420,000 - 629,999:  12.5 BTC
Blocks 630,000 - 839,999:  6.25 BTC
Blocks 840,000 - 1,049,999: 3.125 BTC  (April 2024 halving)

subsidy = 50 * 100_000_000 >> (height // 210_000)  # in satoshis
```

## Merkle Tree

The merkle root in the block header commits to all transactions in the block.

### Construction

1. Compute the TXID (double-SHA-256) of each transaction
2. If odd number of TXIDs, duplicate the last one
3. Pair adjacent hashes and double-SHA-256 each pair: `HASH256(left + right)`
4. Repeat until one hash remains: the merkle root

```
         merkle_root
         /         \
    hash_AB       hash_CD
    /    \        /    \
  txA    txB    txC    txD
```

For a block with a single transaction (just the coinbase), the merkle root equals the coinbase TXID.

### Witness Commitment (BIP141)

SegWit blocks include a witness commitment in the coinbase. The coinbase output contains:

```
OP_RETURN 0x24 0xaa21a9ed <32-byte witness merkle root commitment>
```

The witness merkle tree is computed the same way as the regular merkle tree but using WTXIDs instead of TXIDs (with the coinbase WTXID set to all zeros).

## Block Weight and Size

Since SegWit (BIP141), blocks are measured in **weight units (WU)**, not bytes.

```
weight = base_size * 3 + total_size
```

Where:
- **base_size**: Size of the block serialized without witness data (legacy format)
- **total_size**: Size of the block serialized with witness data (SegWit format)

**Maximum block weight: 4,000,000 WU**

This works out to:
- A block of purely legacy transactions: max ~1 MB (1,000,000 bytes * 4 = 4,000,000 WU)
- A block of purely witness data: max ~4 MB (but unrealistic in practice)
- Typical blocks: 1.5 - 2.5 MB total size

## Difficulty Adjustment

Every 2,016 blocks (~2 weeks), the difficulty adjusts:

```
new_target = old_target * (actual_time / expected_time)

expected_time = 2,016 * 600 seconds = 1,209,600 seconds (2 weeks)
```

Clamping: The adjustment is clamped to a factor of 4 in either direction:
- Maximum increase: new_target = old_target * 4 (difficulty drops 4x)
- Maximum decrease: new_target = old_target / 4 (difficulty increases 4x)

If miners find 2,016 blocks in 1 week (too fast), difficulty roughly doubles.
If miners find 2,016 blocks in 4 weeks (too slow), difficulty roughly halves.

### Off-by-One Bug

Bitcoin's difficulty calculation has a well-known off-by-one error: it uses the timestamp of block N-2016 instead of N-2015, measuring across 2,015 block intervals instead of 2,016. This means difficulty adjusts slightly faster than intended (~0.05% bias).

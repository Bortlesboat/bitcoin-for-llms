# Bitcoin Data Types and Encoding

Canonical reference for byte orders, variable-length integers, hash functions, and integer types used in the Bitcoin protocol.

## Byte Order

Bitcoin uses two byte orders, and confusing them is the single most common source of bugs.

### Internal byte order (little-endian)

Used in **serialized data on the wire and on disk**. The least significant byte comes first.

- Transaction IDs in raw transaction inputs (prev_txid field)
- All integer fields (version, locktime, value, sequence, etc.)
- Block header fields (version, timestamp, bits, nonce)

### Display byte order (big-endian)

Used in **human-readable contexts**. The most significant byte comes first.

- Transaction IDs shown on block explorers
- Block hashes shown on block explorers
- Merkle roots in documentation

### Critical example: Transaction IDs

The genesis block's coinbase transaction ID as displayed:

```
Display (big-endian):  4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b
```

When this TXID appears as a `prev_txid` in a raw transaction input, the bytes are reversed:

```
Serialized (little-endian): 3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a
```

**Rule: To convert between display and serialized TXID, reverse the entire 32-byte sequence.**

## CompactSize (Variable-Length Integer)

Used as a prefix before variable-length fields (input count, output count, script length, etc.).

| Value Range | Prefix | Size | Format |
|------------|--------|------|--------|
| 0x00 - 0xfc | none | 1 byte | uint8_t |
| 0x00fd - 0xffff | 0xfd | 3 bytes | 0xfd + uint16_t LE |
| 0x00010000 - 0xffffffff | 0xfe | 5 bytes | 0xfe + uint32_t LE |
| 0x0000000100000000 - 0xffffffffffffffff | 0xff | 9 bytes | 0xff + uint64_t LE |

### Examples

```
Value: 1       -> Hex: 01
Value: 252     -> Hex: fc
Value: 253     -> Hex: fdfd00
Value: 255     -> Hex: fdff00
Value: 512     -> Hex: fd0002
Value: 65535   -> Hex: fdffff
Value: 65536   -> Hex: fe00000100
```

**Common mistake:** Using a 3-byte encoding for values that fit in 1 byte. While technically parseable by some implementations, canonical encoding requires the smallest possible representation.

## Hash Types

### SHA-256

Single SHA-256. Used for:
- Witness commitment in coinbase
- Taproot tweaks (tagged hashes)

```
SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

### Double-SHA-256 (HASH256)

SHA-256 applied twice: `SHA256(SHA256(data))`. Used for:
- Transaction IDs (TXID)
- Block hashes
- Merkle tree nodes
- Checksum in Base58Check (first 4 bytes)

```
HASH256("") = 5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456
```

### HASH160

SHA-256 then RIPEMD-160: `RIPEMD160(SHA256(data))`. Used for:
- P2PKH addresses (hash of public key)
- P2SH addresses (hash of redeem script)
- P2WPKH witness programs

```
HASH160("") = b472a266d0bd89c13706a4132ccfb16f7c3b9fcb
```

### Tagged Hashes (BIP340/Taproot)

`SHA256(SHA256(tag) || SHA256(tag) || data)` where `tag` is an ASCII string. Used for:
- Taproot key tweaking (tag: "TapTweak")
- Taproot leaf hashing (tag: "TapLeaf")
- Taproot branch hashing (tag: "TapBranch")
- Schnorr signatures (tag: "BIP0340/challenge")

## Common Integer Types

All integers are encoded in **little-endian** byte order in serialized data.

| Type | Size | Range | Used For |
|------|------|-------|----------|
| int32_t | 4 bytes | -2^31 to 2^31-1 | Transaction version |
| uint32_t | 4 bytes | 0 to 2^32-1 | Locktime, sequence, block timestamp, bits, nonce |
| int64_t | 8 bytes | -2^63 to 2^63-1 | Output value (satoshis) |
| uint64_t | 8 bytes | 0 to 2^64-1 | Services field in network messages |

### Value encoding example

1 BTC = 100,000,000 satoshis = 0x05F5E100

```
1 BTC as int64_t LE: 00e1f50500000000
0.5 BTC as int64_t LE: 80f0fa0200000000
0.00001 BTC (1000 sats) as int64_t LE: e803000000000000
```

**Critical: Never use floating point for Bitcoin values.** Always work in integer satoshis. The value 0.1 BTC cannot be represented exactly in IEEE 754 floating point.

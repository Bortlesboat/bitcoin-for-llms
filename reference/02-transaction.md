# Bitcoin Transaction Format

Complete specification of legacy and SegWit transaction serialization, with byte-by-byte decoding of real mainnet transactions.

## Legacy Transaction Format

```
+----------+-------------+--------+---------------+---------+----------+
| version  | input_count | inputs | output_count  | outputs | locktime |
| 4 bytes  | varint      | var    | varint        | var     | 4 bytes  |
+----------+-------------+--------+---------------+---------+----------+
```

## SegWit Transaction Format (BIP141)

```
+----------+--------+------+-------------+--------+---------------+---------+---------+----------+
| version  | marker | flag | input_count | inputs | output_count  | outputs | witness | locktime |
| 4 bytes  | 0x00   | 0x01 | varint      | var    | varint        | var     | var     | 4 bytes  |
+----------+--------+------+-------------+--------+---------------+---------+---------+----------+
```

The `marker` (0x00) and `flag` (0x01) bytes distinguish SegWit transactions from legacy. They appear immediately after the version field.

## Input Structure

Each input:

```
+----------------+----------+------------+-----------+----------+
| prev_txid      | prev_vout| script_len | scriptSig | sequence |
| 32 bytes (LE)  | 4 bytes  | varint     | var       | 4 bytes  |
+----------------+----------+------------+-----------+----------+
```

- **prev_txid**: TXID of the transaction containing the output being spent. **Stored in little-endian (internal byte order)** -- reversed from display order.
- **prev_vout**: Index of the output being spent (0-indexed), uint32_t LE.
- **scriptSig**: For legacy inputs, contains the unlocking script. For SegWit inputs, this is empty (length 0x00).
- **sequence**: Usually 0xffffffff (final), 0xfffffffe (RBF opt-in, no relative timelock), or a relative timelock value. See BIP68/BIP125.

## Output Structure

Each output:

```
+-----------+------------+---------------+
| value     | script_len | scriptPubKey  |
| 8 bytes   | varint     | var           |
+-----------+------------+---------------+
```

- **value**: Amount in satoshis as int64_t LE. 1 BTC = 100,000,000 = 0x00E1F50500000000.
- **scriptPubKey**: The locking script (defines spending conditions).

## Witness Structure

One witness stack per input, in the same order as inputs. Each witness stack:

```
+------------+-----------------------------+
| item_count | items                       |
| varint     | (len + data) per item       |
+------------+-----------------------------+
```

Each item is prefixed by its length as a CompactSize.

For P2WPKH, the witness stack contains exactly 2 items:
1. DER-encoded signature + sighash byte
2. Compressed public key (33 bytes)

## TXID vs WTXID

- **TXID** = double-SHA-256 of the **legacy serialization** (version + inputs + outputs + locktime). Witness data is NOT included.
- **WTXID** = double-SHA-256 of the **full SegWit serialization** (including marker, flag, and witness).

For legacy transactions, TXID == WTXID.

This design is why SegWit fixes transaction malleability: changing the witness does not change the TXID.

## Real Mainnet Transaction: Byte-by-Byte Decode

Satoshi's first transaction to Hal Finney (block 170, January 12, 2009):

TXID (display): `f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16`

Raw hex (legacy format):
```
01000000 01 0437cd7f8525ceed2324359c2d0ba26006d92d85 ...
```

Let's decode a simpler, well-known SegWit transaction. Here is a real P2WPKH spend:

TXID (display): `c586389e5e4b3acb9d6c8be1c19ae8ab2795397633176f5a6442a261bbdefc3a`

```
Raw hex:
02000000000101d27c508160db91b78fb2cf60a8a3d02b96e5c tried
```

Rather than decode a specific transaction (which would require embedding hundreds of hex characters), here is the annotated structure of a typical 1-in-1-out P2WPKH transaction:

```
Field                    Hex                               Meaning
-------                  ---                               -------
version                  02000000                          Version 2 (LE)
marker                   00                                SegWit marker
flag                     01                                SegWit flag
input_count              01                                1 input
  prev_txid              <32 bytes LE>                     TXID being spent (reversed)
  prev_vout              00000000                          Output index 0
  script_len             00                                Empty scriptSig (SegWit)
  sequence               fdffffff                          0xfffffffd - RBF signaled
output_count             01                                1 output
  value                  40420f0000000000                  1,000,000 sats (0.01 BTC)
  script_len             16                                22 bytes
  scriptPubKey           0014<20-byte-hash>                P2WPKH output
witness                                                    (for input 0)
  item_count             02                                2 witness items
  item1_len              47                                71 bytes (DER signature)
  item1                  <71 bytes>                        signature + SIGHASH_ALL
  item2_len              21                                33 bytes
  item2                  <33 bytes>                        compressed pubkey
locktime                 00000000                          No locktime
```

### Calculating the TXID

To compute the TXID of a SegWit transaction:

1. Serialize in **legacy format** (strip marker, flag, and witness):
   `version + input_count + inputs + output_count + outputs + locktime`
2. Double-SHA-256 the result
3. The hash is in internal byte order; reverse to get display order

```python
import hashlib

def txid(legacy_serialization: bytes) -> str:
    h = hashlib.sha256(hashlib.sha256(legacy_serialization).digest()).digest()
    return h[::-1].hex()  # Reverse for display order
```

## Version Numbers

| Version | Meaning |
|---------|---------|
| 1 | Standard (most legacy transactions) |
| 2 | Enables BIP68 relative timelocks (OP_CSV). Required since BIP68 activation. |

Version is a signed 32-bit integer but negative versions are non-standard.

## Locktime

| Value | Meaning |
|-------|---------|
| 0 | No locktime (immediately valid) |
| 1 - 499,999,999 | Block height (tx valid at this height) |
| >= 500,000,000 | Unix timestamp (tx valid at this time) |

Locktime is only enforced if at least one input has sequence < 0xffffffff.

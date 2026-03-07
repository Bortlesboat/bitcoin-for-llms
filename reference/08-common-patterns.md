# Common Bitcoin Transaction Patterns

Practical patterns for UTXO management, multisig, timelocks, and coin selection.

## UTXO Consolidation

Combine many small UTXOs into one larger output during low-fee periods.

```
Inputs:                          Output:
  UTXO_1 (0.001 BTC) ----+
  UTXO_2 (0.002 BTC) ----+--->  Single output (sum - fee)
  UTXO_3 (0.005 BTC) ----+
  UTXO_4 (0.003 BTC) ----+
```

**Why:** Each input adds ~57 vbytes (P2WPKH) to future transactions. Consolidating during low-fee periods saves money on future high-fee spends.

**When:** Fee rate < 5 sat/vB is generally good for consolidation.

**Cost estimate:** For N P2WPKH inputs consolidated into 1 output:
```
vbytes ~ 10.5 + (N * 57.5) + 31
fee = vbytes * fee_rate
```

## Payment Batching

Send to multiple recipients in a single transaction to save fees.

```
Input:                           Outputs:
  UTXO (1.0 BTC) ----+------>   Recipient_1 (0.1 BTC)
                      +------>   Recipient_2 (0.2 BTC)
                      +------>   Recipient_3 (0.15 BTC)
                      +------>   Change (0.549 BTC)
```

**Savings:** Each additional output adds only ~31-43 vbytes, vs a separate transaction which would add ~110+ vbytes (full tx overhead + input + output).

For 10 payments: ~360 vbytes batched vs ~1100 vbytes separate. **~67% fee savings.**

## Multisig

### 2-of-3 Multisig (P2SH-wrapped P2WSH)

The most common multisig setup for custody.

**Redeem script (witness script):**
```
OP_2 <pubkey1> <pubkey2> <pubkey3> OP_3 OP_CHECKMULTISIG
52   21<key1>  21<key2>  21<key3>  53   ae
```

**P2WSH address derivation:**
```python
import hashlib

witness_script = bytes.fromhex("5221{key1}21{key2}21{key3}53ae")
script_hash = hashlib.sha256(witness_script).digest()
# Encode as bech32 with witness version 0 to get bc1q... address
```

**Spending (witness):**
```
witness:
  item_count: 4
  item_0: ""  (empty, required by OP_CHECKMULTISIG off-by-one bug)
  item_1: <signature_A>
  item_2: <signature_B>
  item_3: <witness_script>
```

The empty item at position 0 is required because of a historical off-by-one bug in OP_CHECKMULTISIG that pops one extra element from the stack.

### Native 2-of-3 P2WSH (no P2SH wrapping)

Same witness script, but the scriptPubKey is:
```
OP_0 <32-byte SHA256 of witness_script>
0020{sha256}
```

This is more fee-efficient than P2SH-wrapped because it avoids the extra P2SH layer.

### Taproot Multisig (MuSig2 or Script Path)

Taproot offers two multisig approaches:

1. **MuSig2 (key path):** Aggregate keys into a single Taproot output. On-chain it looks like a regular single-sig spend. Most private and cheapest.

2. **Script path:** Encode multisig conditions as Tapscript leaves. Uses OP_CHECKSIGADD instead of OP_CHECKMULTISIG:
```
<pubkey1> OP_CHECKSIG <pubkey2> OP_CHECKSIGADD <pubkey3> OP_CHECKSIGADD OP_2 OP_NUMEQUAL
```

## Timelocks

### Absolute Timelocks

**nLockTime (transaction level):**
```
locktime < 500,000,000  -> block height
locktime >= 500,000,000 -> Unix timestamp
```
At least one input must have sequence < 0xffffffff for nLockTime to be enforced.

**OP_CHECKLOCKTIMEVERIFY (script level, BIP65):**
```
<expiry_time> OP_CLTV OP_DROP <pubkey> OP_CHECKSIG
```
Fails if the transaction's nLockTime < expiry_time. Also fails if nLockTime type (height vs time) doesn't match.

Example: Lock funds until block 900,000:
```
03a0bb0d  (900000 in script number encoding, LE)
OP_CLTV OP_DROP
<pubkey> OP_CHECKSIG
```

### Relative Timelocks (BIP68, BIP112)

**nSequence (input level):**

When bit 31 is NOT set (value < 0x80000000), relative timelock is active:
```
Bit 22 = 0: value is in blocks (lower 16 bits)
Bit 22 = 1: value is in 512-second intervals (lower 16 bits)
```

Requires transaction version >= 2.

```
sequence = 0x00000090  -> 144 blocks (~1 day) relative lock
sequence = 0x00400090  -> 144 * 512 seconds (~20.5 hours) relative lock
```

**OP_CHECKSEQUENCEVERIFY (script level, BIP112):**
```
<relative_lock> OP_CSV OP_DROP <pubkey> OP_CHECKSIG
```

### Common Timelock Patterns

**HTLC (Hash Time-Locked Contract):**
```
OP_IF
    OP_HASH160 <payment_hash> OP_EQUALVERIFY <recipient_pubkey> OP_CHECKSIG
OP_ELSE
    <timeout> OP_CLTV OP_DROP <sender_pubkey> OP_CHECKSIG
OP_ENDIF
```

Used in Lightning Network payment channels and atomic swaps.

## Coin Selection Strategies

### Largest-First

Pick UTXOs from largest to smallest until the target amount is covered.

- Pros: Simple, uses fewest inputs
- Cons: Creates unnecessary change, tends to fragment UTXO set over time

### Branch-and-Bound (BnB)

Bitcoin Core's default (since v0.17). Tries to find a UTXO combination that exactly matches the target + fee (no change output needed).

- Pros: Eliminates change output (~31 vB savings), improves privacy
- Cons: Only works when an exact match exists; falls back to other strategies

### Knapsack

Random selection with multiple iterations to minimize waste. Used as Bitcoin Core's fallback when BnB fails.

### Single Random Draw

Pick UTXOs randomly until target is met. Used in some wallets for privacy (makes UTXO selection non-deterministic).

## Change Output Best Practices

1. **Always verify total_input >= total_output + fee.** If not, you're creating an invalid transaction.

2. **If total_input - total_output - fee < dust_limit**, add the excess to the fee instead of creating a dust change output.

3. **Randomize change output position.** Don't always put change last -- it makes the change output identifiable.

4. **Match change output type** to the spending input type for privacy. If spending from P2WPKH, make the change output P2WPKH too.

5. **Avoid round numbers** in the payment output. Paying exactly 0.1 BTC makes the change output obvious. (Though this is a wallet concern, not a protocol requirement.)

## Transaction Batching Example

```python
# Instead of 3 separate transactions:
# tx1: input_A -> recipient_1 + change_1  (141 vB)
# tx2: input_B -> recipient_2 + change_2  (141 vB)
# tx3: input_C -> recipient_3 + change_3  (141 vB)
# Total: 423 vB

# Batch into 1 transaction:
# tx: input_A -> recipient_1 + recipient_2 + recipient_3 + change  (~203 vB)
# Savings: ~52%
```

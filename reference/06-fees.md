# Bitcoin Transaction Fees

Weight units, virtual bytes, fee rates, Replace-by-Fee (RBF), and Child-Pays-for-Parent (CPFP).

## Weight Units

Since SegWit activation, transaction size is measured in weight units (WU).

**Core formula:**
```
weight = base_size * 3 + total_size
```

- **base_size**: Transaction serialized WITHOUT witness data (legacy format)
- **total_size**: Transaction serialized WITH witness data (full SegWit format)

This means:
- **Non-witness bytes** (version, inputs, outputs, locktime) cost **4 WU each**
- **Witness bytes** (marker, flag, witness items) cost **1 WU each**

### Why the Discount?

Witness data gets a 75% discount because:
1. It can be pruned by non-archival nodes
2. It doesn't affect the UTXO set
3. The discount incentivizes SegWit adoption

## Virtual Bytes (vbytes)

```
vbytes = weight / 4  (round up)
```

Fee rates are expressed in **sat/vB** (satoshis per virtual byte).

### Size Comparison by Transaction Type

| Type | Typical Size | Typical Weight | Typical vbytes |
|------|-------------|---------------|---------------|
| P2PKH (1-in, 1-out) | 192 bytes | 768 WU | 192 vB |
| P2WPKH (1-in, 1-out) | 110 bytes | 273 WU | 69 vB |
| P2TR (1-in, 1-out) | 111 bytes | 234 WU | 59 vB |
| P2WPKH (1-in, 2-out) | 141 bytes | 357 WU | 90 vB |
| P2TR (1-in, 2-out) | 143 bytes | 318 WU | 80 vB |

P2TR is ~15% cheaper than P2WPKH, which is ~65% cheaper than P2PKH.

## Fee Calculation

```
fee = fee_rate_sat_per_vb * vbytes
```

**Critical mistake:** Using total byte size instead of virtual byte size. For a SegWit transaction, the total serialized size is larger than vbytes because witness data gets discounted.

### Example

A P2WPKH transaction:
- Total size: 222 bytes
- Base size (without witness): 146 bytes
- Weight: 146 * 3 + 222 = 660 WU
- vbytes: 660 / 4 = 165 vB

At 10 sat/vB: fee = 10 * 165 = 1,650 sats

**Wrong calculation:** 10 * 222 = 2,220 sats (overpaying by 35%)

## Fee Estimation

Bitcoin Core provides fee estimation via RPC:

```
bitcoin-cli estimatesmartfee 6
```

Returns estimated fee rate (BTC/kvB) to confirm within N blocks. Multiply by 100,000 to get sat/vB:

```json
{
  "feerate": 0.00012345,
  "blocks": 6
}
```
0.00012345 BTC/kvB = 12.345 sat/vB

### Fee Priority Tiers (rough guide, varies with network conditions)

| Priority | Target | Typical Range |
|----------|--------|--------------|
| Next block | 1 block | 20-200+ sat/vB |
| High | 2-3 blocks | 10-50 sat/vB |
| Medium | 6 blocks | 5-20 sat/vB |
| Low | 12-24 blocks | 1-10 sat/vB |
| Economy | 144 blocks (1 day) | 1-5 sat/vB |

These ranges vary enormously based on mempool congestion. During fee spikes, next-block can exceed 500 sat/vB.

## Replace-by-Fee (RBF) -- BIP125

Allows replacing an unconfirmed transaction with a higher-fee version.

### Signaling RBF

Set at least one input's sequence number to less than `0xfffffffe`:

```
sequence = 0xfffffffd  # Signals RBF, no relative timelock
sequence = 0xfffffffe  # Signals RBF (less than 0xffffffff), enables nLockTime
sequence = 0xffffffff  # FINAL -- does NOT signal RBF, disables nLockTime
```

### Replacement Rules (BIP125)

1. The original transaction must signal replaceability (sequence < 0xfffffffe)
2. The replacement must pay a **higher absolute fee** than the original
3. The replacement must pay a fee rate high enough to cover its own relay (minimum relay fee)
4. The replacement must not add more than 100 unconfirmed inputs
5. The additional fee must cover the minimum relay fee for the replacement's size

### Full RBF (Bitcoin Core 28.0+)

As of Bitcoin Core 28.0, full RBF is enabled by default (`mempoolfullrbf=1`). This means **any** unconfirmed transaction can be replaced, even without BIP125 signaling. However, some nodes and services may still only honor BIP125 opt-in RBF.

## Child-Pays-for-Parent (CPFP)

Instead of replacing a transaction, create a **child transaction** that spends one of the parent's outputs with a high enough fee to incentivize miners to confirm both.

```
Parent tx: 200 vB, fee = 200 sats (1 sat/vB -- too low)
Child tx:  100 vB, fee = 5,800 sats

Combined: 300 vB, total fee = 6,000 sats
Effective fee rate: 6,000 / 300 = 20 sat/vB -- good enough
```

### CPFP Carve-Out (BIP143 / package relay)

Bitcoin Core 28.0+ supports **package relay**, which evaluates parent+child as a unit for mempool admission. This means a parent transaction below the mempool minimum fee can still be accepted if accompanied by a high-fee child.

### When to Use RBF vs CPFP

| Scenario | Use |
|----------|-----|
| You sent the original tx and want to bump fee | RBF (cheaper, replaces the tx) |
| You are the **recipient** and want faster confirmation | CPFP (spend the output you received) |
| Original tx didn't signal RBF and sender is uncooperative | CPFP (only option pre-full-RBF) |
| Need to add/remove outputs | RBF (can change tx structure) |

## Dust Limit

Outputs below the dust threshold are rejected by default:

```
P2PKH:  546 sats
P2SH:   540 sats
P2WPKH: 294 sats
P2WSH:  330 sats
P2TR:   330 sats
```

The dust limit is calculated as: `3 * (output_size + input_size) * minRelayTxFee / 1000`

An output is "dust" if spending it would cost more in fees than it's worth.

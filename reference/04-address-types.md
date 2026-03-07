# Bitcoin Address Types

Complete reference for all 5 address types: encoding, derivation, prefixes, and real mainnet examples.

## Summary Table

| Type | Version | BIP | Mainnet Prefix | Testnet Prefix | Script Pattern | Encoding |
|------|---------|-----|----------------|----------------|---------------|----------|
| P2PKH | - | - | `1` | `m` or `n` | `OP_DUP OP_HASH160 <20B> OP_EQUALVERIFY OP_CHECKSIG` | Base58Check |
| P2SH | - | BIP16 | `3` | `2` | `OP_HASH160 <20B> OP_EQUAL` | Base58Check |
| P2WPKH | 0 | BIP141/BIP84 | `bc1q` | `tb1q` | `OP_0 <20B>` | Bech32 |
| P2WSH | 0 | BIP141 | `bc1q` | `tb1q` | `OP_0 <32B>` | Bech32 |
| P2TR | 1 | BIP341/BIP86 | `bc1p` | `tb1p` | `OP_1 <32B>` | Bech32m |

## P2PKH (Pay-to-Public-Key-Hash)

The original address type from Bitcoin's launch.

**Mainnet example:** `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` (Satoshi's genesis address)

**Derivation from public key:**

```
1. Start with compressed public key (33 bytes, starts with 02 or 03)
   pubkey = 0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798

2. HASH160 the public key
   hash = RIPEMD160(SHA256(pubkey))
   hash = 751e76e8199196d454941c45d1b3a323f1433bd6

3. Prepend version byte (0x00 for mainnet, 0x6f for testnet)
   versioned = 00751e76e8199196d454941c45d1b3a323f1433bd6

4. Double-SHA-256 the versioned payload, take first 4 bytes as checksum
   checksum = HASH256(versioned)[:4]
   checksum = c3e26988

5. Append checksum
   payload = 00751e76e8199196d454941c45d1b3a323f1433bd6c3e26988

6. Base58 encode
   address = 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
```

**scriptPubKey:** `76a914{hash160}88ac`

## P2SH (Pay-to-Script-Hash)

Locks funds to the hash of an arbitrary script. The spender reveals the script at spend time.

**Mainnet example:** `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`

**Derivation from redeem script:**

```
1. Start with the redeem script (e.g., a 2-of-3 multisig)
   redeemScript = 5221<pubkey1>21<pubkey2>21<pubkey3>53ae

2. HASH160 the redeem script
   hash = RIPEMD160(SHA256(redeemScript))

3. Prepend version byte (0x05 for mainnet, 0xc4 for testnet)

4. Append 4-byte checksum (first 4 bytes of double-SHA-256)

5. Base58 encode
```

**scriptPubKey:** `a914{hash160}87`

## P2WPKH (Pay-to-Witness-Public-Key-Hash)

SegWit v0 for single public key. Lower fees than P2PKH.

**Mainnet example:** `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`

**Derivation from public key:**

```
1. Start with compressed public key (33 bytes)
   pubkey = 0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798

2. HASH160 the public key
   hash = 751e76e8199196d454941c45d1b3a323f1433bd6

3. Bech32 encode with:
   - HRP (human-readable part): "bc" (mainnet) or "tb" (testnet)
   - Witness version: 0
   - Witness program: the 20-byte hash

   address = bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

**scriptPubKey:** `0014{hash160}` (OP_0 + push 20 bytes)

## P2WSH (Pay-to-Witness-Script-Hash)

SegWit v0 for arbitrary scripts. Uses SHA-256 (not HASH160).

**Mainnet example:** `bc1qrp33g0q5b5698ahp5jnf0y5ems08xka9r0fmhk2l0xr4e87y8gqpzpl0g`

**Derivation from witness script:**

```
1. Start with the witness script (e.g., multisig)

2. SHA-256 the witness script (NOT HASH160 -- this is different from P2SH!)
   hash = SHA256(witnessScript)  # 32 bytes

3. Bech32 encode with:
   - HRP: "bc" (mainnet) or "tb" (testnet)
   - Witness version: 0
   - Witness program: the 32-byte SHA-256 hash
```

**scriptPubKey:** `0020{sha256}` (OP_0 + push 32 bytes)

**Critical difference from P2SH:** P2WSH uses SHA-256 (32 bytes), not HASH160 (20 bytes). This provides 128-bit collision resistance vs 80-bit for HASH160.

## P2TR (Pay-to-Taproot)

Witness v1. Uses Schnorr signatures and Bech32m encoding.

**Mainnet example:** `bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3s7a`

**Derivation (key path, BIP86):**

```
1. Start with the internal public key (32 bytes, x-only -- no prefix byte)
   internal_key = <32 bytes>

2. Compute the tweak (BIP86 uses an empty script tree):
   t = tagged_hash("TapTweak", internal_key)

3. Compute the tweaked public key:
   output_key = internal_key + t*G  (point addition)

4. Take the x-coordinate of the output key (32 bytes)

5. Bech32m encode with:
   - HRP: "bc" (mainnet) or "tb" (testnet)
   - Witness version: 1
   - Witness program: the 32-byte tweaked x-only pubkey
```

**scriptPubKey:** `5120{tweaked_x_pubkey}` (OP_1 + push 32 bytes)

**Important:** P2TR uses Bech32**m** (BIP350), not Bech32. Using Bech32 for witness v1+ addresses will produce invalid addresses.

## Encoding Comparison

### Base58Check (P2PKH, P2SH)

```
Alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
(no 0, O, I, l to avoid visual ambiguity)

Format: Base58(version_byte + payload + checksum)
Checksum: first 4 bytes of HASH256(version_byte + payload)
```

### Bech32 (SegWit v0) -- BIP173

```
Alphabet: qpzry9x8gf2tvdw0s3jn54khce6mua7l
Format: HRP + "1" + data + 6-char checksum
HRP: "bc" (mainnet), "tb" (testnet), "bcrt" (regtest)
```

### Bech32m (SegWit v1+) -- BIP350

Same format as Bech32 but with a different checksum constant (0x2bc830a3 instead of 0x01). This was introduced to fix an error detection weakness in Bech32 for certain lengths.

| Witness Version | Encoding |
|----------------|----------|
| 0 | Bech32 |
| 1-16 | Bech32m |

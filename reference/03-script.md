# Bitcoin Script

Stack-based scripting language reference covering opcodes, standard script patterns, and execution semantics.

## Execution Model

Bitcoin Script is a stack-based, Forth-like language. It is intentionally **not Turing-complete** (no loops).

Execution flow for spending:
1. Execute the **scriptSig** (unlocking script) -- pushes data onto the stack
2. Copy the stack to a new execution context
3. Execute the **scriptPubKey** (locking script) against the copied stack
4. Transaction is valid if the top stack element is truthy (non-zero) and execution did not abort

For P2SH, there is an additional step where the serialized redeem script is deserialized and executed.

For SegWit (v0 and v1), the witness program is interpreted directly by consensus rules rather than through the general script interpreter.

## Standard Script Patterns

### P2PKH (Pay-to-Public-Key-Hash)

Locks to a public key hash. The spender must provide a signature and the full public key.

**scriptPubKey:**
```
OP_DUP OP_HASH160 <20-byte-pubkey-hash> OP_EQUALVERIFY OP_CHECKSIG
76      a9         14 <hash>              88              ac
```

**scriptSig:**
```
<signature> <pubkey>
```

Hex template: `76a914{hash160}88ac`

### P2SH (Pay-to-Script-Hash) -- BIP16

Locks to the hash of a redeem script. Enables complex spending conditions.

**scriptPubKey:**
```
OP_HASH160 <20-byte-script-hash> OP_EQUAL
a9         14 <hash>              87
```

**scriptSig:**
```
<...signatures and data...> <serialized-redeem-script>
```

Hex template: `a914{hash160}87`

### P2WPKH (Pay-to-Witness-Public-Key-Hash) -- BIP141, Witness v0

**scriptPubKey:**
```
OP_0 <20-byte-pubkey-hash>
00   14 <hash>
```

**scriptSig:** Empty (must be empty for SegWit)

**Witness:**
```
<signature> <pubkey>
```

Hex template: `0014{hash160}`

### P2WSH (Pay-to-Witness-Script-Hash) -- BIP141, Witness v0

**scriptPubKey:**
```
OP_0 <32-byte-script-hash>
00   20 <SHA256-of-witness-script>
```

Note: P2WSH uses SHA-256 (not HASH160) of the witness script.

Hex template: `0020{sha256}`

### P2TR (Pay-to-Taproot) -- BIP341, Witness v1

**scriptPubKey:**
```
OP_1 <32-byte-tweaked-pubkey>
51   20 <key>
```

Spending via key path: witness contains a single Schnorr signature (64 or 65 bytes).

Spending via script path: witness contains script inputs, the script itself, and the control block.

Hex template: `5120{tweaked_pubkey}`

### OP_RETURN (Data Embedding)

**scriptPubKey:**
```
OP_RETURN <data>
6a       <push-opcodes + data>
```

Provably unspendable. Used for embedding arbitrary data (up to 80 bytes standardness limit). The output value should be 0.

## Opcodes Reference

### Constants

| Hex | Name | Description |
|-----|------|-------------|
| 0x00 | OP_0 / OP_FALSE | Push empty byte array (falsy) |
| 0x01 - 0x4b | N/A | Push next N bytes onto stack (direct push) |
| 0x4c | OP_PUSHDATA1 | Next 1 byte is length, then push that many bytes |
| 0x4d | OP_PUSHDATA2 | Next 2 bytes (LE) is length, then push that many bytes |
| 0x4e | OP_PUSHDATA4 | Next 4 bytes (LE) is length, then push that many bytes |
| 0x4f | OP_1NEGATE | Push -1 |
| 0x51 - 0x60 | OP_1 through OP_16 | Push number 1-16 |

### Flow Control

| Hex | Name | Description |
|-----|------|-------------|
| 0x61 | OP_NOP | No operation |
| 0x63 | OP_IF | Execute if top stack is truthy |
| 0x64 | OP_NOTIF | Execute if top stack is falsy |
| 0x67 | OP_ELSE | Alternate branch |
| 0x68 | OP_ENDIF | End conditional |
| 0x69 | OP_VERIFY | Fail if top stack is falsy |
| 0x6a | OP_RETURN | Mark transaction as invalid (used for data embedding) |

### Stack Operations

| Hex | Name | Description |
|-----|------|-------------|
| 0x75 | OP_DROP | Remove top stack item |
| 0x76 | OP_DUP | Duplicate top stack item |
| 0x6b | OP_TOALTSTACK | Move top item to alt stack |
| 0x6c | OP_FROMALTSTACK | Move top alt stack item to main stack |
| 0x73 | OP_IFDUP | Duplicate if truthy |
| 0x77 | OP_NIP | Remove second-to-top item |
| 0x78 | OP_OVER | Copy second-to-top to top |
| 0x7a | OP_ROLL | Move item N deep to top |
| 0x79 | OP_SWAP | Swap top two items |
| 0x7b | OP_ROT | Rotate top three items |
| 0x7c | OP_2DROP | Remove top two items |
| 0x7d | OP_2DUP | Duplicate top two items |
| 0x7e | OP_3DUP | Duplicate top three items |

### Arithmetic

| Hex | Name | Description |
|-----|------|-------------|
| 0x8b | OP_ADD | a + b |
| 0x8c | OP_SUB | a - b |
| 0x87 | OP_EQUAL | Push 1 if equal, else 0 |
| 0x88 | OP_EQUALVERIFY | OP_EQUAL + OP_VERIFY |
| 0x9c | OP_NUMEQUAL | Push 1 if numbers equal |
| 0xa0 | OP_GREATERTHAN | Push 1 if a > b |
| 0x9f | OP_LESSTHAN | Push 1 if a < b |
| 0xa4 | OP_MAX | Push larger of a, b |
| 0xa3 | OP_MIN | Push smaller of a, b |

### Crypto

| Hex | Name | Description |
|-----|------|-------------|
| 0xa6 | OP_RIPEMD160 | RIPEMD-160 hash |
| 0xa7 | OP_SHA1 | SHA-1 hash |
| 0xa8 | OP_SHA256 | SHA-256 hash |
| 0xa9 | OP_HASH160 | SHA-256 then RIPEMD-160 |
| 0xaa | OP_HASH256 | Double SHA-256 |
| 0xac | OP_CHECKSIG | Verify signature against pubkey |
| 0xad | OP_CHECKSIGVERIFY | OP_CHECKSIG + OP_VERIFY |
| 0xae | OP_CHECKMULTISIG | M-of-N multisig verification |
| 0xaf | OP_CHECKMULTISIGVERIFY | OP_CHECKMULTISIG + OP_VERIFY |
| 0xba | OP_CHECKSIGADD | BIP342 Tapscript: increment counter if sig valid |

### Locktime

| Hex | Name | Description |
|-----|------|-------------|
| 0xb1 | OP_CHECKLOCKTIMEVERIFY (OP_CLTV) | BIP65: fail if locktime not reached |
| 0xb2 | OP_CHECKSEQUENCEVERIFY (OP_CSV) | BIP112: fail if relative timelock not met |

## Data Push Rules

This is a common source of bugs:

| Data Length | Method |
|------------|--------|
| 0 bytes | OP_0 (0x00) |
| 1-75 bytes | Direct push: single byte length prefix (0x01-0x4b) followed by data |
| 76-255 bytes | OP_PUSHDATA1 (0x4c) + 1-byte length + data |
| 256-65535 bytes | OP_PUSHDATA2 (0x4d) + 2-byte length (LE) + data |
| 65536+ bytes | OP_PUSHDATA4 (0x4e) + 4-byte length (LE) + data |

**Important:** Using OP_PUSHDATA1 for data shorter than 76 bytes is non-standard (though valid). Always use the minimal push opcode.

## Script Size Limits

- Maximum script size: 10,000 bytes (legacy), no limit for SegWit witness scripts
- Maximum stack element size: 520 bytes (legacy/witness v0), 80 bytes for OP_RETURN data
- Maximum number of non-push opcodes per script: 201 (legacy)
- Maximum stack size: 1,000 elements
- Tapscript (witness v1): removes the 201 opcode limit and the 10,000 byte script limit

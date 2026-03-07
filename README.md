# Bitcoin for LLMs

A structured Bitcoin protocol reference optimized for AI/LLM context windows.

## The Problem

LLMs make Bitcoin coding mistakes because:

- Training data mixes outdated protocol info with current specs
- Byte order conventions (internal vs display) are routinely confused
- Satoshi/BTC conversions introduce floating point errors
- Witness data handling changed fundamentals that older examples ignore
- RPC interfaces evolve across versions with subtle breaking changes

This repository provides authoritative, structured reference material that can be dropped into an LLM context window to dramatically reduce these errors.

## How to Use

**Option 1: Full context injection**
Copy `claude-context.md` into your project's `CLAUDE.md` or system prompt. This single file (~15K tokens) covers the most critical patterns and pitfalls.

**Option 2: RAG / selective retrieval**
Use individual reference files for retrieval-augmented generation. Each file starts with a one-line summary for snippet extraction.

**Option 3: Example code**
The `examples/` directory contains working Python scripts for common Bitcoin operations with no external dependencies (except RPC).

## Reference Files

| File | Contents |
|------|----------|
| [01-data-types.md](reference/01-data-types.md) | Byte orders, CompactSize, hash types, integer sizes |
| [02-transaction.md](reference/02-transaction.md) | Legacy and SegWit transaction formats, byte-by-byte decoding |
| [03-script.md](reference/03-script.md) | Script opcodes, standard patterns (P2PKH, P2SH, P2WPKH, P2WSH, P2TR) |
| [04-address-types.md](reference/04-address-types.md) | All 5 address types with derivation steps and encoding |
| [05-blocks.md](reference/05-blocks.md) | Block headers, coinbase transactions, merkle trees, difficulty |
| [06-fees.md](reference/06-fees.md) | Weight units, vbytes, fee rates, RBF, CPFP |
| [07-rpc-reference.md](reference/07-rpc-reference.md) | 20 most-used RPCs with example input/output |
| [08-common-patterns.md](reference/08-common-patterns.md) | UTXO consolidation, batching, multisig, timelocks, coin selection |
| [09-error-patterns.md](reference/09-error-patterns.md) | Top 10 mistakes LLMs make when writing Bitcoin code |
| [10-testing.md](reference/10-testing.md) | Regtest, signet, test frameworks, validation patterns |

## Examples

| File | Description |
|------|-------------|
| [decode-tx.py](examples/decode-tx.py) | Decode raw transaction hex field-by-field (no dependencies) |
| [build-tx.py](examples/build-tx.py) | Construct a P2WPKH transaction from scratch |
| [fee-estimate.py](examples/fee-estimate.py) | Query Bitcoin Core RPC for fee estimates and mempool info |

## Context File

| File | Description |
|------|-------------|
| [claude-context.md](claude-context.md) | Single-file Bitcoin reference for LLM system prompts (~15K tokens) |

## Contributing

PRs welcome. Priority areas:
- Additional real mainnet transaction examples
- Taproot script path spending examples
- Lightning Network basics reference
- More error patterns from real LLM failures

## License

MIT

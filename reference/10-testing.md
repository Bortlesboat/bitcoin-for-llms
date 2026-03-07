# Bitcoin Testing

Regtest, signet, testmempoolaccept, and testing patterns for Bitcoin development.

## Network Comparison

| Network | Purpose | Block Time | Mining | Coins Worth |
|---------|---------|-----------|--------|-------------|
| mainnet | Production | ~10 min | Real PoW | Real value |
| testnet3 | Public testing | ~10 min | Easy PoW | Worthless (faucets) |
| testnet4 | Public testing (BIP94) | ~10 min | Easy PoW | Worthless |
| signet | Controlled testing | ~10 min | Signed blocks | Worthless (faucets) |
| regtest | Local testing | Instant (on demand) | `generatetoaddress` | No network |

## Regtest (Regression Test)

The fastest way to test. You control block creation entirely.

### Setup

```bash
# Start regtest daemon
bitcoind -regtest -daemon

# Or with a custom datadir
bitcoind -regtest -datadir=/tmp/btc-test -daemon
```

### Essential Commands

```bash
# Create a wallet
bitcoin-cli -regtest createwallet "test"

# Get a new address
ADDR=$(bitcoin-cli -regtest getnewaddress "" bech32m)

# Mine 101 blocks (first 100 coinbases need to mature before spending)
bitcoin-cli -regtest generatetoaddress 101 "$ADDR"

# Check balance
bitcoin-cli -regtest getbalance
# 50.00000000 (only block 1's coinbase is mature)

# Send coins
bitcoin-cli -regtest sendtoaddress "bcrt1q..." 1.0

# Mine a block to confirm
bitcoin-cli -regtest generatetoaddress 1 "$ADDR"
```

### Why 101 Blocks?

Coinbase outputs require 100 confirmations before they can be spent (consensus rule). Mining 101 blocks means the first block's coinbase (50 BTC) has exactly 100 confirmations and is spendable.

### Multiple Nodes

```bash
# Node 1 (default ports)
bitcoind -regtest -daemon -port=18444 -rpcport=18443

# Node 2 (different ports, different datadir)
bitcoind -regtest -daemon -datadir=/tmp/node2 -port=18544 -rpcport=18543

# Connect them
bitcoin-cli -regtest addnode "127.0.0.1:18544" add
```

## Signet

A centralized testnet where blocks are signed by a trusted authority. More stable than testnet (no wild difficulty swings or block storms).

### Default Signet

```bash
bitcoind -signet -daemon
bitcoin-cli -signet getblockchaininfo
```

Default signet faucet: https://signetfaucet.com/

### Custom Signet

You can run your own signet with your own block signer:

```bash
# Generate a signing key
bitcoin-cli -regtest getnewaddress "" bech32m
PRIVKEY=$(bitcoin-cli -regtest dumpprivkey "$ADDR")

# Configure custom signet
bitcoind -signet -signetchallenge=<script_hex> -daemon
```

## testmempoolaccept

Validates a signed transaction against all mempool and consensus rules without broadcasting. Essential for pre-flight checks.

```bash
bitcoin-cli testmempoolaccept '["<signed_tx_hex>"]'
```

### Success Response

```json
[{
  "txid": "abc123...",
  "wtxid": "def456...",
  "allowed": true,
  "vsize": 141,
  "fees": {
    "base": 0.00001410
  }
}]
```

### Failure Response

```json
[{
  "txid": "abc123...",
  "allowed": false,
  "reject-reason": "min relay fee not met, 0 < 141"
}]
```

### Common Rejection Reasons

| reject-reason | Cause |
|--------------|-------|
| `missing-inputs` | Referenced UTXO doesn't exist or already spent |
| `txn-mempool-conflict` | Conflicts with existing mempool transaction |
| `insufficient fee` | Fee below mempool minimum |
| `min relay fee not met` | Fee below minimum relay fee |
| `bad-txns-inputs-missingorspent` | Input references a spent output |
| `non-mandatory-script-verify-flag` | Script validation failed |
| `dust` | Output below dust threshold |
| `non-BIP68-final` | Relative timelock not satisfied |
| `bad-txns-in-belowout` | Sum of inputs < sum of outputs |

**Best practice:** Always call `testmempoolaccept` before `sendrawtransaction`. It catches errors without risking broadcast of an invalid transaction.

## Bitcoin Core Functional Test Framework

Bitcoin Core includes a Python test framework in `test/functional/`.

### Running Tests

```bash
# Run a single test
test/functional/wallet_basic.py

# Run all tests
test/functional/test_runner.py

# Run with specific options
test/functional/wallet_basic.py --loglevel=DEBUG --tmpdir=/tmp/test
```

### Writing a Test

```python
#!/usr/bin/env python3
"""Example functional test."""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal

class ExampleTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True

    def run_test(self):
        self.log.info("Mining blocks...")
        self.generate(self.nodes[0], 101)

        self.log.info("Sending transaction...")
        addr = self.nodes[1].getnewaddress()
        txid = self.nodes[0].sendtoaddress(addr, 1.0)

        self.log.info("Mining to confirm...")
        self.generate(self.nodes[0], 1)

        # Verify
        tx = self.nodes[1].gettransaction(txid)
        assert_equal(tx["confirmations"], 1)

        self.log.info("Test passed!")

if __name__ == '__main__':
    ExampleTest(__file__).main()
```

### Key Test Framework Methods

```python
# Mining
self.generate(node, nblocks)            # Mine blocks (preferred over generatetoaddress)
self.generateblock(node, addr, txlist)  # Mine specific transactions

# Connections
self.connect_nodes(0, 1)               # Connect node 0 to node 1
self.disconnect_nodes(0, 1)            # Disconnect

# Sync
self.sync_all()                        # Wait for all nodes to sync
self.sync_blocks()                     # Sync blocks only
self.sync_mempools()                   # Sync mempools only

# Assertions
assert_equal(a, b)                     # Exact equality
assert_greater_than(a, b)             # a > b
assert_raises_rpc_error(code, msg, func, *args)  # Expect RPC error
```

## Common Test Patterns

### Testing Transaction Validation

```python
def test_invalid_tx(self):
    """Verify that an invalid transaction is rejected."""
    node = self.nodes[0]
    self.generate(node, 101)

    # Create a raw transaction
    utxo = node.listunspent()[0]
    inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]
    outputs = {node.getnewaddress(): utxo["amount"] - Decimal("0.001")}
    raw = node.createrawtransaction(inputs, outputs)
    signed = node.signrawtransactionwithwallet(raw)

    # Validate before broadcast
    result = node.testmempoolaccept([signed["hex"]])
    assert result[0]["allowed"]

    # Broadcast
    txid = node.sendrawtransaction(signed["hex"])
    assert txid in node.getrawmempool()
```

### Testing RBF

```python
def test_rbf(self):
    """Test Replace-by-Fee."""
    node = self.nodes[0]
    self.generate(node, 101)

    # Send with RBF signaled (sequence < 0xfffffffe)
    utxo = node.listunspent()[0]
    addr = node.getnewaddress()

    # Original tx with low fee
    raw1 = node.createrawtransaction(
        [{"txid": utxo["txid"], "vout": utxo["vout"], "sequence": 0xfffffffd}],
        {addr: utxo["amount"] - Decimal("0.0001")}
    )
    signed1 = node.signrawtransactionwithwallet(raw1)
    txid1 = node.sendrawtransaction(signed1["hex"])

    # Replacement tx with higher fee
    raw2 = node.createrawtransaction(
        [{"txid": utxo["txid"], "vout": utxo["vout"], "sequence": 0xfffffffd}],
        {addr: utxo["amount"] - Decimal("0.001")}  # Higher fee
    )
    signed2 = node.signrawtransactionwithwallet(raw2)
    txid2 = node.sendrawtransaction(signed2["hex"])

    # Original should be replaced
    mempool = node.getrawmempool()
    assert txid1 not in mempool
    assert txid2 in mempool
```

### Testing with P2WSH Scripts

```python
def test_p2wsh(self):
    """Test custom witness script spending."""
    node = self.nodes[0]
    self.generate(node, 101)

    # Create a simple script: <pubkey> OP_CHECKSIG
    pubkey = node.getaddressinfo(node.getnewaddress())["pubkey"]
    witness_script = CScript([bytes.fromhex(pubkey), OP_CHECKSIG])

    # Compute P2WSH address
    script_hash = sha256(witness_script)
    scriptPubKey = CScript([OP_0, script_hash])

    # Fund the P2WSH output
    addr = script_to_p2wsh(witness_script)
    txid = node.sendtoaddress(addr, 1.0)
    self.generate(node, 1)

    # Spend it with the witness
    # ... (construct spending tx with witness containing signature + witness_script)
```

## Quick Reference: Testing Checklist

Before submitting any Bitcoin transaction code:

1. Test on regtest first (instant blocks, free coins)
2. Use `testmempoolaccept` before `sendrawtransaction`
3. Verify TXID byte order (display vs internal)
4. Verify all values are in satoshis (no floats)
5. Verify fee is reasonable (`estimatesmartfee` or manual calculation)
6. Verify change output exists and is above dust limit
7. Verify signature includes sighash byte
8. Test edge cases: dust outputs, maximum weight, timelocks
9. Test on signet before mainnet for anything non-trivial
10. Never test on mainnet with significant funds

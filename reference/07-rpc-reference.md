# Bitcoin Core RPC Reference

The 20 most-used RPC commands with example inputs and outputs for Bitcoin Core v27+.

## Connection

Default RPC endpoint: `http://127.0.0.1:8332` (mainnet), `:18332` (testnet), `:18443` (regtest).

Authentication: via cookie file (`~/.bitcoin/.cookie`) or `rpcuser`/`rpcpassword` in `bitcoin.conf`.

```bash
# Using bitcoin-cli (reads cookie automatically)
bitcoin-cli getblockchaininfo

# Using curl
curl --user user:password --data-binary \
  '{"jsonrpc":"1.0","method":"getblockchaininfo","params":[]}' \
  -H 'content-type:text/plain;' http://127.0.0.1:8332/
```

---

## Blockchain

### getblockchaininfo

Returns current blockchain state.

```bash
bitcoin-cli getblockchaininfo
```

```json
{
  "chain": "main",
  "blocks": 830000,
  "headers": 830000,
  "bestblockhash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670",
  "difficulty": 72006146478564.96,
  "time": 1709236145,
  "mediantime": 1709233568,
  "verificationprogress": 0.9999989,
  "initialblockdownload": false,
  "chainwork": "000000000000000000000000000000000000000069d28a3c4e0a0e21e1b1ca38",
  "size_on_disk": 619854102528,
  "pruned": false
}
```

### getblockcount

Returns the height of the most-work fully-validated chain.

```bash
bitcoin-cli getblockcount
```

```
830000
```

### getblockhash

Returns the block hash at a given height.

```bash
bitcoin-cli getblockhash 0
```

```
"000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
```

### getblock

Returns block data. Verbosity: 0=hex, 1=JSON, 2=JSON with decoded txs.

```bash
bitcoin-cli getblock "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f" 1
```

```json
{
  "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
  "confirmations": 830001,
  "height": 0,
  "version": 1,
  "merkleroot": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
  "time": 1231006505,
  "nonce": 2083236893,
  "bits": "1d00ffff",
  "difficulty": 1,
  "nTx": 1,
  "tx": [
    "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
  ]
}
```

---

## Transactions

### getrawtransaction

Returns raw transaction data. Requires `txindex=1` for non-wallet transactions (or the tx must be in mempool).

```bash
# Get hex
bitcoin-cli getrawtransaction "txid"

# Get decoded JSON
bitcoin-cli getrawtransaction "txid" true
```

```json
{
  "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
  "hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
  "version": 1,
  "size": 275,
  "vsize": 275,
  "weight": 1100,
  "locktime": 0,
  "vin": [
    {
      "txid": "0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9",
      "vout": 0,
      "scriptSig": {
        "asm": "304402204e45e16932b8af514961...",
        "hex": "47304402204e45e16932b8af514961..."
      },
      "sequence": 4294967295
    }
  ],
  "vout": [
    {
      "value": 10.00000000,
      "n": 0,
      "scriptPubKey": {
        "asm": "04ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84c OP_CHECKSIG",
        "hex": "4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac",
        "type": "pubkey"
      }
    },
    {
      "value": 40.00000000,
      "n": 1,
      "scriptPubKey": {
        "type": "pubkey"
      }
    }
  ]
}
```

### decoderawtransaction

Decodes a raw hex transaction without requiring txindex.

```bash
bitcoin-cli decoderawtransaction "0200000001..."
```

Returns the same JSON structure as `getrawtransaction` with `verbose=true`.

### sendrawtransaction

Broadcasts a signed raw transaction to the network.

```bash
bitcoin-cli sendrawtransaction "signed_tx_hex"
```

Returns the TXID on success. Fails if the transaction is invalid or conflicts with mempool policy.

Optional parameter: `maxfeerate` (BTC/kvB) -- rejects if fee rate exceeds this (safety check).

```bash
bitcoin-cli sendrawtransaction "hex" 0.10  # Reject if > 0.10 BTC/kvB
```

### testmempoolaccept

Validates a transaction against mempool policy WITHOUT broadcasting.

```bash
bitcoin-cli testmempoolaccept '["signed_tx_hex"]'
```

```json
[
  {
    "txid": "abc123...",
    "wtxid": "def456...",
    "allowed": true,
    "vsize": 141,
    "fees": {
      "base": 0.00001410
    }
  }
]
```

If rejected:
```json
[
  {
    "txid": "abc123...",
    "allowed": false,
    "reject-reason": "insufficient fee"
  }
]
```

**Best practice:** Always call `testmempoolaccept` before `sendrawtransaction`.

---

## Mempool

### getmempoolinfo

Returns mempool statistics.

```bash
bitcoin-cli getmempoolinfo
```

```json
{
  "loaded": true,
  "size": 45123,
  "bytes": 23456789,
  "usage": 98765432,
  "total_fee": 1.23456789,
  "maxmempool": 300000000,
  "mempoolminfee": 0.00001000,
  "minrelaytxfee": 0.00001000,
  "incrementalrelayfee": 0.00001000,
  "unbroadcastcount": 0,
  "fullrbf": true
}
```

### getrawmempool

Returns all transaction IDs in the mempool.

```bash
# Just TXIDs
bitcoin-cli getrawmempool

# With fee info
bitcoin-cli getrawmempool true
```

---

## Fee Estimation

### estimatesmartfee

Estimates fee rate for confirmation within N blocks.

```bash
bitcoin-cli estimatesmartfee 6
```

```json
{
  "feerate": 0.00015678,
  "blocks": 6
}
```

The `feerate` is in **BTC/kvB** (BTC per 1000 virtual bytes). Convert to sat/vB:

```
sat_per_vb = feerate * 100_000_000 / 1000 = feerate * 100_000
0.00015678 BTC/kvB = 15.678 sat/vB
```

Optional modes: `"ECONOMICAL"` (default) or `"CONSERVATIVE"`.

---

## UTXO Set

### gettxout

Returns details about an unspent transaction output.

```bash
bitcoin-cli gettxout "txid" 0
```

```json
{
  "bestblock": "00000000000000000002...",
  "confirmations": 5,
  "value": 0.01000000,
  "scriptPubKey": {
    "asm": "0 751e76e8199196d454941c45d1b3a323f1433bd6",
    "hex": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
    "type": "witness_v0_keyhash",
    "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
  },
  "coinbase": false
}
```

Returns `null` if the output has been spent or doesn't exist.

### scantxoutset

Scans the UTXO set for outputs matching descriptors. Useful for finding funds without a wallet.

```bash
bitcoin-cli scantxoutset start '["addr(bc1q...)", "addr(1A1z...)"]'
```

```json
{
  "success": true,
  "txouts": 123456789,
  "height": 830000,
  "bestblock": "00000000...",
  "unspents": [
    {
      "txid": "abc...",
      "vout": 0,
      "scriptPubKey": "0014...",
      "desc": "addr(bc1q...)#checksum",
      "amount": 0.50000000,
      "coinbase": false,
      "height": 829500
    }
  ],
  "total_amount": 0.50000000
}
```

---

## Validation

### validateaddress

Validates a Bitcoin address and returns information about it.

```bash
bitcoin-cli validateaddress "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
```

```json
{
  "isvalid": true,
  "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
  "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
  "isscript": false,
  "iswitness": true,
  "witness_version": 0,
  "witness_program": "751e76e8199196d454941c45d1b3a323f1433bd6"
}
```

### decodescript

Decodes a hex-encoded script.

```bash
bitcoin-cli decodescript "76a914751e76e8199196d454941c45d1b3a323f1433bd688ac"
```

```json
{
  "asm": "OP_DUP OP_HASH160 751e76e8199196d454941c45d1b3a323f1433bd6 OP_EQUALVERIFY OP_CHECKSIG",
  "type": "pubkeyhash",
  "address": "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH",
  "p2sh": "3LHMqwrrFFfBcTm3wfSTcmHNbQFsNq3qkH"
}
```

---

## Network

### getpeerinfo

Returns information about connected peers.

```bash
bitcoin-cli getpeerinfo
```

Returns an array of peer objects with address, version, services, latency, etc.

### getnetworkinfo

Returns network state information.

```bash
bitcoin-cli getnetworkinfo
```

```json
{
  "version": 270000,
  "subversion": "/Satoshi:27.0.0/",
  "protocolversion": 70016,
  "connections": 125,
  "connections_in": 117,
  "connections_out": 8,
  "relayfee": 0.00001000,
  "incrementalfee": 0.00001000,
  "localaddresses": []
}
```

---

## Transaction Construction

### createrawtransaction

Creates an unsigned raw transaction.

```bash
bitcoin-cli createrawtransaction \
  '[{"txid":"input_txid","vout":0}]' \
  '[{"bc1q...":0.01},{"bc1q...":0.48}]'
```

Returns unsigned transaction hex. Amounts are in BTC.

**Important:** You must manually calculate change. The difference between input value and output value becomes the fee. Forgetting a change output sends the difference to miners.

### signrawtransactionwithkey

Signs a raw transaction with provided private keys.

```bash
bitcoin-cli signrawtransactionwithkey "unsigned_hex" '["privkey_WIF"]'
```

```json
{
  "hex": "02000000...",
  "complete": true
}
```

If `complete` is `false`, not all inputs could be signed with the provided keys.

---

## Mining (Regtest)

### getblocktemplate

Returns a block template for mining. Used by mining pools.

```bash
bitcoin-cli getblocktemplate '{"rules":["segwit"]}'
```

Returns a large JSON object with transactions to include, target, etc.

For regtest testing, use `generatetoaddress` instead:

```bash
bitcoin-cli -regtest generatetoaddress 101 "bcrt1q..."
```

Generates 101 blocks (100 to mature the first coinbase + 1) and returns block hashes.

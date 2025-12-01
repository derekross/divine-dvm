# What's Hot on diVine

A Nostr Data Vending Machine (DVM) that serves trending videos from [diVine](https://divine.video).

## What is this?

This DVM responds to **kind 5300** (Content Discovery) job requests and returns the hottest videos from diVine, ranked by engagement and recency using the NIP-50 `sort:hot` algorithm.

## Quick Start

```bash
# Clone and enter directory
cd divine-dvm

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env and add your NOSTR_PRIVATE_KEY

# Run
python -m divine_dvm.main
```

## Generate a Key

```bash
python -c "from nostr_sdk import Keys; k = Keys.generate(); print(f'NOSTR_PRIVATE_KEY={k.secret_key().to_bech32()}')"
```

## Configuration

Edit `.env`:

```bash
# Required
NOSTR_PRIVATE_KEY=nsec1...

# Optional
DVM_NAME=What's Hot on diVine
DVM_IDENTIFIER=divine-hot-videos
MAX_RESULTS=20
DIVINE_RELAY=wss://relay.divine.video
```

## How It Works

1. DVM listens for `kind:5300` job requests on Nostr relays
2. When a request arrives, it queries `wss://relay.divine.video` with NIP-50 search `sort:hot`
3. Returns `kind:6300` results with addressable event tags pointing to hot videos

## Job Request Format

```json
{
  "kind": 5300,
  "content": "",
  "tags": [
    ["i", "hot videos", "text"],
    ["p", "<DVM_PUBKEY>"],
    ["param", "max_results", "10"]
  ]
}
```

## Response Format

```json
{
  "kind": 6300,
  "content": "[[\"a\", \"34236:<pubkey>:<d-tag>\", \"wss://relay.divine.video\"], ...]"
}
```

## Production Deployment

See [PLAN.md](PLAN.md) for systemd, Docker, and PM2 deployment options.

## License

MIT

## Links

- [diVine](https://divine.video)
- [NIP-90: Data Vending Machines](https://github.com/nostr-protocol/nips/blob/master/90.md)
- [nostrdvm Framework](https://github.com/believethehype/nostrdvm)

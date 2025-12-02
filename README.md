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

## Running as a System Service

### Setup

```bash
# Create a dedicated user (optional but recommended)
sudo useradd -r -s /bin/false dvm

# Copy project to /opt
sudo cp -r . /opt/divine-dvm
sudo chown -R dvm:dvm /opt/divine-dvm

# Create virtual environment and install
cd /opt/divine-dvm
sudo -u dvm python -m venv .venv
sudo -u dvm .venv/bin/pip install -e .

# Configure environment
sudo cp .env.example .env
sudo nano .env  # Add your NOSTR_PRIVATE_KEY
sudo chown dvm:dvm .env
sudo chmod 600 .env
```

### Create the Service File

```bash
sudo nano /etc/systemd/system/divine-dvm.service
```

```ini
[Unit]
Description=What's Hot on diVine DVM
After=network.target

[Service]
Type=simple
User=dvm
Group=dvm
WorkingDirectory=/opt/divine-dvm
ExecStart=/opt/divine-dvm/.venv/bin/python -m divine_dvm.main
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/divine-dvm

[Install]
WantedBy=multi-user.target
```

### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable divine-dvm

# Start the service
sudo systemctl start divine-dvm

# Check status
sudo systemctl status divine-dvm

# View logs
sudo journalctl -u divine-dvm -f
```

### Management Commands

```bash
sudo systemctl stop divine-dvm      # Stop
sudo systemctl restart divine-dvm   # Restart
sudo systemctl status divine-dvm    # Status
sudo journalctl -u divine-dvm -n 50 # Last 50 log lines
```

## License

MIT

## Links

- [diVine](https://divine.video)
- [NIP-90: Data Vending Machines](https://github.com/nostr-protocol/nips/blob/master/90.md)
- [nostrdvm Framework](https://github.com/believethehype/nostrdvm)

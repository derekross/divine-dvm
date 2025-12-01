# DVM Plan: "What's Hot on diVine"

A Nostr Data Vending Machine (NIP-90) that serves the hot video feed from diVine.

## Overview

This DVM will:
1. Listen for job requests on Nostr relays
2. Query `wss://relay.divine.video` for hot videos using NIP-50 search
3. Return video event references as DVM results
4. Announce itself via NIP-89 for discoverability

---

## Part 1: Technical Specifications

### DVM Kind

- **Request Kind**: `5300` (Content Discovery)
- **Result Kind**: `6300` (Content Discovery Result)
- **Feedback Kind**: `7000` (Job Feedback)

Kind 5300 is the standard for "Nostr content a user might be interested in" - perfect for a hot video feed.

### Video Event Kind

- **Kind 34236**: Addressable short-form video (used by diVine)
  - Note: This is a custom kind used by diVine for TikTok-style videos
  - Standard NIP-71 defines kind 21 (normal) and 22 (short), but diVine uses 34236

### NIP-50 Query Format

From the divine-web analysis, the hot feed query is:
```python
{
  "kinds": [34236],
  "limit": 20,
  "search": "sort:hot"
}
```

### Relay Configuration

- **Source Relay**: `wss://relay.divine.video` (NIP-50 enabled)
- **Listening Relays**: Standard DVM relays + divine relay

---

## Part 2: Language & Framework

### Chosen: Python with nostrdvm

**Rationale:**
1. **nostrdvm framework** provides complete DVM infrastructure out of the box
2. Handles NIP-89/NIP-90 compliance automatically
3. Built-in job request handling, relay management, feedback events
4. Many existing content discovery examples to reference
5. Battle-tested in production

### Dependencies

```toml
[project]
dependencies = [
    "nostr-dvm>=1.1.0",
    "python-dotenv>=1.0.0",
]
```

The nostrdvm package brings:
- `nostr-sdk` (Rust bindings for Python)
- Event signing and publishing
- Subscription management
- NIP-89 announcement utilities

---

## Part 3: Project Structure

```
divine-dvm/
├── src/
│   └── divine_dvm/
│       ├── __init__.py
│       ├── main.py              # Entry point
│       └── tasks/
│           ├── __init__.py
│           └── hot_videos.py    # DVM task implementation
├── pyproject.toml
├── .env.example
├── .gitignore
├── PLAN.md
└── README.md
```

---

## Part 4: Implementation Details

### Core Task Class (`hot_videos.py`)

The `DiscoverHotVideos` class extends `DVMTaskInterface`:

```python
class DiscoverHotVideos(DVMTaskInterface):
    KIND = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY  # 5300
    TASK = "discover-content"
    FIX_COST = 0  # Free service
```

Key methods:
- `init_dvm()` - Initialize configuration
- `is_input_supported()` - Validate input tags
- `create_request_from_nostr_event()` - Parse job parameters
- `process()` - Query divine relay and return results
- `post_process()` - Optional text formatting

### NIP-50 Query Logic

```python
async def _query_hot_videos(self, limit: int):
    client = Client()
    await client.add_relay("wss://relay.divine.video")
    await client.connect()

    filter = (
        Filter()
        .kind(Kind(34236))
        .limit(limit)
        .custom_tag("search", ["sort:hot"])
    )

    events = await client.fetch_events([filter], timeout)
    # Parse and return video data
```

### Response Format

Returns JSON array of addressable event tags:
```json
[
  ["a", "34236:<pubkey>:<d-tag>", "wss://relay.divine.video"],
  ["a", "34236:<pubkey>:<d-tag>", "wss://relay.divine.video"]
]
```

---

## Part 5: Running the DVM

### Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Configure environment
cp .env.example .env
# Edit .env and add NOSTR_PRIVATE_KEY

# 4. Run
python -m divine_dvm.main
# Or: divine-dvm
```

### Generate Keys

```bash
python -c "from nostr_sdk import Keys; k = Keys.generate(); print(f'NOSTR_PRIVATE_KEY={k.secret_key().to_bech32()}')"
```

### Configuration (.env)

```bash
# Required
NOSTR_PRIVATE_KEY=nsec1...

# Optional
DVM_NAME=What's Hot on diVine
DVM_IDENTIFIER=divine-hot-videos
MAX_RESULTS=20
DIVINE_RELAY=wss://relay.divine.video
```

---

## Part 6: Production Deployment

### Option 1: Systemd Service

```ini
# /etc/systemd/system/divine-dvm.service
[Unit]
Description=What's Hot on diVine DVM
After=network.target

[Service]
Type=simple
User=dvm
WorkingDirectory=/opt/divine-dvm
Environment=NOSTR_PRIVATE_KEY=nsec1...
ExecStart=/opt/divine-dvm/.venv/bin/python -m divine_dvm.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable divine-dvm
sudo systemctl start divine-dvm
```

### Option 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

CMD ["python", "-m", "divine_dvm.main"]
```

```bash
docker build -t divine-dvm .
docker run -d --env-file .env --name divine-dvm divine-dvm
```

### Option 3: PM2 (with python interpreter)

```bash
pm2 start "python -m divine_dvm.main" --name divine-dvm
```

---

## Part 7: NIP-89 Announcement

The DVM automatically publishes its handler information on startup:

```json
{
  "kind": 31990,
  "content": "{
    \"name\": \"What's Hot on diVine\",
    \"picture\": \"https://divine.video/logo.png\",
    \"about\": \"Discover what's hot on diVine! This DVM returns trending short-form videos from the diVine platform, ranked by engagement and recency.\",
    \"supportsEncryption\": false,
    \"nip90Params\": {
      \"max_results\": {
        \"required\": false,
        \"description\": \"Maximum number of videos to return (default: 20)\"
      }
    }
  }",
  "tags": [
    ["d", "<identifier>"],
    ["k", "5300"]
  ]
}
```

---

## Part 8: Testing

### Manual Test with a DVM Client

1. Go to [dvmdash.live](https://dvmdash.live) or use vendata.io
2. Search for "What's Hot on diVine" DVM
3. Submit a job request

### Test Job Request

```json
{
  "kind": 5300,
  "content": "",
  "tags": [
    ["i", "hot divine videos", "text"],
    ["p", "<DVM_PUBKEY>"],
    ["param", "max_results", "10"]
  ]
}
```

### Expected Response (kind 6300)

```json
{
  "kind": 6300,
  "content": "[[\"a\", \"34236:abc123:video-id\", \"wss://relay.divine.video\"], ...]",
  "tags": [
    ["request", "<original-request-json>"],
    ["e", "<job-request-id>"],
    ["p", "<customer-pubkey>"]
  ]
}
```

---

## Part 9: Job Processing Flow

```
┌─────────────────┐
│  Client sends   │
│  kind:5300 job  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   DVM receives  │
│   job request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send kind:7000  │
│ "processing"    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query divine    │
│ relay NIP-50    │
│ sort:hot        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse video     │
│ events          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Publish         │
│ kind:6300       │
│ with results    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send kind:7000  │
│ "success"       │
└─────────────────┘
```

---

## Summary Checklist

- [x] Choose Python + nostrdvm framework
- [x] Create project structure
- [x] Implement DiscoverHotVideos task class
- [x] Implement NIP-50 query to divine relay
- [x] Configure NIP-89 announcement
- [x] Create main entry point
- [x] Add environment configuration
- [ ] Generate DVM keypair
- [ ] Deploy and run bot
- [ ] Test with DVM client
- [ ] Monitor and maintain

---

## Resources

- [NIP-90: Data Vending Machines](https://github.com/nostr-protocol/nips/blob/master/90.md)
- [NIP-89: Recommended Application Handlers](https://github.com/nostr-protocol/nips/blob/master/89.md)
- [NIP-50: Search Capability](https://github.com/nostr-protocol/nips/blob/master/50.md)
- [nostrdvm Framework](https://github.com/believethehype/nostrdvm)
- [DVM Kind 5300 Spec](https://github.com/nostr-protocol/data-vending-machines/blob/master/kinds/5300.md)
- [nostr-sdk Python](https://github.com/rust-nostr/nostr/tree/master/bindings/nostr-sdk-ffi/bindings-python)

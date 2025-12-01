#!/usr/bin/env python3
"""
What's Hot on diVine - Main Entry Point

This script initializes and runs the diVine DVM that serves
trending videos from the divine relay.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from nostr_sdk import Keys, SecretKey

from divine_dvm.tasks.hot_videos import (
    DiscoverHotVideos,
    build_dvm,
    update_profile_with_nip05,
    DEFAULT_RELAY_LIST,
    DEFAULT_ANNOUNCE_RELAY_LIST,
)


def create_env_file():
    """Create a template .env file if it doesn't exist."""
    env_path = Path(".env")
    if not env_path.exists():
        template = """# diVine DVM Configuration

# Nostr private key for the DVM (nsec or hex format)
# Generate one with: python -c "from nostr_sdk import Keys; k = Keys.generate(); print(f'NOSTR_PRIVATE_KEY={k.secret_key().to_bech32()}')"
NOSTR_PRIVATE_KEY=

# DVM display name
DVM_NAME=What's Hot on diVine

# DVM description (used in NIP-89 announcement)
DVM_ABOUT=Discover what's hot on diVine! This DVM returns trending short-form videos from the diVine platform, ranked by engagement and recency.

# DVM profile picture URL (used in NIP-89 announcement)
DVM_PICTURE_URL=https://divine.video/logo.png

# Unique identifier for NIP-89 (should be unique per DVM instance)
DVM_IDENTIFIER=divine-hot-videos

# Maximum results to return (default: 20)
MAX_RESULTS=20

# Divine relay URL (for querying hot videos)
DIVINE_RELAY=wss://relay.divine.video

# Relays to listen for job requests on (comma-separated)
# These are the relays where the DVM will receive kind:5300 requests
RELAY_LIST=wss://relay.divine.video,wss://relay.damus.io,wss://nos.lol,wss://relay.primal.net,wss://relay.ditto.pub

# Relays to publish NIP-89 announcements to (comma-separated)
# These are the relays where the DVM advertises itself
ANNOUNCE_RELAY_LIST=wss://relay.divine.video,wss://relay.damus.io,wss://nos.lol,wss://relay.primal.net,wss://relay.ditto.pub
"""
        env_path.write_text(template)
        print(f"Created template .env file at {env_path.absolute()}")
        print("Please edit .env and add your NOSTR_PRIVATE_KEY before running again.")
        return False
    return True


def load_keys() -> Keys:
    """Load or generate Nostr keys from environment."""
    private_key = os.getenv("NOSTR_PRIVATE_KEY", "").strip()

    if not private_key:
        print("Error: NOSTR_PRIVATE_KEY not set in environment or .env file")
        print("\nTo generate a new key, run:")
        print('  python -c "from nostr_sdk import Keys; k = Keys.generate(); print(k.secret_key().to_bech32())"')
        sys.exit(1)

    try:
        # parse() handles both nsec and hex formats
        secret_key = SecretKey.parse(private_key)
        return Keys(secret_key)
    except Exception as e:
        print(f"Error loading private key: {e}")
        sys.exit(1)


def parse_relay_list(env_var: str, default: list[str]) -> list[str]:
    """Parse a comma-separated relay list from environment variable."""
    value = os.getenv(env_var, "").strip()
    if not value:
        return default
    return [r.strip() for r in value.split(",") if r.strip()]


def main():
    """Main entry point for the diVine DVM."""
    print("=" * 50)
    print("  What's Hot on diVine - Nostr DVM")
    print("=" * 50)
    print()

    # Check and create .env file
    if not create_env_file():
        sys.exit(0)

    # Load environment variables
    load_dotenv()

    # Load configuration
    name = os.getenv("DVM_NAME", "What's Hot on diVine")
    identifier = os.getenv("DVM_IDENTIFIER", "divine-hot-videos")
    about = os.getenv("DVM_ABOUT", "Discover what's hot on diVine! This DVM returns trending short-form videos from the diVine platform, ranked by engagement and recency.")
    picture_url = os.getenv("DVM_PICTURE_URL", "").strip() or None
    nip05 = os.getenv("DVM_NIP05", "").strip() or None
    lud16 = os.getenv("DVM_LUD16", "").strip() or None
    amount = os.getenv("DVM_AMOUNT", "free").strip()
    max_results = int(os.getenv("MAX_RESULTS", "20"))
    relay_url = os.getenv("DIVINE_RELAY", "wss://relay.divine.video")

    # Parse relay lists
    relay_list = parse_relay_list("RELAY_LIST", DEFAULT_RELAY_LIST)
    announce_relay_list = parse_relay_list("ANNOUNCE_RELAY_LIST", DEFAULT_ANNOUNCE_RELAY_LIST)

    print(f"DVM Name: {name}")
    print(f"Identifier: {identifier}")
    print(f"Divine Relay: {relay_url}")
    print(f"Max Results: {max_results}")
    print()
    print("Listening Relays:")
    for r in relay_list:
        print(f"  - {r}")
    print()
    print("Announce Relays (NIP-89):")
    for r in announce_relay_list:
        print(f"  - {r}")
    print()

    # Load keys
    keys = load_keys()
    print(f"DVM Public Key: {keys.public_key().to_bech32()}")
    print()

    # Build and configure DVM
    options = {
        "max_results": max_results,
        "relay_url": relay_url,
    }

    dvm = build_dvm(
        name=name,
        identifier=identifier,
        keys=keys,
        options=options,
        relay_list=relay_list,
        announce_relay_list=announce_relay_list,
        picture_url=picture_url,
        about=about,
        nip05=nip05,
        lud16=lud16,
        amount=amount,
    )

    # Update profile with correct nip05/lud16 separation
    # (nostrdvm incorrectly sets nip05 = lud16, so we do our own update)
    asyncio.run(update_profile_with_nip05(
        keys=keys,
        name=name,
        about=about,
        picture=picture_url or "https://divine.video/logo.png",
        nip05=nip05,
        lud16=lud16,
        relay_list=announce_relay_list,
    ))

    print("Starting DVM...")
    print("Listening for job requests (kind 5300)...")
    print("Press Ctrl+C to stop")
    print()

    # Run the DVM
    try:
        dvm.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error running DVM: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

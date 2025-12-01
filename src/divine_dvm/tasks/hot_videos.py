"""
What's Hot on diVine - DVM Task

This task queries wss://relay.divine.video for trending short-form videos
using NIP-50 search with sort:hot parameter.
"""

import json
import asyncio
from datetime import timedelta
from typing import Optional

from nostr_sdk import (
    Client,
    Filter,
    Kind,
    Keys,
    Metadata,
    NostrSigner,
    Tag,
    Timestamp,
)

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag


# diVine uses kind 34236 for short-form videos (addressable events)
DIVINE_VIDEO_KIND = 34236
DIVINE_RELAY = "wss://relay.divine.video"

# Default relay lists
DEFAULT_RELAY_LIST = [
    "wss://relay.divine.video",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.ditto.pub",
]

DEFAULT_ANNOUNCE_RELAY_LIST = [
    "wss://relay.divine.video",
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://relay.ditto.pub",
]


class DiscoverHotVideos(DVMTaskInterface):
    """
    DVM that returns trending videos from diVine using NIP-50 search.

    This queries the divine relay with search: "sort:hot" to get
    videos ranked by recency and engagement.
    """

    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0

    def __init__(
        self,
        name: str,
        dvm_config: DVMConfig,
        nip89config: NIP89Config,
        nip88config: Optional[NIP88Config] = None,
        admin_config: Optional[dict] = None,
        options: Optional[dict] = None,
    ):
        super().__init__(
            name=name,
            dvm_config=dvm_config,
            nip89config=nip89config,
            nip88config=nip88config,
            admin_config=admin_config,
            options=options,
        )
        self.max_results = 20
        self.relay_url = DIVINE_RELAY

    async def init_dvm(
        self,
        name: str,
        dvm_config: DVMConfig,
        nip89config: NIP89Config,
        nip88config: Optional[NIP88Config] = None,
        admin_config: Optional[dict] = None,
        options: Optional[dict] = None,
    ):
        """Initialize the DVM with configuration."""
        dvm_config.SCRIPT = name

        if options is not None:
            if "max_results" in options:
                self.max_results = int(options["max_results"])
            if "relay_url" in options:
                self.relay_url = options["relay_url"]

    async def is_input_supported(self, tags: list, client: Client, dvm_config: DVMConfig) -> bool:
        """
        Check if the input is supported.

        For content discovery, we accept text input or no input at all.
        """
        for tag in tags:
            if tag.as_vec()[0] == "i":
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(
        self,
        event,
        client: Client,
        dvm_config: DVMConfig,
    ) -> dict:
        """
        Create a request form from a Nostr job request event.

        Extracts parameters like max_results from the event tags.
        """
        request_form = {"jobID": event.id().to_hex()}

        # Default options
        max_results = self.max_results

        # Parse parameters from event tags
        for tag in event.tags().to_vec():
            tag_vec = tag.as_vec()
            if len(tag_vec) >= 3 and tag_vec[0] == "param":
                if tag_vec[1] == "max_results":
                    max_results = int(tag_vec[2])

        request_form["max_results"] = max_results
        return request_form

    async def process(self, request_form: dict) -> str:
        """
        Process the job request by querying divine relay for hot videos.

        Uses NIP-50 search parameter to get videos sorted by "hot" algorithm.
        Returns a JSON array of addressable event tags.
        """
        max_results = request_form.get("max_results", self.max_results)

        # Query the divine relay for hot videos
        videos = await self._query_hot_videos(max_results)

        if not videos:
            return json.dumps([])

        # Convert to event tags
        result_list = []
        for video in videos[:max_results]:
            # Use 'e' tag format with event ID for client compatibility:
            # ["e", "<event-id>", "<relay-hint>"]
            event_id = video["event_id"]
            e_tag = Tag.parse(["e", event_id, self.relay_url])
            result_list.append(e_tag.as_vec())

        return json.dumps(result_list)

    async def _query_hot_videos(self, limit: int) -> list[dict]:
        """
        Query the divine relay for hot videos using NIP-50 search.

        The divine relay supports NIP-50 with sort modes like:
        - sort:hot (recent + high engagement)
        - sort:top (most referenced/popular all-time)
        - sort:rising (gaining traction)
        """
        videos = []

        try:
            # Create a temporary client for querying
            client = Client()
            await client.add_relay(self.relay_url)
            await client.connect()

            # Build NIP-50 filter with search parameter
            video_filter = (
                Filter()
                .kind(Kind(DIVINE_VIDEO_KIND))
                .limit(limit)
                .search("sort:hot")  # NIP-50 search parameter - recent + high engagement
            )

            # Query with timeout
            timeout = timedelta(seconds=10)
            events = await client.fetch_events(video_filter, timeout)

            for event in events.to_vec():
                video_data = self._parse_video_event(event)
                if video_data:
                    videos.append(video_data)

            await client.disconnect()

        except Exception as e:
            print(f"Error querying divine relay: {e}")

        return videos

    def _parse_video_event(self, event) -> Optional[dict]:
        """
        Parse a video event and extract relevant metadata.

        Returns dict with pubkey, d_tag, title, and other metadata.
        """
        try:
            pubkey = event.author().to_hex()
            d_tag = None
            title = None

            for tag in event.tags().to_vec():
                tag_vec = tag.as_vec()
                if len(tag_vec) >= 2:
                    if tag_vec[0] == "d":
                        d_tag = tag_vec[1]
                    elif tag_vec[0] == "title":
                        title = tag_vec[1]

            if not d_tag:
                return None

            return {
                "pubkey": pubkey,
                "d_tag": d_tag,
                "title": title,
                "event_id": event.id().to_hex(),
                "created_at": event.created_at().as_secs(),
            }
        except Exception as e:
            print(f"Error parsing video event: {e}")
            return None

    async def post_process(self, result: str, event) -> str:
        """
        Post-process results if text/plain output is requested.

        Converts the JSON array of tags into human-readable format.
        """
        # Check if text output was requested
        for tag in event.tags().to_vec():
            tag_vec = tag.as_vec()
            if len(tag_vec) >= 2 and tag_vec[0] == "output":
                if tag_vec[1] == "text/plain":
                    return self._format_as_text(result)

        return result

    def _format_as_text(self, result: str) -> str:
        """Convert JSON result to human-readable text."""
        try:
            tags = json.loads(result)
            if not tags:
                return "No hot videos found."

            lines = ["Hot Videos on diVine:", ""]
            for i, tag in enumerate(tags, 1):
                if len(tag) >= 2:
                    # tag[1] is the event ID
                    event_id = tag[1]
                    lines.append(f"{i}. {event_id}")

            return "\n".join(lines)
        except Exception:
            return result


async def update_profile_with_nip05(
    keys: Keys,
    name: str,
    about: str,
    picture: str,
    nip05: Optional[str],
    lud16: Optional[str],
    relay_list: list[str],
):
    """
    Update the DVM profile with correct nip05 and lud16 fields.

    The nostrdvm framework incorrectly sets nip05 = lud16, so we do our own update.
    """
    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()

    metadata = Metadata()
    metadata = metadata.set_name(name)
    metadata = metadata.set_display_name(name)
    metadata = metadata.set_about(about)
    metadata = metadata.set_picture(picture)
    if nip05:
        metadata = metadata.set_nip05(nip05)
    if lud16:
        metadata = metadata.set_lud16(lud16)

    print(f"[{name}] Setting profile metadata for {keys.public_key().to_bech32()}...")
    print(metadata.as_json())
    await client.set_metadata(metadata)
    await client.disconnect()


def build_dvm(
    name: str,
    identifier: str,
    keys: Keys,
    options: Optional[dict] = None,
    relay_list: Optional[list[str]] = None,
    announce_relay_list: Optional[list[str]] = None,
    picture_url: Optional[str] = None,
    about: Optional[str] = None,
    nip05: Optional[str] = None,
    lud16: Optional[str] = None,
    amount: str = "free",
) -> DiscoverHotVideos:
    """
    Build and configure the What's Hot on diVine DVM.

    Args:
        name: Display name for the DVM
        identifier: Unique identifier for NIP-89
        keys: Nostr keys for the DVM
        options: Optional configuration overrides
        relay_list: Relays the DVM operates on and listens for job requests
        announce_relay_list: Relays to publish NIP-89 announcements to
        picture_url: URL to the DVM's profile picture for NIP-89 announcement
        about: Description of the DVM for NIP-89 announcement
        nip05: NIP-05 identifier for verification (e.g., user@domain.com)
        lud16: Lightning address for tips/zaps (e.g., user@getalby.com)
        amount: Cost for using the DVM ("free" or millisats amount)

    Returns:
        Configured DiscoverHotVideos instance
    """
    # DVM configuration
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = keys.secret_key().to_hex()
    dvm_config.IDENTIFIER = identifier
    dvm_config.LNBITS_INVOICE_KEY = ""  # Free service, no payment required
    dvm_config.LNBITS_ADMIN_KEY = ""
    dvm_config.FIX_COST = 0
    if nip05:
        dvm_config.NIP05 = nip05
    if lud16:
        dvm_config.LN_ADDRESS = lud16

    # Configure relays
    dvm_config.RELAY_LIST = relay_list or DEFAULT_RELAY_LIST
    dvm_config.ANNOUNCE_RELAY_LIST = announce_relay_list or DEFAULT_ANNOUNCE_RELAY_LIST

    # Admin configuration
    # Note: UPDATE_PROFILE is disabled because nostrdvm sets nip05 = lud16 incorrectly
    # We handle profile updates ourselves in main.py with correct nip05/lud16 separation
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = True
    admin_config.UPDATE_PROFILE = False

    # NIP-89 announcement configuration
    default_picture = "https://divine.video/logo.png"
    default_about = "Discover what's hot on diVine! This DVM returns trending short-form videos from the diVine platform, ranked by engagement and recency."
    nip89info = {
        "name": name,
        "picture": picture_url or default_picture,
        "about": about or default_about,
        "amount": amount,  # "free" or millisats amount
        "supportsEncryption": False,
        "acceptsNutZaps": False,
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "Maximum number of videos to return (default: 20)",
            }
        },
    }

    nip89config = NIP89Config()
    nip89config.KIND = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DiscoverHotVideos(
        name=name,
        dvm_config=dvm_config,
        nip89config=nip89config,
        admin_config=admin_config,
        options=options or {"max_results": 20},
    )

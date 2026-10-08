import base64
import hashlib
import json
import re
from typing import Dict, Iterable, List


ARCHETYPE_RULES = [
    ("Arishem", {"Arishem"}),
    ("Thanos", {"Thanos"}),
    ("Galactus", {"Galactus"}),
    ("High Evolutionary", {"HighEvolutionary"}),
    ("Cerebro", {"Cerebro"}),
    ("Patriot", {"Patriot"}),
    ("Silver Surfer", {"SilverSurfer"}),
    ("Discard", {"Hela", "MODOK", "Apocalypse", "Dracula"}),
    ("Destroy", {"Knull", "Death", "Deadpool", "Nimrod", "Venom"}),
    ("Move", {"HumanTorch", "MultipleMan", "Heimdall", "MadameWeb"}),
    ("Bounce", {"Beast", "Falcon", "HitMonkey"}),
    ("Ongoing", {"Spectrum", "Onslaught"}),
    ("On Reveal", {"Wong", "Odin"}),
]


def normalize_cards(cards: Iterable[str]) -> List[str]:
    return sorted({str(card).strip() for card in cards if str(card).strip()}, key=str.casefold)


def deck_fingerprint(cards: Iterable[str]) -> str:
    canonical = "|".join(normalize_cards(cards))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_deck_code(cards: Iterable[str], name: str) -> str:
    payload = {
        "Cards": [{"CardDefId": card} for card in normalize_cards(cards)],
        "Name": name,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def infer_archetype(cards: Iterable[str]) -> str:
    compact = {re.sub(r"[^a-z0-9]", "", card.casefold()) for card in cards}
    for label, anchors in ARCHETYPE_RULES:
        normalized = {re.sub(r"[^a-z0-9]", "", anchor.casefold()) for anchor in anchors}
        if compact.intersection(normalized):
            return label
    return "Otros"


def make_deck_name(cards: Iterable[str], metadata: Dict[str, Dict]) -> str:
    unique = normalize_cards(cards)
    ranked = sorted(
        unique,
        key=lambda card: (
            int(metadata.get(card, {}).get("cost") or 0),
            int(metadata.get(card, {}).get("power") or 0),
            card.casefold(),
        ),
        reverse=True,
    )
    display = [metadata.get(card, {}).get("name") or card for card in ranked[:2]]
    return " / ".join(display) if display else "Mazo sin nombre"


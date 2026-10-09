import json
import logging
import os
from typing import Dict, Iterable, List

import requests

try:
    from .deck_utils import deck_fingerprint, infer_archetype, make_deck_code, make_deck_name
    from .models import DeckSnapshot
except ImportError:
    from deck_utils import deck_fingerprint, infer_archetype, make_deck_code, make_deck_name
    from models import DeckSnapshot


logger = logging.getLogger("snapcomplete")

SUPABASE_URL = "https://ytdzngkbndthkutccrkn.supabase.co/rest/v1/rpc/"
# Clave publica del navegador de SnapComplete; no es una credencial del usuario.
PUBLIC_KEY = "sb_publishable_VlU5KB6tysM0IlsvxsskUg_Bo9Jz6BO"
CARD_DATA_URL = "https://snapjson.untapped.gg/v1/latest/cards.json"
SOURCE_URL = "https://snapcomplete.com/play/decks"
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(MODULE_DIR) if os.path.basename(MODULE_DIR) == "src" else MODULE_DIR
CARD_CACHE_PATH = os.path.join(BASE_DIR, "data", "card_metadata.json")


class SnapCompleteClient:
    def __init__(self, timeout: int = 45) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "BuscadorMazosSnap/1.0 (+uso personal; una revision programada)",
                "Accept": "application/json",
            }
        )

    def _rpc(self, name: str, body: Dict) -> object:
        response = self.session.post(
            f"{SUPABASE_URL}{name}",
            headers={
                "apikey": PUBLIC_KEY,
                "Authorization": f"Bearer {PUBLIC_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def fetch_card_dictionary(self) -> Dict[int, str]:
        payload = self._rpc("get_card_dictionary", {})
        if not isinstance(payload, list):
            raise ValueError("La fuente devolvio un diccionario de cartas no valido")
        return {int(card_id): str(def_id) for card_id, def_id in payload}

    def fetch_card_metadata(self) -> Dict[str, Dict]:
        response = self.session.get(CARD_DATA_URL, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        metadata = {
            str(item.get("defId")): item
            for item in payload
            if isinstance(item, dict) and item.get("defId")
        }
        os.makedirs(os.path.dirname(CARD_CACHE_PATH), exist_ok=True)
        public_metadata = {
            def_id: {
                "name": str(item.get("name") or def_id),
                "cost": int(item.get("cost") or 0),
                "power": int(item.get("power") or 0),
            }
            for def_id, item in metadata.items()
        }
        with open(CARD_CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(public_metadata, handle, ensure_ascii=False, separators=(",", ":"))
        return metadata

    def fetch_decks(
        self,
        *,
        period: str = "week",
        mode: str = "ranked-conquest",
        minimum_games: int = 10,
        maximum_decks: int = 250,
        sort: str = "win_rate",
    ) -> List[DeckSnapshot]:
        dictionary = self.fetch_card_dictionary()
        metadata = self.fetch_card_metadata()
        sort_code = {"win_rate": "wrq", "matches": "m", "cube_rate": "crq"}.get(sort, "wrq")
        payload = self._rpc(
            "get_deck_snapshot_v4",
            {
                "p_period": period,
                "p_mode_filter": mode,
                "p_sp_pct": None,
                "p_cl_min": None,
                "p_cl_max": None,
                "p_min_games": max(1, int(minimum_games)),
                "p_period_start_override": None,
                "p_sort": sort_code,
                "p_sort_dir": "desc",
                "p_limit": max(1, min(1000, int(maximum_decks))),
                "p_bucket_starts": None,
                "p_locations": None,
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("La fuente devolvio una respuesta de mazos no valida")
        rows = payload.get("decks") or payload.get("rows") or []
        decks: List[DeckSnapshot] = []
        for row in rows:
            deck = decode_deck_row(row, dictionary, metadata, period)
            if deck:
                decks.append(deck)
        logger.info("Mazos validos recibidos de SnapComplete: %s", len(decks))
        return decks


def decode_deck_row(
    row: Iterable,
    dictionary: Dict[int, str],
    metadata: Dict[str, Dict],
    period: str,
) -> DeckSnapshot | None:
    values = list(row)
    if len(values) < 13 or not isinstance(values[0], list):
        return None
    try:
        cards = [dictionary[int(card_id)] for card_id in values[0]]
    except (KeyError, TypeError, ValueError):
        return None
    if len(cards) != 12 or len(set(cards)) != 12:
        return None
    players, matches, wins, losses = map(int, values[1:5])
    cubes_won, cubes_lost = int(values[5]), int(values[6])
    qualified_players = int(values[11] or 0)
    external_id = str(values[12])
    fingerprint = deck_fingerprint(cards)
    name = make_deck_name(cards, metadata)
    win_rate = round((wins / matches) * 100, 1) if matches else 0.0
    cube_rate = round((cubes_won - cubes_lost) / matches, 2) if matches else 0.0
    return DeckSnapshot(
        fingerprint=fingerprint,
        external_id=external_id,
        name=name,
        archetype=infer_archetype(cards),
        cards=cards,
        deck_code=make_deck_code(cards, name),
        players=players,
        qualified_players=qualified_players,
        matches=matches,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        cube_rate=cube_rate,
        source="SnapComplete",
        source_url=SOURCE_URL,
        source_period=period,
    )


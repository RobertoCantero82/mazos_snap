from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DeckSnapshot:
    fingerprint: str
    external_id: str
    name: str
    archetype: str
    cards: List[str]
    deck_code: str
    players: int
    qualified_players: int
    matches: int
    wins: int
    losses: int
    win_rate: float
    cube_rate: float
    source: str
    source_url: str
    source_period: str


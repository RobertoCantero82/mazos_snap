import html
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(MODULE_DIR) if os.path.basename(MODULE_DIR) == "src" else MODULE_DIR


def render_dashboard(
    decks: Iterable[Dict],
    *,
    path: str | None = None,
    recent_days: int = 7,
) -> str:
    path = path or os.path.join(BASE_DIR, "panel_mazos.html")
    decks = sorted(
        list(decks),
        key=lambda deck: _parse_date(deck.get("first_seen"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    threshold = datetime.now(timezone.utc) - timedelta(days=max(1, recent_days))
    cards = []
    for deck in decks:
        first_seen = _parse_date(deck.get("first_seen"))
        is_new = bool(first_seen and first_seen >= threshold)
        card_names = deck.get("cards") or []
        search = " ".join(
            [deck.get("name", ""), deck.get("archetype", ""), *card_names]
        ).casefold()
        pills = "".join(f"<li>{html.escape(str(card))}</li>" for card in card_names)
        cards.append(
            f"""
            <article class="deck" data-search="{html.escape(search, quote=True)}"
                     data-archetype="{html.escape(deck.get('archetype', 'Otros'), quote=True)}"
                     data-new="{'1' if is_new else '0'}"
                     data-first-seen="{html.escape(str(deck.get('first_seen') or ''), quote=True)}"
                     data-win-rate="{float(deck.get('win_rate') or 0):.4f}"
                     data-matches="{int(deck.get('matches') or 0)}"
                     data-cards="{html.escape('|'.join(str(card).casefold() for card in card_names), quote=True)}">
              <div class="deck-head">
                <div><span class="badge">{html.escape(deck.get('archetype', 'Otros'))}</span>{'<span class="new">NUEVO</span>' if is_new else ''}
                <h2>{html.escape(deck.get('name', 'Mazo'))}</h2></div>
                <div class="rate"><strong>{float(deck.get('win_rate') or 0):.1f}%</strong><small>victorias</small></div>
              </div>
              <ul class="cards">{pills}</ul>
              <div class="metrics"><span>{int(deck.get('matches') or 0):,} partidas</span><span>{float(deck.get('cube_rate') or 0):+.2f} cubos</span><span>{int(deck.get('players') or 0):,} jugadores</span></div>
              <div class="foot"><span>Detectado: {_display_date(deck.get('first_seen'))}</span><span>Visto {int(deck.get('times_seen') or 1)} veces</span></div>
              <div class="actions"><button data-code="{html.escape(deck.get('deck_code', ''), quote=True)}">Copiar mazo</button><a href="{html.escape(deck.get('source_url', '#'), quote=True)}" target="_blank">Ver fuente</a></div>
            </article>
            """
        )
    archetypes = sorted({str(deck.get("archetype") or "Otros") for deck in decks})
    options = "".join(f'<option value="{html.escape(value, quote=True)}">{html.escape(value)}</option>' for value in archetypes)
    all_card_names = sorted(
        {str(card) for deck in decks for card in (deck.get("cards") or [])},
        key=str.casefold,
    )
    exclusion_options = "".join(
        f'<label class="card-option"><input type="checkbox" value="{html.escape(card.casefold(), quote=True)}"><span>{html.escape(card)}</span></label>'
        for card in all_card_names
    )
    generated = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    document = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radar de mazos Marvel Snap</title><style>
:root{{--bg:#080b12;--panel:#121826;--soft:#1c2638;--ink:#eef3ff;--muted:#a8b3c7;--blue:#5aa8ff;--gold:#ffd05a;--green:#59e0a2}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top,#16213a 0,#080b12 42%);color:var(--ink);font-family:Segoe UI,Arial,sans-serif}}
.shell{{max-width:1200px;margin:auto;padding:34px 20px 60px}}header{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:24px}}h1{{font-size:clamp(30px,5vw,52px);margin:0}}header p{{color:var(--muted);margin:8px 0 0}}.summary{{text-align:right;color:var(--gold);font-weight:700}}
.filters{{display:grid;grid-template-columns:minmax(230px,1fr) 190px 190px 210px auto;gap:12px;background:#0e1421ee;padding:14px;border:1px solid #263248;border-radius:16px;position:sticky;top:8px;z-index:5;backdrop-filter:blur(12px)}}input,select,button{{font:inherit}}input,select{{width:100%;background:var(--soft);color:var(--ink);border:1px solid #35435c;border-radius:10px;padding:11px}}label{{display:flex;align-items:center;gap:8px;color:var(--muted);padding:0 8px}}.filters>label input{{width:auto;accent-color:var(--blue)}}.exclude{{position:relative}}.exclude summary{{list-style:none;background:var(--soft);border:1px solid #35435c;border-radius:10px;padding:11px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.exclude summary::-webkit-details-marker{{display:none}}.exclude summary::after{{content:'▾';float:right;color:var(--muted)}}.exclude[open] summary::after{{content:'▴'}}.exclude-menu{{position:absolute;top:48px;right:0;width:310px;background:#121a29;border:1px solid #35435c;border-radius:12px;padding:10px;box-shadow:0 18px 45px #000b}}.exclude-list{{max-height:290px;overflow:auto;margin:8px 0}}.card-option{{padding:7px 5px;border-radius:7px;cursor:pointer}}.card-option:hover{{background:#202b3e}}.card-option input{{width:auto;accent-color:var(--blue)}}.clear{{width:100%;background:#293750;color:var(--ink)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;margin-top:20px}}.deck{{background:linear-gradient(155deg,#151d2c,#0e1420);border:1px solid #2a3850;border-radius:18px;padding:18px;box-shadow:0 16px 34px #0005}}.deck-head{{display:flex;justify-content:space-between;gap:12px}}h2{{font-size:20px;margin:9px 0}}.badge,.new{{display:inline-block;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:700;background:#27344b;color:#cfe3ff}}.new{{background:var(--green);color:#052317;margin-left:6px}}.rate{{text-align:right;color:var(--green)}}.rate strong{{font-size:25px;display:block}}.rate small{{color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;list-style:none;padding:0;margin:14px 0}}.cards li{{background:#1b2537;border:1px solid #2b3b55;border-radius:8px;padding:7px;text-align:center;font-size:12px;overflow:hidden;text-overflow:ellipsis}}.metrics,.foot,.actions{{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}}.metrics{{color:var(--gold);font-size:13px}}.foot{{color:var(--muted);font-size:12px;border-top:1px solid #28354b;margin-top:14px;padding-top:11px}}.actions{{margin-top:14px}}button,.actions a{{border:0;border-radius:9px;padding:9px 12px;text-decoration:none;font-weight:700;cursor:pointer}}button{{background:var(--blue);color:#071425}}.actions a{{background:#26344b;color:var(--ink)}}.empty{{color:var(--muted);text-align:center;padding:60px}}
@media(max-width:900px){{.filters{{grid-template-columns:1fr 1fr}}}}@media(max-width:680px){{header{{align-items:start;flex-direction:column}}.summary{{text-align:left}}.filters{{grid-template-columns:1fr;position:static}}.grid{{grid-template-columns:1fr}}.exclude-menu{{position:static;width:100%;margin-top:8px}}}}
</style></head><body><div class="shell"><header><div><h1>Radar de mazos</h1><p>Marvel Snap · combinaciones nuevas y evolución del meta</p></div><div class="summary">{len(decks)} mazos<br><small>Actualizado {generated}</small></div></header>
<div class="filters"><input id="search" type="search" placeholder="Buscar carta, mazo o arquetipo…"><select id="archetype"><option value="">Todos los arquetipos</option>{options}</select><select id="order" aria-label="Ordenar mazos"><option value="date_desc">Más recientes primero</option><option value="date_asc">Más antiguos primero</option><option value="win_desc">Mayor porcentaje de victorias</option><option value="matches_desc">Más partidas</option></select><details class="exclude" id="exclude"><summary id="excludeSummary">Excluir cartas</summary><div class="exclude-menu"><input id="excludeSearch" type="search" placeholder="Buscar una carta…"><div class="exclude-list" id="excludeList">{exclusion_options}</div><button class="clear" id="clearExclusions" type="button">Quitar exclusiones</button></div></details><label><input id="onlyNew" type="checkbox"> Solo nuevos</label></div>
<main class="grid" id="grid">{''.join(cards)}</main><p class="empty" id="empty" hidden>No hay mazos con esos filtros.</p></div>
<script>
const q=document.getElementById('search'),a=document.getElementById('archetype'),n=document.getElementById('onlyNew'),order=document.getElementById('order'),grid=document.getElementById('grid'),items=[...document.querySelectorAll('.deck')],empty=document.getElementById('empty'),excludeList=document.getElementById('excludeList'),excludeSearch=document.getElementById('excludeSearch'),excludeSummary=document.getElementById('excludeSummary');
function excludedCards(){{return new Set([...excludeList.querySelectorAll('input:checked')].map(input=>input.value))}}
function filter(){{const text=q.value.toLowerCase(),arch=a.value,excluded=excludedCards();let shown=0;for(const el of items){{const deckCards=new Set(el.dataset.cards.split('|'));const hasExcluded=[...excluded].some(card=>deckCards.has(card));const ok=el.dataset.search.includes(text)&&(!arch||el.dataset.archetype===arch)&&(!n.checked||el.dataset.new==='1')&&!hasExcluded;el.hidden=!ok;if(ok)shown++}}excludeSummary.textContent=excluded.size?`Excluir cartas (${{excluded.size}})`: 'Excluir cartas';empty.hidden=shown!==0}}
function sortDecks(){{const mode=order.value;items.sort((x,y)=>{{if(mode==='date_asc')return x.dataset.firstSeen.localeCompare(y.dataset.firstSeen);if(mode==='win_desc')return Number(y.dataset.winRate)-Number(x.dataset.winRate);if(mode==='matches_desc')return Number(y.dataset.matches)-Number(x.dataset.matches);return y.dataset.firstSeen.localeCompare(x.dataset.firstSeen)}}).forEach(el=>grid.appendChild(el))}}
q.addEventListener('input',filter);a.addEventListener('change',filter);n.addEventListener('change',filter);order.addEventListener('change',sortDecks);excludeList.addEventListener('change',filter);
excludeSearch.addEventListener('input',()=>{{const text=excludeSearch.value.toLowerCase();for(const option of excludeList.querySelectorAll('.card-option'))option.hidden=!option.textContent.toLowerCase().includes(text)}});
document.getElementById('clearExclusions').addEventListener('click',()=>{{excludeList.querySelectorAll('input:checked').forEach(input=>input.checked=false);filter()}});
document.addEventListener('click',async e=>{{const b=e.target.closest('button[data-code]');if(!b)return;await navigator.clipboard.writeText(b.dataset.code);const old=b.textContent;b.textContent='Copiado';setTimeout(()=>b.textContent=old,1300)}});
</script></body></html>"""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(document)
    return path


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _display_date(value: str | None) -> str:
    date = _parse_date(value)
    return date.astimezone().strftime("%d/%m/%Y %H:%M") if date else "—"


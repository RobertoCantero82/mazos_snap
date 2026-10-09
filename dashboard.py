import html
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(MODULE_DIR) if os.path.basename(MODULE_DIR) == "src" else MODULE_DIR
CARD_CACHE_PATH = os.path.join(BASE_DIR, "data", "card_metadata.json")
try:
    MADRID = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    # Algunos Python de Windows no incluyen la base IANA. GitHub Actions sí.
    MADRID = timezone(timedelta(hours=2), "Europe/Madrid")


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
    metadata = _load_card_metadata()
    threshold = datetime.now(timezone.utc) - timedelta(days=max(1, recent_days))
    deck_articles = []
    all_cards: Dict[str, Dict[str, str]] = {}
    new_count = 0

    for deck in decks:
        first_seen = _parse_date(deck.get("first_seen"))
        is_new = int(deck.get("times_seen") or 1) <= 1 and bool(
            first_seen and first_seen >= threshold
        )
        new_count += int(is_new)
        raw_cards = [str(card) for card in (deck.get("cards") or [])]
        card_views = []
        for def_id in raw_cards:
            card_meta = metadata.get(def_id, {})
            display_name = str(card_meta.get("name") or _humanize_card_name(def_id))
            image_url = _card_image_url(display_name)
            all_cards.setdefault(
                def_id.casefold(),
                {"id": def_id, "name": display_name, "image": image_url},
            )
            card_views.append(
                f"""
                <li class="card-tile" title="{html.escape(display_name, quote=True)}">
                  <span class="card-fallback">{html.escape(_initials(display_name))}</span>
                  <img loading="lazy" decoding="async" src="{html.escape(image_url, quote=True)}"
                       alt="{html.escape(display_name, quote=True)}"
                       onerror="this.parentElement.classList.add('no-image');this.remove()">
                  <span class="card-name">{html.escape(display_name)}</span>
                </li>"""
            )

        fingerprint = str(deck.get("fingerprint") or "")
        display_cards = [all_cards[card.casefold()]["name"] for card in raw_cards]
        search = " ".join(
            [str(deck.get("name") or ""), str(deck.get("archetype") or ""), *display_cards]
        ).casefold()
        deck_articles.append(
            f"""
            <article class="deck" data-search="{html.escape(search, quote=True)}"
                     data-id="{html.escape(fingerprint, quote=True)}"
                     data-archetype="{html.escape(str(deck.get('archetype') or 'Otros'), quote=True)}"
                     data-new="{'1' if is_new else '0'}"
                     data-first-seen="{html.escape(str(deck.get('first_seen') or ''), quote=True)}"
                     data-win-rate="{float(deck.get('win_rate') or 0):.4f}"
                     data-matches="{int(deck.get('matches') or 0)}"
                     data-cards="{html.escape('|'.join(card.casefold() for card in raw_cards), quote=True)}">
              <div class="deck-head">
                <div class="deck-title"><div><span class="badge">{html.escape(str(deck.get('archetype') or 'Otros'))}</span>{'<span class="new">NUEVO</span>' if is_new else ''}</div>
                <h2>{html.escape(str(deck.get('name') or 'Mazo'))}</h2></div>
                <button class="favorite" type="button" aria-label="Guardar en favoritos" title="Guardar en favoritos">☆</button>
              </div>
              <ul class="cards">{''.join(card_views)}</ul>
              <div class="stats">
                <div><strong>{float(deck.get('win_rate') or 0):.1f}%</strong><span>victorias</span></div>
                <div><strong>{float(deck.get('cube_rate') or 0):+.2f}</strong><span>cubos</span></div>
                <div><strong>{int(deck.get('matches') or 0):,}</strong><span>partidas</span></div>
                <div><strong>{int(deck.get('players') or 0):,}</strong><span>jugadores</span></div>
              </div>
              <div class="foot"><span>Detectado {_display_date(deck.get('first_seen'))}</span><span>Visto {int(deck.get('times_seen') or 1)} veces</span></div>
              <div class="actions"><button class="copy" type="button" data-code="{html.escape(str(deck.get('deck_code') or ''), quote=True)}">Copiar mazo</button><a href="{html.escape(str(deck.get('source_url') or '#'), quote=True)}" target="_blank" rel="noopener">Ver fuente ↗</a></div>
            </article>"""
        )

    archetypes = sorted({str(deck.get("archetype") or "Otros") for deck in decks})
    options = "".join(
        f'<option value="{html.escape(value, quote=True)}">{html.escape(value)}</option>'
        for value in archetypes
    )
    exclusion_options = "".join(
        f"""<label class="exclude-card" data-name="{html.escape(card['name'].casefold(), quote=True)}">
          <input type="checkbox" value="{html.escape(key, quote=True)}">
          <span class="exclude-thumb"><img loading="lazy" src="{html.escape(card['image'], quote=True)}" alt="" onerror="this.remove()"></span>
          <span>{html.escape(card['name'])}</span><b>✓</b>
        </label>"""
        for key, card in sorted(all_cards.items(), key=lambda item: item[1]["name"].casefold())
    )

    now = datetime.now(MADRID)
    generated = now.strftime("%d/%m/%Y · %H:%M")
    next_update = _next_update(now).strftime("%d/%m · %H:%M")
    average_win = sum(float(deck.get("win_rate") or 0) for deck in decks) / len(decks) if decks else 0
    total_matches = sum(int(deck.get("matches") or 0) for deck in decks)
    document = _document(
        articles="".join(deck_articles),
        deck_count=len(decks),
        new_count=new_count,
        archetype_count=len(archetypes),
        average_win=average_win,
        total_matches=total_matches,
        generated=generated,
        next_update=next_update,
        archetype_options=options,
        exclusion_options=exclusion_options,
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(document)
    return path


def _document(**data: object) -> str:
    template = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#070910"><title>Radar de mazos Marvel Snap</title><style>
:root{{--bg:#070910;--panel:#101522;--panel2:#171e2e;--line:#29344a;--ink:#f5f7ff;--muted:#9da9bf;--cyan:#55d9ff;--blue:#5595ff;--pink:#ff4fa3;--gold:#ffd45c;--green:#5be3a7;--shadow:0 22px 60px #0008}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:radial-gradient(circle at 12% -10%,#263d73 0,transparent 31%),radial-gradient(circle at 92% 6%,#5a1747 0,transparent 26%),var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;min-height:100vh}}.shell{{max-width:1500px;margin:auto;padding:28px 24px 80px}}
.hero{{position:relative;overflow:hidden;border:1px solid #34425e;background:linear-gradient(120deg,#111a2bdf,#13101fef);border-radius:26px;padding:30px;box-shadow:var(--shadow)}}.hero:after{{content:"";position:absolute;width:380px;height:380px;right:-100px;top:-210px;background:radial-gradient(circle,#55d9ff55,transparent 66%);pointer-events:none}}.eyebrow{{color:var(--cyan);font-weight:800;letter-spacing:.14em;text-transform:uppercase;font-size:12px}}.hero-main{{display:flex;align-items:end;justify-content:space-between;gap:24px}}.hero h1{{font-size:clamp(34px,5vw,62px);line-height:.98;margin:9px 0 10px;letter-spacing:-.045em}}.hero h1 span{{background:linear-gradient(90deg,var(--cyan),#a98cff,var(--pink));-webkit-background-clip:text;color:transparent}}.subtitle{{margin:0;color:var(--muted);font-size:17px}}.updated{{text-align:right;color:var(--muted);line-height:1.6;white-space:nowrap}}.updated strong{{color:var(--ink)}}
.overview{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}}.overview div{{background:#080c15aa;border:1px solid #293650;border-radius:15px;padding:14px 16px}}.overview strong{{display:block;font-size:24px}}.overview span{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}}.overview .highlight strong{{color:var(--green)}}
.toolbar{{position:sticky;top:8px;z-index:10;margin-top:18px;background:#0c111ddd;border:1px solid #2b3750;border-radius:20px;padding:14px;backdrop-filter:blur(18px);box-shadow:0 14px 35px #0007}}.filter-main,.filter-more{{display:grid;gap:10px}}.filter-main{{grid-template-columns:minmax(240px,1fr) 190px 210px 220px}}.filter-more{{grid-template-columns:170px 170px auto auto auto;margin-top:10px}}.control{{min-width:0}}.control label{{display:block;color:var(--muted);font-size:11px;margin:0 0 5px 3px;text-transform:uppercase;letter-spacing:.07em}}input,select,button{{font:inherit}}input,select{{width:100%;color:var(--ink);background:var(--panel2);border:1px solid #34415a;border-radius:11px;padding:11px 12px;outline:none}}input:focus,select:focus{{border-color:var(--cyan);box-shadow:0 0 0 3px #55d9ff18}}.toggle{{display:flex;align-items:center;gap:8px;padding:0 9px;color:var(--muted);white-space:nowrap}}.toggle input{{width:auto;accent-color:var(--cyan)}}
.exclude{{position:relative}}.exclude summary{{list-style:none;color:var(--ink);background:var(--panel2);border:1px solid #34415a;border-radius:11px;padding:11px 12px;cursor:pointer;white-space:nowrap}}.exclude summary::-webkit-details-marker{{display:none}}.exclude summary:after{{content:"▾";float:right;color:var(--muted)}}.exclude[open] summary{{border-color:var(--cyan)}}.exclude-menu{{position:absolute;top:48px;right:0;width:min(390px,92vw);background:#111827;border:1px solid #3a4965;border-radius:16px;padding:12px;box-shadow:var(--shadow)}}.exclude-list{{max-height:430px;overflow:auto;display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:10px 0}}.exclude-card{{position:relative;display:grid;grid-template-columns:34px 1fr auto;align-items:center;gap:8px;padding:7px;border:1px solid transparent;border-radius:10px;cursor:pointer;color:#dce5f6;font-size:12px}}.exclude-card:hover{{background:#202a3d}}.exclude-card:has(input:checked){{border-color:var(--pink);background:#3a1830}}.exclude-card input{{position:absolute;opacity:0}}.exclude-card b{{display:none;color:var(--pink)}}.exclude-card:has(input:checked) b{{display:block}}.exclude-thumb{{width:34px;height:42px;border-radius:6px;overflow:hidden;background:#273149}}.exclude-thumb img{{width:100%;height:100%;object-fit:cover}}.clear{{width:100%;background:#293750;color:var(--ink);border:0;border-radius:10px;padding:10px;cursor:pointer}}
.results-bar{{display:flex;justify-content:space-between;align-items:center;gap:18px;margin:22px 2px 12px}}.results-bar p{{margin:0;color:var(--muted)}}.results-bar strong{{color:var(--ink)}}.legend{{display:flex;gap:12px;color:var(--muted);font-size:12px}}.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;background:var(--green)}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.deck{{background:linear-gradient(145deg,#131a29,#0c111c);border:1px solid #2a3750;border-radius:20px;padding:17px;box-shadow:0 16px 40px #0005;transition:transform .2s,border-color .2s}}.deck:hover{{transform:translateY(-2px);border-color:#4c638b}}.deck-head{{display:flex;justify-content:space-between;gap:12px;min-height:60px}}.deck-title{{min-width:0}}.deck h2{{font-size:20px;line-height:1.2;margin:8px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.badge,.new{{display:inline-block;border-radius:999px;padding:4px 9px;font-size:10px;font-weight:800;letter-spacing:.04em;background:#263550;color:#d9e8ff}}.new{{background:var(--green);color:#06271a;margin-left:6px}}.favorite{{flex:0 0 40px;height:40px;border:1px solid #34435d;border-radius:50%;background:#172033;color:#aebbd0;font-size:25px;cursor:pointer;line-height:1}}.favorite.active{{color:var(--gold);border-color:#8b7130;background:#342b18}}.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;list-style:none;padding:0;margin:15px 0}}.card-tile{{position:relative;aspect-ratio:.73;border-radius:9px;overflow:hidden;background:linear-gradient(145deg,#253a66,#39223d);border:1px solid #35445e}}.card-tile img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1}}.card-fallback{{position:absolute;inset:0;display:grid;place-items:center;font-size:18px;font-weight:900;color:#ffffff77}}.card-name{{position:absolute;z-index:2;bottom:0;left:0;right:0;padding:14px 3px 4px;background:linear-gradient(transparent,#05070df2 48%);font-size:9px;line-height:1.05;text-align:center;color:white;text-shadow:0 1px 3px #000;min-height:30px}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}}.stats div{{background:#171f30;border:1px solid #28364e;border-radius:10px;padding:9px;text-align:center}}.stats strong{{display:block;color:var(--green);font-size:17px}}.stats span{{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;margin-top:2px}}.foot,.actions{{display:flex;justify-content:space-between;gap:10px;align-items:center}}.foot{{color:var(--muted);font-size:11px;border-top:1px solid #27344b;margin-top:12px;padding-top:10px}}.actions{{margin-top:12px}}.actions button,.actions a{{border:0;border-radius:10px;padding:9px 13px;text-decoration:none;font-weight:750;cursor:pointer}}.copy{{background:linear-gradient(90deg,var(--blue),var(--cyan));color:#061320}}.actions a{{background:#202b3e;color:var(--ink)}}
.load-zone{{text-align:center;margin-top:26px}}.load-more{{background:#1a263b;border:1px solid #3b4d6b;color:var(--ink);border-radius:13px;padding:12px 24px;font-weight:800;cursor:pointer}}.empty{{color:var(--muted);text-align:center;padding:70px 20px}}.footer-note{{text-align:center;color:#6f7d94;font-size:12px;margin-top:36px}}
@media(max-width:1080px){{.grid{{grid-template-columns:1fr}}.filter-main{{grid-template-columns:1fr 1fr}}.filter-more{{grid-template-columns:1fr 1fr auto auto}}.overview{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:680px){{.shell{{padding:14px 12px 55px}}.hero{{padding:22px 18px}}.hero-main{{display:block}}.updated{{text-align:left;margin-top:16px}}.overview{{gap:8px}}.overview div{{padding:11px}}.overview strong{{font-size:19px}}.toolbar{{position:static}}.filter-main,.filter-more{{grid-template-columns:1fr}}.toggle{{padding:7px 3px}}.exclude-menu{{position:fixed;left:10px;right:10px;top:70px;width:auto;max-height:80vh}}.exclude-list{{max-height:56vh}}.results-bar{{align-items:start;flex-direction:column}}.legend{{display:none}}.cards{{grid-template-columns:repeat(4,1fr)}}.deck{{padding:13px}}.stats{{grid-template-columns:repeat(2,1fr)}}.foot{{align-items:start;flex-direction:column}}.actions a,.actions button{{text-align:center;flex:1}}}}
</style></head><body><div class="shell">
<header class="hero"><div class="hero-main"><div><div class="eyebrow">Rastreador del meta</div><h1>Radar de mazos <span>Marvel Snap</span></h1><p class="subtitle">Descubre combinaciones, compara su rendimiento y encuentra mazos que sí puedes jugar.</p></div><div class="updated"><strong>Actualizado {generated}</strong><br>Próxima revisión {next_update}</div></div>
<div class="overview"><div><strong>{deck_count:,}</strong><span>mazos encontrados</span></div><div class="highlight"><strong>{new_count:,}</strong><span>nuevos desde el último rastreo</span></div><div><strong>{archetype_count}</strong><span>arquetipos</span></div><div><strong>{total_matches:,}</strong><span>partidas analizadas</span></div></div></header>
<section class="toolbar" aria-label="Filtros"><div class="filter-main"><div class="control"><label for="search">Buscar carta o mazo</label><input id="search" type="search" placeholder="Buscar carta, mazo o arquetipo…"></div><div class="control"><label for="archetype">Arquetipo</label><select id="archetype"><option value="">Todos</option>{archetype_options}</select></div><div class="control"><label for="order">Orden</label><select id="order"><option value="date_desc">Más recientes primero</option><option value="win_desc">Mayor porcentaje de victorias</option><option value="matches_desc">Más partidas</option><option value="date_asc">Más antiguos primero</option></select></div><div class="control"><label>Cartas que no tienes</label><details class="exclude" id="exclude"><summary id="excludeSummary">Excluir cartas</summary><div class="exclude-menu"><input id="excludeSearch" type="search" placeholder="Buscar una carta…"><div class="exclude-list" id="excludeList">{exclusion_options}</div><button class="clear" id="clearExclusions" type="button">Quitar exclusiones</button></div></details></div></div>
<div class="filter-more"><div class="control"><label for="minWin">Victorias mínimas</label><select id="minWin"><option value="0">Cualquiera</option><option value="50">50% o más</option><option value="55">55% o más</option><option value="60">60% o más</option><option value="65">65% o más</option></select></div><div class="control"><label for="minMatches">Partidas mínimas</label><select id="minMatches"><option value="0">Cualquiera</option><option value="25">25 o más</option><option value="50">50 o más</option><option value="100">100 o más</option><option value="250">250 o más</option></select></div><label class="toggle"><input id="onlyNew" type="checkbox"> Solo nuevos</label><label class="toggle"><input id="onlyFavorites" type="checkbox"> Solo favoritos</label><label class="toggle"><input id="compact" type="checkbox"> Vista compacta</label></div></section>
<div class="results-bar"><p><strong id="resultCount">0</strong> mazos coinciden · mostrando <strong id="visibleCount">0</strong></p><div class="legend"><span><i class="dot"></i>Datos de la última semana</span><span>Media del radar: {average_win:.1f}% victorias</span></div></div>
<main class="grid" id="grid">{articles}</main><p class="empty" id="empty" hidden>No hay mazos con esos filtros. Prueba a quitar alguna exclusión.</p><div class="load-zone"><button class="load-more" id="loadMore" type="button">Mostrar más mazos</button></div><p class="footer-note">Datos públicos de SnapComplete · Favoritos y exclusiones se guardan únicamente en este navegador.</p></div>
<script>
const PAGE=24,grid=document.getElementById('grid'),items=[...document.querySelectorAll('.deck')];let limit=PAGE,filtered=[];
const $=id=>document.getElementById(id),favorites=new Set(JSON.parse(localStorage.getItem('snapFavorites')||'[]'));const controls=['search','archetype','order','minWin','minMatches','onlyNew','onlyFavorites'];
function excluded(){{return new Set([...$('excludeList').querySelectorAll('input:checked')].map(x=>x.value))}}
function decorateFavorites(){{items.forEach(el=>{{const b=el.querySelector('.favorite'),active=favorites.has(el.dataset.id);b.classList.toggle('active',active);b.textContent=active?'★':'☆';b.setAttribute('aria-label',active?'Quitar de favoritos':'Guardar en favoritos')}})}}
function apply(){{const text=$('search').value.toLowerCase().trim(),arch=$('archetype').value,minWin=+$('minWin').value,minMatches=+$('minMatches').value,blocked=excluded();filtered=items.filter(el=>{{const cards=new Set(el.dataset.cards.split('|'));return el.dataset.search.includes(text)&&(!arch||el.dataset.archetype===arch)&&+el.dataset.winRate>=minWin&&+el.dataset.matches>=minMatches&&(!$('onlyNew').checked||el.dataset.new==='1')&&(!$('onlyFavorites').checked||favorites.has(el.dataset.id))&&![...blocked].some(c=>cards.has(c))}});const mode=$('order').value;filtered.sort((x,y)=>mode==='date_asc'?x.dataset.firstSeen.localeCompare(y.dataset.firstSeen):mode==='win_desc'?+y.dataset.winRate-+x.dataset.winRate:mode==='matches_desc'?+y.dataset.matches-+x.dataset.matches:y.dataset.firstSeen.localeCompare(x.dataset.firstSeen));items.forEach(el=>el.hidden=true);filtered.slice(0,limit).forEach(el=>{{el.hidden=false;grid.appendChild(el)}});$('resultCount').textContent=filtered.length.toLocaleString('es-ES');$('visibleCount').textContent=Math.min(limit,filtered.length).toLocaleString('es-ES');$('empty').hidden=filtered.length!==0;$('loadMore').hidden=limit>=filtered.length;const count=blocked.size;$('excludeSummary').textContent=count?`Excluir cartas (${{count}})`:'Excluir cartas';}}
controls.forEach(id=>$(id).addEventListener(id==='search'?'input':'change',()=>{{limit=PAGE;apply()}}));$('excludeList').addEventListener('change',()=>{{limit=PAGE;apply()}});$('excludeSearch').addEventListener('input',e=>{{const t=e.target.value.toLowerCase();document.querySelectorAll('.exclude-card').forEach(x=>x.hidden=!x.dataset.name.includes(t))}});$('clearExclusions').addEventListener('click',()=>{{document.querySelectorAll('#excludeList input:checked').forEach(x=>x.checked=false);limit=PAGE;apply()}});$('loadMore').addEventListener('click',()=>{{limit+=PAGE;apply()}});$('compact').addEventListener('change',e=>document.body.classList.toggle('compact',e.target.checked));
document.addEventListener('click',async e=>{{const fav=e.target.closest('.favorite');if(fav){{const id=fav.closest('.deck').dataset.id;favorites.has(id)?favorites.delete(id):favorites.add(id);localStorage.setItem('snapFavorites',JSON.stringify([...favorites]));decorateFavorites();apply();return}}const b=e.target.closest('button[data-code]');if(!b)return;try{{await navigator.clipboard.writeText(b.dataset.code);const old=b.textContent;b.textContent='Copiado ✓';setTimeout(()=>b.textContent=old,1400)}}catch{{b.textContent='No se pudo copiar'}}}});
const compactStyle=document.createElement('style');compactStyle.textContent='body.compact .card-name{{display:none}}body.compact .deck{{padding:11px}}body.compact .cards{{gap:3px;margin:9px 0}}body.compact .foot{{display:none}}';document.head.appendChild(compactStyle);decorateFavorites();apply();
</script></body></html>'''
    return template.format(**data)


def _load_card_metadata() -> Dict[str, Dict]:
    try:
        with open(CARD_CACHE_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _humanize_card_name(value: str) -> str:
    specials = {
        "DrDoom": "Doctor Doom", "DrOctopus": "Doctor Octopus",
        "SpiderMan": "Spider-Man", "IronMan": "Iron Man",
        "AntMan": "Ant-Man", "MODOK": "M.O.D.O.K.", "X23": "X-23",
        "JeffTheBabyLandShark": "Jeff the Baby Land Shark",
        "JeffTheBabyDolphin": "Jeff the Baby Dolphin!?",
    }
    if value in specials:
        return specials[value]
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return spaced.replace("_", " ").strip()


def _card_image_url(display_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
    return f"https://marvelsnapzone.com/wp-content/themes/blocksy-child/assets/media/cards/{slug}.webp"


def _initials(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(word[0] for word in words[:3]).upper() or "?"


def _next_update(now: datetime) -> datetime:
    for hour in (10, 19):
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _display_date(value: str | None) -> str:
    date = _parse_date(value)
    return date.astimezone(MADRID).strftime("%d/%m/%Y · %H:%M") if date else "—"

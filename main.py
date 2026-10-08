import argparse
import json
import logging
import os
import sys
import webbrowser
from pathlib import Path

from src.dashboard import render_dashboard
from src.database import (
    finish_run,
    init_db,
    list_decks,
    start_run,
    stats,
    upsert_decks,
)
from src.source_snapcomplete import SnapCompleteClient


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "radar_mazos.log")

if getattr(sys.stdout, "encoding", "") != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
logger = logging.getLogger("main")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def update() -> dict:
    config = load_config()
    source = config.get("source", {})
    init_db()
    run_id = start_run()
    try:
        logger.info("Consultando mazos publicos de Marvel Snap...")
        decks = SnapCompleteClient().fetch_decks(
            period=str(source.get("period", "week")),
            mode=str(source.get("mode", "ranked-conquest")),
            minimum_games=int(source.get("minimum_games", 10)),
            maximum_decks=int(source.get("maximum_decks", 250)),
            sort=str(source.get("sort", "win_rate")),
        )
        inserted, updated = upsert_decks(decks)
        finish_run(
            run_id,
            status="ok",
            fetched=len(decks),
            inserted=inserted,
            updated=updated,
        )
        panel = rebuild_dashboard(config)
        result = {
            "recibidos": len(decks),
            "nuevos": inserted,
            "actualizados": updated,
            "panel": panel,
        }
        logger.info("Actualizacion terminada: %s", result)
        return result
    except Exception as exc:
        finish_run(run_id, status="error", message=str(exc))
        logger.exception("No se pudo actualizar el radar")
        raise


def rebuild_dashboard(config: dict | None = None) -> str:
    config = config or load_config()
    dashboard = config.get("dashboard", {})
    decks = list_decks(limit=int(dashboard.get("maximum_rows", 1000)))
    return render_dashboard(
        decks,
        recent_days=int(dashboard.get("recent_days", 7)),
    )


def open_dashboard() -> str:
    init_db()
    path = rebuild_dashboard()
    webbrowser.open(Path(path).resolve().as_uri())
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Radar local de mazos de Marvel Snap")
    parser.add_argument("--update", action="store_true", help="Buscar y guardar mazos nuevos.")
    parser.add_argument("--open", action="store_true", help="Abrir el panel local.")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadisticas de la base de datos.")
    parser.add_argument("--init", action="store_true", help="Crear la base de datos vacia.")
    args = parser.parse_args()

    if args.update:
        print("Resultado:", update())
    elif args.open:
        print("Panel abierto:", open_dashboard())
    elif args.stats:
        init_db()
        print("Estadisticas:", stats())
    elif args.init:
        init_db()
        print("Base de datos preparada.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


"""
seed.py
Script para popular o banco de dados com dados reais da API PandaScore.
Execute este arquivo separadamente: python seed.py

Pode ser executado múltiplas vezes sem duplicar dados (upsert).
"""

import sys
from database.connection import init_db, SessionLocal
from database import repository as repo
from services import pandascore_api as api


def seed_matches(status_filter: str = None, pages: int = 2, per_page: int = 50):
    """
    Busca partidas da API e salva no banco de dados.

    Args:
        status_filter: None (todas), 'running', 'finished', ou 'not_started'
        pages:         quantas páginas buscar da API
        per_page:      partidas por página
    """
    db = SessionLocal()
    total_saved = 0
    total_skipped = 0

    print(f"\n{'='*50}")
    print(f"  CS Match Tracker — Seed de Dados")
    print(f"{'='*50}")
    if status_filter:
        print(f"  Filtro: {status_filter}")
    print(f"  Páginas: {pages} | Por página: {per_page}")
    print(f"{'='*50}\n")

    try:
        for page in range(1, pages + 1):
            print(f"[Seed] Buscando página {page}...")
            matches = api.fetch_matches(page=page, per_page=per_page, status=status_filter)

            if not matches:
                print(f"[Seed] Nenhuma partida retornada na página {page}. Encerrando.")
                break

            for match_data in matches:
                _save_match(db, match_data)
                total_saved += 1

            db.commit()
            print(f"[Seed] Página {page} salva com sucesso ({len(matches)} partidas).")

    except Exception as e:
        db.rollback()
        print(f"\n[Seed] ERRO: {e}")
        raise
    finally:
        db.close()

    print(f"\n{'='*50}")
    print(f"  Seed concluído!")
    print(f"  Partidas processadas : {total_saved}")
    print(f"{'='*50}\n")


def _save_match(db, match_data: dict):
    """
    Salva uma partida e seus times no banco.
    Lógica de upsert: cria se não existe, atualiza se já existe.
    """
    winner_db_id = None

    # 1. Garante que todos os times estão no banco
    for team in match_data.get("teams", []):
        if team.get("id") and team.get("slug"):
            repo.get_or_create_team(
                db=db,
                team_id=team["id"],
                name=team["name"],
                slug=team["slug"],
            )

    # 2. Determina o ID do time vencedor no banco (se houver)
    winner = match_data.get("winner")
    if winner and winner.get("slug"):
        winner_team = repo.get_team_by_slug(db, winner["slug"])
        if winner_team:
            winner_db_id = winner_team.id

    # 3. Cria ou atualiza a partida
    match = repo.create_or_update_match(
        db=db,
        match_id=match_data["id"],
        name=match_data.get("name", ""),
        status=match_data["status"],
        scheduled_at=match_data.get("scheduled_at"),
        winner_id=winner_db_id,
    )

    # 4. Associa os times à partida
    for team in match_data.get("teams", []):
        if team.get("slug"):
            team_db = repo.get_team_by_slug(db, team["slug"])
            if team_db:
                is_winner = winner and winner.get("slug") == team["slug"]
                repo.add_team_to_match(
                    db=db,
                    match_id=match.id,
                    team_id=team_db.id,
                    is_winner=bool(is_winner),
                )


if __name__ == "__main__":
    # Inicializa o banco (cria tabelas se necessário)
    print("[Seed] Inicializando banco de dados...")
    init_db()

    # Lê argumento de linha de comando opcional: python seed.py finished
    status_arg = sys.argv[1] if len(sys.argv) > 1 else None

    # Executa o seed
    seed_matches(status_filter=status_arg, pages=2, per_page=50)

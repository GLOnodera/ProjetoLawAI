"""
app.py
Ponto de entrada da aplicação Flask.
Define as rotas e conecta todas as camadas da aplicação.
"""

from flask import Flask, render_template, request
from database.connection import init_db, SessionLocal
from database import repository as repo

# ─────────────────────────────────────────────
# Inicialização do Flask
# ─────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)


# ─────────────────────────────────────────────
# Context manager para sessão de banco por request
# ─────────────────────────────────────────────

def get_db_session():
    """Cria uma sessão de banco para uso em uma rota."""
    return SessionLocal()


# ─────────────────────────────────────────────
# Rotas
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """
    Rota principal — lista todas as partidas.
    Suporta filtro opcional por status via query string: /?status=finished
    """
    db = get_db_session()
    status_filter = request.args.get("status", "").strip().lower() or None

    try:
        if status_filter and status_filter in ("running", "finished", "not_started"):
            matches = repo.get_matches_by_status(db, status_filter)
        else:
            matches = repo.get_all_matches(db)
            status_filter = None  # normaliza para o template

        # Conta partidas por status para exibir nos badges do header
        all_matches = repo.get_all_matches(db)
        stats = _compute_stats(all_matches)

    finally:
        db.close()

    return render_template(
        "index.html",
        matches=matches,
        status_filter=status_filter,
        stats=stats,
    )


@app.route("/match/<int:match_id>")
def match_detail(match_id: int):
    """
    Página de detalhes de uma partida.
    Combina dados do banco (base) com dados ricos da API (mapas + jogadores).
    """
    db = get_db_session()
    try:
        from sqlalchemy.orm import joinedload
        from database.models import Match, MatchTeam
        match = (
            db.query(Match)
            .filter(Match.id == match_id)
            .options(
                joinedload(Match.teams).joinedload(MatchTeam.team),
                joinedload(Match.winner),
            )
            .first()
        )
        if not match:
            return render_template("index.html", matches=[], stats={}, error=f"Partida #{match_id} não encontrada.")
    finally:
        db.close()

    # Busca dados ricos da API (mapas e jogadores)
    from services import pandascore_api as api
    detail = api.fetch_match_detail(match_id)
    maps    = detail.get("maps", [])
    players = detail.get("players", [])

    print(f"[App] Detalhes partida {match_id}: {len(maps)} mapa(s), {len(players)} jogador(es)")

    # Agrupa jogadores por time para facilitar a exibição
    players_by_team = {}
    for p in players:
        team_name = p["team_name"]
        players_by_team.setdefault(team_name, []).append(p)

    return render_template(
        "match_detail.html",
        match=match,
        maps=maps,
        players_by_team=players_by_team,
        api_available=True,
    )


@app.route("/team/<slug>")
def team_matches(slug: str):
    """
    Rota para ver partidas de um time específico.
    Preparada para uso futuro com filtro por time na interface.
    """
    db = get_db_session()
    try:
        team = repo.get_team_by_slug(db, slug)
        if not team:
            return render_template("index.html", matches=[], stats={}, error=f"Time '{slug}' não encontrado.")

        matches = repo.get_matches_by_team_slug(db, slug)
        stats = _compute_stats(matches)
    finally:
        db.close()

    return render_template(
        "index.html",
        matches=matches,
        status_filter=None,
        stats=stats,
        team_filter=team,
    )


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _compute_stats(matches: list) -> dict:
    """
    Calcula estatísticas simples para exibir no header da página.
    """
    total = len(matches)
    live = sum(1 for m in matches if m.status == "running")
    finished = sum(1 for m in matches if m.status == "finished")
    upcoming = sum(1 for m in matches if m.status == "not_started")
    return {
        "total": total,
        "live": live,
        "finished": finished,
        "upcoming": upcoming,
    }


# ─────────────────────────────────────────────
# Inicialização
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Garante que as tabelas existem antes de iniciar o servidor
    init_db()
    print("\n🎮 CS Match Tracker rodando em http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
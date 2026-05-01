"""
database/repository.py
Camada de repositório — abstrai todas as operações de banco de dados.
Nenhuma query SQL deve aparecer fora deste arquivo.
"""

from sqlalchemy.orm import Session
from database.models import Team, Match, MatchTeam


# ─────────────────────────────────────────────
# TEAMS
# ─────────────────────────────────────────────

def get_or_create_team(db: Session, team_id: int, name: str, slug: str) -> Team:
    """
    Busca um time pelo slug. Se não existir, cria.
    Garante que times não sejam duplicados mesmo ao re-importar dados.
    """
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        team = Team(id=team_id, name=name, slug=slug)
        db.add(team)
        db.flush()  # flush para obter o ID sem commitar a transação inteira
    return team


def get_all_teams(db: Session) -> list[Team]:
    """Retorna todos os times cadastrados."""
    return db.query(Team).order_by(Team.name).all()


def get_team_by_slug(db: Session, slug: str) -> Team | None:
    """Busca um time pelo slug."""
    return db.query(Team).filter(Team.slug == slug).first()


# ─────────────────────────────────────────────
# MATCHES
# ─────────────────────────────────────────────

def get_match_by_id(db: Session, match_id: int) -> Match | None:
    """Busca uma partida pelo ID."""
    return db.query(Match).filter(Match.id == match_id).first()


def create_or_update_match(
    db: Session,
    match_id: int,
    name: str,
    status: str,
    scheduled_at,
    winner_id: int | None,
) -> Match:
    """
    Cria uma nova partida ou atualiza os dados de uma existente.
    Estratégia upsert simples baseada no ID da partida.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if match:
        # Atualiza campos que podem mudar (status, vencedor)
        match.status = status
        match.winner_id = winner_id
    else:
        match = Match(
            id=match_id,
            name=name,
            status=status,
            scheduled_at=scheduled_at,
            winner_id=winner_id,
        )
        db.add(match)
    db.flush()
    return match


def get_all_matches(db: Session) -> list[Match]:
    """
    Retorna todas as partidas ordenadas por data (mais recentes primeiro).
    Faz eager loading dos relacionamentos para evitar N+1 queries.
    """
    from sqlalchemy.orm import joinedload
    return (
        db.query(Match)
        .options(
            joinedload(Match.teams).joinedload(MatchTeam.team),
            joinedload(Match.winner),
        )
        .order_by(Match.scheduled_at.desc().nullslast())
        .all()
    )


def get_matches_by_status(db: Session, status: str) -> list[Match]:
    """Filtra partidas por status (running, finished, not_started)."""
    from sqlalchemy.orm import joinedload
    return (
        db.query(Match)
        .filter(Match.status == status)
        .options(
            joinedload(Match.teams).joinedload(MatchTeam.team),
            joinedload(Match.winner),
        )
        .order_by(Match.scheduled_at.desc().nullslast())
        .all()
    )


def get_matches_by_team_slug(db: Session, team_slug: str) -> list[Match]:
    """
    Filtra partidas em que um time específico participou.
    Preparado para uso futuro com filtro por time na interface.
    """
    from sqlalchemy.orm import joinedload
    team = get_team_by_slug(db, team_slug)
    if not team:
        return []
    return (
        db.query(Match)
        .join(MatchTeam, Match.id == MatchTeam.match_id)
        .filter(MatchTeam.team_id == team.id)
        .options(
            joinedload(Match.teams).joinedload(MatchTeam.team),
            joinedload(Match.winner),
        )
        .order_by(Match.scheduled_at.desc().nullslast())
        .all()
    )


# ─────────────────────────────────────────────
# MATCH TEAMS
# ─────────────────────────────────────────────

def add_team_to_match(
    db: Session, match_id: int, team_id: int, is_winner: bool = False
) -> MatchTeam:
    """
    Associa um time a uma partida. Evita duplicatas verificando antes de inserir.
    """
    existing = (
        db.query(MatchTeam)
        .filter(MatchTeam.match_id == match_id, MatchTeam.team_id == team_id)
        .first()
    )
    if existing:
        existing.is_winner = is_winner
        return existing

    entry = MatchTeam(match_id=match_id, team_id=team_id, is_winner=is_winner)
    db.add(entry)
    db.flush()
    return entry

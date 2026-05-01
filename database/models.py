"""
database/models.py
Define os modelos ORM (tabelas) do banco de dados.
Segue princípios de normalização e boas práticas de modelagem relacional.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.connection import Base


class Team(Base):
    """
    Tabela: teams
    Representa um time de CS/CS2.
    Usa o slug como identificador único para evitar duplicatas.
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Relacionamento reverso: um time pode participar de várias partidas
    match_entries = relationship("MatchTeam", back_populates="team")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Match(Base):
    """
    Tabela: matches
    Representa uma partida de CS/CS2 da PandaScore.
    """
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)           # ex: running, finished, not_started
    scheduled_at = Column(DateTime, nullable=True)         # data/hora agendada
    winner_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Relacionamentos
    winner = relationship("Team", foreign_keys=[winner_id])
    teams = relationship("MatchTeam", back_populates="match")

    def __repr__(self):
        return f"<Match(id={self.id}, status='{self.status}')>"


class MatchTeam(Base):
    """
    Tabela: match_teams
    Tabela de junção entre Match e Team.
    Registra quais times participaram de cada partida e quem venceu.
    """
    __tablename__ = "match_teams"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    is_winner = Column(Boolean, default=False, nullable=False)

    # Relacionamentos
    match = relationship("Match", back_populates="teams")
    team = relationship("Team", back_populates="match_entries")

    def __repr__(self):
        return f"<MatchTeam(match_id={self.match_id}, team_id={self.team_id}, winner={self.is_winner})>"

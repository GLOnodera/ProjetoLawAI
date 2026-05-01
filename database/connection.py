"""
database/connection.py
Gerencia a conexão com o banco de dados SQLite usando SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL do banco SQLite — o arquivo ficará na raiz do projeto
DATABASE_URL = "sqlite:///cs_match_tracker.db"

# Engine principal do SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necessário para SQLite com Flask
    echo=False,  # mude para True para ver as queries SQL no terminal
)

# Fábrica de sessões — cada request usa sua própria sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para os modelos ORM
Base = declarative_base()


def get_db():
    """
    Gerador que fornece uma sessão de banco de dados.
    Garante que a sessão seja fechada corretamente após o uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Cria todas as tabelas no banco de dados se ainda não existirem.
    Deve ser chamado na inicialização da aplicação.
    """
    # Importa os modelos para registrá-los no Base antes de criar as tabelas
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

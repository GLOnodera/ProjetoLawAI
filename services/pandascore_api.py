"""
services/pandascore_api.py
Camada de serviço responsável por toda comunicação com a API PandaScore.
Isola os detalhes da API do resto da aplicação.
Documentação: https://developers.pandascore.co/
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Configurações da API
# ─────────────────────────────────────────────

PANDASCORE_API_KEY = os.getenv("PANDASCORE_API_KEY", "")
BASE_URL = "https://api.pandascore.co"

# Headers padrão para todas as requisições
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {PANDASCORE_API_KEY}",
}


# ─────────────────────────────────────────────
# Funções utilitárias
# ─────────────────────────────────────────────

def _get(endpoint: str, params: dict = None) -> list | dict | None:
    """
    Faz uma requisição GET à API PandaScore.
    Retorna o JSON decodificado ou None em caso de erro.
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, params=params or {}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"[PandaScore] HTTP Error {response.status_code}: {e}")
        return None
    except requests.exceptions.ConnectionError:
        print("[PandaScore] Erro de conexão. Verifique sua internet.")
        return None
    except requests.exceptions.Timeout:
        print("[PandaScore] Timeout ao conectar à API.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[PandaScore] Erro inesperado: {e}")
        return None


def _parse_datetime(dt_string: str | None) -> datetime | None:
    """
    Converte string ISO 8601 da API para objeto datetime do Python.
    Exemplo: "2024-03-15T18:00:00Z" → datetime(2024, 3, 15, 18, 0, 0)
    """
    if not dt_string:
        return None
    try:
        # Remove o 'Z' e converte
        return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────
# Estrutura de dados normalizada
# ─────────────────────────────────────────────

def _normalize_team(team_data: dict | None) -> dict | None:
    """
    Extrai e normaliza os campos relevantes de um time.
    Retorna None se os dados forem inválidos.
    """
    if not team_data or not isinstance(team_data, dict):
        return None
    return {
        "id": team_data.get("id"),
        "name": team_data.get("name", "Unknown Team"),
        "slug": team_data.get("slug", f"team-{team_data.get('id')}"),
    }


def _normalize_match(match_data: dict) -> dict | None:
    """
    Transforma os dados brutos de uma partida da API em uma estrutura limpa.
    Retorna None se a partida não tiver os campos mínimos necessários.
    """
    if not match_data or not match_data.get("id"):
        return None

    # Extrai os times participantes
    opponents = match_data.get("opponents", [])
    teams = []
    for opponent_entry in opponents:
        opponent = opponent_entry.get("opponent")
        team = _normalize_team(opponent)
        if team:
            teams.append(team)

    # Determina o vencedor (pode ser None se a partida ainda não terminou)
    winner_data = match_data.get("winner")
    winner = _normalize_team(winner_data)

    return {
        "id": match_data.get("id"),
        "name": match_data.get("name") or match_data.get("slug", ""),
        "status": match_data.get("status", "unknown"),
        "scheduled_at": _parse_datetime(match_data.get("scheduled_at")),
        "winner": winner,
        "teams": teams,
    }


# ─────────────────────────────────────────────
# Funções públicas da API
# ─────────────────────────────────────────────

def fetch_matches(page: int = 1, per_page: int = 50, status: str = None) -> list[dict]:
    """
    Busca partidas de CS2 da PandaScore.

    Args:
        page:     número da página (paginação da API)
        per_page: quantidade de partidas por página (máx 100)
        status:   filtra por status: 'running', 'finished', 'not_started'

    Returns:
        Lista de dicionários normalizados representando cada partida.
    """
    params = {
        "page": page,
        "per_page": per_page,
        "sort": "-scheduled_at",  # mais recentes primeiro
    }
    if status:
        params["filter[status]"] = status

    raw_data = _get("/csgo/matches", params=params)

    if not raw_data or not isinstance(raw_data, list):
        return []

    normalized = []
    for item in raw_data:
        match = _normalize_match(item)
        if match:
            normalized.append(match)

    print(f"[PandaScore] {len(normalized)} partidas obtidas (página {page})")
    return normalized


def fetch_upcoming_matches(per_page: int = 25) -> list[dict]:
    """Atalho para buscar partidas futuras (not_started)."""
    return fetch_matches(per_page=per_page, status="not_started")


def fetch_live_matches(per_page: int = 25) -> list[dict]:
    """Atalho para buscar partidas ao vivo (running)."""
    return fetch_matches(per_page=per_page, status="running")


def fetch_past_matches(per_page: int = 25) -> list[dict]:
    """Atalho para buscar partidas encerradas (finished)."""
    return fetch_matches(per_page=per_page, status="finished")


# ─────────────────────────────────────────────
# Detalhes ricos de uma partida (mapas + jogadores)
# ─────────────────────────────────────────────

def fetch_match_detail(match_id: int) -> dict | None:
    """
    Busca os detalhes completos de uma partida:
    - Placar por mapa (games)
    - Estatísticas individuais de cada jogador

    Retorna dados parciais mesmo se alguma sub-requisição falhar.
    """
    # 1. Dados base da partida
    print(f"[PandaScore] Buscando detalhes da partida {match_id}...")
    raw = _get(f"/csgo/matches/{match_id}")

    if not raw or not isinstance(raw, dict):
        print(f"[PandaScore] Falha ao buscar partida {match_id} — resposta: {raw}")
        # Retorna estrutura vazia mas válida para não travar a página
        return {"id": match_id, "maps": [], "players": []}

    match = _normalize_match(raw)
    if not match:
        print(f"[PandaScore] Não foi possível normalizar dados da partida {match_id}")
        return {"id": match_id, "maps": [], "players": []}

    # 2. Mapas (games) dentro da partida
    maps = _extract_maps(raw)
    print(f"[PandaScore] {len(maps)} mapa(s) encontrado(s)")
    match["maps"] = maps

    # 3. Estatísticas dos jogadores (falha graciosamente)
    try:
        players = fetch_match_players(match_id)
        print(f"[PandaScore] {len(players)} jogador(es) encontrado(s)")
    except Exception as e:
        print(f"[PandaScore] Erro ao buscar jogadores: {e}")
        players = []
    match["players"] = players

    return match


def _extract_maps(raw_match: dict) -> list[dict]:
    """
    Extrai e normaliza os dados de cada mapa (game) de uma partida.
    Cada game representa um mapa jogado (ex: Mirage, Inferno…)
    """
    games = raw_match.get("games", []) or []
    maps = []

    for game in games:
        # Placar de cada time no mapa
        results = game.get("results") or []
        team_scores = []
        for r in results:
            team_data = r.get("team") or {}
            team_scores.append({
                "team_id":   team_data.get("id"),
                "team_name": team_data.get("name", "?"),
                "score":     r.get("score", 0),
            })

        # Vencedor do mapa
        winner_data = game.get("winner") or {}
        winner_name = winner_data.get("name") if isinstance(winner_data, dict) else None

        maps.append({
            "id":          game.get("id"),
            "number":      game.get("position", len(maps) + 1),  # número do mapa
            "status":      game.get("status", "not_started"),
            "map_name":    (game.get("map") or {}).get("name") or f"Mapa {game.get('position', '?')}",
            "winner_name": winner_name,
            "team_scores": team_scores,
        })

    # Ordena pelos mapas em sequência
    maps.sort(key=lambda m: m["number"])
    return maps


def fetch_match_players(match_id: int) -> list[dict]:
    """
    Busca as estatísticas dos jogadores de uma partida.
    Endpoint: GET /csgo/matches/{id}/players/stats
    Retorna lista normalizada com kills, deaths, assists, rating, etc.
    """
    raw = _get(f"/csgo/matches/{match_id}/players/stats")

    # A PandaScore retorna um objeto com chave "results" para stats
    if not raw:
        return []

    # Pode vir como lista direta ou dentro de {"results": [...]}
    players_raw = raw if isinstance(raw, list) else raw.get("results", [])

    players = []
    for entry in players_raw:
        player = entry.get("player") or {}
        stats  = entry.get("stats") or {}
        team   = entry.get("team") or {}

        # Calcula KD ratio com proteção contra divisão por zero
        kills  = stats.get("kills", 0) or 0
        deaths = stats.get("deaths", 1) or 1
        kd     = round(kills / deaths, 2)

        players.append({
            "name":     player.get("name", "Unknown"),
            "slug":     player.get("slug", ""),
            "team_id":  team.get("id"),
            "team_name": team.get("name", "?"),
            # Estatísticas principais
            "kills":    kills,
            "deaths":   stats.get("deaths", 0) or 0,
            "assists":  stats.get("assists", 0) or 0,
            "kd_ratio": kd,
            "headshots": stats.get("headshots", 0) or 0,
            "headshot_pct": stats.get("headshots_percentage", 0) or 0,
            "adr":      stats.get("average_damage_per_round", 0) or 0,
            "rating":   stats.get("rating", 0) or 0,
        })

    # Ordena: maior rating primeiro, dentro do mesmo time
    players.sort(key=lambda p: (p["team_name"], -p["rating"]))
    return players
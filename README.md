# CS Match Tracker 🎮

Sistema web para acompanhar partidas de Counter-Strike 2, consumindo dados da API PandaScore e exibindo em uma interface dark mode estilo esports.

## Tecnologias

- **Python 3.11+**
- **Flask** — servidor web
- **SQLAlchemy** — ORM para banco de dados
- **SQLite** — banco de dados embutido
- **Requests** — consumo da API REST
- **PandaScore API** — dados de partidas de CS2

## Estrutura do Projeto

```
cs_match_tracker/
├── app.py                      # Ponto de entrada Flask (rotas)
├── seed.py                     # Script de importação de dados
├── requirements.txt
├── .env.example
├── database/
│   ├── connection.py           # Engine e sessão SQLAlchemy
│   ├── models.py               # Modelos ORM (tabelas)
│   └── repository.py          # Camada de acesso a dados
├── services/
│   └── pandascore_api.py       # Integração com a API PandaScore
└── web/
    ├── templates/
    │   └── index.html          # Template principal Jinja2
    └── static/
        └── style.css           # Estilos dark mode
```

## Como Rodar

### 1. Clone o repositório
```bash
git clone <repo-url>
cd cs_match_tracker
```

### 2. Crie e ative um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env e adicione sua chave da PandaScore
```

### 5. Popule o banco de dados
```bash
# Busca partidas de todos os status (running, finished, not_started)
python seed.py

# Ou filtre por status específico:
python seed.py finished
python seed.py running
python seed.py not_started
```

### 6. Inicie o servidor
```bash
python app.py
```

Acesse: **http://localhost:5000**

## Funcionalidades

- 📋 Listagem de todas as partidas em cards
- 🔴 Indicador pulsante para partidas ao vivo
- 🏆 Destaque visual para o time vencedor
- 🔍 Filtros por status (Ao Vivo / Previstas / Concluídas)
- 🎯 Filtro por time (clique no nome do time no rodapé do card)
- 📱 Layout responsivo
- 🔄 Seed idempotente (sem duplicação ao re-executar)

## API PandaScore

Obtenha sua API key gratuita em: https://pandascore.co/

A API oferece até 1.000 requisições/hora no plano gratuito.

## Exemplo de .env

```env
PANDASCORE_API_KEY=seu_token_aqui
FLASK_ENV=development
FLASK_DEBUG=1
```

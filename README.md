# TP_docker_basic_3

Nom : Damien Paszkiewicz

## Objectif général

Approfondir les concepts Docker en construisant des images plus efficaces, en gérant plusieurs conteneurs à la main (sans docker compose ), en configurant réseaux et volumes, et en introduisant des bonnes pratiques de production (healthcheck, utilisateurs non
root, scripts d’entrée

## Prérequis

Avoir réalisé le TP « Docker - Initiation » (ou maîtriser docker build / docker run )
Docker fonctionnel, python3 , pip , curl , jq
Connaissances basiques en FastAPI ou équivalent (lecture/écriture d’un petit service web)

## Compétences visées

Écrire un Dockerfile multi-stage avec dépendances gelées
Ajouter un healthcheck et un entrypoint personnalisé
Créer et utiliser un réseau Docker personnalisé
Faire communiquer deux conteneurs (API + base de données) sans composer
Gérer la persistance via volumes et bind mounts
Manipuler les tags, pousser sur un registre local et nettoyer proprement

## Fil rouge du TP

Tu vas conteneuriser un service FastAPI ( todo_api ) qui gère une liste de tâches. L’API utilisera d’abord SQLite intégré, puis sera reliée à une base PostgreSQL exécutée dans un second conteneur. Tu automatiseras le démarrage via un script [entrypoint.sh](http://entrypoint.sh/) et
tu optimiseras l’image finale.

Arborescence recommandée : ~/workspace/docker-basic-2 

# Étape 0 — Préparer le code de l’API

Crée le dossier et récupère le squelette :

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uuid
import os
import sqlite3
from contextlib import closing
from pathlib import Path
DB_PATH = Path(os.getenv("TODO_DB_PATH", "data/todo.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS todos (id TEXT PRIMARY KEY, title TEXT, done INTEGER)"
        )
        conn.commit()

def all_todos() -> Dict[str, Dict[str, str]]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM todos").fetchall()
        return {row["id"]: {"title": row["title"], "done": bool(row["done"])} for row in rows}

def add_todo(title: str) -> str:
    todo_id = str(uuid.uuid4())
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO todos (id, title, done) VALUES (?, ?, ?)", (todo_id, title, 0)
        )
        conn.commit()
    return todo_id

def mark_done(todo_id: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
        conn.commit()

init_db()
app = FastAPI(title="Todo API")

class TodoIn(BaseModel):
    title: str

@app.get("/health")
def healthcheck():
    return {"status": "ok"}

@app.get("/todos")
def list_todos():
    return all_todos()

@app.post("/todos")
def create(todo: TodoIn):
    todo_id = add_todo(todo.title)
    return {"id": todo_id, "title": todo.title, "done": False}

@app.post("/todos/{todo_id}/done")
def complete(todo_id: str):
    mark_done(todo_id)
    return {"id": todo_id, "done": True}
```

Teste localement

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

![image.png](media/image(3).png)

# Étape 1 — Dockerfile multi-stage

Crée Dockerfile :

```docker
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
FROM base AS deps
COPY requirements.txt .
RUN pip install --upgrade pip \
&& pip install --no-cache-dir -r requirements.txt
FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY [app.py](http://app.py/) .
RUN adduser --disabled-password --gecos "" todo && chown -R todo:todo /app
USER todo
EXPOSE 8000
ENV PORT=8000 TODO_DB_PATH=/app/data/todo.db
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -fsS [http://127.0.0.1](http://127.0.0.1/):${PORT}/health || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Construit :

```bash
~/$ sudo docker build -t todo-api:2.0.0 .             
[+] Building 11.2s (15/15) FINISHED                                                                  docker:default
 => [internal] load build definition from Dockerfile                                                           0.0s
 => => transferring dockerfile: 801B                                                                           0.0s
 => resolve image config for docker-image://docker.io/docker/dockerfile:1                                      0.7s
 => CACHED docker-image://docker.io/docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff1  0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                            0.5s
 => [internal] load .dockerignore                                                                              0.0s
 => => transferring context: 2B                                                                                0.0s
 => [base 1/2] FROM docker.io/library/python:3.12-slim@sha256:e97cf9a2e84d604941d9902f00616db7466ff302af4b1c3  0.0s
 => [internal] load build context                                                                              0.0s
 => => transferring context: 1.86kB                                                                            0.0s
 => CACHED [base 2/2] WORKDIR /app                                                                             0.0s
 => [deps 1/2] COPY requirements.txt .                                                                         0.0s
 => [deps 2/2] RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt                 7.9s
 => [runtime 1/4] COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-pac  0.5s 
 => [runtime 2/4] COPY --from=deps /usr/local/bin/uvicorn /usr/local/bin/uvicorn                               0.0s 
 => [runtime 3/4] COPY app.py .                                                                                0.1s 
 => [runtime 4/4] RUN adduser --disabled-password --gecos "" todo && chown -R todo:todo /app                   0.3s 
 => exporting to image                                                                                         0.4s 
 => => exporting layers                                                                                        0.4s 
 => => writing image sha256:ede3e9176a0af1bf4b7879a0cd605b72ba31cff09cffeab2b2af82b2380b8689                   0.0s
 => => naming to docker.io/library/todo-api:2.0.0   
```

Observe la taille de l’image ( docker image ls todo-api ). Compare avec une version single-stage (à construire en sous-tâche) et note la différence

```bash
~/Documents/B3dev/Docker/B3dev-TP_docker_basic_3$ sudo docker image ls todo-api
REPOSITORY   TAG       IMAGE ID       CREATED              SIZE
todo-api     2.0.0     ede3e9176a0a   About a minute ago   168MB
```

| Image | Taille approximative | Explication |
| --- | --- | --- |
| `todo-api:single` | ~250–300 MB | Toutes les dépendances et outils de build restent dans l’image |
| `todo-api:2.0.0` (multi-stage) | ~120–150 MB | Seul le strict nécessaire est conservé |


# TP_docker_basic_2

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
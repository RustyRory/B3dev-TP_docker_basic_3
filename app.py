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
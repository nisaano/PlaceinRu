import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.contracts import SessionState
from app.dialogue import missing


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS requests (session_id TEXT, request_id TEXT, fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(session_id, request_id))")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, timezone):
        state = SessionState(session_id=str(uuid4()), timezone=timezone)
        state.missing_parameters = missing(state.trip)
        state.pending_question = state.missing_parameters[0]
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?,?)", (state.session_id, state.model_dump_json()))
        return state

    def get(self, session_id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            raise KeyError(session_id)
        return SessionState.model_validate_json(row[0])

    def mutate(self, session_id, request, kind, operation):
        fingerprint = json.dumps({"kind": kind, "request": request.model_dump(mode="json")}, sort_keys=True)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT fingerprint,response FROM requests WHERE session_id=? AND request_id=?", (session_id, request.request_id)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise Conflict("Этот request_id уже использован для другого действия")
                return json.loads(previous[1])
            row = db.execute("SELECT data FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                raise KeyError(session_id)
            state = SessionState.model_validate_json(row[0])
            if state.state_version != request.expected_state_version:
                raise Conflict("Поездка уже изменена. Обновите состояние и повторите действие.")
            response = operation(state)
            db.execute("UPDATE sessions SET data=? WHERE id=?", (response["state"].model_dump_json(), session_id))
            serializable = {**response, "state": response["state"].model_dump(mode="json")}
            db.execute("INSERT INTO requests VALUES (?,?,?,?)", (session_id, request.request_id, fingerprint, json.dumps(serializable, ensure_ascii=False)))
        return serializable

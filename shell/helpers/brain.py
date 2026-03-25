from __future__ import annotations

import json
import sqlite3
import struct

import sqlite_vec

import workspace as ws
from shell.helpers.embedding import EMBEDDING_DIMS, embed_texts


def _embed_texts(texts):
    """Wrapper so tests can mock embedding generation."""
    return embed_texts(texts)


def _vec_connect():
    conn = ws._connect()
    return conn


def _load_vec_extension(conn):
    if not hasattr(conn, "load_extension"):
        return False
    if hasattr(conn, "enable_load_extension"):
        conn.enable_load_extension(True)
    try:
        sqlite_vec.load(conn)
        return True
    finally:
        if hasattr(conn, "enable_load_extension"):
            conn.enable_load_extension(False)


def _serialize_vec(vec):
    return struct.pack(f"{len(vec)}f", *vec)


def _ensure_vec_table(conn):
    ws._ensure_schema(conn)
    if _load_vec_extension(conn):
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_thoughts USING vec0(embedding float[{EMBEDDING_DIMS}])"
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vec_thoughts (
                rowid INTEGER PRIMARY KEY,
                embedding BLOB NOT NULL
            )
            """
        )
    conn.commit()


def _deserialize_vec(blob):
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def _distance(a, b):
    return sum((left - right) ** 2 for left, right in zip(a, b)) ** 0.5


def _vec_extension_available(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'vec_thoughts' AND type IN ('table', 'virtual table')"
    ).fetchone()
    if row is None:
        return False
    sql = str(row["sql"] or "")
    return "USING vec0" in sql


def capture(content, tags=None, source=""):
    thought = ws.capture_thought(content=content, tags=tags, source=source)
    try:
        embedding = _embed_texts([content])[0]
        with _vec_connect() as conn:
            _ensure_vec_table(conn)
            conn.execute(
                """
                INSERT INTO vec_thoughts(rowid, embedding)
                VALUES ((SELECT rowid FROM thoughts WHERE id = ?), ?)
                """,
                (thought["id"], _serialize_vec(embedding)),
            )
            conn.commit()
    except Exception:
        ws.delete_thought(thought["id"])
        raise
    return thought


def search(query, limit=10, tag=""):
    query_vec = _embed_texts([query])[0]
    with _vec_connect() as conn:
        _ensure_vec_table(conn)
        if _vec_extension_available(conn):
            if tag:
                rows = conn.execute(
                    """
                    SELECT t.id, t.content, t.tags_json, t.source, t.created_at, v.distance
                    FROM vec_thoughts v
                    JOIN thoughts t ON t.rowid = v.rowid
                    WHERE v.embedding MATCH ? AND k = ?
                      AND t.tags_json LIKE ?
                    ORDER BY v.distance
                    """,
                    (_serialize_vec(query_vec), limit * 3, f'%"{tag}"%'),
                ).fetchall()[:limit]
            else:
                rows = conn.execute(
                    """
                    SELECT t.id, t.content, t.tags_json, t.source, t.created_at, v.distance
                    FROM vec_thoughts v
                    JOIN thoughts t ON t.rowid = v.rowid
                    WHERE v.embedding MATCH ? AND k = ?
                    ORDER BY v.distance
                    """,
                    (_serialize_vec(query_vec), limit),
                ).fetchall()
            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "tags": json.loads(row["tags_json"] or "[]"),
                    "source": row["source"],
                    "created_at": row["created_at"],
                    "distance": row["distance"],
                }
                for row in rows
            ]

        if tag:
            rows = conn.execute(
                """
                SELECT t.id, t.content, t.tags_json, t.source, t.created_at, v.embedding
                FROM vec_thoughts v
                JOIN thoughts t ON t.rowid = v.rowid
                WHERE t.tags_json LIKE ?
                """,
                (f'%"{tag}"%',),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT t.id, t.content, t.tags_json, t.source, t.created_at, v.embedding
                FROM vec_thoughts v
                JOIN thoughts t ON t.rowid = v.rowid
                """,
            ).fetchall()
    ranked = []
    for row in rows:
        ranked.append(
            {
                "id": row["id"],
                "content": row["content"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "source": row["source"],
                "created_at": row["created_at"],
                "distance": _distance(_deserialize_vec(row["embedding"]), query_vec),
            }
        )
    ranked.sort(key=lambda row: row["distance"])
    return ranked[:limit]


def list_recent(limit=50, tag=""):
    return ws.list_thoughts(limit=limit, tag=tag or None)


def stats():
    return ws.thought_stats()


def delete(thought_id):
    with _vec_connect() as conn:
        _ensure_vec_table(conn)
        row = conn.execute("SELECT rowid FROM thoughts WHERE id = ?", (thought_id,)).fetchone()
        if row is None:
            return {"deleted": False}
        rowid = row["rowid"]
        conn.execute("BEGIN")
        conn.execute("DELETE FROM vec_thoughts WHERE rowid = ?", (rowid,))
        conn.execute("DELETE FROM thoughts WHERE id = ?", (thought_id,))
        conn.commit()
    ws._audit("thought_deleted", thought_id, actor="system", detail="")
    return {"deleted": True}

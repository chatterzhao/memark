"""Read-only adapters for extracting drawers from supported memory-tool stores."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class PalaceReadError(RuntimeError):
    """Raised when a palace cannot be read through supported adapter surfaces."""


@dataclass(slots=True)
class PalaceDrawer:
    drawer_id: str
    document: str
    wing: str | None
    room: str | None
    source_file: str | None
    filed_at: str | None
    ingest_mode: str | None
    extract_mode: str | None
    added_by: str | None
    chunk_index: int | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _coerce_metadata_value(row: sqlite3.Row) -> Any:
    if row["string_value"] is not None:
        return row["string_value"]
    if row["int_value"] is not None:
        return int(row["int_value"])
    if row["float_value"] is not None:
        return float(row["float_value"])
    if row["bool_value"] is not None:
        return bool(row["bool_value"])
    return None


def _from_metadata_map(drawer_id: str, metadata: dict[str, Any]) -> PalaceDrawer | None:
    document = metadata.get("chroma:document")
    if not isinstance(document, str) or not document.strip():
        return None
    chunk_index = metadata.get("chunk_index")
    if isinstance(chunk_index, bool):
        chunk_index = int(chunk_index)
    elif not isinstance(chunk_index, int):
        chunk_index = None
    return PalaceDrawer(
        drawer_id=drawer_id,
        document=document,
        wing=metadata.get("wing") if isinstance(metadata.get("wing"), str) else None,
        room=metadata.get("room") if isinstance(metadata.get("room"), str) else None,
        source_file=metadata.get("source_file") if isinstance(metadata.get("source_file"), str) else None,
        filed_at=metadata.get("filed_at") if isinstance(metadata.get("filed_at"), str) else None,
        ingest_mode=metadata.get("ingest_mode") if isinstance(metadata.get("ingest_mode"), str) else None,
        extract_mode=metadata.get("extract_mode") if isinstance(metadata.get("extract_mode"), str) else None,
        added_by=metadata.get("added_by") if isinstance(metadata.get("added_by"), str) else None,
        chunk_index=chunk_index,
    )


def _read_with_chromadb(
    palace_dir: Path,
    *,
    ingest_mode: str | None,
    wing: str | None,
    room: str | None,
    limit: int | None,
) -> list[PalaceDrawer]:
    try:
        import chromadb  # type: ignore
    except ModuleNotFoundError as exc:
        raise PalaceReadError("chromadb is not installed in the current Python environment") from exc

    try:
        client = chromadb.PersistentClient(path=str(palace_dir))
        collection = client.get_collection("mempalace_drawers")
    except Exception as exc:  # pragma: no cover - exact exception depends on chromadb version
        raise PalaceReadError(f"unable to open MemPalace collection at {palace_dir}") from exc

    where: dict[str, object] = {}
    if ingest_mode:
        where["ingest_mode"] = ingest_mode
    if wing:
        where["wing"] = wing
    if room:
        where["room"] = room
    query_where = where or None

    results: list[PalaceDrawer] = []
    offset = 0
    batch_size = 500
    while True:
        kwargs: dict[str, object] = {
            "include": ["documents", "metadatas"],
            "limit": batch_size,
            "offset": offset,
        }
        if query_where is not None:
            kwargs["where"] = query_where
        batch = collection.get(**kwargs)
        ids = batch.get("ids", [])
        docs = batch.get("documents", [])
        metas = batch.get("metadatas", [])
        if not docs:
            break
        for drawer_id, document, metadata in zip(ids, docs, metas):
            meta = dict(metadata or {})
            if not isinstance(document, str):
                continue
            record = _from_metadata_map(
                str(drawer_id),
                {"chroma:document": document, **meta},
            )
            if record is None:
                continue
            results.append(record)
            if limit is not None and len(results) >= limit:
                return results
        offset += len(docs)
        if len(docs) < batch_size:
            break
    return results


def _read_with_sqlite(
    palace_dir: Path,
    *,
    ingest_mode: str | None,
    wing: str | None,
    room: str | None,
    limit: int | None,
) -> list[PalaceDrawer]:
    db_path = palace_dir / "chroma.sqlite3"
    if not db_path.exists():
        raise PalaceReadError(f"MemPalace chroma.sqlite3 not found at {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT
              embeddings.id AS embedding_row_id,
              embeddings.embedding_id AS drawer_id,
              embedding_metadata.key AS key,
              embedding_metadata.string_value AS string_value,
              embedding_metadata.int_value AS int_value,
              embedding_metadata.float_value AS float_value,
              embedding_metadata.bool_value AS bool_value
            FROM embeddings
            JOIN embedding_metadata
              ON embedding_metadata.id = embeddings.id
            ORDER BY embeddings.id, embedding_metadata.key
            """
        )
        grouped: dict[int, dict[str, Any]] = {}
        drawer_ids: dict[int, str] = {}
        for row in rows:
            embedding_row_id = int(row["embedding_row_id"])
            grouped.setdefault(embedding_row_id, {})
            drawer_ids[embedding_row_id] = str(row["drawer_id"])
            grouped[embedding_row_id][str(row["key"])] = _coerce_metadata_value(row)
    except sqlite3.Error as exc:
        raise PalaceReadError(f"unable to read {db_path}") from exc
    finally:
        conn.close()

    results: list[PalaceDrawer] = []
    for embedding_row_id in sorted(grouped):
        metadata = grouped[embedding_row_id]
        if ingest_mode and metadata.get("ingest_mode") != ingest_mode:
            continue
        if wing and metadata.get("wing") != wing:
            continue
        if room and metadata.get("room") != room:
            continue
        record = _from_metadata_map(drawer_ids[embedding_row_id], metadata)
        if record is None:
            continue
        results.append(record)
        if limit is not None and len(results) >= limit:
            break
    return results


def _read_mempal_sqlite(
    palace_dir: Path,
    *,
    ingest_mode: str | None,
    wing: str | None,
    room: str | None,
    limit: int | None,
) -> list[PalaceDrawer]:
    db_path = palace_dir / "palace.db"
    if not db_path.exists():
        raise PalaceReadError(f"MemPal palace.db not found at {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        filters = ["deleted_at IS NULL"]
        params: list[object] = []
        if ingest_mode == "convos":
            filters.append("source_type = ?")
            params.append("conversation")
        if wing:
            filters.append("wing = ?")
            params.append(wing)
        if room:
            filters.append("room = ?")
            params.append(room)
        where_clause = " AND ".join(filters)
        sql = (
            "SELECT id, content, wing, room, source_file, added_at, chunk_index "
            f"FROM drawers WHERE {where_clause} ORDER BY added_at, id"
        )
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        raise PalaceReadError(f"unable to read {db_path}") from exc
    finally:
        conn.close()

    results: list[PalaceDrawer] = []
    for row in rows:
        chunk_index = row["chunk_index"]
        if isinstance(chunk_index, bool):
            chunk_index = int(chunk_index)
        elif not isinstance(chunk_index, int):
            chunk_index = None
        results.append(
            PalaceDrawer(
                drawer_id=str(row["id"]),
                document=str(row["content"]),
                wing=str(row["wing"]) if row["wing"] is not None else None,
                room=str(row["room"]) if row["room"] is not None else None,
                source_file=str(row["source_file"]) if row["source_file"] is not None else None,
                filed_at=str(row["added_at"]) if row["added_at"] is not None else None,
                ingest_mode="convos" if ingest_mode == "convos" else None,
                extract_mode=None,
                added_by="mempal",
                chunk_index=chunk_index,
            )
        )
    return results


def read_palace_drawers(
    palace_dir: Path,
    *,
    ingest_mode: str | None = "convos",
    wing: str | None = None,
    room: str | None = None,
    limit: int | None = None,
) -> list[PalaceDrawer]:
    normalized_palace = palace_dir.expanduser().resolve()
    if not normalized_palace.exists():
        raise PalaceReadError(f"MemPalace directory does not exist: {normalized_palace}")

    try:
        if (normalized_palace / "palace.db").exists():
            return _read_mempal_sqlite(
                normalized_palace,
                ingest_mode=ingest_mode,
                wing=wing,
                room=room,
                limit=limit,
            )
        try:
            return _read_with_chromadb(
                normalized_palace,
                ingest_mode=ingest_mode,
                wing=wing,
                room=room,
                limit=limit,
            )
        except PalaceReadError:
            return _read_with_sqlite(
                normalized_palace,
                ingest_mode=ingest_mode,
                wing=wing,
                room=room,
                limit=limit,
            )
    except PalaceReadError as exc:
        raise PalaceReadError(f"unable to read memory store at {normalized_palace}") from exc

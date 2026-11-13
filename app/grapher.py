"""Grapher: MD/JSON sidecars → nodes/edges (+ vectors) → Relate .rl."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import Knobs


@dataclass
class Node:
    label: str
    key: str
    props: dict = field(default_factory=dict)


def _cy_str(v: str) -> str:
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def build_cypher(nodes: list[Node], edges: list[tuple[str, str, str, dict]],
                 vector_props: dict[str, list[float]], vector_dim: int) -> list[str]:
    stmts: list[str] = []
    if vector_props:
        stmts.append(f"CREATE VECTOR INDEX doc_embedding IF NOT EXISTS "
                     f"FOR (d:Document) ON (d.embedding) OPTIONS {{indexConfig: "
                     f"{{`vector.dimensions`: {vector_dim}, `vector.similarity_function`: 'cosine'}}}}")
    for n in nodes:
        props = ", ".join(
            f"{key}: {_cy_str(val)}" if isinstance(val, str) else f"{key}: {json.dumps(val)}"
            for key, val in n.props.items())
        stmts.append(f"MERGE (n:{n.label} {{key: {_cy_str(n.key)}}}) "
                     f"SET n += {{{props}}}")
    for src, rel, dst, props in edges:
        p = ", ".join(f"{key}: {_cy_str(val)}" if isinstance(val, str) else f"{key}: {json.dumps(val)}"
                      for key, val in props.items()) or ""
        stmts.append(
            f"MATCH (a {{key: {_cy_str(src)}}}), (b {{key: {_cy_str(dst)}}}) "
            f"MERGE (a)-[r:{rel} {('{'+p+'}') if p else ''}]->(b)")
    for key, vec in vector_props.items():
        stmts.append(f"MATCH (d:Document {{key: {_cy_str(key)}}}) "
                     f"SET d.embedding = vector({json.dumps(vec)})")
    return stmts


def graphify(k: Knobs) -> dict:
    scrubbed = k.spool_dir / "scrubbed"
    nodes: list[Node] = []
    edges: list = []
    vectors: dict = {}
    dim = 0

    for md_file in sorted(scrubbed.glob("*.md")):
        meta_file = md_file.with_suffix(".md").with_name(md_file.stem + ".scrub.json")
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
        text = md_file.read_text(encoding="utf-8", errors="replace")
        key = md_file.stem
        nodes.append(Node("Document", key, {"path": meta.get("path", key),
                                            "redactions": meta.get("redactions", 0)}))
        for email, alias in (meta.get("alias") or {}).items():
            # alias values like CONTACT-1; email is already redacted in text but
            # the mapping lives locally — store alias-nodes, never raw PII
            alias_key = alias
            nodes.append(Node("Contact", alias_key, {}))
            edges.append((key, "MENTIONS", alias_key, {"via": alias}))

        vec = None
        try:
            from .llmqa import embed
            vec = embed(text, k)
        except Exception:
            vec = None
        if vec:
            vectors[key] = vec
            dim = len(vec)

    stats = {"docs": len([n for n in nodes if n.label == "Document"]),
             "contacts": len([n for n in nodes if n.label == "Contact"]),
             "edges": len(edges), "vectors": len(vectors), "dim": dim}

    if nodes or edges:
        stmts = build_cypher(nodes, edges, vectors, dim)
        k.out_dir.mkdir(parents=True, exist_ok=True)
        out = k.out_dir / "build.cypher"
        out.write_text(";\n\n".join(stmts) + ";\n", encoding="utf-8")
        stats["cypher"] = str(out)
        try:
            import relate  # type: ignore
            stats["relate"] = _execute(k, stmts)
        except ImportError:
            stats["relate"] = ("wheel-not-installed — pipe build.cypher into "
                              "`relate query --database personal.rl`")
    return stats


def _execute(k: Knobs, stmts: list[str]) -> str:
    import relate  # type: ignore
    db = relate.connect(str(k.graph_path))
    ok = 0
    for s in stmts:
        try:
            db.execute(s)
            ok += 1
        except Exception:
            continue
    return f"{ok}/{len(stmts)} statements applied"

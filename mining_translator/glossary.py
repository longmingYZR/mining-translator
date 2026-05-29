"""Glossary CRUD operations for mining terminology."""

import json
import os
import uuid
from datetime import datetime, timezone
from .config import CATEGORIES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_glossary(lang_pair: str) -> dict:
    return {
        "metadata": {
            "version": "1.0",
            "language_pair": lang_pair,
            "total_terms": 0,
            "last_updated": _now(),
        },
        "categories": CATEGORIES,
        "terms": [],
    }


def load_glossary(lang: str, glossary_dir: str) -> dict:
    """Load glossary JSON file. Returns empty glossary if file doesn't exist."""
    filepath = os.path.join(glossary_dir, f"zh-{lang}.json")
    if not os.path.exists(filepath):
        return empty_glossary(f"zh-{lang}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return empty_glossary(f"zh-{lang}")


def save_glossary(glossary: dict, lang: str, glossary_dir: str):
    """Atomically save glossary JSON file."""
    glossary["metadata"]["total_terms"] = len(glossary["terms"])
    glossary["metadata"]["last_updated"] = _now()

    filepath = os.path.join(glossary_dir, f"zh-{lang}.json")
    tmppath = filepath + ".tmp"
    with open(tmppath, "w", encoding="utf-8") as f:
        json.dump(glossary, f, indent=2, ensure_ascii=False)
    os.replace(tmppath, filepath)


def merge_terms(glossary: dict, new_terms: list[dict], source_file: str = None) -> dict:
    """Merge extracted terms into glossary. Dedup by source+target match."""
    for term in new_terms:
        source = term.get("source", "").strip()
        target = term.get("target", "").strip()
        if not source or not target:
            continue

        existing = _find_term(glossary, source, target)
        if existing:
            existing["occurrence_count"] = existing.get("occurrence_count", 0) + 1
            if source_file and source_file not in existing.get("source_documents", []):
                existing.setdefault("source_documents", []).append(source_file)
            if term.get("context"):
                contexts = existing.setdefault("contexts", [])
                if term["context"] not in contexts:
                    contexts.append(term["context"])
            existing["updated_at"] = _now()
        else:
            term["id"] = str(uuid.uuid4())
            term["source"] = source
            term["target"] = target
            term.setdefault("definition", "")
            term.setdefault("category", "其他")
            term.setdefault("contexts", [term.get("context")] if term.get("context") else [])
            term.setdefault("source_documents", [source_file] if source_file else [])
            term.setdefault("occurrence_count", 1)
            term.setdefault("confidence", term.get("confidence", "auto"))
            term["created_at"] = _now()
            term["updated_at"] = _now()
            glossary["terms"].append(term)

    return glossary


def _find_term(glossary: dict, source: str, target: str) -> dict | None:
    for t in glossary["terms"]:
        if t["source"] == source and t["target"] == target:
            return t
    return None


def search_terms(glossary: dict, query: str) -> list[dict]:
    """Search terms by fuzzy matching source, target, or definition."""
    q = query.lower()
    results = []
    for t in glossary["terms"]:
        if q in t["source"].lower() or q in t["target"].lower() or q in t.get("definition", "").lower():
            results.append(t)
    return results


def list_terms(glossary: dict, category: str = None, limit: int = 50) -> list[dict]:
    """List terms, optionally filtered by category, sorted by occurrence_count desc."""
    terms = glossary["terms"]
    if category:
        terms = [t for t in terms if t.get("category") == category]
    terms = sorted(terms, key=lambda t: t.get("occurrence_count", 0), reverse=True)
    return terms[:limit]


def add_term(glossary: dict, source: str, target: str, definition: str = None,
             category: str = None, confidence: str = "confirmed") -> dict:
    """Manually add a term."""
    existing = _find_term(glossary, source, target)
    if existing:
        return glossary
    term = {
        "id": str(uuid.uuid4()),
        "source": source.strip(),
        "target": target.strip(),
        "definition": definition or "",
        "category": category or "其他",
        "contexts": [],
        "source_documents": [],
        "occurrence_count": 1,
        "confidence": confidence,
        "created_at": _now(),
        "updated_at": _now(),
    }
    glossary["terms"].append(term)
    return glossary


def edit_term(glossary: dict, term_id: str, **kwargs) -> bool:
    """Edit a term by ID. Updates only provided fields."""
    for t in glossary["terms"]:
        if t["id"] == term_id:
            for k, v in kwargs.items():
                if v is not None and k in t:
                    t[k] = v
            t["updated_at"] = _now()
            return True
    return False


def delete_term(glossary: dict, term_id: str) -> bool:
    """Delete a term by ID."""
    for i, t in enumerate(glossary["terms"]):
        if t["id"] == term_id:
            glossary["terms"].pop(i)
            return True
    return False


def get_stats(glossary: dict) -> dict:
    """Return glossary statistics."""
    terms = glossary["terms"]
    by_category = {}
    by_confidence = {}
    for t in terms:
        cat = t.get("category", "其他")
        by_category[cat] = by_category.get(cat, 0) + 1
        conf = t.get("confidence", "auto")
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

    recent = sorted(terms, key=lambda t: t.get("created_at", ""), reverse=True)[:10]

    return {
        "total_terms": len(terms),
        "by_category": by_category,
        "by_confidence": by_confidence,
        "recently_added": [
            {"id": t["id"], "source": t["source"], "target": t["target"]}
            for t in recent
        ],
    }


def find_terms_in_text(text: str, glossary: dict, max_terms: int = 50) -> list[dict]:
    """Find glossary terms that appear in the given text. Sorted by term length desc."""
    matches = []
    for t in glossary["terms"]:
        if t["source"] in text:
            matches.append(t)
    matches.sort(key=lambda t: len(t["source"]), reverse=True)
    return matches[:max_terms]

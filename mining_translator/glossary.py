"""Unified glossary CRUD - Chinese -> English + Spanish, single JSON file."""

import json
import os
import uuid
from datetime import datetime, timezone
from .config import CATEGORIES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_glossary() -> dict:
    return {
        "metadata": {
            "version": "2.0",
            "total_terms": 0,
            "last_updated": _now(),
        },
        "categories": CATEGORIES,
        "terms": [],
    }


def load_glossary(glossary_dir: str) -> dict:
    filepath = os.path.join(glossary_dir, "terms.json")
    if not os.path.exists(filepath):
        return empty_glossary()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return empty_glossary()


def save_glossary(glossary: dict, glossary_dir: str):
    glossary["metadata"]["total_terms"] = len(glossary["terms"])
    glossary["metadata"]["last_updated"] = _now()
    filepath = os.path.join(glossary_dir, "terms.json")
    tmppath = filepath + ".tmp"
    with open(tmppath, "w", encoding="utf-8") as f:
        json.dump(glossary, f, indent=2, ensure_ascii=False)
    os.replace(tmppath, filepath)


def merge_terms(glossary: dict, new_terms: list[dict], target_lang: str,
                source_file: str = None) -> dict:
    """Merge extracted terms. target_lang is 'en' or 'es'."""
    for term in new_terms:
        source = term.get("source", "").strip()
        target = term.get("target", "").strip()
        if not source or not target:
            continue

        existing = _find_by_source(glossary, source)
        if existing:
            existing[target_lang] = target
            existing["occurrence_count"] = existing.get("occurrence_count", 0) + 1
            if source_file and source_file not in existing.get("source_documents", []):
                existing.setdefault("source_documents", []).append(source_file)
            if term.get("context"):
                contexts = existing.setdefault("contexts", [])
                if term["context"] not in contexts:
                    contexts.append(term["context"])
            existing["updated_at"] = _now()
        else:
            entry = {
                "id": str(uuid.uuid4()),
                "source": source,
                "en": target if target_lang == "en" else "",
                "es": target if target_lang == "es" else "",
                "definition": term.get("definition", ""),
                "category": term.get("category", "其他"),
                "contexts": [term.get("context")] if term.get("context") else [],
                "source_documents": [source_file] if source_file else [],
                "occurrence_count": 1,
                "confidence": term.get("confidence", "auto"),
                "created_at": _now(),
                "updated_at": _now(),
            }
            glossary["terms"].append(entry)
    return glossary


def _find_by_source(glossary: dict, source: str) -> dict | None:
    for t in glossary["terms"]:
        if t["source"] == source:
            return t
    return None


def search_terms(glossary: dict, query: str) -> list[dict]:
    q = query.lower()
    results = []
    for t in glossary["terms"]:
        if (q in t["source"].lower() or q in t.get("en", "").lower()
                or q in t.get("es", "").lower() or q in t.get("definition", "").lower()):
            results.append(t)
    return results


def list_terms(glossary: dict, category: str = None, limit: int = 50) -> list[dict]:
    terms = glossary["terms"]
    if category:
        terms = [t for t in terms if t.get("category") == category]
    terms = sorted(terms, key=lambda t: t.get("occurrence_count", 0), reverse=True)
    return terms[:limit]


def add_term(glossary: dict, source: str, en: str = "", es: str = "",
             definition: str = None, category: str = None, confidence: str = "confirmed") -> dict:
    existing = _find_by_source(glossary, source)
    if existing:
        if en:
            existing["en"] = en
        if es:
            existing["es"] = es
        existing["updated_at"] = _now()
        return glossary
    term = {
        "id": str(uuid.uuid4()),
        "source": source.strip(),
        "en": en.strip(),
        "es": es.strip(),
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
    for t in glossary["terms"]:
        if t["id"] == term_id:
            for k, v in kwargs.items():
                if v is not None and k in t:
                    t[k] = v
            t["updated_at"] = _now()
            return True
    return False


def delete_term(glossary: dict, term_id: str) -> bool:
    for i, t in enumerate(glossary["terms"]):
        if t["id"] == term_id:
            glossary["terms"].pop(i)
            return True
    return False


def get_stats(glossary: dict) -> dict:
    terms = glossary["terms"]
    by_category = {}
    by_confidence = {}
    for t in terms:
        cat = t.get("category", "其他")
        by_category[cat] = by_category.get(cat, 0) + 1
        conf = t.get("confidence", "auto")
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
    return {
        "total_terms": len(terms),
        "by_category": by_category,
        "by_confidence": by_confidence,
    }


def find_terms_in_text(text: str, glossary: dict, target_lang: str = None,
                        max_terms: int = 50) -> list[dict]:
    """Find glossary terms that appear in the text. Returns [{source, target}, ...]."""
    matches = []
    for t in glossary["terms"]:
        if t["source"] in text:
            target = t.get(target_lang, "") if target_lang else (t.get("en", "") or t.get("es", ""))
            if target:
                matches.append({"source": t["source"], "target": target})
    matches.sort(key=lambda t: len(t["source"]), reverse=True)
    return matches[:max_terms]

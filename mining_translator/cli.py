"""CLI entry point for mining-translator."""

import argparse
import io
import os
import sys
import logging

from . import config
from .translator import translate_file
from .glossary import (
    load_glossary, save_glossary, list_terms, search_terms,
    add_term, edit_term, delete_term, get_stats,
)
from .adapters.auto import supported_formats


def _setup_logging():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _output_path(input_path: str, target_lang: str) -> str:
    base, ext = os.path.splitext(os.path.basename(input_path))
    if ext.lower() == ".pdf":
        ext = ".txt"
    os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
    return os.path.join(config.DEFAULT_OUTPUT_DIR, f"{base}_translated_{target_lang}{ext}")


def cmd_translate(args):
    input_path = args.input
    target_lang = args.target
    output_path = args.output or _output_path(input_path, target_lang)

    if os.path.isdir(input_path):
        _batch_translate(input_path, target_lang, args)
        return

    print(f"Translating: {input_path}", file=sys.stderr)
    print(f"  Target: {target_lang}", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    try:
        _, terms = translate_file(
            filepath=input_path, target_lang=target_lang,
            output_path=output_path, backend=args.backend,
            do_extract=not args.no_extract,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Done: {output_path}", file=sys.stderr)
    if terms:
        print(f"Extracted {len(terms)} new mining terms", file=sys.stderr)
        for t in terms[:5]:
            print(f"  - {t['source']} -> {t['target']}", file=sys.stderr)
        if len(terms) > 5:
            print(f"  ... and {len(terms) - 5} more", file=sys.stderr)


def _batch_translate(input_dir: str, target_lang: str, args):
    exts = supported_formats()
    files = [os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir))
             if os.path.splitext(f)[1].lower() in exts]
    if not files:
        print(f"No supported files found in {input_dir}", file=sys.stderr)
        return

    print(f"Batch translating {len(files)} files", file=sys.stderr)
    for i, f in enumerate(files, 1):
        output = args.output or _output_path(f, target_lang)
        print(f"\n[{i}/{len(files)}] {os.path.basename(f)}", file=sys.stderr)
        try:
            translate_file(filepath=f, target_lang=target_lang,
                           output_path=output, backend=args.backend,
                           do_extract=not args.no_extract)
        except Exception as e:
            print(f"  Failed: {e}", file=sys.stderr)


def cmd_glossary_list(args):
    g = load_glossary(config.GLOSSARY_DIR)
    terms = list_terms(g, category=args.category, limit=args.limit)
    if not terms:
        print("Glossary is empty.")
        return
    print(f"Glossary ({len(terms)} terms shown)")
    print("-" * 70)
    for t in terms:
        print(f"  {t['source']}")
        en = t.get('en', '')
        es = t.get('es', '')
        if en:
            print(f"    EN: {en}")
        if es:
            print(f"    ES: {es}")
        cat = t.get("category", "")
        if cat:
            print(f"    [{cat}] x{t.get('occurrence_count', 0)}")


def cmd_glossary_search(args):
    g = load_glossary(config.GLOSSARY_DIR)
    results = search_terms(g, args.query)
    if not results:
        print(f"No terms matching '{args.query}'")
        return
    print(f"Search '{args.query}': {len(results)} matches")
    print("-" * 70)
    for t in results:
        print(f"  [{t['id'][:8]}] {t['source']}")
        if t.get("en"):
            print(f"    EN: {t['en']}")
        if t.get("es"):
            print(f"    ES: {t['es']}")


def cmd_glossary_add(args):
    g = load_glossary(config.GLOSSARY_DIR)
    add_term(g, source=args.source, en=args.en, es=args.es,
             definition=args.definition, category=args.category)
    save_glossary(g, config.GLOSSARY_DIR)
    print(f"Added: {args.source}")


def cmd_glossary_edit(args):
    g = load_glossary(config.GLOSSARY_DIR)
    ok = edit_term(g, args.term_id,
                   source=args.source, en=args.en, es=args.es,
                   definition=args.definition, category=args.category,
                   confidence=args.confidence)
    if ok:
        save_glossary(g, config.GLOSSARY_DIR)
        print(f"Updated term {args.term_id}")
    else:
        print(f"Term not found: {args.term_id}", file=sys.stderr)
        sys.exit(1)


def cmd_glossary_delete(args):
    g = load_glossary(config.GLOSSARY_DIR)
    if delete_term(g, args.term_id):
        save_glossary(g, config.GLOSSARY_DIR)
        print(f"Deleted term {args.term_id}")
    else:
        print(f"Term not found: {args.term_id}", file=sys.stderr)
        sys.exit(1)


def cmd_glossary_stats(args):
    g = load_glossary(config.GLOSSARY_DIR)
    stats = get_stats(g)
    print(f"Glossary Statistics")
    print(f"  Total terms: {stats['total_terms']}")
    print(f"  By category:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"    {cat}: {count}")


def _add_translate_parser(subparsers):
    p = subparsers.add_parser("translate", help="Translate a file")
    p.add_argument("-i", "--input", required=True, help="Input file or directory")
    p.add_argument("-t", "--target", required=True, choices=["en", "es"])
    p.add_argument("-o", "--output", default=None, help="Output file path")
    p.add_argument("--no-extract", action="store_true")
    p.add_argument("--backend", choices=["deepseek", "claude", "openai"],
                   default=config.DEFAULT_BACKEND)
    p.set_defaults(func=cmd_translate)


def _add_glossary_parser(subparsers):
    p = subparsers.add_parser("glossary", help="Manage glossary")
    subs = p.add_subparsers(dest="glossary_cmd")

    p_list = subs.add_parser("list", help="List terms")
    p_list.add_argument("--category", default=None)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_glossary_list)

    p_search = subs.add_parser("search", help="Search terms")
    p_search.add_argument("query")
    p_search.set_defaults(func=cmd_glossary_search)

    p_add = subs.add_parser("add", help="Add a term")
    p_add.add_argument("--source", required=True)
    p_add.add_argument("--en", default="")
    p_add.add_argument("--es", default="")
    p_add.add_argument("--definition", default=None)
    p_add.add_argument("--category", default=None, choices=config.CATEGORIES)
    p_add.set_defaults(func=cmd_glossary_add)

    p_edit = subs.add_parser("edit", help="Edit a term")
    p_edit.add_argument("term_id")
    p_edit.add_argument("--source", default=None)
    p_edit.add_argument("--en", default=None)
    p_edit.add_argument("--es", default=None)
    p_edit.add_argument("--definition", default=None)
    p_edit.add_argument("--category", default=None, choices=config.CATEGORIES)
    p_edit.add_argument("--confidence", default=None,
                        choices=["auto", "confirmed", "rejected"])
    p_edit.set_defaults(func=cmd_glossary_edit)

    p_del = subs.add_parser("delete", help="Delete a term")
    p_del.add_argument("term_id")
    p_del.set_defaults(func=cmd_glossary_delete)

    p_stats = subs.add_parser("stats", help="Glossary stats")
    p_stats.set_defaults(func=cmd_glossary_stats)


def cmd_gui(args):
    from .gui import main as gui_main
    gui_main()


def main():
    _setup_logging()
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="mining-translator",
        description="Mining document translation tool with terminology glossary",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_translate_parser(subparsers)
    _add_glossary_parser(subparsers)

    p_gui = subparsers.add_parser("gui", help="Launch web GUI")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()

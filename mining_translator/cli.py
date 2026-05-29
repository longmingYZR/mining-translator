"""CLI entry point for mining-translator."""

import argparse
import io
import json
import os
import sys
import logging

from . import config
from .translator import translate_file
from .glossary import (
    load_glossary, save_glossary, list_terms, search_terms,
    add_term, edit_term, delete_term, get_stats,
)
from .adapters.auto import supported_formats, get_adapter


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
    """Generate output path: same filename with _translated_{lang} suffix."""
    dirname = config.DEFAULT_OUTPUT_DIR
    base, ext = os.path.splitext(os.path.basename(input_path))
    # PDF outputs as .txt
    if ext.lower() == ".pdf":
        ext = ".txt"
    return os.path.join(dirname, f"{base}_translated_{target_lang}{ext}")


def cmd_translate(args):
    """Handle the translate subcommand."""
    input_path = args.input
    target_lang = args.target
    output_path = args.output or _output_path(input_path, target_lang)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Check if input is a directory (batch mode)
    if os.path.isdir(input_path):
        _batch_translate(input_path, target_lang, args)
        return

    print(f"Translating: {input_path}", file=sys.stderr)
    print(f"  Target: {target_lang}", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    try:
        _, terms = translate_file(
            filepath=input_path,
            target_lang=target_lang,
            output_path=output_path,
            backend=args.backend,
            do_extract=not args.no_extract,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Done: {output_path}", file=sys.stderr)
    if terms:
        print(f"Extracted {len(terms)} new mining terms", file=sys.stderr)
        for t in terms[:5]:
            print(f"  - {t['source']} → {t['target']}", file=sys.stderr)
        if len(terms) > 5:
            print(f"  ... and {len(terms) - 5} more", file=sys.stderr)


def _batch_translate(input_dir: str, target_lang: str, args):
    """Translate all supported files in a directory."""
    exts = supported_formats()
    files = []
    for f in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(f)[1].lower()
        if ext in exts:
            files.append(os.path.join(input_dir, f))

    if not files:
        print(f"No supported files found in {input_dir}", file=sys.stderr)
        return

    print(f"Batch translating {len(files)} files", file=sys.stderr)
    for i, f in enumerate(files, 1):
        output = args.output or _output_path(f, target_lang)
        print(f"\n[{i}/{len(files)}] {os.path.basename(f)}", file=sys.stderr)
        try:
            translate_file(
                filepath=f,
                target_lang=target_lang,
                output_path=output,
                backend=args.backend,
                do_extract=not args.no_extract,
            )
        except Exception as e:
            print(f"  Failed: {e}", file=sys.stderr)
            continue


def cmd_glossary_list(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    terms = list_terms(glossary, category=args.category, limit=args.limit)

    if not terms:
        print(f"Glossary (zh-{args.lang}) is empty.")
        return

    print(f"Glossary: zh-{args.lang} ({len(terms)} terms shown)")
    print("-" * 60)
    for t in terms:
        cat = t.get("category", "")
        occ = t.get("occurrence_count", 0)
        conf = t.get("confidence", "")
        print(f"  {t['source']} → {t['target']}")
        if cat:
            print(f"    Category: {cat} | Occurrences: {occ} | Confidence: {conf}")


def cmd_glossary_search(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    results = search_terms(glossary, args.query)

    if not results:
        print(f"No terms matching '{args.query}' in zh-{args.lang}")
        return

    print(f"Search results for '{args.query}': {len(results)} matches")
    print("-" * 60)
    for t in results:
        print(f"  [{t['id'][:8]}] {t['source']} → {t['target']}")
        if t.get("definition"):
            print(f"    Definition: {t['definition']}")
        if t.get("contexts"):
            print(f"    Context: {t['contexts'][0][:80]}")


def cmd_glossary_add(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    add_term(
        glossary,
        source=args.source,
        target=args.target,
        definition=args.definition,
        category=args.category,
    )
    save_glossary(glossary, args.lang, config.GLOSSARY_DIR)
    print(f"Added: {args.source} → {args.target}")


def cmd_glossary_edit(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    success = edit_term(
        glossary, args.term_id,
        source=args.source, target=args.target,
        definition=args.definition, category=args.category,
        confidence=args.confidence,
    )
    if success:
        save_glossary(glossary, args.lang, config.GLOSSARY_DIR)
        print(f"Updated term {args.term_id}")
    else:
        print(f"Term not found: {args.term_id}", file=sys.stderr)
        sys.exit(1)


def cmd_glossary_delete(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    if delete_term(glossary, args.term_id):
        save_glossary(glossary, args.lang, config.GLOSSARY_DIR)
        print(f"Deleted term {args.term_id}")
    else:
        print(f"Term not found: {args.term_id}", file=sys.stderr)
        sys.exit(1)


def cmd_glossary_stats(args):
    glossary = load_glossary(args.lang, config.GLOSSARY_DIR)
    stats = get_stats(glossary)

    print(f"Glossary: zh-{args.lang}")
    print(f"  Total terms: {stats['total_terms']}")
    print(f"  By category:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"    {cat}: {count}")
    print(f"  By confidence:")
    for conf, count in sorted(stats["by_confidence"].items()):
        print(f"    {conf}: {count}")
    if stats["recently_added"]:
        print(f"  Recently added:")
        for t in stats["recently_added"][:5]:
            print(f"    {t['source']} → {t['target']}")


def _add_translate_parser(subparsers):
    p = subparsers.add_parser("translate", help="Translate a file")
    p.add_argument("-i", "--input", required=True, help="Input file or directory path")
    p.add_argument("-t", "--target", required=True, choices=["en", "es"],
                   help="Target language")
    p.add_argument("-o", "--output", default=None, help="Output file path")
    p.add_argument("--no-extract", action="store_true", help="Skip term extraction")
    p.add_argument("--backend", choices=["deepseek", "claude", "openai"],
                   default=config.DEFAULT_BACKEND, help="LLM backend")
    p.set_defaults(func=cmd_translate)


def _add_glossary_parser(subparsers):
    p = subparsers.add_parser("glossary", help="Manage terminology glossary")
    subs = p.add_subparsers(dest="glossary_cmd")

    # list
    p_list = subs.add_parser("list", help="List glossary terms")
    p_list.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_list.add_argument("--category", default=None)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_glossary_list)

    # search
    p_search = subs.add_parser("search", help="Search glossary terms")
    p_search.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_search.add_argument("query", help="Search query")
    p_search.set_defaults(func=cmd_glossary_search)

    # add
    p_add = subs.add_parser("add", help="Manually add a term")
    p_add.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_add.add_argument("--source", required=True, help="Chinese source term")
    p_add.add_argument("--target", required=True, help="Target language translation")
    p_add.add_argument("--definition", default=None)
    p_add.add_argument("--category", default=None, choices=config.CATEGORIES)
    p_add.set_defaults(func=cmd_glossary_add)

    # edit
    p_edit = subs.add_parser("edit", help="Edit an existing term")
    p_edit.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_edit.add_argument("term_id", help="Term UUID")
    p_edit.add_argument("--source", default=None)
    p_edit.add_argument("--target", default=None)
    p_edit.add_argument("--definition", default=None)
    p_edit.add_argument("--category", default=None, choices=config.CATEGORIES)
    p_edit.add_argument("--confidence", default=None,
                        choices=["auto", "confirmed", "rejected"])
    p_edit.set_defaults(func=cmd_glossary_edit)

    # delete
    p_del = subs.add_parser("delete", help="Delete a term by ID")
    p_del.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_del.add_argument("term_id", help="Term UUID")
    p_del.set_defaults(func=cmd_glossary_delete)

    # stats
    p_stats = subs.add_parser("stats", help="Glossary statistics")
    p_stats.add_argument("-l", "--lang", required=True, choices=["en", "es"])
    p_stats.set_defaults(func=cmd_glossary_stats)


def cmd_gui(args):
    """Launch the Gradio web UI."""
    from .gui import main as gui_main
    gui_main()


def main():
    _setup_logging()

    # Fix Windows console encoding
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(
        prog="mining-translator",
        description="Mining document translation tool with terminology glossary",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_translate_parser(subparsers)
    _add_glossary_parser(subparsers)

    p_gui = subparsers.add_parser("gui", help="Launch the web-based GUI")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

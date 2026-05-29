"""Core translation pipeline - format-agnostic."""

import json
import logging
import os
import re
from . import config
from .llm import translate_text, TranslationError
from .prompts import build_translation_prompt
from .glossary import load_glossary, save_glossary, merge_terms, find_terms_in_text
from .adapters.auto import get_adapter

logger = logging.getLogger(__name__)


def translate_file(filepath: str, target_lang: str, output_path: str = None,
                   glossary_dir: str = None, backend: str = None,
                   do_extract: bool = True) -> tuple[str, list[dict]]:
    """Translate a file. Returns (output_path, new_terms)."""
    glossary_dir = glossary_dir or config.GLOSSARY_DIR
    backend = backend or config.DEFAULT_BACKEND

    adapter = get_adapter(filepath)
    blocks = adapter.extract_texts(filepath)

    translatable = [b for b in blocks if adapter.needs_translation(b)]

    if not translatable:
        for b in blocks:
            b.translated = b.text
        adapter.write_translated(filepath, blocks, output_path)
        return output_path, []

    glossary = load_glossary(glossary_dir)
    combined_text = _combine_blocks(translatable)
    matched_terms = find_terms_in_text(combined_text, glossary, target_lang, max_terms=50)

    system_prompt, user_prompt = build_translation_prompt(
        combined_text, target_lang, matched_terms
    )

    try:
        raw_response = translate_text(
            combined_text, target_lang, system_prompt, user_prompt, backend
        )
    except TranslationError as e:
        logger.error(f"Translation failed: {e}")
        raise

    translated_text, extracted_terms = _parse_response(raw_response)
    _split_translations(translatable, translated_text)

    for b in blocks:
        if b not in translatable:
            b.translated = b.text

    adapter.write_translated(filepath, blocks, output_path)

    filename = os.path.basename(filepath)
    if do_extract and extracted_terms:
        merge_terms(glossary, extracted_terms, target_lang, source_file=filename)
        save_glossary(glossary, glossary_dir)

    return output_path, extracted_terms


def _combine_blocks(blocks: list) -> str:
    if len(blocks) == 1:
        return blocks[0].text
    parts = []
    for i, b in enumerate(blocks):
        parts.append(f"[BLOCK_{i}]\n{b.text}\n[/BLOCK_{i}]")
    return "\n\n".join(parts)


def _split_translations(blocks: list, translated_text: str):
    if len(blocks) == 1:
        blocks[0].translated = translated_text.strip()
        return
    for i, b in enumerate(blocks):
        pattern = rf"\[BLOCK_{i}\](.*?)\[/BLOCK_{i}\]"
        match = re.search(pattern, translated_text, re.DOTALL)
        if match:
            b.translated = match.group(1).strip()
        else:
            logger.warning(f"Could not find translation for block {i}, keeping original")
            b.translated = b.text


def _parse_response(raw: str) -> tuple[str, list[dict]]:
    terms_json = ""
    if "---TERMS---" in raw:
        parts = raw.split("---TERMS---", 1)
        translated = parts[0].strip()
        terms_json = parts[1].strip()
    else:
        match = re.search(r"\[\s*\{.*?\}\s*\]", raw, re.DOTALL)
        if match:
            translated = raw[:match.start()].strip()
            terms_json = match.group(0)
        else:
            logger.warning("Could not parse LLM response")
            return raw.strip(), []

    try:
        terms = json.loads(terms_json)
        if isinstance(terms, list):
            return translated, terms
    except json.JSONDecodeError:
        try:
            terms = json.loads(re.sub(r",\s*]", "]", terms_json))
            if isinstance(terms, list):
                return translated, terms
        except json.JSONDecodeError:
            logger.warning("Failed to parse terms JSON")
    return translated, []

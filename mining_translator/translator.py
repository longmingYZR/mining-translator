"""Core translation pipeline - format-agnostic."""

import json
import logging
import re
from . import config
from .llm import translate_text, TranslationError
from .prompts import build_translation_prompt
from .glossary import load_glossary, save_glossary, merge_terms, find_terms_in_text
from .adapters.auto import get_adapter
from .adapters.base import TextBlock

logger = logging.getLogger(__name__)


def translate_file(
    filepath: str,
    target_lang: str,
    output_path: str = None,
    glossary_dir: str = None,
    backend: str = None,
    do_extract: bool = True,
) -> tuple[str, list[dict]]:
    """Translate a single file. Returns (output_path, new_terms)."""
    glossary_dir = glossary_dir or config.GLOSSARY_DIR
    backend = backend or config.DEFAULT_BACKEND

    adapter = get_adapter(filepath)
    blocks = adapter.extract_texts(filepath)

    # Filter blocks that need translation (contain Chinese)
    translatable = [b for b in blocks if adapter.needs_translation(b)]

    if not translatable:
        # No Chinese text found, copy file as-is
        for b in blocks:
            b.translated = b.text
        adapter.write_translated(filepath, blocks, output_path)
        return output_path, []

    # Load glossary and find relevant terms
    glossary = load_glossary(target_lang, glossary_dir)

    # Combine all source texts for one API call
    # For multi-block files, join with separators
    combined_text = _combine_blocks(translatable)

    # Find matching glossary terms
    matched_terms = find_terms_in_text(combined_text, glossary, max_terms=50)

    # Build prompt and call LLM
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

    # Parse response
    translated_text, extracted_terms = _parse_response(raw_response)

    # Split combined translation back into blocks
    _split_translations(translatable, translated_text)

    # If any blocks weren't translatable, keep them as-is
    for b in blocks:
        if b not in translatable:
            b.translated = b.text

    # Write output
    adapter.write_translated(filepath, blocks, output_path)

    # Merge new terms
    filename = filepath.split("/")[-1].split("\\")[-1]
    if do_extract and extracted_terms:
        merge_terms(glossary, extracted_terms, source_file=filename)
        save_glossary(glossary, target_lang, glossary_dir)

    return output_path, extracted_terms


def _combine_blocks(blocks: list[TextBlock]) -> str:
    """Combine multiple text blocks into one translatable string."""
    if len(blocks) == 1:
        return blocks[0].text
    parts = []
    for i, b in enumerate(blocks):
        parts.append(f"[BLOCK_{i}]\n{b.text}\n[/BLOCK_{i}]")
    return "\n\n".join(parts)


def _split_translations(blocks: list[TextBlock], translated_text: str):
    """Split combined translation back into individual blocks."""
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
    """Parse LLM response into (translated_text, extracted_terms)."""
    terms_json = ""
    if "---TERMS---" in raw:
        parts = raw.split("---TERMS---", 1)
        translated = parts[0].strip()
        terms_json = parts[1].strip()
    else:
        # Fallback: try to find JSON array at the end
        match = re.search(r"\[\s*\{.*?\}\s*\]", raw, re.DOTALL)
        if match:
            terms_start = match.start()
            translated = raw[:terms_start].strip()
            terms_json = match.group(0)
        else:
            logger.warning("Could not find ---TERMS--- separator or JSON array in response")
            return raw.strip(), []

    # Parse terms JSON
    try:
        terms = json.loads(terms_json)
        if isinstance(terms, list):
            return translated, terms
    except json.JSONDecodeError:
        # Try to fix common issues
        try:
            cleaned = re.sub(r",\s*]", "]", terms_json)
            terms = json.loads(cleaned)
            if isinstance(terms, list):
                return translated, terms
        except json.JSONDecodeError:
            logger.warning("Failed to parse terms JSON from response")

    return translated, []

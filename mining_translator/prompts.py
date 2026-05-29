"""Prompt templates for translation and terminology extraction."""

import json


TRANSLATION_SYSTEM = {
    "en": "You are a professional mining industry translator, expert in Chinese-to-English translation. Use the provided glossary for consistent terminology.",
    "es": "You are a professional mining industry translator, expert in Chinese-to-Spanish translation. Use the provided glossary for consistent terminology.",
}


def build_translation_prompt(source_text: str, target_lang: str,
                             glossary_terms: list[dict]) -> tuple[str, str]:
    lang_name = {"en": "English", "es": "Spanish"}[target_lang]

    system = TRANSLATION_SYSTEM[target_lang]

    glossary_str = ""
    if glossary_terms:
        items = [{"source": t["source"], "target": t["target"]} for t in glossary_terms]
        glossary_str = json.dumps(items, ensure_ascii=False, indent=2)

    user = f"""【Known Glossary - use these standard translations】
{glossary_str or "(empty)"}

【Text to translate】
{source_text}

【Output format】
Step 1: Output the complete translation (pure translated text).
Step 2: Output "---TERMS---" as a separator.
Step 3: Output a JSON array of ALL mining terminology found:
[
  {{
    "source": "中文术语",
    "target": "{lang_name} translation",
    "definition": "Brief explanation in {lang_name}",
    "category": "采矿方法|矿物/矿石|设备/机械|安全|环保|地质/勘探|选矿|冶炼/冶金|合同/法律|其他",
    "confidence": "auto"
  }}
]
- If a term is in the glossary, use THAT exact translation.
- Do not miss any specialized mining term."""

    return system, user

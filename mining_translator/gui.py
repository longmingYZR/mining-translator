"""Gradio web UI for mining-translator."""

import os
import gradio as gr

from . import config
from .translator import translate_file
from .glossary import (
    load_glossary, save_glossary, list_terms, search_terms,
    add_term, edit_term, delete_term, get_stats,
)


THEME = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="gray",
    neutral_hue="stone",
).set(
    body_text_size="14px",
    button_primary_background_fill="*primary_600",
    button_primary_text_color="white",
)


def create_ui():
    with gr.Blocks(title="Mining Translator") as app:
        gr.Markdown("# Mining Translator 矿业翻译工具\n> Chinese -> English / Spanish")

        with gr.Tabs():
            with gr.TabItem("Translate 翻译"):
                _build_translate_tab()
            with gr.TabItem("Glossary 术语库"):
                _build_glossary_tab()
    return app


def _build_translate_tab():
    gr.Markdown("### Upload file, select language, translate")

    with gr.Row():
        file_input = gr.File(
            label="Select file",
            file_types=[".txt", ".xlsx", ".xlsm", ".xls", ".docx", ".pptx", ".pdf", ".md", ".csv"],
        )
        target_lang = gr.Radio(
            choices=[("English", "en"), ("Espanol", "es")],
            value="en",
            label="Target language",
        )

    with gr.Row():
        translate_btn = gr.Button("Translate", variant="primary", size="lg")

    status = gr.Markdown("")

    with gr.Row():
        preview_out = gr.Textbox(label="Translation preview", lines=12, interactive=False)

    with gr.Row():
        terms_out = gr.Dataframe(
            headers=["Chinese", "Translation", "Category"],
            label="Extracted terms",
            interactive=False,
            wrap=True,
        )
        download_out = gr.File(label="Download translated file", visible=False)

    translate_btn.click(
        fn=_handle_translate,
        inputs=[file_input, target_lang],
        outputs=[status, preview_out, terms_out, download_out],
    )


def _build_glossary_tab():
    gr.Markdown("### Glossary 术语库")

    with gr.Tabs():
        with gr.TabItem("Browse 浏览"):
            with gr.Row():
                search_box = gr.Textbox(label="Search", scale=3)
                category_filter = gr.Dropdown(
                    choices=["All"] + config.CATEGORIES,
                    value="All",
                    label="Category",
                    scale=1,
                )
            term_table = gr.Dataframe(
                headers=["ID", "Chinese", "English", "Espanol", "Category", "Count"],
                label="Terms",
                interactive=False,
                wrap=True,
            )
            refresh_btn = gr.Button("Refresh")
            refresh_btn.click(
                fn=_handle_list_terms,
                inputs=[search_box, category_filter],
                outputs=term_table,
            )

        with gr.TabItem("Add 添加"):
            with gr.Row():
                ns = gr.Textbox(label="Chinese", scale=2)
                nen = gr.Textbox(label="English", scale=2)
                nes = gr.Textbox(label="Espanol", scale=2)
            with gr.Row():
                ncat = gr.Dropdown(choices=config.CATEGORIES, label="Category", scale=1)
                ndef = gr.Textbox(label="Definition", scale=2)
            add_btn = gr.Button("Add", variant="primary")
            add_msg = gr.Markdown("")
            add_btn.click(
                fn=_handle_add_term,
                inputs=[ns, nen, nes, ncat, ndef],
                outputs=add_msg,
            ).then(
                fn=_handle_list_terms,
                inputs=[search_box, category_filter],
                outputs=term_table,
            )

        with gr.TabItem("Stats 统计"):
            stats_btn = gr.Button("Refresh")
            stats_out = gr.Markdown("")
            stats_btn.click(fn=_handle_stats, inputs=[], outputs=stats_out)


def _handle_translate(file, target_lang):
    if file is None:
        return "Please upload a file first", "", None, None

    filepath = file.name
    if not filepath:
        return "Invalid file path", "", None, None

    base, ext = os.path.splitext(os.path.basename(filepath))
    if ext.lower() == ".pdf":
        ext = ".txt"

    # Save to output directory (NOT temp)
    os.makedirs(config.DEFAULT_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(
        config.DEFAULT_OUTPUT_DIR,
        f"{base}_translated_{target_lang}{ext}"
    )

    try:
        out_path, terms = translate_file(
            filepath=filepath,
            target_lang=target_lang,
            output_path=output_path,
        )

        # Read preview
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                preview = f.read()[:3000]
        except Exception:
            preview = "(Binary file - download to view)"

        term_rows = [
            [t.get("source", ""), t.get("target", ""), t.get("category", "")]
            for t in terms
        ] if terms else []

        lang_label = "English" if target_lang == "en" else "Spanish"
        status = f"Done! Extracted **{len(terms)}** mining terms. File saved to `output/`"

        return status, preview, term_rows, out_path

    except Exception as e:
        return f"Translation failed: {e}", "", None, None


def _handle_list_terms(query, category):
    glossary = load_glossary(config.GLOSSARY_DIR)
    terms = glossary["terms"]
    if query and query.strip():
        terms = search_terms(glossary, query.strip())
    if category and category != "All":
        terms = [t for t in terms if t.get("category") == category]
    terms = sorted(terms, key=lambda t: t.get("occurrence_count", 0), reverse=True)
    return [
        [t["id"][:8], t["source"], t.get("en", ""), t.get("es", ""),
         t.get("category", ""), t.get("occurrence_count", 0)]
        for t in terms
    ]


def _handle_add_term(source, en, es, category, definition):
    if not source or (not en and not es):
        return "Chinese and at least one translation required"
    glossary = load_glossary(config.GLOSSARY_DIR)
    add_term(glossary, source, en=en, es=es, definition=definition, category=category)
    save_glossary(glossary, config.GLOSSARY_DIR)
    return f"Added: **{source}**"


def _handle_stats():
    glossary = load_glossary(config.GLOSSARY_DIR)
    stats = get_stats(glossary)
    md = f"### Statistics\n- **Total terms**: {stats['total_terms']}\n\n**By category**:\n"
    for cat, count in sorted(stats["by_category"].items()):
        md += f"- {cat}: {count}\n"
    md += "\n**By confidence**:\n"
    for conf, count in sorted(stats["by_confidence"].items()):
        md += f"- {conf}: {count}\n"
    return md


def main():
    app = create_ui()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=THEME,
    )


if __name__ == "__main__":
    main()

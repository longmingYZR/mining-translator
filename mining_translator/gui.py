"""Gradio web UI for mining-translator."""

import os
import tempfile
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
    with gr.Blocks(title="矿业翻译工具 Mining Translator") as app:
        gr.Markdown("""
        # 矿业翻译工具 Mining Translator
        > 中文 → 英语 / 西班牙语 | 自动积累矿业术语库
        """)

        with gr.Tabs():
            with gr.TabItem("翻译"):
                _build_translate_tab()
            with gr.TabItem("术语库"):
                _build_glossary_tab()

    return app


def _build_translate_tab():
    gr.Markdown("### 上传文件，开始翻译")

    with gr.Row():
        with gr.Column(scale=2):
            file_input = gr.File(
                label="选择文件",
                file_types=[".txt", ".xlsx", ".xlsm", ".docx", ".pptx", ".pdf", ".md", ".csv"],
            )
        with gr.Column(scale=1):
            target_lang = gr.Radio(
                choices=[("英语", "en"), ("西班牙语", "es")],
                value="en",
                label="目标语言",
            )
            translate_btn = gr.Button("翻译", variant="primary", size="lg")

    status = gr.Markdown("")

    with gr.Row():
        with gr.Column():
            preview_out = gr.Textbox(label="翻译结果预览", lines=15, interactive=False)
        with gr.Column():
            terms_out = gr.Dataframe(
                headers=["中文术语", "译文", "分类", "出现次数"],
                label="提取的矿业术语",
                interactive=False,
                wrap=True,
            )

    download_out = gr.File(label="下载翻译文件", visible=False)

    translate_btn.click(
        fn=_handle_translate,
        inputs=[file_input, target_lang],
        outputs=[status, preview_out, terms_out, download_out],
    )


def _build_glossary_tab():
    gr.Markdown("### 术语库管理")

    lang_sel = gr.Radio(
        choices=[("中英", "en"), ("中西", "es")],
        value="en",
        label="术语库",
    )

    with gr.Tabs():
        with gr.TabItem("浏览术语"):
            with gr.Row():
                search_box = gr.Textbox(label="搜索", placeholder="输入关键词...", scale=3)
                category_filter = gr.Dropdown(
                    choices=["全部"] + config.CATEGORIES,
                    value="全部",
                    label="分类筛选",
                    scale=1,
                )

            term_table = gr.Dataframe(
                headers=["ID", "中文", "译文", "分类", "出现次数", "置信度"],
                label="术语列表",
                interactive=False,
                wrap=True,
            )
            refresh_btn = gr.Button("刷新", size="sm")

            refresh_btn.click(
                fn=_handle_list_terms,
                inputs=[lang_sel, search_box, category_filter],
                outputs=term_table,
            )

        with gr.TabItem("添加术语"):
            with gr.Row():
                new_source = gr.Textbox(label="中文术语", scale=2)
                new_target = gr.Textbox(label="译文", scale=2)
            with gr.Row():
                new_cat = gr.Dropdown(choices=config.CATEGORIES, label="分类", scale=1)
                new_def = gr.Textbox(label="定义说明", scale=2)
            add_btn = gr.Button("添加", variant="primary")
            add_msg = gr.Markdown("")

            add_btn.click(
                fn=_handle_add_term,
                inputs=[lang_sel, new_source, new_target, new_cat, new_def],
                outputs=add_msg,
            ).then(
                fn=_handle_list_terms,
                inputs=[lang_sel, search_box, category_filter],
                outputs=term_table,
            )

        with gr.TabItem("统计"):
            stats_btn = gr.Button("刷新统计")
            stats_out = gr.Markdown("")

            stats_btn.click(
                fn=_handle_stats,
                inputs=lang_sel,
                outputs=stats_out,
            )


# ---- Handlers ----

def _handle_translate(file, target_lang):
    if file is None:
        return "请先上传文件", "", None, None

    filepath = file.name
    if filepath is None:
        return "文件路径无效", "", None, None

    # Generate output in temp dir
    base, ext = os.path.splitext(os.path.basename(filepath))
    if ext.lower() == ".pdf":
        ext = ".txt"
    output_path = os.path.join(tempfile.mkdtemp(), f"{base}_translated_{target_lang}{ext}")

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
            preview = "(二进制文件，请下载查看)"

        # Build terms table
        if terms:
            term_rows = [
                [t.get("source", ""), t.get("target", ""),
                 t.get("category", ""), t.get("occurrence_count", 1)]
                for t in terms
            ]
        else:
            term_rows = []

        status = f"✅ 翻译完成 | 提取 **{len(terms)}** 个矿业术语 | 术语已自动入库"

        return status, preview, term_rows, out_path

    except Exception as e:
        return f"❌ 翻译失败: {str(e)}", "", None, None


def _handle_list_terms(lang, query, category):
    glossary = load_glossary(lang, config.GLOSSARY_DIR)
    terms = glossary["terms"]

    if query and query.strip():
        terms = search_terms(glossary, query.strip())
    if category and category != "全部":
        terms = [t for t in terms if t.get("category") == category]

    terms = sorted(terms, key=lambda t: t.get("occurrence_count", 0), reverse=True)

    return [
        [t["id"][:8], t["source"], t["target"],
         t.get("category", ""), t.get("occurrence_count", 0),
         t.get("confidence", "auto")]
        for t in terms
    ]


def _handle_add_term(lang, source, target, category, definition):
    if not source or not target:
        return "❌ 中文术语和译文不能为空"
    glossary = load_glossary(lang, config.GLOSSARY_DIR)
    add_term(glossary, source, target, definition=definition, category=category)
    save_glossary(glossary, lang, config.GLOSSARY_DIR)
    return f"✅ 已添加: **{source}** → **{target}**"


def _handle_stats(lang):
    glossary = load_glossary(lang, config.GLOSSARY_DIR)
    stats = get_stats(glossary)

    md = f"### 术语库: zh-{lang}\n"
    md += f"- **总术语数**: {stats['total_terms']}\n\n"
    md += "**按分类**:\n"
    for cat, count in sorted(stats["by_category"].items()):
        md += f"- {cat}: {count}\n"

    md += "\n**按置信度**:\n"
    for conf, count in sorted(stats["by_confidence"].items()):
        md += f"- {conf}: {count}\n"

    if stats["recently_added"]:
        md += "\n**最近添加**:\n"
        for t in stats["recently_added"][:5]:
            md += f"- {t['source']} → {t['target']}\n"

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

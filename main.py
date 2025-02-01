# streamlit_app_expanded_fixed.py
# ------------------------------------
# メインの Streamlit アプリ (機能拡充版、設定変更しても入力テキストは消えない例)

import streamlit as st
import re
import io
import json
import pandas as pd  # 必要なら使う
from typing import List, Dict, Tuple, Optional
import multiprocessing
import streamlit.components.v1 as components


from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    hat_to_circumflex,
    circumflex_to_hat,

    replace_esperanto_chars,
    import_placeholders,

    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process,
    apply_ruby_html_header_and_footer
)

# ページ設定
st.set_page_config(page_title="用于世界语文本（含汉字）替换的工具", layout="wide")

st.title("处理世界语文本的汉字替换与 HTML 形式注解（扩展版）")

st.write("---")

# 1) JSONファイル (置換ルール) をロードする (デフォルト or アップロード)
selected_option = st.radio(
    "要如何处理 JSON 文件？(读取替换用 JSON 文件)",
    ("使用默认文件", "上传文件")
)

with st.expander("**示例 JSON 文件（替换用 JSON 文件）**"):
    # サンプルファイルのパス
    json_file_path = './Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json'
    # JSONファイルを読み込んでダウンロードボタンを生成
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例替换用 JSON 文件",
            data=file_json,
            file_name="替换用JSON文件示例.json",
            mime="application/json"
        )

replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "使用默认文件":
    default_json_path = "./Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json"
    try:
        with open(default_json_path, 'r', encoding='utf-8') as f:
            combined_data = json.load(f)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
        st.success("成功读取默认的 JSON 文件。")
    except Exception as e:
        st.error(f"读取 JSON 文件失败: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("上传 JSON 文件（合并3个JSON文件）.json 格式", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("成功读取已上传的 JSON 文件。")
        except Exception as e:
            st.error(f"读取已上传的 JSON 文件失败: {e}")
            st.stop()
    else:
        st.warning("尚未上传 JSON 文件，停止处理。")
        st.stop()

# 2) placeholders (占位符) の読み込み
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt'
)


st.write("---")

# 設定パラメータ (UI) - 高度な設定
st.header("高级设置（并行处理）")
with st.expander("展开并行处理的详细设置"):
    st.write("""
            在此可设置在替换世界语文本（含汉字）时使用的并行处理进程数。  
            """)
    use_parallel = st.checkbox("启用并行处理", value=False)
    num_processes = st.number_input("并行进程数", min_value=2, max_value=6, value=4, step=1)

st.write("---")

# 例: 出力形式など。必要に応じて追加カスタマイズ
format_type = st.selectbox(
    "请选择输出格式（与创建替换用 JSON 文件时相同）：",
    [
        "HTML格式_Ruby文字_大小调整",
        "HTML格式_Ruby文字_大小调整_汉字替换",
        "HTML格式",
        "HTML格式_汉字替换",
        "括弧(号)格式",
        "括弧(号)格式_汉字替换",
        "替换后文字列のみ(仅)保留(简单替换)"
    ]
)

# フォーム外で、変数 processed_text を初期化
processed_text = ""

# 4) 入力テキストのソースを選択 (アップロード or テキストエリア)
st.subheader("输入文本来源")
source_option = st.radio("如何提供输入文本？", ("手动输入", "上传文件"))

uploaded_text = ""
if source_option == "上传文件":
    text_file = st.file_uploader("上传文本文件（UTF-8 编码）", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("文件已读取。")
    else:
        st.warning("尚未上传文本文件。请切换为手动输入或上传文件。")

if "text0_value" not in st.session_state:
    st.session_state["text0_value"] = ""

with st.form(key='text_input_form'):
    if source_option == "手动输入":
        text0 = st.text_area(
            "请输入世界语文本",
            height=150,
            value=st.session_state["text0_value"]
        )
    else:
        if not st.session_state["text0_value"] and uploaded_text:
            st.session_state["text0_value"] = uploaded_text
        text0 = st.text_area(
            "世界语文本（已从文件读取）",
            value=st.session_state["text0_value"],
            height=150
        )

    st.markdown("""如果以「%」(格式为「%<不超过 50 个字符>%」)包裹文本，则该部分不会被替换，会保留原样。""")
    st.markdown("""此外，如果以「@」(格式为「@<不超过 18 个字符>@」)包裹文本，则该部分将执行局部的汉字替换。""")

    letter_type = st.radio('请选择输出的世界语字符形式', ('上标格式', 'x 形式', '^形式'))

    submit_btn = st.form_submit_button('提交')
    cancel_btn = st.form_submit_button('取消')

    if submit_btn:
        st.session_state["text0_value"] = text0

        if use_parallel:
            processed_text = parallel_process(
                text=text0,
                num_processes=num_processes,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )
        else:
            processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                text=text0,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )

        # letter_typeに応じて再変換
        if letter_type == '上標格式':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

# =========================================
# フォーム外の処理: 結果表示・ダウンロード
# =========================================
if processed_text:

    if "HTML" in format_type:
        tab1, tab2 = st.tabs(["HTML 预览", "替换结果（HTML 源代码）"])
        with tab1:
            components.html(processed_text, height=500, scrolling=True)
        with tab2:
            st.text_area("", processed_text, height=300)
    else:
        tab3_list = st.tabs(["替换后的文本"])
        with tab3_list[0]:
            st.text_area("", processed_text, height=300)

    download_data = processed_text.encode('utf-8')
    st.download_button(
        label="下载替换结果",
        data=download_data,
        file_name="替换结果.html",
        mime="text/html"
    )

st.write("---")
st.title("应用的 GitHub 仓库")
st.markdown("https://github.com/Takatakatake/Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese")

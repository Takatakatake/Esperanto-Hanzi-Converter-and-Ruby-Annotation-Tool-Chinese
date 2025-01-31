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

from esp_text_replacement_module import (
    x_to_circumflex,
    circumflex_to_x,
    x_to_hat,
    hat_to_x,
    hat_to_circumflex,
    circumflex_to_hat,

    replace_esperanto_chars,
    convert_to_circumflex,
    unify_halfwidth_spaces,
    wrap_text_with_ruby,
    safe_replace,
    import_placeholders,

    find_percent_enclosed_strings_for_skipping_replacement,
    create_replacements_list_for_intact_parts,
    find_at_enclosed_strings_for_localized_replacement,
    create_replacements_list_for_localized_replacement,

    orchestrate_comprehensive_esperanto_text_replacement,
    process_segment,
    parallel_process
)


st.title("エスペラント文を漢字置換したり、HTML形式の訳ルビを振ったりする (拡張版)")

# 1) JSONファイル (置換ルール) をロードする (デフォルト or アップロード)
selected_option = st.radio(
    "JSONファイルをどうしますか？ (置換用JSONファイルの読み込み)",
    ("デフォルトを使用する", "アップロードする")
)

replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "デフォルトを使用する":
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
        st.success("デフォルトJSONの読み込みに成功しました。")
    except Exception as e:
        st.error(f"JSONファイルの読み込みに失敗: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("JSONファイルをアップロード (合并3个JSON文件).json 形式)", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("アップロードしたJSONの読み込みに成功しました。")
        except Exception as e:
            st.error(f"アップロードJSONファイルの読み込みに失敗: {e}")
            st.stop()
    else:
        st.warning("JSONファイルがアップロードされていません。処理を停止します。")
        st.stop()

# 2) placeholders (占位符) の読み込み
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt'
)

# 3) 設定パラメータ (UI) - 高度な設定
st.subheader("高度な設定 (並列処理)")
with st.expander("詳細設定を開く"):
    use_parallel = st.checkbox("並列処理を使う (テキストが多い場合に高速化)", value=False)
    num_processes = st.number_input("同時プロセス数 (CPUコア数や環境による)", min_value=1, max_value=6, value=4, step=1)

st.write("---")

# 例: 出力形式など。必要に応じて追加カスタマイズ
format_type = st.selectbox(
    "出力形式を選択(置換用のJSONファイルを作成したときと同じ形式を選択):",
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
st.subheader("入力テキストのソース")
source_option = st.radio("入力テキストをどうしますか？", ("手動入力", "ファイルアップロード"))

uploaded_text = ""
if source_option == "ファイルアップロード":
    text_file = st.file_uploader("テキストファイルをアップロード (UTF-8)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("ファイルを読み込みました。")
    else:
        st.warning("テキストファイルがアップロードされていません。手動入力に切り替えるかファイルをアップロードしてください。")

# ------------------------------------------------
# session_state を使って、ユーザーが再設定時にも
# 入力したテキストが消えないようにする例 (あえてやるなら)
# ------------------------------------------------
if "text0_value" not in st.session_state:
    st.session_state["text0_value"] = ""

with st.form(key='text_input_form'):
    # ここでテキストエリアのデフォルト値を session_state から取得
    if source_option == "手動入力":
        text0 = st.text_area(
            "エスペラントの文章を入力してください",
            height=150,
            value=st.session_state["text0_value"]
        )
    else:
        # アップロード済みテキスト
        if not st.session_state["text0_value"] and uploaded_text:
            # セッションステートが空なら、アップロードテキストを初期設定
            st.session_state["text0_value"] = uploaded_text
        text0 = st.text_area(
            "エスペラントの文章(ファイル読み込み済み)",
            value=st.session_state["text0_value"],
            height=150
        )
    st.markdown("""「%」で前後を囲む(「%<50文字以内の文字列>%」形式)と、「%」で囲まれた部分は文字列(漢字)置換せず、元のまま保持することができます。""")
    st.markdown("""また、「@」で前後を囲む(「@<18文字以内の文字列>@」形式)と、「@」で囲まれた部分を局所的に文字列(漢字)置換します。""")
    letter_type = st.radio('出力文字形式', ('上付き文字', 'x 形式', '^形式'))

    submit_btn = st.form_submit_button('送信')
    cancel_btn = st.form_submit_button('キャンセル')

    if submit_btn:
        # ユーザーが送信ボタンを押した時点で、text0 の値を session_state に保存
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
        if letter_type == '上付き文字':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
            ruby_style_head = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ほとんどの環境で動作するルビ表示</title>
<style>

    :root {
    --ruby-color: blue;
    --ruby-font-size: 50%;
    }

    .text-S_S { font-size: 12px; }
    .text-M_M {
    font-size: 16px; 
    font-family: Arial, sans-serif;
    line-height: 1.6 !important; 
    display: block; 
    position: relative;
    }
    .text-L_L { font-size: 20px; }
    .text-X_X { font-size: 24px; }
    ruby {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    vertical-align: top !important;
    line-height: 1.2 !important;
    margin: 0 !important;
    padding: 0 !important;
    }
    .ruby-XXXS_S { --ruby-font-size: 30%; }
    .ruby-XXS_S { --ruby-font-size: 30%; }
    .ruby-XS_S  { --ruby-font-size: 30%; }
    .ruby-S_S   { --ruby-font-size: 40%; }
    .ruby-M_M   { --ruby-font-size: 50%; }
    .ruby-L_L   { --ruby-font-size: 60%; }
    .ruby-XL_L  { --ruby-font-size: 70%; }
    .ruby-XXL_L { --ruby-font-size: 80%; }
    rt {
    display: block !important;
    font-size: var(--ruby-font-size);
    color: var(--ruby-color);
    line-height: 1.05;
    text-align: center;
    }
    rt.ruby-XXXS_S {
    transform: translateY(-6.6em) !important;
    }    
    rt.ruby-XXS_S {
    transform: translateY(-5.6em) !important;
    }
    rt.ruby-XS_S {
    transform: translateY(-4.6em) !important;
    }
    rt.ruby-S_S {
    transform: translateY(-3.7em) !important;
    }
    rt.ruby-M_M {
    transform: translateY(-3.1em) !important;
    }
    rt.ruby-L_L {
    transform: translateY(-2.8em) !important;
    }
    rt.ruby-XL_L {
    transform: translateY(-2.5em) !important;
    }
    rt.ruby-XXL_L {
    transform: translateY(-2.3em) !important;
    }

</style>
</head>
<body>
<p class="text-M_M">
"""
            ruby_style_tail = "</p></body></html>"
        elif format_type in ('HTML格式','HTML格式_汉字替换'):
            ruby_style_head = """<style>
ruby rt {
    color: blue;
}
</style>
"""
            ruby_style_tail = "<br>"
        else:
            ruby_style_head = ""
            ruby_style_tail = ""

        processed_text = ruby_style_head + processed_text + ruby_style_tail

# =========================================
# フォーム外の処理: 結果表示・ダウンロード
# =========================================
if processed_text:
    st.text_area("文字列置換後のテキスト(プレビュー)", processed_text, height=300)

    download_data = processed_text.encode('utf-8')
    st.download_button(
        label="ダウンロード (HTML)",
        data=download_data,
        file_name="processed_text.html",
        mime="text/html"
    )

st.write("---")
st.title("アプリのGitHubリポジトリ")
st.markdown("https://github.com/Takatakatake/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-")

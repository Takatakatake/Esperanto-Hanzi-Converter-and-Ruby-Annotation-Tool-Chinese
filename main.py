# main.py
# --------------------------------------------------------------------
# 这里是 Streamlit 应用程序的主文件 (扩展功能版 202502)
# --------------------------------------------------------------------

import streamlit as st
import re
import io
import json
import pandas as pd  # 如果需要的话使用
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components

import multiprocessing
# 在使用 multiprocessing 时，为避免 PicklingError，必须在 streamlit 中显式指定 "spawn"：
# 如果已经设置过 start method，则会抛出 RuntimeError，这里直接忽略
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass

# 从 esp_text_replacement_module.py 中导入必要函数
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

# --------------------------------------------------------------------
# 通过对函数的结果进行 cache_data，可以加快读取默认的替换用 JSON 文件(可能有 50MB左右)
# (约 1.0 秒 -> 0.5 秒 的加速)
# --------------------------------------------------------------------
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    从 JSON 文件中读取以下三种列表并以元组形式返回:
      1) replacements_final_list
      2) replacements_list_for_localized_string
      3) replacements_list_for_2char
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    replacements_final_list = data.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    replacements_list_for_localized_string = data.get(
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []
    )
    replacements_list_for_2char = data.get(
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []
    )

    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )

# 设置页面基本信息
st.set_page_config(page_title="（汉字替换）世界语文本转换工具", layout="wide")

# 页面主标题
st.title("将世界语文本转换为汉字形式，或生成带有汉字注释的 HTML (扩展版)")

st.write("---")

# --------------------------------------------------------------------
# 第1步：读取 JSON 文件（替换规则）。
#   用户可选择“使用默认”或“上传自定义 JSON”
# --------------------------------------------------------------------
selected_option = st.radio(
    "请选择替换规则 JSON 文件的读取方式：",
    ("使用默认 JSON", "上传 JSON 文件")
)

# 在折叠框中提供一个示例 JSON 文件可下载
with st.expander("【示例 JSON 文件（替换用）】"):
    json_file_path = './Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json'
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例 JSON（替换用）",
            data=file_json,
            file_name="示例_替换用JSON文件.json",
            mime="application/json"
        )

# 准备好这三个列表，以便之后进行替换
replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "使用默认 JSON":
    default_json_path = "./Appの运行に使用する各类文件/最终的な替换用リスト(列表)(合并3个JSON文件).json"
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(default_json_path)
        st.success("成功读取默认 JSON 文件。")
    except Exception as e:
        st.error(f"读取默认 JSON 文件时出错: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("请上传 JSON 文件 (合并3个JSON文件).json 格式", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("已成功读取上传的 JSON 文件。")
        except Exception as e:
            st.error(f"读取上传 JSON 文件时出错: {e}")
            st.stop()
    else:
        st.warning("尚未上传 JSON 文件，无法继续执行。")
        st.stop()

# --------------------------------------------------------------------
# 2) 读取一些与替换相关的 placeholder(占位符) 文件
# --------------------------------------------------------------------
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt'
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt'
)

st.write("---")

# --------------------------------------------------------------------
# 给用户提供一个并行处理（multiprocessing）的配置选项
# --------------------------------------------------------------------
st.header("高级设置：并行处理选项")
with st.expander("点击此处配置并行处理"):
    st.write("""
        如果文本很大，可以通过多进程并行处理加快转换速度。
        请在此处勾选“使用并行处理”，并指定进程数。
    """)
    use_parallel = st.checkbox("使用并行处理", value=False)
    num_processes = st.number_input("并行进程数量", min_value=2, max_value=4, value=4, step=1)


st.write("---")

# --------------------------------------------------------------------
# 选择“输出形式”（HTML 或者带括号等等）
# --------------------------------------------------------------------
format_type = st.selectbox(
    "请选择输出格式（请与生成替换用JSON时的设定保持一致）：",
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

# 准备一个全局字符串 processed_text 来保存处理后的文本
processed_text = ""

# --------------------------------------------------------------------
# 4) 选择如何输入待转换的文本（手动输入或上传文件）
# --------------------------------------------------------------------
st.subheader("输入文本来源")
source_option = st.radio("请选择输入文本的方式：", ("手动输入", "上传文件"))

uploaded_text = ""
if source_option == "上传文件":
    text_file = st.file_uploader("上传文本文件 (UTF-8 编码)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("文件已读取。")
    else:
        st.warning("尚未上传文本文件，请重新上传或切换为手动输入。")

# --------------------------------------------------------------------
# 使用表单的方式，让用户输入文本并提交
# --------------------------------------------------------------------
with st.form(key='profile_form'):
    # 如果上传了文本，则在 text_area 中默认填充
    if uploaded_text:
        initial_text = uploaded_text
    else:
        initial_text = st.session_state.get("text0_value", "")

    text0 = st.text_area(
        "请输入世界语文章",
        height=150,
        value=initial_text  
    )

    st.markdown("""如果您使用“%”包裹文本（例如“%这段文本%”），则这部分内容将**跳过替换**。""")
    st.markdown("""另外，如果您用“@”包裹文本（例如“@这段文本@”），则这部分内容将**只做局部替换**（即使用特定的局部替换列表）。""")

    # 让用户选择“输出字符形式”（上标形式、x 形式、^ 形式）
    letter_type = st.radio('选择世界语字母形式', ('上标形式', 'x 形式', '^形式'))

    # 提交、取消按钮
    submit_btn = st.form_submit_button('提交')
    cancel_btn = st.form_submit_button("取消")

    # 如果用户点击“取消”，则停止执行
    if cancel_btn:
        st.warning("操作已取消。")
        st.stop()

    # 如果点击了“提交”
    if submit_btn:
        # 将本次输入保存到会话状态
        st.session_state["text0_value"] = text0  

        # 根据是否勾选并行处理，调用不同函数
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

        # 将上标形式等应用到结果中
        if letter_type == '上标形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == '^形式':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

# --------------------------------------------------------------------
# 表单外：若已经生成 processed_text，则展示结果
# --------------------------------------------------------------------
if processed_text:
    # 如果文本过大，仅显示部分行：例如先显示前 47 行 + "..." + 后 3 行
    MAX_PREVIEW_LINES = 250  
    lines = processed_text.splitlines()

    if len(lines) > MAX_PREVIEW_LINES:
        first_part = lines[:247]
        last_part = lines[-3:]
        preview_text = "\n".join(first_part) + "\n...\n" + "\n".join(last_part)
        st.warning(
            f"文本行数较多（共 {len(lines)} 行），只显示部分内容（前 247 行 + 后 3 行）。"
        )
    else:
        preview_text = processed_text

    # 如果输出中带有 HTML，则分两个 Tab：一个用于渲染，一个用于查看源码
    if "HTML" in format_type:
        tab1, tab2 = st.tabs(["HTML 预览", "HTML 源码"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area("HTML源码", preview_text, height=300)
    else:
        tab3_list = st.tabs(["转换结果"])
        with tab3_list[0]:
            st.text_area("", preview_text, height=300)

    download_data = processed_text.encode('utf-8')
    st.download_button(
        label="下载转换结果 (HTML)",
        data=download_data,
        file_name="转换结果.html",
        mime="text/html"
    )

st.write("---")
st.title("GitHub 仓库链接")
st.markdown("https://github.com/Takatakatake/Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool_Chinese_beta")
st.markdown("https://github.com/Takatakatake/Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese")

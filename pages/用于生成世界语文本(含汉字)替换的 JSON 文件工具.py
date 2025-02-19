# 用于生成世界语文本(含汉字)替换的 JSON 文件工具.py
# ---------------------------------------------------------------------
# 说明：
#   这是一个放置在 streamlit pages 文件夹中的脚本，用于生成“替换用 JSON 文件”
#   main.py 会调用该 JSON 文件进行世界语文本中插入汉字/注释等操作。
#   本工具允许用户上传 CSV 和自定义 JSON，合并生成大规模的替换规则 JSON。

import streamlit as st
import pandas as pd
import io
import os
import re
import json
import streamlit as st
from typing import List, Dict, Tuple, Optional
import multiprocessing
from io import StringIO
import streamlit.components.v1 as components

# ---------------------------------------------------------------------
# 从 esp_text_replacement_module.py 和 esp_replacement_json_make_module.py
# 导入必要的函数，用来进行世界语字符转换、并行处理构建替换字典等。
# ---------------------------------------------------------------------
from esp_text_replacement_module import (
    convert_to_circumflex,
    safe_replace,
    import_placeholders,
    apply_ruby_html_header_and_footer
)
from esp_replacement_json_make_module import (
    convert_to_circumflex,
    output_format,
    import_placeholders,
    capitalize_ruby_and_rt,
    process_chunk_for_pre_replacements,
    parallel_build_pre_replacements_dict,
    remove_redundant_ruby_if_identical
)

# ---------------------------------------------------------------------
# 以下是关于动词后缀(活用)以及若干特殊后缀(例如 an, on) 的变量定义。
# 这些数据会在生成 JSON 的流程中被使用，用来给特定单词自动添加后缀。
# ---------------------------------------------------------------------

# 动词活用词尾 (as, is, os, us 等)
verb_suffix_2l = {
    'as':'as', 'is':'is', 'os':'os', 'us':'us','at':'at','it':'it','ot':'ot',
    'ad':'ad','iĝ':'iĝ','ig':'ig','ant':'ant','int':'int','ont':'ont'
}

# 例如 an, on 这两个列表，用于在处理世界语词根 + 后缀“an”/“on”时，自动拆分或区分不同含义
AN = [
    ['dietan', '/diet/an/', '/diet/an'],
    ['afrikan', '/afrik/an/', '/afrik/an'],
    ['movadan', '/mov/ad/an/', '/mov/ad/an'],
    ['akcian', '/akci/an/', '/akci/an'],
    ['montaran', '/mont/ar/an/', '/mont/ar/an'],
    ['amerikan', '/amerik/an/', '/amerik/an'],
    ['regnan', '/regn/an/', '/regn/an'],
    ['dezertan', '/dezert/an/', '/dezert/an'],
    ['asocian', '/asoci/an/', '/asoci/an'],
    ['insulan', '/insul/an/', '/insul/an'],
    ['azian', '/azi/an/', '/azi/an'],
    ['ŝtatan', '/ŝtat/an/', '/ŝtat/an'],
    ['doman', '/dom/an/', '/dom/an'],
    ['montan', '/mont/an/', '/mont/an'],
    ['familian', '/famili/an/', '/famili/an'],
    ['urban', '/urb/an/', '/urb/an'],
    ['popolan', '/popol/an/', '/popol/an'],
    ['dekan', '/dekan/', '/dek/an'],
    ['partian', '/parti/an/', '/parti/an'],
    ['lokan', '/lok/an/', '/lok/an'],
    ['ŝipan', '/ŝip/an/', '/ŝip/an'],
    ['eklezian', '/eklezi/an/', '/eklezi/an'],
    ['landan', '/land/an/', '/land/an'],
    ['orientan', '/orient/an/', '/orient/an'],
    ['lernejan', '/lern/ej/an/', '/lern/ej/an'],
    ['enlandan', '/en/land/an/', '/en/land/an'],
    ['kalkan', '/kalkan/', '/kalk/an'],
    ['estraran', '/estr/ar/an/', '/estr/ar/an'],
    ['etnan', '/etn/an/', '/etn/an'],
    ['eŭropan', '/eŭrop/an/', '/eŭrop/an'],
    ['fazan', '/fazan/', '/faz/an'],
    ['polican', '/polic/an/', '/polic/an'],
    ['socian', '/soci/an/', '/soci/an'],
    ['societan', '/societ/an/', '/societ/an'],
    ['grupan', '/grup/an/', '/grup/an'],
    ['ligan', '/lig/an/', '/lig/an'],
    ['nacian', '/naci/an/', '/naci/an'],
    ['koran', '/koran/', '/kor/an'],
    ['religian', '/religi/an/', '/religi/an'],
    ['kuban', '/kub/an/', '/kub/an'],
    ['majoran', '/major/an/', '/major/an'],
    ['nordan', '/nord/an/', '/nord/an'],
    ['paran', 'paran', '/par/an'],
    ['parizan', '/pariz/an/', '/pariz/an'],
    ['parokan', '/parok/an/', '/parok/an'],
    ['podian', '/podi/an/', '/podi/an'],
    ['rusian', '/rus/i/an/', '/rus/ian'],
    ['satan', '/satan/', '/sat/an'],
    ['sektan', '/sekt/an/', '/sekt/an'],
    ['senatan', '/senat/an/', '/senat/an'],
    ['skisman', '/skism/an/', '/skism/an'],
    ['sudan', 'sudan', '/sud/an'],
    ['utopian', '/utopi/an/', '/utopi/an'],
    ['vilaĝan', '/vilaĝ/an/', '/vilaĝ/an'],
    ['arĝentan', '/arĝent/an/', '/arĝent/an']
]

ON = [
    ['duon', '/du/on/', '/du/on'],
    ['okon', '/ok/on/', '/ok/on'],
    ['nombron', '/nombr/on/', '/nombr/on'],
    ['patron', '/patron/', '/patr/on'],
    ['karbon', '/karbon/', '/karb/on'],
    ['ciklon', '/ciklon/', '/cikl/on'],
    ['aldon', '/al/don/', '/ald/on'],
    ['balon', '/balon/', '/bal/on'],
    ['baron', '/baron/', '/bar/on'],
    ['baston', '/baston/', '/bast/on'],
    ['magneton', '/magnet/on/', '/magnet/on'],
    ['beton', 'beton', '/bet/on'],
    ['bombon', '/bombon/', '/bomb/on'],
    ['breton', 'breton', '/bret/on'],
    ['burĝon', '/burĝon/', '/burĝ/on'],
    ['centon', '/cent/on/', '/cent/on'],
    ['milon', '/mil/on/', '/mil/on'],
    ['kanton', '/kanton/', '/kant/on'],
    ['citron', '/citron/', '/citr/on'],
    ['platon', 'platon', '/plat/on'],
    ['dekon', '/dek/on/', '/dek/on'],
    ['kvaron', '/kvar/on/', '/kvar/on'],
    ['kvinon', '/kvin/on/', '/kvin/on'],
    ['seson', '/ses/on/', '/ses/on'],
    ['trion', '/tri/on/', '/tri/on'],
    ['karton', '/karton/', '/kart/on'],
    ['foton', '/fot/on/', '/fot/on'],
    ['peron', '/peron/', '/per/on'],
    ['elektron', '/elektr/on/', '/elektr/on'],
    ['drakon', 'drakon', '/drak/on'],
    ['mondon', '/mon/don/', '/mond/on'],
    ['pension', '/pension/', '/pensi/on'],
    ['ordon', '/ordon/', '/ord/on'],
    ['eskadron', 'eskadron', '/eskadr/on'],
    ['senton', '/sen/ton/', '/sent/on'],
    ['eston', 'eston', '/est/on'],
    ['fanfaron', '/fanfaron/', '/fanfar/on'],
    ['feston', '/feston/', '/fest/on'],
    ['flegmon', 'flegmon', '/flegm/on'],
    ['fronton', '/fronton/', '/front/on'],
    ['galon', '/galon/', '/gal/on'],
    ['mason', '/mason/', '/mas/on'],
    ['helikon', 'helikon', '/helik/on'],
    ['kanon', '/kanon/', '/kan/on'],
    ['kapon', '/kapon/', '/kap/on'],
    ['kokon', '/kokon/', '/kok/on'],
    ['kolon', '/kolon/', '/kol/on'],
    ['komision', '/komision/', '/komisi/on'],
    ['salon', '/salon/', '/sal/on'],
    ['ponton', '/ponton/', '/pont/on'],
    ['koton', '/koton/', '/kot/on'],
    ['kripton', 'kripton', '/kript/on'],
    ['kupon', '/kupon/', '/kup/on'],
    ['lakon', 'lakon', '/lak/on'],
    ['ludon', '/lu/don/', '/lud/on'],
    ['melon', '/melon/', '/mel/on'],
    ['menton', '/menton/', '/ment/on'],
    ['milion', '/milion/', '/mili/on'],
    ['milionon', '/milion/on/', '/milion/on'],
    ['naŭon', '/naŭ/on/', '/naŭ/on'],
    ['violon', '/violon/', '/viol/on'],
    ['trombon', '/trombon/', '/tromb/on'],
    ['senson', '/sen/son/', '/sens/on'],
    ['sepon', '/sep/on/', '/sep/on'],
    ['skadron', 'skadron', '/skadr/on'],
    ['stadion', '/stadion/', '/stadi/on'],
    ['tetraon', 'tetraon', '/tetra/on'],
    ['timon', '/timon/', '/tim/on'],
    ['valon', 'valon', '/val/on']
]

# allowed_values 用于处理 -1 等表示不进行替换的自定义设定
allowed_values = {-1, "-1", "ー１", "ー1", "-１", "－１", "－1"}

# ---------------------------------------------------------------------
# 以下三组列表用于处理 2 字母词根 （前缀/后缀/独立词根）
# ---------------------------------------------------------------------
suffix_2char_roots = [
    'ad', 'ag', 'am', 'ar', 'as', 'at', 'av', 'di', 'ec', 'eg', 'ej',
    'em', 'er', 'et', 'id', 'ig', 'il', 'in', 'ir', 'is', 'it', 'lu',
    'nj', 'op', 'or', 'os', 'ot', 'ov', 'pi', 'te', 'uj', 'ul', 'um',
    'us', 'uz','ĝu','aĵ','iĝ','aĉ','aĝ','ŝu','eĥ'
]
prefix_2char_roots = [
    'al', 'am', 'av', 'bo', 'di', 'du', 'ek', 'el', 'en', 'fi', 'ge',
    'ir', 'lu', 'ne', 'ok', 'or', 'ov', 'pi', 're', 'te', 'uz','ĝu',
    'aĉ','aĝ','ŝu','eĥ'
]
standalone_2char_roots = [
    'al', 'ci', 'da', 'de', 'di', 'do', 'du', 'el', 'en', 'fi', 'ha',
    'he', 'ho', 'ia', 'ie', 'io', 'iu', 'ja', 'je', 'ju','ke', 'la',
    'li', 'mi', 'ne', 'ni', 'nu', 'ok', 'ol', 'po', 'se', 'si', 've',
    'vi','ŭa','aŭ','ĉe','ĝi','ŝi','ĉu'
]

# ---------------------------------------------------------------------
# 下面从文件中读取相应的 placeholder，用于全域替换、二字词根替换、局部替换
# ---------------------------------------------------------------------
imported_placeholders_for_global_replacement = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_$20987$-$499999$_全域替换用.txt'
)
imported_placeholders_for_2char_replacement = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_$13246$-$19834$_二文字词根替换用.txt'
)
imported_placeholders_for_local_replacement = import_placeholders(
    './Appの运行に使用する各类文件/占位符(placeholders)_@20374@-@97648@_局部文字列替换用.txt'
)

# ---------------------------------------------------------------------
# 从 JSON 读取“Unicode_BMP全范围字符宽度(Arial16).json”
# 用于在生成 HTML 形式时，针对文字宽度做精细化处理
# ---------------------------------------------------------------------
with open("./Appの运行に使用する各类文件/Unicode_BMP全范围文字幅(宽)_Arial16.json", "r", encoding="utf-8") as fp:
    char_widths_dict = json.load(fp)

# ---------------------------------------------------------------------
# 设置当前 Streamlit 页面的基本属性（标题、布局等）
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="生成用于世界语文本(汉字)替换的 JSON 文件",
    layout="wide"
)
st.title("生成世界语文本(含汉字)替换所需的 JSON 文件")
st.write("---")

# ---------------------------------------------------------------------
# 给出本页面功能的简单说明
# ---------------------------------------------------------------------
with st.expander("使用说明（点击展开）", expanded=True):
    st.markdown("""
    **本页面简介：**  
    您可以在这里生成一份“世界语文本替换用的 JSON 文件”（可能体积较大，约 50MB），  
    main.py 中会使用该 JSON 文件来执行自动替换、加注汉字或 Ruby。

    使用步骤如下：  
    1. 上传或使用默认的 CSV 文件（其中包含“世界语词根 → 中文（或汉字）”的对应关系）。  
    2. （可选）上传或使用默认的 JSON 文件（可自定义词根解析方式、特殊替换等）。  
    3. 点击按钮，即可生成“合并后的替换 JSON 文件”并下载。

    如果您需要参考格式，可在下方折叠处下载示例文件。
    """)

# ---------------------------------------------------------------------
# 展示一些可下载的示例文件（CSV/JSON/Excel）
# ---------------------------------------------------------------------
with st.expander("示例文件列表（点击下载）"):
    st.write("**示例文件：**")

    # 示例 CSV 1
    st.markdown("""
    **示例 CSV 1：世界语词根 - 中文含义对应表**  
    （如果您有自定义的 CSV，该 CSV 应有两列，第一列是世界语词根，第二列是对应的翻译/汉字/含义）
    """)
    file_path0 = './Appの运行に使用する各类文件/世界语词根-中文注释对应列表.csv'
    with open(file_path0, "rb") as file:
        btn = st.download_button(
            label="下载示例 CSV 1（词根 → 中文/汉字）",
            data=file,
            file_name="示例_世界语词根_中文对应.csv",
            mime="text/csv"
        )

    # 示例 CSV 2
    st.markdown("""
    **示例 CSV 2：世界语词根 - 汉字 对应表（Mingeo 方案）**  
    可作为参考，用 Mingeo 先生的汉字化思路。
    """)
    file_path0 = './Appの运行に使用する各类文件/Mingeo先生版 世界语词根-汉字对应列表.csv'
    with open(file_path0, "rb") as file:
        btn = st.download_button(
            label="下载示例 CSV 2（Mingeo 先生版本）",
            data=file,
            file_name="世界语词根_汉字对应_Mingeo.csv",
            mime="text/csv"
        )

    # 示例 CSV 3
    st.markdown("""
    **示例 CSV 3：世界语词根 - 汉字 对应表**  
    """)
    file_path0 = './Appの运行に使用する各类文件/世界语词根-汉字对应列表.csv'
    with open(file_path0, "rb") as file:
        btn = st.download_button(
            label="下载示例 CSV 3（词根 - 汉字）",
            data=file,
            file_name="世界语词根_汉字对应.csv",
            mime="text/csv"
        )

    # 示例 JSON 1
    st.markdown("""
    **示例 JSON 1：世界语单词词根解析的用户自定义设置**  
    例如决定某些词是否算作动词，并自动添加(as,is,os)等后缀等。  
    文件内有详细注释，请结合实际需要进行编辑。
    """)
    json_file_path = './Appの运行に使用する各类文件/世界语单词词根分解方法の使用者自定义设置.json'
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例 JSON 1（自定义词根分解）",
            data=file_json,
            file_name="示例_词根分解自定义.json",
            mime="application/json"
        )

    # 示例 JSON 2
    st.markdown("""
    **示例 JSON 2：自定义替换后文字（不太推荐）**  
    除了 CSV + 词根分解 JSON，大多数情况不需要此额外文件。  
    仅在极少数场合，用于指定某些特殊词的特殊汉字。
    """)
    json_file_path2 = './Appの运行に使用する各类文件/替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json'
    with open(json_file_path2, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例 JSON 2（自定义替换后文字）",
            data=file_json,
            file_name="示例_自定义替换后文字.json",
            mime="application/json"
        )

    # 示例 Excel
    st.markdown("""
    **示例 Excel：世界语词根 - 日语 词义+掌握等级  
    （仅作参考，帮助您确定常用/非常用词根，非必需文件）**
    """)
    with open('./Appの运行に使用する各类文件/エスペラント語根-日本語訳ルビ対応リスト(習得レベル付き).xlsx', "rb") as file:
        st.download_button(
            label="下载示例 Excel（带日语词义、掌握等级）",
            data=file,
            file_name="示例_世界语词根_日语等级.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.write("---")

# ---------------------------------------------------------------------
# 提供一个下拉菜单，让用户选择输出格式（例如 HTML+Ruby 等）
# （与 main.py 中的 format_type 对应）
# ---------------------------------------------------------------------
# 供用户选择的输出格式（原先是韩语/日语等），改用中文标签
options = {
    'HTML形式＿调整Ruby文字大小': 'HTML格式_Ruby文字_大小调整',
    'HTML形式＿调整Ruby文字大小（含汉字替换）': 'HTML格式_Ruby文字_大小调整_汉字替换',
    'HTML形式（不带汉字替换）': 'HTML格式',
    'HTML形式（带汉字替换）': 'HTML格式_汉字替换',
    '括号形式（不带汉字替换）': '括弧(号)格式',
    '括号形式（带汉字替换）': '括弧(号)格式_汉字替换',
    '仅保留替换后文字列（简单替换）': '替换后文字列のみ(仅)保留(简单替换)'
}
display_options = list(options.keys())
selected_display = st.selectbox('请选择输出格式：', display_options)
format_type = options[selected_display]

# 做一个小测试：展示几段文本的转换效果
main_text_list = ['Esperant','lingv', 'pac', 'amik', 'ec']
ruby_content_list = ['世界语', '语言', '和平', '友', '性质']
formatted_text = ''
for i, item in enumerate(main_text_list):
    formatted_text += output_format(item, ruby_content_list[i], format_type, char_widths_dict)

st.write("---")

# 以 HTML + Ruby 的方式显示示例
st.markdown("**格式化示例文本：**")
components.html(apply_ruby_html_header_and_footer(formatted_text, format_type), height=40, scrolling=False)
st.write("---")

# ---------------------------------------------------------------------
# 第 1 步：选择 CSV 文件（上传 或 使用默认）
# ---------------------------------------------------------------------
st.header("第一步：准备 CSV 文件")
st.markdown("""
此 CSV 文件包含“世界语词根 - 翻译（汉字/中文）”信息。  
请在下方选择使用默认示例文件，或上传自己的 CSV 文件。
""")

csv_choice = st.radio("CSV 文件来源：", ("上传 CSV", "使用默认 CSV"))
csv_path_default = "./Appの运行に使用する各类文件/世界语词根-中文注释对应列表.csv"

CSV_data_imported = None

if csv_choice == "上传 CSV":
    st.write("请上传任意 CSV 文件（UTF-8 编码），包含两列：[词根, 翻译]")
    uploaded_file = st.file_uploader("请选择 CSV 文件", type=['csv'])
    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode("utf-8")
        # 将内部所有世界语字母转换成带抑扬符（ĉ, ĝ 等）
        converted_text = convert_to_circumflex(file_contents)
        csv_buffer = StringIO(converted_text)
        CSV_data_imported = pd.read_csv(csv_buffer, encoding="utf-8", usecols=[0, 1])
        st.success("CSV 文件已上传并读取。")
    else:
        st.warning("尚未上传任何 CSV 文件。")
        st.stop()

elif csv_choice == "使用默认 CSV":
    try:
        with open(csv_path_default, 'r', encoding="utf-8") as file:
            text = file.read()
        converted_text = convert_to_circumflex(text)
        csv_buffer = StringIO(converted_text)
        CSV_data_imported = pd.read_csv(csv_buffer, encoding="utf-8", usecols=[0, 1])
        st.info("已使用默认 CSV 文件。")
    except FileNotFoundError:
        st.error("找不到默认 CSV 文件，无法继续。")
        st.stop()

st.write("CSV 文件加载完成。继续下一步。")
st.write("---")

# ---------------------------------------------------------------------
# 第二步：准备 JSON 文件（包括词根分解规则、替换后文字等）
# ---------------------------------------------------------------------
st.header("第二步：准备词根分解法/自定义替换 JSON 文件")
st.markdown("""
如果您有自定义的“词根解析/拆分”或“特殊替换后文字”，  
可在这里上传 JSON 文件，也可使用示例 JSON 文件。
""")

# 1) 词根分解法 JSON
json_choice = st.radio("1) 词根分解法 JSON 文件：", ("上传 JSON", "使用默认 JSON"))
json_path_default = "./Appの运行に使用する各类文件/世界语单词词根分解方法の使用者自定义设置.json"
custom_stemming_setting_list = None

if json_choice == "上传 JSON":
    uploaded_json = st.file_uploader("请上传词根分解自定义 JSON：", type=['json'])
    if uploaded_json is not None:
        custom_stemming_setting_list = json.load(uploaded_json)
        st.success("词根分解 JSON 文件已上传。")
    else:
        st.warning("尚未上传此 JSON 文件。")
        st.stop()
elif json_choice == "使用默认 JSON":
    try:
        with open(json_path_default, "r", encoding="utf-8") as g:
            custom_stemming_setting_list = json.load(g)
        st.info("已使用默认 JSON（词根分解）。")
    except FileNotFoundError:
        st.error("未找到默认词根分解 JSON 文件。")
        st.stop()

# 2) 自定义替换后文字 JSON
json_choice2 = st.radio("2) 替换后文字自定义 JSON 文件：", ("上传 JSON", "使用默认 JSON"))
json_path_default2 = "./Appの运行に使用する各类文件/替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
user_replacement_item_setting_list = None

if json_choice2 == "上传 JSON":
    uploaded_json = st.file_uploader("请上传替换后文字自定义 JSON：", type=['json'])
    if uploaded_json is not None:
        user_replacement_item_setting_list = json.load(uploaded_json)
        st.success("自定义替换后文字 JSON 文件已上传。")
    else:
        st.warning("尚未上传此 JSON 文件。")
        st.stop()
elif json_choice2 == "使用默认 JSON":
    try:
        with open(json_path_default2, "r", encoding="utf-8") as g:
            user_replacement_item_setting_list = json.load(g)
        st.info("已使用默认 JSON（替换后文字）。")
    except FileNotFoundError:
        st.error("找不到默认的“替换后文字” JSON 文件。")
        st.stop()

st.write("---")

# ---------------------------------------------------------------------
# 第三步：可选的高级设置：并行处理
# ---------------------------------------------------------------------
st.header("第三步：并行处理（高级设置）")
with st.expander("点击展开并行处理设置"):
    st.write("""
    若要生成大规模替换 JSON，处理速度可能较慢。  
    这里可以勾选“使用并行处理”，并设置要启动的 CPU 进程数（2~6）。
    """)
    use_parallel = st.checkbox("使用并行处理", value=False)
    num_processes = st.number_input("并行进程数量", min_value=2, max_value=6, value=5, step=1)

st.write("### 最后，生成替换用 JSON 文件")

# ---------------------------------------------------------------------
# 在页面上放置一个按钮，点击后开始构建替换用 JSON
# ---------------------------------------------------------------------
if st.button("生成并下载替换用 JSON 文件"):
    with st.spinner("正在生成替换用 JSON 文件，请稍候……"):
        # -------------------------------------------------------------
        # 1) 读取“大规模世界语词典/列表” (E_stem_with_Part_Of_Speech_list)
        #    内含约数万条世界语单词(含词性信息)
        # -------------------------------------------------------------
        with open("./Appの运行に使用する各类文件/PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json", "r", encoding="utf-8") as g:
            E_stem_with_Part_Of_Speech_list = json.load(g)

        # 先读取“世界语全部词根(约11137个)”到一个临时字典
        temporary_replacements_dict = {}
        with open("./Appの运行に使用する各类文件/世界语全部词根_约11137个_202501.txt", 'r', encoding='utf-8') as file:
            E_roots = file.readlines()
            for E_root in E_roots:
                E_root = E_root.strip()
                if not E_root.isdigit(): 
                    # 临时记录：[替换后文字, 替换优先级]
                    # 先全部设成 E_root 本身，优先级设为 len(E_root)
                    temporary_replacements_dict[E_root] = [E_root, len(E_root)]

        # -------------------------------------------------------------
        # 2) 用 CSV 文件中的词根->(汉字/翻译) 覆盖这个临时字典
        # -------------------------------------------------------------
        for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
            if pd.notna(E_root) and pd.notna(hanzi_or_meaning) \
               and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
                temporary_replacements_dict[E_root] = [
                    output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict),
                    len(E_root)
                ]

        # -------------------------------------------------------------
        # 3) 把临时字典转为列表，并根据优先级(字符串长度)从大到小排序
        # -------------------------------------------------------------
        temporary_replacements_list_1 = []
        for old, new in temporary_replacements_dict.items():
            temporary_replacements_list_1.append((old, new[0], new[1]))
        temporary_replacements_list_2 = sorted(temporary_replacements_list_1, key=lambda x: x[2], reverse=True)

        # -------------------------------------------------------------
        # 4) 用 placeholder(占位符) 来构建 “(old->placeholder->new)” 的安全替换列表
        # -------------------------------------------------------------
        temporary_replacements_list_final = []
        for kk in range(len(temporary_replacements_list_2)):
            temporary_replacements_list_final.append([
                temporary_replacements_list_2[kk][0],
                temporary_replacements_list_2[kk][1],
                imported_placeholders_for_global_replacement[kk]
            ])

        # -------------------------------------------------------------
        # 5) 对 E_stem_with_Part_Of_Speech_list 执行批量替换（可并行）
        # -------------------------------------------------------------
        if use_parallel:
            pre_replacements_dict_1 = parallel_build_pre_replacements_dict(
                E_stem_with_Part_Of_Speech_list,
                temporary_replacements_list_final,
                num_processes
            )
        else:
            # 如果用户不使用并行，则手动循环，顺便显示进度
            progress_bar = st.progress(0)
            progress_text = st.empty()

            total_items = len(E_stem_with_Part_Of_Speech_list)
            pre_replacements_dict_1 = {}

            for i, j in enumerate(E_stem_with_Part_Of_Speech_list):
                if len(j) == 2:
                    if len(j[0]) >= 2:
                        if j[0] in pre_replacements_dict_1:
                            if j[1] not in pre_replacements_dict_1[j[0]][1]:
                                pre_replacements_dict_1[j[0]] = [
                                    pre_replacements_dict_1[j[0]][0],
                                    pre_replacements_dict_1[j[0]][1] + ',' + j[1]
                                ]
                        else:
                            pre_replacements_dict_1[j[0]] = [
                                safe_replace(j[0], temporary_replacements_list_final),
                                j[1]
                            ]

                if i % 1000 == 0:
                    current_count = i + 1
                    progress_value = int(current_count / total_items * 100)
                    progress_bar.progress(progress_value)
                    progress_text.write(f"处理进度：{current_count}/{total_items} ...")

            progress_bar.progress(100)
            progress_text.write("批量处理已完成 (100%)，可能还有少量收尾操作……")

        # 例如可在这里 pop 掉某些键
        keys_to_remove = ['domen', 'teren','posten']
        for key in keys_to_remove:
            pre_replacements_dict_1.pop(key, None)

        # -------------------------------------------------------------
        # 6) 将 pre_replacements_dict_1 进一步做各种优先级、后缀添加等处理：
        #    生成 “replacements_final_list” 的最终形态
        # -------------------------------------------------------------
        pre_replacements_dict_2 = {}
        for i,j in pre_replacements_dict_1.items():
            if i==j[0]:
                pre_replacements_dict_2[i.replace('/', '')] = [
                    j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),
                    j[1],
                    len(i.replace('/', ''))*10000 - 3000
                ]
            else:
                pre_replacements_dict_2[i.replace('/', '')] = [
                    j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),
                    j[1],
                    len(i.replace('/', ''))*10000
                ]

        #-------------------------------------------------------------
        # (8) ここから先は、AN, ON, 動詞語尾などの接頭辞/接尾辞を用いた
        #     優先順位調整を大量に行う。
        #
        #     具体的には、辞書 pre_replacements_dict_2 をさらに書き換えたり、
        #     新しいキー(=語尾を付けた形など)を追加して、より精度の高い置換を行えるようにしている。
        #
        #     コード量は多いですが、やっていることは
        #       「(語根 + an)を名詞/形容詞とみなすか、それとも接尾辞an(員)とみなすか」
        #       「(語根 + as)で動詞現在形にする場合の優先順位をどうするか」
        #     などの細かいルール付けです。
        #-------------------------------------------------------------

        #------------------------------------------
        # verb_suffix_2l_2 という辞書を作る:
        #   verb_suffix_2l の各キー(例:'as')とその置換結果をsafe_replace()で更新
        #   こうすることで "(語根)+(動詞接尾辞)" に対してルビなどを入れ込めるようにします。
        #------------------------------------------
        verb_suffix_2l_2={}
        for original_verb_suffix,replaced_verb_suffix in verb_suffix_2l.items():
            # 例: 'as'→'as' のままのことが多いが、safe_replaceで更に別ルビを当てはめる可能性あり
            verb_suffix_2l_2[original_verb_suffix] = safe_replace(replaced_verb_suffix, temporary_replacements_list_final)

        # 一番の工夫ポイント(以下、コメントはコード内にある通り):
        #  置換の優先順位をどう定めるかで、置換の精度が大きく変わる。
        #  文字数の多い単語を先に置換する、動詞の場合は活用語尾を付けた形を優先度高くするetc.
        #
        # pre_replacements_dict_1→pre_replacements_dict_2→pre_replacements_dict_3
        # という流れで段階的に書き換え、最終的に "replacements_final_list" へまとめる方針。

        unchangeable_after_creation_list=[]
        AN_replacement = safe_replace('an', temporary_replacements_list_final)
        AN_treatment=[]

        pre_replacements_dict_3={}
        pre_replacements_dict_2_copy = pre_replacements_dict_2.copy()
        
        # (8-1) 例えば "xxxan" という語があり、それが名詞品詞("名词")なのに
        #        中で "an"がルビとして置換されている...等、誤置換を防ぐための調整。
        for i,j in pre_replacements_dict_2_copy.items(): # j[0]:置換後文字列, j[1]:品詞, j[2]:優先順位
            if i.endswith('an') and (AN_replacement in j[0]) and ("名词" in j[1]) and (i[:-2] in pre_replacements_dict_2_copy):
                # 形容詞語尾anと接尾辞anが衝突する場合などに対応
                AN_treatment.append([i,j[0]])
                pre_replacements_dict_2.pop(i, None)
                # そこへさらに "i+"o,"i+"a,"i+"e などの派生形を追加する処理
                for k in ["o","a","e"]:
                    if not i+k in pre_replacements_dict_2_copy:
                        pre_replacements_dict_3[i+k]=[j[0]+k, j[2]+len(k)*10000-2000]
            elif (j[1] == "名词") and (len(i)<=6) and not(j[2] in [60000,50000,40000,30000,20000]):
                # 名詞で6文字以下、かつ特定優先順位でないものを調整
                for k in ["o"]:
                    if not i+k in pre_replacements_dict_2_copy:
                        pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-2000]
                pre_replacements_dict_2.pop(i, None)

        # (8-2) 2文字語根の特別処理(例えば "am" "ar" など)
        #       動詞の接尾辞(ag, ig等)を足した形の置換を優先させたいが、名詞や形容詞の場合はどうするか等
        for i,j in pre_replacements_dict_2.items():
            # j[2]が20000の場合は2文字語根の優先度っぽい
            if j[2]==20000:
                # 名詞の場合
                if "名词" in j[1]:
                    for k in ["o","on",'oj']:
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[' '+i+k] = [' '+j[0]+k, j[2] + (len(k)+1)*10000 - 5000]
                # 形容詞の場合
                if "形容词" in j[1]:
                    for k in ["a","aj",'an']:
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[' '+i+k] = [' '+j[0]+k, j[2] + (len(k)+1)*10000 - 5000]
                        else:
                            pre_replacements_dict_3[i+k] = [j[0]+k, j[2] + len(k)*10000 - 5000]
                            unchangeable_after_creation_list.append(i+k)
                # 副詞の場合
                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[' '+i+k] = [' '+j[0]+k, j[2] + (len(k)+1)*10000 - 5000]
                        else:
                            pre_replacements_dict_3[' '+i+k] = [' '+j[0]+k, j[2] + (len(k)+1)*10000 - 5000]
                # 動詞の場合(ここが複雑; 動詞活用語尾(as,is,os,etc)と組み合わせる)
                if "动词" in j[1]:
                    for k1,k2 in verb_suffix_2l_2.items():
                        if not i+k1 in pre_replacements_dict_2:
                            pre_replacements_dict_3[i+k1] = [j[0]+k2, j[2] + len(k1)*10000 - 3000]
                        elif j[0]+k2 != pre_replacements_dict_2[i+k1][0]:
                            pre_replacements_dict_3[i+k1] = [j[0]+k2, j[2] + len(k1)*10000 - 3000]
                            unchangeable_after_creation_list.append(i+k1)
                    for k in ["u ","i ","u","i"]:
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i+k] = [j[0]+k, j[2] + len(k)*10000 - 3000]
                continue
            
            else:
                if not i in unchangeable_after_creation_list:# unchangeable_after_creation_list に含まれる場合は除外。(上記で新しく定めた語根分解が更新されてしまわないようにするため。)
                    pre_replacements_dict_3[i]=[j[0],j[2]]# 品詞情報はここで用いるためにあった。以後は不要なので省いていく。
                if j[2]==60000 or j[2]==50000 or j[2]==40000 or j[2]==30000:# 文字数が比較的少なく(<=5)、実際に置換するエスペラント語根(文字数×10000)のみを対象とする 
                    if "名词" in j[1]:# 名词については形容词、副词と違い、置換しないものにもoをつける。
                        for k in ["o","on",'oj']:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]# 既存でないものは優先順位を大きく下げる→普通の品詞接尾辞が既存でないという言い方はおかしい気がしてきた。(20240612)
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]# 新しく作った方の語根分解を優先する
                                unchangeable_after_creation_list.append(i+k)
                            # on系[['nombron', '<ruby>nombr<rt class="ruby-X_X_X">数</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>nombr<rt class="ruby-X_X_X">数</rt></ruby>on'], ['patron', '<ruby>patron<rt class="ruby-X_X_X">後援者</rt></ruby>', '<ruby>patr<rt class="ruby-X_X_X">父</rt></ruby>on'], ['karbon', '<ruby>karbon<rt class="ruby-L_L_L">[化]炭素</rt></ruby>', '<ruby>karb<rt class="ruby-X_X_X">炭</rt></ruby>on'], ['ciklon', '<ruby>ciklon<rt class="ruby-X_X_X">低気圧</rt></ruby>', '<ruby>cikl<rt class="ruby-X_X_X">周期</rt></ruby>on'], ['aldon', '<ruby>al<rt class="ruby-S_S_S">~の方へ</rt></ruby><ruby>don<rt class="ruby-M_M_M">与える</rt></ruby>', '<ruby>ald<rt class="ruby-M_M_M">アルト</rt></ruby>on'], ['balon', '<ruby>balon<rt class="ruby-X_X_X">気球</rt></ruby>', '<ruby>bal<rt class="ruby-M_M_M">舞踏会</rt></ruby>on'], ['baron', '<ruby>baron<rt class="ruby-X_X_X">男爵</rt></ruby>', '<ruby>bar<rt class="ruby-L_L_L">障害</rt></ruby>on'], ['baston', '<ruby>baston<rt class="ruby-X_X_X">棒</rt></ruby>', '<ruby>bast<rt class="ruby-M_M_M">[植]じん皮</rt></ruby>on'], ['magneton', '<ruby>magnet<rt class="ruby-L_L_L">[理]磁石</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>magnet<rt class="ruby-L_L_L">[理]磁石</rt></ruby>on'], ['beton', 'beton', '<ruby>bet<rt class="ruby-M_M_M">ビート</rt></ruby>on'], ['bombon', '<ruby>bombon<rt class="ruby-L_L_L">キャンデー</rt></ruby>', '<ruby>bomb<rt class="ruby-X_X_X">爆弾</rt></ruby>on'], ['breton', 'breton', '<ruby>bret<rt class="ruby-X_X_X">棚</rt></ruby>on'], ['burgxon', '<ruby>burgxon<rt class="ruby-X_X_X">芽</rt></ruby>', '<ruby>burgx<rt class="ruby-M_M_M">ブルジョワ</rt></ruby>on'], ['centon', '<ruby>cent<rt class="ruby-X_X_X">百</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>cent<rt class="ruby-X_X_X">百</rt></ruby>on'], ['milon', '<ruby>mil<rt class="ruby-X_X_X">千</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>mil<rt class="ruby-X_X_X">千</rt></ruby>on'], ['kanton', '<ruby>kanton<rt class="ruby-M_M_M">(フランスの)郡</rt></ruby>', '<ruby>kant<rt class="ruby-M_M_M">(を)歌う</rt></ruby>on'], ['citron', '<ruby>citron<rt class="ruby-M_M_M">[果]シトロン</rt></ruby>', '<ruby>citr<rt class="ruby-M_M_M">[楽]チター</rt></ruby>on'], ['platon', 'platon', '<ruby>plat<rt class="ruby-L_L_L">平たい</rt></ruby>on'], ['dekon', '<ruby>dek<rt class="ruby-X_X_X">十</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>dek<rt class="ruby-X_X_X">十</rt></ruby>on'], ['kvaron', '<ruby>kvar<rt class="ruby-X_X_X">四</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>kvar<rt class="ruby-X_X_X">四</rt></ruby>on'], ['kvinon', '<ruby>kvin<rt class="ruby-X_X_X">五</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>kvin<rt class="ruby-X_X_X">五</rt></ruby>on'], ['seson', '<ruby>ses<rt class="ruby-X_X_X">六</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>ses<rt class="ruby-X_X_X">六</rt></ruby>on'], ['trion', '<ruby>tri<rt class="ruby-X_X_X">三</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>tri<rt class="ruby-X_X_X">三</rt></ruby>on'], ['karton', '<ruby>karton<rt class="ruby-X_X_X">厚紙</rt></ruby>', '<ruby>kart<rt class="ruby-L_L_L">カード</rt></ruby>on'], ['foton', '<ruby>fot<rt class="ruby-S_S_S">写真を撮る</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>fot<rt class="ruby-S_S_S">写真を撮る</rt></ruby>on'], ['peron', '<ruby>peron<rt class="ruby-X_X_X">階段</rt></ruby>', '<ruby>per<rt class="ruby-M_M_M">よって</rt></ruby>on'], ['elektron', '<ruby>elektr<rt class="ruby-X_X_X">電気</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>elektr<rt class="ruby-X_X_X">電気</rt></ruby>on'], ['drakon', 'drakon', '<ruby>drak<rt class="ruby-X_X_X">竜</rt></ruby>on'], ['mondon', '<ruby>mon<rt class="ruby-L_L_L">金銭</rt></ruby><ruby>don<rt class="ruby-M_M_M">与える</rt></ruby>', '<ruby>mond<rt class="ruby-X_X_X">世界</rt></ruby>on'], ['pension', '<ruby>pension<rt class="ruby-X_X_X">下宿屋</rt></ruby>', '<ruby>pensi<rt class="ruby-X_X_X">年金</rt></ruby>on'], ['ordon', '<ruby>ordon<rt class="ruby-M_M_M">(を)命令する</rt></ruby>', '<ruby>ord<rt class="ruby-L_L_L">順序</rt></ruby>on'], ['eskadron', 'eskadron', '<ruby>eskadr<rt class="ruby-L_L_L">[軍]艦隊</rt></ruby>on'], ['senton', '<ruby>sen<rt class="ruby-S_S_S">(~)なしで</rt></ruby><ruby>ton<rt class="ruby-M_M_M">[楽]楽音</rt></ruby>', '<ruby>sent<rt class="ruby-M_M_M">(を)感じる</rt></ruby>on'], ['eston', 'eston', '<ruby>est<rt class="ruby-S_S_S">(~)である</rt></ruby>on'], ['fanfaron', '<ruby>fanfaron<rt class="ruby-L_L_L">大言壮語する</rt></ruby>', '<ruby>fanfar<rt class="ruby-S_S_S">[楽]ファンファーレ</rt></ruby>on'], ['fero', 'fero', '<ruby>fer<rt class="ruby-X_X_X">鉄</rt></ruby>o'], ['feston', '<ruby>feston<rt class="ruby-X_X_X">花綱</rt></ruby>', '<ruby>fest<rt class="ruby-M_M_M">(を)祝う</rt></ruby>on'], ['flegmon', 'flegmon', '<ruby>flegm<rt class="ruby-X_X_X">冷静</rt></ruby>on'], ['fronton', '<ruby>fronton<rt class="ruby-M_M_M">[建]ペディメント</rt></ruby>', '<ruby>front<rt class="ruby-X_X_X">正面</rt></ruby>on'], ['galon', '<ruby>galon<rt class="ruby-M_M_M">[服]モール</rt></ruby>', '<ruby>gal<rt class="ruby-M_M_M">[生]胆汁</rt></ruby>on'], ['mason', '<ruby>mason<rt class="ruby-X_X_X">築く</rt></ruby>', '<ruby>mas<rt class="ruby-M_M_M">かたまり</rt></ruby>on'], ['helikon', 'helikon', '<ruby>helik<rt class="ruby-S_S_S">[動]カタツムリ</rt></ruby>on'], ['kanon', '<ruby>kanon<rt class="ruby-L_L_L">[軍]大砲</rt></ruby>', '<ruby>kan<rt class="ruby-M_M_M">[植]アシ</rt></ruby>on'], ['kapon', '<ruby>kapon<rt class="ruby-M_M_M">去勢オンドリ</rt></ruby>', '<ruby>kap<rt class="ruby-X_X_X">頭</rt></ruby>on'], ['kokon', '<ruby>kokon<rt class="ruby-M_M_M">[虫]繭(まゆ)</rt></ruby>', '<ruby>kok<rt class="ruby-M_M_M">ニワトリ</rt></ruby>on'], ['kolon', '<ruby>kolon<rt class="ruby-L_L_L">[建]円柱</rt></ruby>', '<ruby>kol<rt class="ruby-M_M_M">[解]首</rt></ruby>on'], ['komision', '<ruby>komision<rt class="ruby-L_L_L">(調査)委員会</rt></ruby>', '<ruby>komisi<rt class="ruby-M_M_M">(を)委託する</rt></ruby>on'], ['salon', '<ruby>salon<rt class="ruby-L_L_L">サロン</rt></ruby>', '<ruby>sal<rt class="ruby-X_X_X">塩</rt></ruby>on'], ['ponton', '<ruby>ponton<rt class="ruby-L_L_L">[軍]平底舟</rt></ruby>', '<ruby>pont<rt class="ruby-X_X_X">橋</rt></ruby>on'], ['koton', '<ruby>koton<rt class="ruby-X_X_X">綿</rt></ruby>', '<ruby>kot<rt class="ruby-X_X_X">泥</rt></ruby>on'], ['kripton', 'kripton', '<ruby>kript<rt class="ruby-M_M_M">[宗]地下聖堂</rt></ruby>on'], ['kupon', '<ruby>kupon<rt class="ruby-M_M_M">クーポン券</rt></ruby>', '<ruby>kup<rt class="ruby-M_M_M">吸い玉</rt></ruby>on'], ['lakon', 'lakon', '<ruby>lak<rt class="ruby-M_M_M">ラッカー</rt></ruby>on'], ['ludon', '<ruby>lu<rt class="ruby-S_S_S">賃借する</rt></ruby><ruby>don<rt class="ruby-M_M_M">与える</rt></ruby>', '<ruby>lud<rt class="ruby-M_M_M">(を)遊ぶ</rt></ruby>on'], ['melon', '<ruby>melon<rt class="ruby-M_M_M">[果]メロン</rt></ruby>', '<ruby>mel<rt class="ruby-M_M_M">アナグマ</rt></ruby>on'], ['menton', '<ruby>menton<rt class="ruby-L_L_L">[解]下あご</rt></ruby>', '<ruby>ment<rt class="ruby-M_M_M">[植]ハッカ</rt></ruby>on'], ['milion', '<ruby>milion<rt class="ruby-X_X_X">百万</rt></ruby>', '<ruby>mili<rt class="ruby-M_M_M">[植]キビ</rt></ruby>on'], ['milionon', '<ruby>milion<rt class="ruby-X_X_X">百万</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>milion<rt class="ruby-X_X_X">百万</rt></ruby>on'], ['nauxon', '<ruby>naux<rt class="ruby-X_X_X">九</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>naux<rt class="ruby-X_X_X">九</rt></ruby>on'], ['violon', '<ruby>violon<rt class="ruby-M_M_M">[楽]バイオリン</rt></ruby>', '<ruby>viol<rt class="ruby-M_M_M">[植]スミレ</rt></ruby>on'], ['refoj', '<ruby>re<rt class="ruby-M_M_M">再び</rt></ruby><ruby>foj<rt class="ruby-X_X_X">回</rt></ruby>', '<ruby>ref<rt class="ruby-M_M_M">リーフ</rt></ruby>oj'], ['trombon', '<ruby>trombon<rt class="ruby-M_M_M">[楽]トロンボーン</rt></ruby>', '<ruby>tromb<rt class="ruby-M_M_M">[気]たつまき</rt></ruby>on'], ['samo', 'samo', '<ruby>sam<rt class="ruby-M_M_M">同一の</rt></ruby>o'], ['savoj', 'savoj', '<ruby>sav<rt class="ruby-M_M_M">救助する</rt></ruby>oj'], ['senson', '<ruby>sen<rt class="ruby-S_S_S">(~)なしで</rt></ruby><ruby>son<rt class="ruby-M_M_M">音がする</rt></ruby>', '<ruby>sens<rt class="ruby-M_M_M">[生]感覚</rt></ruby>on'], ['sepon', '<ruby>sep<rt class="ruby-X_X_X">七</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>sep<rt class="ruby-X_X_X">七</rt></ruby>on'], ['skadron', 'skadron', '<ruby>skadr<rt class="ruby-M_M_M">[軍]騎兵中隊</rt></ruby>on'], ['stadion', '<ruby>stadion<rt class="ruby-L_L_L">スタジアム</rt></ruby>', '<ruby>stadi<rt class="ruby-X_X_X">段階</rt></ruby>on'], ['tetraon', 'tetraon', '<ruby>tetra<rt class="ruby-S_S_S">エゾライチョウ</rt></ruby>on'], ['timon', '<ruby>timon<rt class="ruby-L_L_L">かじ棒</rt></ruby>', '<ruby>tim<rt class="ruby-M_M_M">恐れる</rt></ruby>on'], ['valon', 'valon', '<ruby>val<rt class="ruby-M_M_M">[地]谷</rt></ruby>on'], ['veto', 'veto', '<ruby>vet<rt class="ruby-M_M_M">賭ける</rt></ruby>o']]
                            # on系以外は、'fero','refoj','samo','savoj','veto'
                    if "形容词" in j[1]:
                        for k in ["a","aj",'an']:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]# 新しく作った方の語根分解を優先する つまり、"an"は形容詞語尾として語根分解する。
                                unchangeable_after_creation_list.append(i+k)
                            # an系 [['dietan', '<ruby>diet<rt class="ruby-M_M_M">[医]規定食</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>diet<rt class="ruby-M_M_M">[医]規定食</rt></ruby>an'], ['afrikan', '<ruby>afrik<rt class="ruby-S_S_S">[地名]アフリカ</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>afrik<rt class="ruby-S_S_S">[地名]アフリカ</rt></ruby>an'], ['movadan', '<ruby>mov<rt class="ruby-M_M_M">動かす</rt></ruby><ruby>ad<rt class="ruby-S_S_S">継続行為</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>mov<rt class="ruby-M_M_M">動かす</rt></ruby><ruby>ad<rt class="ruby-S_S_S">継続行為</rt></ruby>an'], ['akcian', '<ruby>akci<rt class="ruby-M_M_M">[商]株式</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>akci<rt class="ruby-M_M_M">[商]株式</rt></ruby>an'], ['montaran', '<ruby>mont<rt class="ruby-X_X_X">山</rt></ruby><ruby>ar<rt class="ruby-M_M_M">集団</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>mont<rt class="ruby-X_X_X">山</rt></ruby><ruby>ar<rt class="ruby-M_M_M">集団</rt></ruby>an'], ['amerikan', '<ruby>amerik<rt class="ruby-M_M_M">[地名]アメリカ</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>amerik<rt class="ruby-M_M_M">[地名]アメリカ</rt></ruby>an'], ['regnan', '<ruby>regn<rt class="ruby-M_M_M">[法]国家</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>regn<rt class="ruby-M_M_M">[法]国家</rt></ruby>an'], ['dezertan', '<ruby>dezert<rt class="ruby-X_X_X">砂漠</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>dezert<rt class="ruby-X_X_X">砂漠</rt></ruby>an'], ['asocian', '<ruby>asoci<rt class="ruby-X_X_X">協会</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>asoci<rt class="ruby-X_X_X">協会</rt></ruby>an'], ['insulan', '<ruby>insul<rt class="ruby-X_X_X">島</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>insul<rt class="ruby-X_X_X">島</rt></ruby>an'], ['azian', '<ruby>azi<rt class="ruby-M_M_M">アジア</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>azi<rt class="ruby-M_M_M">アジア</rt></ruby>an'], ['sxtatan', '<ruby>sxtat<rt class="ruby-X_X_X">国家</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>sxtat<rt class="ruby-X_X_X">国家</rt></ruby>an'], ['doman', '<ruby>dom<rt class="ruby-X_X_X">家</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>dom<rt class="ruby-X_X_X">家</rt></ruby>an'], ['montan', '<ruby>mont<rt class="ruby-X_X_X">山</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>mont<rt class="ruby-X_X_X">山</rt></ruby>an'], ['familian', '<ruby>famili<rt class="ruby-X_X_X">家族</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>famili<rt class="ruby-X_X_X">家族</rt></ruby>an'], ['urban', '<ruby>urb<rt class="ruby-X_X_X">市</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>urb<rt class="ruby-X_X_X">市</rt></ruby>an'], ['inka', 'inka', '<ruby>ink<rt class="ruby-M_M_M">インク</rt></ruby>a'], ['popolan', '<ruby>popol<rt class="ruby-X_X_X">人民</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>popol<rt class="ruby-X_X_X">人民</rt></ruby>an'], ['dekan', '<ruby>dekan<rt class="ruby-L_L_L">学部長</rt></ruby>', '<ruby>dek<rt class="ruby-X_X_X">十</rt></ruby>an'], ['partian', '<ruby>parti<rt class="ruby-L_L_L">[政]党派</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>parti<rt class="ruby-L_L_L">[政]党派</rt></ruby>an'], ['lokan', '<ruby>lok<rt class="ruby-L_L_L">場所</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>lok<rt class="ruby-L_L_L">場所</rt></ruby>an'], ['sxipan', '<ruby>sxip<rt class="ruby-X_X_X">船</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>sxip<rt class="ruby-X_X_X">船</rt></ruby>an'], ['eklezian', '<ruby>eklezi<rt class="ruby-L_L_L">[宗]教会</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>eklezi<rt class="ruby-L_L_L">[宗]教会</rt></ruby>an'], ['landan', '<ruby>land<rt class="ruby-X_X_X">国</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>land<rt class="ruby-X_X_X">国</rt></ruby>an'], ['orientan', '<ruby>orient<rt class="ruby-M_M_M">方位定める;東</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>orient<rt class="ruby-M_M_M">方位定める;東</rt></ruby>an'], ['lernejan', '<ruby>lern<rt class="ruby-S_S_S">(を)学習する</rt></ruby><ruby>ej<rt class="ruby-M_M_M">場所</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>lern<rt class="ruby-S_S_S">(を)学習する</rt></ruby><ruby>ej<rt class="ruby-M_M_M">場所</rt></ruby>an'], ['enlandan', '<ruby>en<rt class="ruby-M_M_M">中で</rt></ruby><ruby>land<rt class="ruby-X_X_X">国</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>en<rt class="ruby-M_M_M">中で</rt></ruby><ruby>land<rt class="ruby-X_X_X">国</rt></ruby>an'], ['kalkan', '<ruby>kalkan<rt class="ruby-X_X_X">[解]踵</rt></ruby>', '<ruby>kalk<rt class="ruby-M_M_M">[化]石灰</rt></ruby>an'], ['estraran', '<ruby>estr<rt class="ruby-M_M_M">[接尾辞]長</rt></ruby><ruby>ar<rt class="ruby-M_M_M">集団</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>estr<rt class="ruby-M_M_M">[接尾辞]長</rt></ruby><ruby>ar<rt class="ruby-M_M_M">集団</rt></ruby>an'], ['etnan', '<ruby>etn<rt class="ruby-L_L_L">民族</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>etn<rt class="ruby-L_L_L">民族</rt></ruby>an'], ['euxropan', '<ruby>euxrop<rt class="ruby-L_L_L">ヨーロッパ</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>euxrop<rt class="ruby-L_L_L">ヨーロッパ</rt></ruby>an'], ['fazan', '<ruby>fazan<rt class="ruby-L_L_L">[鳥]キジ</rt></ruby>', '<ruby>faz<rt class="ruby-M_M_M">[理]位相</rt></ruby>an'], ['polican', '<ruby>polic<rt class="ruby-X_X_X">警察</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>polic<rt class="ruby-X_X_X">警察</rt></ruby>an'], ['socian', '<ruby>soci<rt class="ruby-X_X_X">社会</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>soci<rt class="ruby-X_X_X">社会</rt></ruby>an'], ['societan', '<ruby>societ<rt class="ruby-X_X_X">会</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>societ<rt class="ruby-X_X_X">会</rt></ruby>an'], ['grupan', '<ruby>grup<rt class="ruby-M_M_M">グループ</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>grup<rt class="ruby-M_M_M">グループ</rt></ruby>an'], ['havaj', 'havaj', '<ruby>hav<rt class="ruby-S_S_S">持っている</rt></ruby>aj'], ['ligan', '<ruby>lig<rt class="ruby-S_S_S">結ぶ;連盟</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>lig<rt class="ruby-S_S_S">結ぶ;連盟</rt></ruby>an'], ['nacian', '<ruby>naci<rt class="ruby-X_X_X">国民</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>naci<rt class="ruby-X_X_X">国民</rt></ruby>an'], ['koran', '<ruby>koran<rt class="ruby-M_M_M">[宗]コーラン</rt></ruby>', '<ruby>kor<rt class="ruby-X_X_X">心</rt></ruby>an'], ['religian', '<ruby>religi<rt class="ruby-X_X_X">宗教</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>religi<rt class="ruby-X_X_X">宗教</rt></ruby>an'], ['kuban', '<ruby>kub<rt class="ruby-M_M_M">立方体</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>kub<rt class="ruby-M_M_M">立方体</rt></ruby>an'], ['lama', '<ruby>lama<rt class="ruby-M_M_M">[宗]ラマ僧</rt></ruby>', '<ruby>lam<rt class="ruby-M_M_M">びっこの</rt></ruby>a'], ['majoran', '<ruby>major<rt class="ruby-M_M_M">[軍]陸軍少佐</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>major<rt class="ruby-M_M_M">[軍]陸軍少佐</rt></ruby>an'], ['malaj', 'malaj', '<ruby>mal<rt class="ruby-M_M_M">正反対</rt></ruby>aj'], ['marian', 'marian', '<ruby>mari<rt class="ruby-L_L_L">マリア</rt></ruby>an'], ['nordan', '<ruby>nord<rt class="ruby-X_X_X">北</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>nord<rt class="ruby-X_X_X">北</rt></ruby>an'], ['paran', 'paran', '<ruby>par<rt class="ruby-L_L_L">一対</rt></ruby>an'], ['parizan', '<ruby>pariz<rt class="ruby-M_M_M">[地名]パリ</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>pariz<rt class="ruby-M_M_M">[地名]パリ</rt></ruby>an'], ['parokan', '<ruby>parok<rt class="ruby-L_L_L">[宗]教区</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>parok<rt class="ruby-L_L_L">[宗]教区</rt></ruby>an'], ['podian', '<ruby>podi<rt class="ruby-L_L_L">ひな壇</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>podi<rt class="ruby-L_L_L">ひな壇</rt></ruby>an'], ['rusian', '<ruby>rus<rt class="ruby-M_M_M">ロシア人</rt></ruby>i<ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>rus<rt class="ruby-M_M_M">ロシア人</rt></ruby>ian'], ['satan', '<ruby>satan<rt class="ruby-M_M_M">[宗]サタン</rt></ruby>', '<ruby>sat<rt class="ruby-M_M_M">満腹した</rt></ruby>an'], ['sektan', '<ruby>sekt<rt class="ruby-M_M_M">[宗]宗派</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>sekt<rt class="ruby-M_M_M">[宗]宗派</rt></ruby>an'], ['senatan', '<ruby>senat<rt class="ruby-M_M_M">[政]参議院</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>senat<rt class="ruby-M_M_M">[政]参議院</rt></ruby>an'], ['skisman', '<ruby>skism<rt class="ruby-M_M_M">(団体の)分裂</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>skism<rt class="ruby-M_M_M">(団体の)分裂</rt></ruby>an'], ['sudan', 'sudan', '<ruby>sud<rt class="ruby-X_X_X">南</rt></ruby>an'], ['utopian', '<ruby>utopi<rt class="ruby-M_M_M">ユートピア</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>utopi<rt class="ruby-M_M_M">ユートピア</rt></ruby>an'], ['vilagxan', '<ruby>vilagx<rt class="ruby-X_X_X">村</rt></ruby><ruby>an<rt class="ruby-M_M_M">会員</rt></ruby>', '<ruby>vilagx<rt class="ruby-X_X_X">村</rt></ruby>an']]
                            # an系以外は'inka','malaj','havaj','lama'　　'marian'については、'マリアan'で行く。
                    if "副词" in j[1]:
                        for k in ["e"]:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]# 新しく作った方の語根分解を優先する
                                unchangeable_after_creation_list.append(i+k)
                            # [['alte', '<ruby>alte<rt class="ruby-M_M_M">タチアオイ</rt></ruby>', '<ruby>alt<rt class="ruby-L_L_L">高い</rt></ruby>e'], ['apoge', '<ruby>apoge<rt class="ruby-M_M_M">[天]遠地点</rt></ruby>', '<ruby>apog<rt class="ruby-M_M_M">(を)支える</rt></ruby>e'], ['kaze', '<ruby>kaze<rt class="ruby-M_M_M">[化]凝乳</rt></ruby>', '<ruby>kaz<rt class="ruby-M_M_M">[文]格</rt></ruby>e'], ['pere', '<ruby>pere<rt class="ruby-M_M_M">破滅する</rt></ruby>', '<ruby>per<rt class="ruby-M_M_M">よって</rt></ruby>e'], ['kore', 'kore', '<ruby>kor<rt class="ruby-X_X_X">心</rt></ruby>e'], ['male', 'male', '<ruby>mal<rt class="ruby-M_M_M">正反対</rt></ruby>e'], ['sole', '<ruby>sole<rt class="ruby-M_M_M">シタビラメ</rt></ruby>', '<ruby>sol<rt class="ruby-M_M_M">唯一の</rt></ruby>e']]
                    if "动词" in j[1]:
                        for k1,k2 in verb_suffix_2l_2.items():
                            if not i+k1 in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]
                            elif j[0]+k2 != pre_replacements_dict_2[i+k1][0]:
                                pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]# 新しく作った方の語根分解を優先する
                                unchangeable_after_creation_list.append(i+k1)
                            # [['regulus', 'regulus', '<ruby>regul<rt class="ruby-X_X_X">規則</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['akirant', 'akirant', '<ruby>akir<rt class="ruby-S_S_S">(を)獲得する</rt></ruby><ruby>ant<rt class="ruby-S_S_S">能動;継続</rt></ruby>'], ['radius', 'radius', '<ruby>radi<rt class="ruby-L_L_L">[理]線</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['premis', '<ruby>premis<rt class="ruby-X_X_X">前提</rt></ruby>', '<ruby>prem<rt class="ruby-M_M_M">(を)押える</rt></ruby><ruby>is<rt class="ruby-S_S_S">過去形</rt></ruby>'], ['sonat', '<ruby>sonat<rt class="ruby-M_M_M">[楽]ソナタ</rt></ruby>', '<ruby>son<rt class="ruby-M_M_M">音がする</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['format', '<ruby>format<rt class="ruby-X_X_X">[印]判</rt></ruby>', '<ruby>form<rt class="ruby-X_X_X">形</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['markot', '<ruby>markot<rt class="ruby-L_L_L">[園]取木</rt></ruby>', '<ruby>mark<rt class="ruby-L_L_L">しるし</rt></ruby><ruby>ot<rt class="ruby-S_S_S">受動将然</rt></ruby>'], ['nomad', '<ruby>nomad<rt class="ruby-L_L_L">遊牧民</rt></ruby>', '<ruby>nom<rt class="ruby-L_L_L">名前</rt></ruby><ruby>ad<rt class="ruby-S_S_S">継続行為</rt></ruby>'], ['kantat', '<ruby>kantat<rt class="ruby-M_M_M">[楽]カンタータ</rt></ruby>', '<ruby>kant<rt class="ruby-M_M_M">(を)歌う</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['kolorad', 'kolorad', '<ruby>kolor<rt class="ruby-X_X_X">色</rt></ruby><ruby>ad<rt class="ruby-S_S_S">継続行為</rt></ruby>'], ['diplomat', '<ruby>diplomat<rt class="ruby-X_X_X">外交官</rt></ruby>', '<ruby>diplom<rt class="ruby-X_X_X">免状</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['diskont', '<ruby>diskont<rt class="ruby-M_M_M">[商]手形割引する</rt></ruby>', '<ruby>disk<rt class="ruby-X_X_X">円盤</rt></ruby><ruby>ont<rt class="ruby-S_S_S">能動;将然</rt></ruby>'], ['endos', 'endos', '<ruby>end<rt class="ruby-L_L_L">必要</rt></ruby><ruby>os<rt class="ruby-S_S_S">未来形</rt></ruby>'], ['esperant', '<ruby>esperant<rt class="ruby-L_L_L">エスペラント</rt></ruby>', '<ruby>esper<rt class="ruby-M_M_M">(を)希望する</rt></ruby><ruby>ant<rt class="ruby-S_S_S">能動;継続</rt></ruby>'], ['forkant', '<ruby>for<rt class="ruby-M_M_M">離れて</rt></ruby><ruby>kant<rt class="ruby-M_M_M">(を)歌う</rt></ruby>', '<ruby>fork<rt class="ruby-S_S_S">[料]フォーク</rt></ruby><ruby>ant<rt class="ruby-S_S_S">能動;継続</rt></ruby>'], ['gravit', 'gravit', '<ruby>grav<rt class="ruby-L_L_L">重要な</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>'], ['konus', '<ruby>konus<rt class="ruby-L_L_L">[数]円錐</rt></ruby>', '<ruby>kon<rt class="ruby-S_S_S">知っている</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['salat', '<ruby>salat<rt class="ruby-M_M_M">[料]サラダ</rt></ruby>', '<ruby>sal<rt class="ruby-X_X_X">塩</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['legat', '<ruby>legat<rt class="ruby-M_M_M">[宗]教皇特使</rt></ruby>', '<ruby>leg<rt class="ruby-M_M_M">(を)読む</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['lekant', '<ruby>lekant<rt class="ruby-M_M_M">[植]マーガレット</rt></ruby>', '<ruby>lek<rt class="ruby-M_M_M">なめる</rt></ruby><ruby>ant<rt class="ruby-S_S_S">能動;継続</rt></ruby>'], ['lotus', '<ruby>lotus<rt class="ruby-L_L_L">[植]ハス</rt></ruby>', '<ruby>lot<rt class="ruby-L_L_L">くじ</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['malvolont', '<ruby>mal<rt class="ruby-M_M_M">正反対</rt></ruby><ruby>volont<rt class="ruby-L_L_L">自ら進んで</rt></ruby>', '<ruby>mal<rt class="ruby-M_M_M">正反対</rt></ruby><ruby>vol<rt class="ruby-S_S_S">意志がある</rt></ruby><ruby>ont<rt class="ruby-S_S_S">能動;将然</rt></ruby>'], ['mankis', '<ruby>man<rt class="ruby-X_X_X">手</rt></ruby><ruby>kis<rt class="ruby-M_M_M">キスする</rt></ruby>', '<ruby>mank<rt class="ruby-M_M_M">欠けている</rt></ruby><ruby>is<rt class="ruby-S_S_S">過去形</rt></ruby>'], ['minus', '<ruby>minus<rt class="ruby-L_L_L">マイナス</rt></ruby>', '<ruby>min<rt class="ruby-L_L_L">鉱山</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['patos', '<ruby>patos<rt class="ruby-M_M_M">[芸]パトス</rt></ruby>', '<ruby>pat<rt class="ruby-S_S_S">フライパン</rt></ruby><ruby>os<rt class="ruby-S_S_S">未来形</rt></ruby>'], ['predikat', '<ruby>predikat<rt class="ruby-X_X_X">[文]述部</rt></ruby>', '<ruby>predik<rt class="ruby-M_M_M">(を)説教する</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['rabat', '<ruby>rabat<rt class="ruby-L_L_L">[商]割引</rt></ruby>', '<ruby>rab<rt class="ruby-M_M_M">強奪する</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['rabot', '<ruby>rabot<rt class="ruby-S_S_S">かんなをかける</rt></ruby>', '<ruby>rab<rt class="ruby-M_M_M">強奪する</rt></ruby><ruby>ot<rt class="ruby-S_S_S">受動将然</rt></ruby>'], ['remont', 'remont', '<ruby>rem<rt class="ruby-L_L_L">漕ぐ</rt></ruby><ruby>ont<rt class="ruby-S_S_S">能動;将然</rt></ruby>'], ['satirus', 'satirus', '<ruby>satir<rt class="ruby-M_M_M">諷刺(詩;文)</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['sendat', '<ruby>sen<rt class="ruby-S_S_S">(~)なしで</rt></ruby><ruby>dat<rt class="ruby-L_L_L">日付</rt></ruby>', '<ruby>send<rt class="ruby-M_M_M">(を)送る</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['sendot', '<ruby>sen<rt class="ruby-S_S_S">(~)なしで</rt></ruby><ruby>dot<rt class="ruby-M_M_M">持参金</rt></ruby>', '<ruby>send<rt class="ruby-M_M_M">(を)送る</rt></ruby><ruby>ot<rt class="ruby-S_S_S">受動将然</rt></ruby>'], ['spirit', '<ruby>spirit<rt class="ruby-X_X_X">精神</rt></ruby>', '<ruby>spir<rt class="ruby-M_M_M">呼吸する</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>'], ['spirant', 'spirant', '<ruby>spir<rt class="ruby-M_M_M">呼吸する</rt></ruby><ruby>ant<rt class="ruby-S_S_S">能動;継続</rt></ruby>'], ['taksus', '<ruby>taksus<rt class="ruby-L_L_L">[植]イチイ</rt></ruby>', '<ruby>taks<rt class="ruby-S_S_S">(を)評価する</rt></ruby><ruby>us<rt class="ruby-S_S_S">条件法</rt></ruby>'], ['tenis', 'tenis', '<ruby>ten<rt class="ruby-M_M_M">支え持つ</rt></ruby><ruby>is<rt class="ruby-S_S_S">過去形</rt></ruby>'], ['traktat', '<ruby>traktat<rt class="ruby-X_X_X">[政]条約</rt></ruby>', '<ruby>trakt<rt class="ruby-M_M_M">(を)取り扱う</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['trikot', '<ruby>trikot<rt class="ruby-M_M_M">[織]トリコット</rt></ruby>', '<ruby>trik<rt class="ruby-S_S_S">編み物をする</rt></ruby><ruby>ot<rt class="ruby-S_S_S">受動将然</rt></ruby>'], ['trilit', '<ruby>tri<rt class="ruby-X_X_X">三</rt></ruby><ruby>lit<rt class="ruby-M_M_M">ベッド</rt></ruby>', '<ruby>tril<rt class="ruby-M_M_M">[楽]トリル</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>'], ['vizit', '<ruby>vizit<rt class="ruby-M_M_M">(を)訪問する</rt></ruby>', '<ruby>viz<rt class="ruby-L_L_L">ビザ</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>'], ['volont', '<ruby>volont<rt class="ruby-L_L_L">自ら進んで</rt></ruby>', '<ruby>vol<rt class="ruby-S_S_S">意志がある</rt></ruby><ruby>ont<rt class="ruby-S_S_S">能動;将然</rt></ruby>']]
                        for k in ["u ","i ","u","i"]:# 动词の"u","i"単体の接尾辞は後ろが空白と決まっているので、2文字分増やすことができる。
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]# 新しく作った方の語根分解を優先する
                                unchangeable_after_creation_list.append(i+k)
                            # [['agxi', '<ruby>agxi<rt class="ruby-L_L_L">打ち歩</rt></ruby>', '<ruby>agx<rt class="ruby-L_L_L">年齢</rt></ruby>i'], ['premi', '<ruby>premi<rt class="ruby-X_X_X">賞品</rt></ruby>', '<ruby>prem<rt class="ruby-M_M_M">(を)押える</rt></ruby>i'], ['bari', 'bari', '<ruby>bar<rt class="ruby-L_L_L">障害</rt></ruby>i'], ['tempi', '<ruby>tempi<rt class="ruby-L_L_L">こめかみ</rt></ruby>', '<ruby>temp<rt class="ruby-X_X_X">時間</rt></ruby>i'], ['noktu', '<ruby>noktu<rt class="ruby-S_S_S">[鳥]コフクロウ</rt></ruby>', '<ruby>nokt<rt class="ruby-X_X_X">夜</rt></ruby>u'], ['vakcini', 'vakcini', '<ruby>vakcin<rt class="ruby-M_M_M">[薬]ワクチン</rt></ruby>i'], ['procesi', '<ruby>procesi<rt class="ruby-X_X_X">[宗]行列</rt></ruby>', '<ruby>proces<rt class="ruby-L_L_L">[法]訴訟</rt></ruby>i'], ['statu', '<ruby>statu<rt class="ruby-X_X_X">立像</rt></ruby>', '<ruby>stat<rt class="ruby-X_X_X">状態</rt></ruby>u'], ['devi', 'devi', '<ruby>dev<rt class="ruby-L_L_L">must</rt></ruby>i'], ['feri', '<ruby>feri<rt class="ruby-X_X_X">休日</rt></ruby>', '<ruby>fer<rt class="ruby-X_X_X">鉄</rt></ruby>i'], ['fleksi', '<ruby>fleksi<rt class="ruby-M_M_M">[文]語尾変化</rt></ruby>', '<ruby>fleks<rt class="ruby-M_M_M">(を)曲げる</rt></ruby>i'], ['pensi', '<ruby>pensi<rt class="ruby-X_X_X">年金</rt></ruby>', '<ruby>pens<rt class="ruby-X_X_X">思う</rt></ruby>i'], ['jesu', '<ruby>jesu<rt class="ruby-M_M_M">[宗]イエス</rt></ruby>', '<ruby>jes<rt class="ruby-L_L_L">はい</rt></ruby>u'], ['jxaluzi', 'jxaluzi', '<ruby>jxaluz<rt class="ruby-L_L_L">嫉妬深い</rt></ruby>i'], ['konfesi', 'konfesi', '<ruby>konfes<rt class="ruby-M_M_M">(を)告白する</rt></ruby>i'], ['konsili', 'konsili', '<ruby>konsil<rt class="ruby-M_M_M">(を)助言する</rt></ruby>i'], ['legi', '<ruby>legi<rt class="ruby-M_M_M">[史]軍団</rt></ruby>', '<ruby>leg<rt class="ruby-M_M_M">(を)読む</rt></ruby>i'], ['licenci', 'licenci', '<ruby>licenc<rt class="ruby-L_L_L">[商]認可</rt></ruby>i'], ['logxi', '<ruby>logxi<rt class="ruby-L_L_L">[劇]桟敷</rt></ruby>', '<ruby>logx<rt class="ruby-M_M_M">(に)住む</rt></ruby>i'], ['meti', '<ruby>meti<rt class="ruby-L_L_L">手仕事</rt></ruby>', '<ruby>met<rt class="ruby-M_M_M">(を)置く</rt></ruby>i'], ['pasi', '<ruby>pasi<rt class="ruby-X_X_X">情熱</rt></ruby>', '<ruby>pas<rt class="ruby-M_M_M">通過する</rt></ruby>i'], ['revu', '<ruby>revu<rt class="ruby-M_M_M">専門雑誌</rt></ruby>', '<ruby>rev<rt class="ruby-M_M_M">空想する</rt></ruby>u'], ['rabi', '<ruby>rabi<rt class="ruby-M_M_M">[病]狂犬病</rt></ruby>', '<ruby>rab<rt class="ruby-M_M_M">強奪する</rt></ruby>i'], ['religi', '<ruby>religi<rt class="ruby-X_X_X">宗教</rt></ruby>', '<ruby>re<rt class="ruby-M_M_M">再び</rt></ruby><ruby>lig<rt class="ruby-S_S_S">結ぶ;連盟</rt></ruby>i'], ['sagu', '<ruby>sagu<rt class="ruby-M_M_M">[料]サゴ粉</rt></ruby>', '<ruby>sag<rt class="ruby-X_X_X">矢</rt></ruby>u'], ['sekci', '<ruby>sekci<rt class="ruby-X_X_X">部</rt></ruby>', '<ruby>sekc<rt class="ruby-S_S_S">[医]切断する</rt></ruby>i'], ['sendi', '<ruby>sen<rt class="ruby-S_S_S">(~)なしで</rt></ruby><ruby>di<rt class="ruby-X_X_X">神</rt></ruby>', '<ruby>send<rt class="ruby-M_M_M">(を)送る</rt></ruby>i'], ['teni', '<ruby>teni<rt class="ruby-M_M_M">サナダムシ</rt></ruby>', '<ruby>ten<rt class="ruby-M_M_M">支え持つ</rt></ruby>i'], ['vaku', 'vaku', '<ruby>vak<rt class="ruby-S_S_S">あいている</rt></ruby>u'], ['vizi', '<ruby>vizi<rt class="ruby-X_X_X">幻影</rt></ruby>', '<ruby>viz<rt class="ruby-L_L_L">ビザ</rt></ruby>i']]
                elif len(i)>=3 and len(i)<=6:# 3文字から6文字の語根で置換しないもの　　結局2文字の語根で置換しないものについては、完全に除外している。
                    if "名词" in j[1]:# 名词については形容词、副词と違い、置換しないものにもoをつける。
                        for k in ["o"]:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-5000]# 実質3000# 存でないものは優先順位を大きく下げる→普通の品詞接尾辞が既存でないという言い方はおかしい気がしてきた。(20240612)
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pass
                    if "形容词" in j[1]:
                        for k in ["a"]:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-5000]
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pass
                    if "副词" in j[1]:
                        for k in ["e"]:
                            if not i+k in pre_replacements_dict_2:
                                pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-5000]
                            elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                                pass

        # 针对 AN、ON 等也进行对应处理
        for an in AN:
            if an[1].endswith("/an/"):
                i2=an[1]
                i3 = re.sub(r"/an/$", "", i2)
                i4=i3+"/an/o"
                i5=i3+"/an/a"
                i6=i3+"/an/e"
                i7=i3+"/a/n/"
                pre_replacements_dict_3[i4.replace('/', '')]=[safe_replace(i4,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i4.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i5.replace('/', '')]=[safe_replace(i5,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i5.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i6.replace('/', '')]=[safe_replace(i6,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i6.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i7.replace('/', '')]=[safe_replace(i7,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i7.replace('/', ''))-1)*10000+3000]
            else:
                i2=an[1]
                i2_2 = re.sub(r"an$", "", i2)
                i3 = re.sub(r"an/$", "", i2_2)
                i4=i3+"an/o"
                i5=i3+"an/a"
                i6=i3+"an/e"
                i7=i3+"/a/n/"
                pre_replacements_dict_3[i4.replace('/', '')]=[safe_replace(i4,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i4.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i5.replace('/', '')]=[safe_replace(i5,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i5.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i6.replace('/', '')]=[safe_replace(i6,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i6.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i7.replace('/', '')]=[safe_replace(i7,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i7.replace('/', ''))-1)*10000+3000]

        for on in ON:
            if on[1].endswith("/on/"):
                i2=on[1]
                i3 = re.sub(r"/on/$", "", i2)
                i4=i3+"/on/o"
                i5=i3+"/on/a"
                i6=i3+"/on/e"
                i7=i3+"/o/n/"
                pre_replacements_dict_3[i4.replace('/', '')]=[safe_replace(i4,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i4.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i5.replace('/', '')]=[safe_replace(i5,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i5.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i6.replace('/', '')]=[safe_replace(i6,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i6.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i7.replace('/', '')]=[safe_replace(i7,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i7.replace('/', ''))-1)*10000+3000]
            else:
                i2=on[1]
                i2_2 = re.sub(r"on$", "", i2)
                i3 = re.sub(r"on/$", "", i2_2)
                i4=i3+"on/o"
                i5=i3+"on/a"
                i6=i3+"on/e"
                i7=i3+"/o/n/"
                pre_replacements_dict_3[i4.replace('/', '')]=[safe_replace(i4,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i4.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i5.replace('/', '')]=[safe_replace(i5,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i5.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i6.replace('/', '')]=[safe_replace(i6,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i6.replace('/', ''))-1)*10000+3000]
                pre_replacements_dict_3[i7.replace('/', '')]=[safe_replace(i7,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"), (len(i7.replace('/', ''))-1)*10000+3000]

        # -------------------------------------------------------------
        # 7) 应用自定义词根分解 JSON
        # -------------------------------------------------------------
        if len(custom_stemming_setting_list) > 0:
            if len(custom_stemming_setting_list[0]) != 3:
                custom_stemming_setting_list.pop(0)

        for i in custom_stemming_setting_list:
            if len(i)==3:
                try:
                    esperanto_Word_before_replacement = i[0].replace('/', '')
                    if i[1]=="dflt":
                        replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
                    elif i[1] in allowed_values:
                        pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                        if "ne" in i[2]:
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                            i[2].remove("ne")
                        if "verbo_s1" in i[2]:
                            for k1 in verb_suffix_2l.keys():
                                removed_E_word = esperanto_Word_before_replacement + k1
                                pre_replacements_dict_3.pop(removed_E_word, None)
                            i[2].remove("verbo_s1")
                        if "verbo_s2" in i[2]:
                            for k in ["u ", "i ", "u", "i"]:
                                removed_E_word = esperanto_Word_before_replacement + k
                                pre_replacements_dict_3.pop(removed_E_word, None)
                            i[2].remove("verbo_s2")
                        if len(i[2]) >= 1:
                            for j_ in i[2]:
                                j2 = j_.replace('/', '')
                                removed_E_word = esperanto_Word_before_replacement + j2
                                pre_replacements_dict_3.pop(removed_E_word, None)
                        continue
                    elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                        replacement_priority_by_length = int(i[1])

                    Replaced_String = safe_replace(i[0],temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                    if "ne" in i[2]:
                        pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                        i[2].remove("ne")
                    if "verbo_s1" in i[2]:
                        for k1,k2 in verb_suffix_2l.items():
                            replaced_k2 = safe_replace(k2, temporary_replacements_list_final)
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k1]=[Replaced_String+replaced_k2, replacement_priority_by_length+len(k1)*10000]
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ","i ","u","i"]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k]=[Replaced_String+k, replacement_priority_by_length+len(k)*10000]
                        i[2].remove("verbo_s2")
                    if len(i[2])>=1:
                        for j_ in i[2]:
                            j2 = j_.replace('/', '')
                            j3 = safe_replace(j_,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                            pre_replacements_dict_3[esperanto_Word_before_replacement + j2]=[Replaced_String + j3, replacement_priority_by_length+len(j2)*10000]
                    else:
                        pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                except:
                    continue

        # -------------------------------------------------------------
        # 8) 应用“自定义替换后文字” JSON
        # -------------------------------------------------------------
        if len(user_replacement_item_setting_list) > 0:
            if len(user_replacement_item_setting_list[0]) != 4:
                user_replacement_item_setting_list.pop(0)

        for i in user_replacement_item_setting_list:
            if len(i)==4:
                try:   
                    esperanto_Roots_before_replacement = i[0].strip('/').split('/')
                    replaced_roots = i[3].strip('/').split('/')
                    if len(esperanto_Roots_before_replacement) == len(replaced_roots):
                        Replaced_String = ""
                        for kk in range(len(esperanto_Roots_before_replacement)):
                            Replaced_String += output_format(esperanto_Roots_before_replacement[kk],replaced_roots[kk], format_type, char_widths_dict)
                        
                        esperanto_Word_before_replacement = i[0].replace('/', '')
                        if i[1]=="dflt":
                            replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
                        elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                            replacement_priority_by_length = int(i[1])

                        if "ne" in i[2]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                            i[2].remove("ne")
                        if "verbo_s1" in i[2]:
                            for k1,k2 in verb_suffix_2l.items():
                                replaced_k2 = safe_replace(k2,temporary_replacements_list_final)
                                pre_replacements_dict_3[esperanto_Word_before_replacement + k1]=[Replaced_String+replaced_k2, replacement_priority_by_length+len(k1)*10000]
                            i[2].remove("verbo_s1")
                        if "verbo_s2" in i[2]:
                            for k in ["u ","i ","u","i"]:
                                pre_replacements_dict_3[esperanto_Word_before_replacement + k]=[Replaced_String+k, replacement_priority_by_length+len(k)*10000]
                            i[2].remove("verbo_s2")
                        if len(i[2])>=1:
                            for j_ in i[2]:
                                j2 = j_.replace('/', '')
                                j3 = safe_replace(j_,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                                pre_replacements_dict_3[esperanto_Word_before_replacement + j2]=[Replaced_String + j3, replacement_priority_by_length+len(j2)*10000]
                        else:
                            pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                except:
                    continue

        # -------------------------------------------------------------
        # 9) 将生成的 pre_replacements_dict_3 转为列表，并按优先级排序
        # -------------------------------------------------------------
        pre_replacements_list_1=[]
        for old,new in  pre_replacements_dict_3.items():
            if isinstance(new[1], int):
                pre_replacements_list_1.append((old,new[0],new[1]))

        pre_replacements_list_2= sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)

        # 利用 remove_redundant_ruby_if_identical 删除可能出现的 parent=child 的情况
        pre_replacements_list_3=[]
        for kk in range(len(pre_replacements_list_2)):
            if len(pre_replacements_list_2[kk][0])>=3:
                pre_replacements_list_3.append([pre_replacements_list_2[kk][0],remove_redundant_ruby_if_identical(pre_replacements_list_2[kk][1]),imported_placeholders_for_global_replacement[kk]])

        # -------------------------------------------------------------
        # 10) 针对大写/首字母大写等情况，再生成两条替换记录
        # -------------------------------------------------------------
        pre_replacements_list_4=[]
        if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换','HTML格式','HTML格式_汉字替换'):
            for old,new,place_holder in pre_replacements_list_3:
                pre_replacements_list_4.append((old,new,place_holder))
                pre_replacements_list_4.append((old.upper(),new.upper(),place_holder[:-1]+'up$'))
                if old[0]==' ':
                    pre_replacements_list_4.append((old[0] + old[1:].capitalize() ,new[0] + capitalize_ruby_and_rt(new[1:]),place_holder[:-1]+'cap$'))
                else:
                    pre_replacements_list_4.append((old.capitalize(),capitalize_ruby_and_rt(new),place_holder[:-1]+'cap$'))
        elif format_type in ('括弧(号)格式', '括弧(号)格式_汉字替换'):
            for old,new,place_holder in pre_replacements_list_3:
                pre_replacements_list_4.append((old,new,place_holder))
                pre_replacements_list_4.append((old.upper(),new.upper(),place_holder[:-1]+'up$'))
                if old[0]==' ':
                    pre_replacements_list_4.append((old[0] + old[1:].capitalize(),new[0] + new[1:].capitalize(),place_holder[:-1]+'cap$'))
                else:
                    pre_replacements_list_4.append((old.capitalize(),new.capitalize(),place_holder[:-1]+'cap$'))
        elif format_type in ('替换后文字列のみ(仅)保留(简单替换)'):
            for old,new,place_holder in pre_replacements_list_3:
                pre_replacements_list_4.append((old,new,place_holder))
                pre_replacements_list_4.append((old.upper(),new.upper(),place_holder[:-1]+'up$'))
                if old[0]==' ':
                    pre_replacements_list_4.append((old[0] + old[1:].capitalize() ,new[0] + new[1:].capitalize() ,place_holder[:-1]+'cap$'))
                else:
                    pre_replacements_list_4.append((old.capitalize(),new.capitalize(),place_holder[:-1]+'cap$'))

        replacements_final_list=[]
        for old, new, place_holder in pre_replacements_list_4:
            modified_placeholder = place_holder
            if old.startswith(' '):
                modified_placeholder = ' ' + modified_placeholder
                if not new.startswith(' '):
                    new = ' ' + new
            if old.endswith(' '):
                modified_placeholder = modified_placeholder + ' '
                if not new.endswith(' '):
                    new = new + ' '
            replacements_final_list.append((old, new, modified_placeholder))

        # 生成 2字词根的替换列表
        replacements_list_for_suffix_2char_roots=[]
        for i in range(len(suffix_2char_roots)):
            replaced_suffix = remove_redundant_ruby_if_identical(safe_replace(suffix_2char_roots[i],temporary_replacements_list_final))
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i],"$"+replaced_suffix,"$"+imported_placeholders_for_2char_replacement[i]])
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].upper(),"$"+replaced_suffix.upper(),"$"+imported_placeholders_for_2char_replacement[i][:-1]+'up$'])
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].capitalize(),"$"+capitalize_ruby_and_rt(replaced_suffix),"$"+imported_placeholders_for_2char_replacement[i][:-1]+'cap$'])

        replacements_list_for_prefix_2char_roots=[]
        for i in range(len(prefix_2char_roots)):
            replaced_prefix = remove_redundant_ruby_if_identical(safe_replace(prefix_2char_roots[i],temporary_replacements_list_final))
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i]+"$",replaced_prefix+"$",imported_placeholders_for_2char_replacement[i+1000]+"$"])
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].upper()+"$",replaced_prefix.upper()+"$",imported_placeholders_for_2char_replacement[i+1000][:-1]+'up$'+"$"])
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].capitalize()+"$",capitalize_ruby_and_rt(replaced_prefix)+"$",imported_placeholders_for_2char_replacement[i+1000][:-1]+'cap$'+"$"])

        replacements_list_for_standalone_2char_roots=[]
        for i in range(len(standalone_2char_roots)):
            replaced_standalone = remove_redundant_ruby_if_identical(safe_replace(standalone_2char_roots[i],temporary_replacements_list_final))
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i]+" "," "+replaced_standalone+" "," "+imported_placeholders_for_2char_replacement[i+2000]+" "])
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i].upper()+" "," "+replaced_standalone.upper()+" "," "+imported_placeholders_for_2char_replacement[i+2000][:-1]+'up$'+" "])
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i].capitalize()+" "," "+capitalize_ruby_and_rt(replaced_standalone)+" "," "+imported_placeholders_for_2char_replacement[i+2000][:-1]+'cap$'+" "])

        replacements_list_for_2char = replacements_list_for_standalone_2char_roots + replacements_list_for_suffix_2char_roots + replacements_list_for_prefix_2char_roots

        # 用 CSV（仅包含词根→翻译) 构建“局部替换用列表”
        pre_replacements_list_for_localized_string_1=[]
        for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
            if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
                if E_root == hanzi_or_meaning:
                    pre_replacements_list_for_localized_string_1.append([E_root, hanzi_or_meaning, len(E_root)])
                    pre_replacements_list_for_localized_string_1.append([E_root.upper(), hanzi_or_meaning.upper(), len(E_root)])
                    pre_replacements_list_for_localized_string_1.append([E_root.capitalize(), hanzi_or_meaning.capitalize(), len(E_root)])
                else:
                    pre_replacements_list_for_localized_string_1.append([E_root,output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict),len(E_root)])
                    pre_replacements_list_for_localized_string_1.append([E_root.upper(),output_format(E_root.upper(), hanzi_or_meaning.upper(), format_type, char_widths_dict),len(E_root)])
                    pre_replacements_list_for_localized_string_1.append([E_root.capitalize(),output_format(E_root.capitalize(), hanzi_or_meaning.capitalize(), format_type, char_widths_dict),len(E_root)])

        pre_replacements_list_for_localized_string_2 = sorted(pre_replacements_list_for_localized_string_1, key=lambda x: x[2], reverse=True)

        replacements_list_for_localized_string=[]
        for kk in range(len(pre_replacements_list_for_localized_string_2)):
            replacements_list_for_localized_string.append([
                pre_replacements_list_for_localized_string_2[kk][0],
                pre_replacements_list_for_localized_string_2[kk][1],
                imported_placeholders_for_local_replacement[kk]
            ])

        # -------------------------------------------------------------
        # 最终把这三种列表写进一个 JSON 并提供下载
        # -------------------------------------------------------------
        combined_data = {}
        combined_data["全域替换用のリスト(列表)型配列(replacements_final_list)"] = replacements_final_list
        combined_data["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"] = replacements_list_for_2char
        combined_data["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"] = replacements_list_for_localized_string

        download_data = json.dumps(combined_data, ensure_ascii=False, indent=2)
        st.success("替换用 JSON 列表构建完成！")

        st.download_button(
            label="下载生成的（合并三份）替换 JSON 文件",
            data=download_data, 
            file_name="世界语文本替换用_合并3个JSON文件.json",
            mime='application/json'
        )

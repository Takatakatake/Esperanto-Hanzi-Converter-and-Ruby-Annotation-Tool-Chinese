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
    parallel_build_pre_replacements_dict
)

# 事前に作成した Unicode_BMP全范围文字幅(宽)_Arial16.json ファイルを読み込み
with open("./Appの运行に使用する各类文件/Unicode_BMP全范围文字幅(宽)_Arial16.json", "r", encoding="utf-8") as fp:
    char_widths_dict = json.load(fp)   

# ====== 1) ページ設定 & タイトル ======
st.set_page_config(page_title="用于生成世界语文本（含汉字）替换的JSON文件工具", layout="wide")
st.title("生成用于世界语文本（含汉字）替换的 JSON 文件")

st.write("---")
# ====== 2) 概要説明 (使い方) ======
with st.expander("展开使用说明", expanded=True):
    st.markdown("""
    #### 简介
    本页面用于生成在主程序中执行世界语文本（含汉字）替换时所需的 JSON 文件（大小约50MB），并允许您下载该文件。

    **使用流程：**
    1. 准备并上传 **CSV 文件**（例如，世界语词根对应中文翻译等），或者使用默认文件。
    2. 需要的话，准备并上传 **JSON 文件**（例如，对词根分解和替换结果进行自定义设置），或者使用默认文件。
    3. 完成所有配置后，生成 **最终的替换用 JSON 文件** 并下载。

    下方提供了一些示例文件，可参考其格式进行使用。
    """)

# ====== 3) サンプルファイル一覧 (折りたたみ) ======
with st.expander("示例文件一览（可下载）"):
    st.write("#### 示例文件列表")
    st.markdown("""
    **示例CSV1（世界语词根→中文译文列表）**  
    每行都对世界语词根与中文译文进行对应。  
    若想在生成的替换用JSON文件中体现这些对应关系，可自行编辑并上传此类CSV。
    """)
    file_path0 = './Appの运行に使用する各类文件/Ruby格式＿中文.csv'
    with open(file_path0, "rb") as file:
        st.download_button(
            label="下载示例CSV1（世界语词根与中文注释列表）",
            data=file,
            file_name="世界语词根与中文注释列表.csv",
            mime="text/csv"
        )

    st.markdown("""
    **样例 CSV2（世界语词根与汉字对照列表 —— 来自知乎的世界语爱好者 Mingeo 先生的汉字化方案）**  
    这是一个将世界语词根与汉字对应起来的 CSV 文件。
    """)
    # サンプルファイルのパス（保持原代码不变）
    file_path0 = './Appの运行に使用する各类文件/Mingeo_san_hanziization.csv'
    # 读取文件并创建下载按钮
    with open(file_path0, "rb") as file:
        btn = st.download_button(
                label="样例CSV2（世界语词根与汉字对照列表＿Mingeo先生）下载",
                data=file,
                file_name="世界语词根与汉字对照列表＿Mingeo先生.csv",
                mime="text/csv"
            )

    st.markdown("""
    **示例CSV3（世界语词根→汉字对应列表）**  
    此示例文件展示了如何将世界语词根与汉字对应起来。
    """)
    file_path0 = './Appの运行に使用する各类文件/エスペラント語根漢字対応リスト.csv'
    with open(file_path0, "rb") as file:
        st.download_button(
            label="下载示例CSV3（世界语词根与汉字对应列表）",
            data=file,
            file_name="世界语词根与汉字对应列表.csv",
            mime="text/csv"
        )

    st.markdown("""
    **示例JSON1（世界语单词词根分解的自定义设置）**  
    **用途**：可自定义世界语单词如何进行词根分解、  
    是否将动词活用尾或其他词性尾添加到置换列表中等等。  
    文件内对示例有详细说明。（示例：`["am", "dflt", ["verbo_s1"]]`）
    """)
    json_file_path = './Appの运行に使用する各类文件/世界语单词词根分解方法の使用者自定义设置.json'
    with open(json_file_path, "rb") as file_json:
        st.download_button(
            label="下载示例JSON1（世界语单词词根分解自定义设置）",
            data=file_json,
            file_name="世界语单词词根分解自定义设置.json",
            mime="application/json"
        )

    st.markdown("""
    **示例JSON2（替换后文字列的自定义设置）**  
    **用途**：对特定单词追加自定义的汉字/文字列时使用。  
    大多数场合下仅编辑上述 CSV 和词根分解设置 JSON 即可，  
    因此并不强烈推荐另行使用此文件。  
    其内部同样带有更详细的说明。
    """)
    json_file_path2 = './Appの运行に使用する各类文件/替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json'
    with open(json_file_path2, "rb") as file_json:
        st.download_button(
            label="下载示例JSON2（自定义替换后的文字列）",
            data=file_json,
            file_name="自定义替换后的文字列.json",
            mime="application/json"
        )

    st.markdown("""
    **示例Excel1（世界语词根与日语译文列表）**  
    **用途**：若想更灵活地编辑CSV（世界语词根→注释），  
    可参考此Excel文档。它还含有“世界语词根的学习难度”  
    （基于日本语系世界语辞典）的补充信息，以便参考。
    """)
    with open('./Appの运行に使用する各类文件/エスペラント語根日本語訳ルビリスト.xlsx', "rb") as file:
        st.download_button(
            label="下载示例Excel1（世界语词根与日语译文列表）",
            data=file,
            file_name="世界语词根与日语译文列表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.write("---")

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

# 示例部分
main_text_list = ['Esperant','lingv', 'pac', 'amik', 'ec']
ruby_content_list = ['世界语', '语言', '和平', '友', '性质']
formatted_text = ''
for i, item in enumerate(main_text_list):
    formatted_text += output_format(item, ruby_content_list[i], format_type, char_widths_dict)

st.write("---")
st.markdown("**示例（格式化后文本）：**")
components.html(apply_ruby_html_header_and_footer(formatted_text, format_type), height=40, scrolling=False)

st.write("---")

# --- CSV アップロード or デフォルト使用 ---
st.header("步骤1：准备 CSV 文件")
st.markdown("""
此处请选择用于建立翻译/注释信息的 **CSV 文件**（世界语词根 → 中文译文或汉字等）。  
""")
csv_choice = st.radio("是否上传CSV文件？", ("上传", "使用默认文件"))

csv_path_default = "./Appの运行に使用する各类文件/Ruby格式＿中文.csv" 
CSV_data_imported = None

if csv_choice == "上传":
    st.write("请上传您需要的 CSV 文件，建议使用 UTF-8 编码。")
    uploaded_file = st.file_uploader("选择 CSV 文件", type=['csv'])
    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode("utf-8")
        converted_text = convert_to_circumflex(file_contents)
        csv_buffer = StringIO(converted_text)
        CSV_data_imported = pd.read_csv(csv_buffer, encoding="utf-8")
        st.success("CSV 文件上传成功。")
    else:
        st.warning("尚未上传 CSV 文件。")
        st.stop()

elif csv_choice == "使用默认文件":
    try:
        with open(csv_path_default, 'r', encoding="utf-8") as file:
            text = file.read()
        converted_text = convert_to_circumflex(text)
        csv_buffer = StringIO(converted_text)
        CSV_data_imported = pd.read_csv(csv_buffer, encoding="utf-8")
        st.info("使用默认的 CSV 文件。")
    except FileNotFoundError:
        st.error("未找到默认的 CSV 文件，流程终止。")
        st.stop()

st.write("已完成对 CSV 文件的读取，继续下一步。")

st.write("---")
st.header("步骤2：准备 JSON 文件（例如词根分解规则等）")
st.markdown("""
此处可加载自定义的 **JSON 文件** 以设置世界语单词的词根分解方式，以及替换后文字等。  
JSON 文件的具体结构可参考前述示例。
""")

json_choice = st.radio("1. 如何加载（词根分解法）JSON 文件？", ("上传", "使用默认文件"))
json_path_default = "./Appの运行に使用する各类文件/世界语单词词根分解方法の使用者自定义设置.json"
custom_stemming_setting_list = None

if json_choice == "上传":
    uploaded_json = st.file_uploader("请上传 JSON 文件", type=['json'])
    if uploaded_json is not None:
        custom_stemming_setting_list = json.load(uploaded_json)
        st.success("JSON 文件上传成功。")
    else:
        st.warning("尚未上传 JSON 文件。")
        st.stop()
elif json_choice == "使用默认文件":
    try:
        with open(json_path_default, "r", encoding="utf-8") as g:
            custom_stemming_setting_list = json.load(g)
        st.info("使用默认的 JSON 文件。")
    except FileNotFoundError:
        st.error("未找到默认的 JSON 文件。")
        st.stop()

json_choice2 = st.radio("2. 如何加载（替换后文字列）JSON 文件？", ("上传", "使用默认文件"))
json_path_default2 = "./Appの运行に使用する各类文件/替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
user_replacement_item_setting_list = None

if json_choice2 == "上传":
    uploaded_json = st.file_uploader("请上传第二个 JSON 文件", type=['json'])
    if uploaded_json is not None:
        user_replacement_item_setting_list = json.load(uploaded_json)
        st.success("JSON 文件上传成功。")
    else:
        st.warning("尚未上传 JSON 文件。")
        st.stop()
elif json_choice2 == "使用默认文件":
    try:
        with open(json_path_default2, "r", encoding="utf-8") as g:
            user_replacement_item_setting_list = json.load(g)
        st.info("使用默认的 JSON 文件。")
    except FileNotFoundError:
        st.error("未找到默认的 JSON 文件。")
        st.stop()

st.write("---")

st.header("步骤3：并行处理（高级设置）")
with st.expander("展开并行处理选项"):
    st.write("""
    这里可设置在生成替换用 JSON 时，是否采用多进程处理以加快速度。  
    """)
    use_parallel = st.checkbox("使用并行处理", value=False)
    num_processes = st.number_input("进程数量", min_value=2, max_value=6, value=4, step=1)

st.write("### 生成最终替换用 JSON 文件")
if st.button("开始生成替换用 JSON 文件"):
    with st.spinner("正在生成替换用 JSON 文件… 请稍候。"):
        # 以下内部过程不翻译，保持原样
        with open("./Appの运行に使用する各类文件/PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json", "r", encoding="utf-8") as g:
            E_stem_with_Part_Of_Speech_list = json.load(g)

        temporary_replacements_dict={}
        with open("./Appの运行に使用する各类文件/世界语全部词根_约11137个_202501.txt", 'r', encoding='utf-8') as file:
            E_roots = file.readlines()
            for E_root in E_roots:
                E_root = E_root.strip()
                if not E_root.isdigit():
                    temporary_replacements_dict[E_root]=[E_root,len(E_root)]

        for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
            if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
                temporary_replacements_dict[E_root] = [output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict),len(E_root)]

        temporary_replacements_list_1=[]
        for old,new in temporary_replacements_dict.items():
            temporary_replacements_list_1.append((old,new[0],new[1]))
        temporary_replacements_list_2 = sorted(temporary_replacements_list_1, key=lambda x: x[2], reverse=True)

        imported_placeholders = import_placeholders('./Appの运行に使用する各类文件/占位符(placeholders)_$20987$-$499999$_全域替换用.txt')
        temporary_replacements_list_final=[]
        for kk in range(len(temporary_replacements_list_2)):
            temporary_replacements_list_final.append([temporary_replacements_list_2[kk][0],temporary_replacements_list_2[kk][1],imported_placeholders[kk]])

        if use_parallel:
            pre_replacements_dict_1 = parallel_build_pre_replacements_dict(
            E_stem_with_Part_Of_Speech_list,
            temporary_replacements_list_final,
            num_processes)  # CPUコア数に応じて設定。Streamlit Cloudだと2とかになるかもしれません)

        else:
            progress_bar = st.progress(0)
            progress_text = st.empty()  # 進行状況を文字で出すための領域
            # ループ対象の総件数を取得
            total_items = len(E_stem_with_Part_Of_Speech_list)

            pre_replacements_dict_1={}
            for i, j in enumerate(E_stem_with_Part_Of_Speech_list):# 20秒ほどかかる。　先にリストの要素を全て結合して、一つの文字列にしてから置換する方法を試しても(上述)、さほど高速化しなかった。
                if len(j)==2:# (j[0]がエスペラント語根、j[1]が品詞。)
                    if len(j[0])>=2:# 2文字以上のエスペラント語根のみが対象  3で良いのでは(202412)
                        if j[0] in pre_replacements_dict_1:
                            if j[1] not in pre_replacements_dict_1[j[0]][1]:
                                pre_replacements_dict_1[j[0]] = [pre_replacements_dict_1[j[0]][0],pre_replacements_dict_1[j[0]][1] + ',' + j[1]]# 複数品詞の追加
                        else:
                            pre_replacements_dict_1[j[0]]=[safe_replace(j[0], temporary_replacements_list_final),j[1]]# 辞書型配列の追加法
                if i % 1000 == 0:
                    current_count = i + 1  # 1-based で何件目か
                    progress_value = int(current_count / total_items * 100)
                    
                    # プログレスバー更新
                    progress_bar.progress(progress_value)

                    # テキスト表示を更新
                    # 例: 「123/10000 件を処理中...」のように表示
                    progress_text.write(f"{current_count}/{total_items} 个正在处理...")
            # 循环结束，将进度条设为100%，并显示完成提示
            progress_bar.progress(100)
            progress_text.write("耗时最长的处理已完成100%。（还需要大约3~4秒。）")


        keys_to_remove = ['domen', 'teren','posten']# 後でdomen/o,domen/a,domen/e等を追加する。　→確認済み(24/12)
        for key in keys_to_remove:
            pre_replacements_dict_1.pop(key, None)  # 'None' はキーが存在しない場合に返すデフォルト

        # pre_replacements_dict_1→pre_replacements_dict_2  ("'PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表'(E_stem_with_Part_Of_Speech_list)をリスト'temporary_replacements_list_final'(一時的な置換リストの完成版)によって文字列(漢字)置換し終えたリスト(辞書型配列)"(pre_replacements_dict_1)を最終的な置換リスト(replacements_final_list)に成形していく。)
        # pre_replacements_dict_1の'置換対象の単語'、'置換後の文字列'から"/"を抜く(HTML形式にしたい場合、"</rt></ruby>"は"/"を含むので要注意！)。
        # 新たに置換優先順位を表す数字を追加し(置換する単語は'文字数×10000'、置換しない単語は'文字数×10000-3000')、辞書型配列pre_replacements_dict_2として保存。
        pre_replacements_dict_2={}
        for i,j in pre_replacements_dict_1.items():# (iが置換対象の単語、j[0]が置換後の文字列、j[1]が品詞。)
            if i==j[0]:# 置換しない単語  # ⇓の右辺では、HTMLのルビ形式に含まれる'/'を避けながら'置換後の文字列'から"/"を抜く処理を行っている。HTML形式でなくてもしても大丈夫な処理なので、出力形式が'括弧(号)格式'や'替换后文字列のみ(仅)保留(简单替换)'であっても心配無用。
                pre_replacements_dict_2[i.replace('/', '')]=[j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),j[1],len(i.replace('/', ''))*10000-3000]# 置換しない単語は優先順位を下げる
            else:
                pre_replacements_dict_2[i.replace('/', '')]=[j[0].replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>"),j[1],len(i.replace('/', ''))*10000]


        # 基本的には动词に対してのみ活用語尾・接尾辞を追加し、置換対象の単語の文字数を増やす(置換の優先順位を上げる。)
        verb_suffix_2l={'as':'as', 'is':'is', 'os':'os', 'us':'us','at':'at','it':'it','ot':'ot', 'ad':'ad','iĝ':'iĝ','ig':'ig','ant':'ant','int':'int','ont':'ont'}

        verb_suffix_2l_2={}
        for original_verb_suffix,replaced_verb_suffix in verb_suffix_2l.items():
            verb_suffix_2l_2[original_verb_suffix]=safe_replace(replaced_verb_suffix, temporary_replacements_list_final)


        # 一番の工夫ポイント(如何にして置換の優先順位を定め、置換精度を向上させるか。)
        # 基本は単語の文字数が多い順に置換していくことになるが、
        # 例えば、"置換対象の単語に接頭辞、接尾辞を追加し、単語の文字数を増やし、置換の優先順位を上げたものを、置換対象の単語として新たに追加する。"などが、置換精度を上げる方策として考えられる。
        # しかし、いろいろ試した結果、动词に対してのみ活用語尾・接尾辞を追加し、置換対象の単語の文字数を増やす(置換の優先順位を上げる。)のが、ベストに近いことがわかった。

        #  pre_replacements_dict_1→pre_replacements_dict_2→pre_replacements_dict_3  ("'PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表'(E_stem_with_Part_Of_Speech_list)をリスト'temporary_replacements_list_final'(一時的な置換リストの完成版)によって文字列(漢字)置換し終えたリスト(辞書型配列)"(pre_replacements_dict_1)を最終的な置換リスト(replacements_final_list)に成形していく。)

        unchangeable_after_creation_list=[]
        AN_replacement = safe_replace('an', temporary_replacements_list_final)
        AN_treatment=[]

        # pre_replacements_dict_3内での重複の検査をし、それを元に、以下のセルにおける修正がなされている。
        pre_replacements_dict_3={}
        # 辞書をコピーする
        pre_replacements_dict_2_copy = pre_replacements_dict_2.copy()# これがあるので、2回繰り返しするときは2個前のセルに戻ってpre_replacements_dict_2を作り直してからでないといけない。
        for i,j in pre_replacements_dict_2_copy.items():# j[0]:置換後の文字列　j[1]:品詞 j[2]:置換優先順位
            if i.endswith('an') and (AN_replacement in j[0]) and ("名词" in j[1]) and (i[:-2] in pre_replacements_dict_2_copy):# and ("形容词" in pre_replacements_dict_2_copy[i[:-2]][1]) 190個→121個
                AN_treatment.append([i,j[0]])
                pre_replacements_dict_2.pop(i, None)# これで形容詞語尾のanが接尾辞an(員)として、誤って置換されてしまうことは大体防げたハズ。　逆に、接尾辞an(員)が形容詞語尾のanとして、置換されない場合は、後述の局所置換によってその都度対処する。 (202501)
                for k in ["o","a","e"]:
                    if not i+k in pre_replacements_dict_2_copy:
                        pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-2000]
            elif (j[1] == "名词") and (len(i)<=6) and not(j[2]==60000 or j[2]==50000 or j[2]==40000 or j[2]==30000 or j[2]==20000):# 名词だけで、6文字以下で、置換しないやつ  # 置換ミスを防ぐための条件(20240614) altajo,aviso,malm,abes 固有名词対策  意味ふりがなのときは再検討
                for k in ["o"]:
                    if not i+k in pre_replacements_dict_2_copy:
                        pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-2000]# 実質8000 # 既存でないものは優先順位を大きく下げる→普通の品詞接尾辞が既存でないという言い方はおかしい気もするが。(202412)

                    # elif j[0]+k != pre_replacements_dict_2_copy[i+k][0]:# ←本当はこちらの条件のほうが、既に存在してなおかつ語根分解も異なる単語を抽出して来れるため、より良い。
                    else:# 既に存在するのであれば、元々の語根分解を優先し、何もしない。
                        pass
                        # ['buro', 'haloo', 'tauxro', 'unesko']の4個
                pre_replacements_dict_2.pop(i, None)


        for i,j in pre_replacements_dict_2.items():# j[0]:置換後の文字列　j[1]:品詞 j[2]:置換優先順位
            if j[2]==20000:# 2文字で置換するやつ# len(i)<=2:# 1文字は存在しないはずではある。
                # 基本的に非动词の2文字の語根単体を以て置換することはない。　ただし、世界语全部单词_大约44700个(原pejvo.txt).txtに最初から含まれている2文字の語根は既に置換されており、実際の置換にも反映されることになる。
                # 2文字の語根でも、动词については活用語尾を追加することで、自動的に+2文字以上できるので追加した。
                if "名词" in j[1]:
                    for k in ["o","on",'oj']:# "ojn"は不要か
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[' '+i+k]=[' '+j[0]+k,j[2]+(len(k)+1)*10000-5000]
                        # elif j[0]+k != pre_replacements_dict_2[i+k][0]:# ←本当はこちらの条件のほうが、既に存在してなおかつ語根分解も異なる単語を抽出してこれるため、より良い。
                        else:# 既に存在するのであれば、元々の語根分解を優先し、何もしない。
                            pass
                        # [['alo', '<ruby>alo<rt class="ruby-M_M_M">アロエ</rt></ruby>', '<ruby>al<rt class="ruby-S_S_S">~の方へ</rt></ruby>o'], ['duon', '<ruby>du<rt class="ruby-X_X_X">二</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>du<rt class="ruby-X_X_X">二</rt></ruby>on'], ['okon', '<ruby>ok<rt class="ruby-X_X_X">八</rt></ruby><ruby>on<rt class="ruby-M_M_M">分数</rt></ruby>', '<ruby>ok<rt class="ruby-X_X_X">八</rt></ruby>on']]
                if "形容词" in j[1]:
                    for k in ["a","aj",'an']:# "ajn"は不要か  # sia pian ,'an 'も不要
                        if not i+k in pre_replacements_dict_2:# if not なしのほうが良い
                            pre_replacements_dict_3[' '+i+k]=[' '+j[0]+k,j[2]+(len(k)+1)*10000-5000]
                        else:# if not なしのほうが良いというのは既に存在しようとしまいと新しく作った方の語根分解を優先するということ。if not を付けたとしても、elseの方でも同じ処理をするようにすれば何の問題もない。
                            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-5000]# ここは空白なしにすることに(2412)
                            unchangeable_after_creation_list.append(i+k)# 新しく定めた語根分解が後で更新されてしまわないように、unchangeable_after_creation_list に追加。
                            # [['sia', 'sia', '<ruby>si<rt class="ruby-M_M_M">自分</rt></ruby>a'], ['eman', 'eman', '<ruby>em<rt class="ruby-M_M_M">傾向</rt></ruby>an'], ['lian', '<ruby>lian<rt class="ruby-S_S_S">[植]つる植物</rt></ruby>', '<ruby>li<rt class="ruby-X_X_X">彼</rt></ruby>an'], ['pian', '<ruby>pian<rt class="ruby-M_M_M">[楽]ピアノ</rt></ruby>', '<ruby>pi<rt class="ruby-S_S_S">信心深い</rt></ruby>an']]

                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i+k in pre_replacements_dict_2:# if not なしのほうが良い
                            pre_replacements_dict_3[' '+i+k]=[' '+j[0]+k,j[2]+(len(k)+1)*10000-5000]
                        else:
                            pre_replacements_dict_3[' '+i+k]=[' '+j[0]+k,j[2]+(len(k)+1)*10000-5000]
                if "动词" in j[1]:
                    for k1,k2 in verb_suffix_2l_2.items():
                        if not i+k1 in pre_replacements_dict_2:# j[0]:置換後の文字列　j[1]:品詞 j[2]:置換優先順位
                            pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]
                        elif j[0]+k2 != pre_replacements_dict_2[i+k1][0]:
                            pre_replacements_dict_3[i+k1]=[j[0]+k2,j[2]+len(k1)*10000-3000]# 新しく作った方の語根分解を優先する
                            unchangeable_after_creation_list.append(i+k1)# 新しく定めた語根分解が後で更新されてしまわないように、unchangeable_after_creation_list に追加。
                        # [['agat', '<ruby>agat<rt class="ruby-M_M_M">[鉱]メノウ</rt></ruby>', '<ruby>ag<rt class="ruby-S_S_S">行動する</rt></ruby><ruby>at<rt class="ruby-S_S_S">受動継続</rt></ruby>'], ['agit', '<ruby>agit<rt class="ruby-S_S_S">(を)扇動する</rt></ruby>', '<ruby>ag<rt class="ruby-S_S_S">行動する</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>'], ['amas', '<ruby>amas<rt class="ruby-M_M_M">集積;大衆</rt></ruby>', '<ruby>am<rt class="ruby-S_S_S">愛する</rt></ruby><ruby>as<rt class="ruby-S_S_S">現在形</rt></ruby>'], ['iris', '<ruby>iris<rt class="ruby-M_M_M">[解]虹彩</rt></ruby>', '<ruby>ir<rt class="ruby-M_M_M">行く</rt></ruby><ruby>is<rt class="ruby-S_S_S">過去形</rt></ruby>'], ['irit', 'irit', '<ruby>ir<rt class="ruby-M_M_M">行く</rt></ruby><ruby>it<rt class="ruby-S_S_S">受動完了</rt></ruby>']]
                    for k in ["u ","i ","u","i"]:# 动词の"u","i"単体の接尾辞は後ろが空白と決まっているので、2文字分増やすことができる。
                        if not i+k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i+k]=[j[0]+k,j[2]+len(k)*10000-3000]
                        elif j[0]+k != pre_replacements_dict_2[i+k][0]:
                            pass
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

        AN=[['dietan', '/diet/an/', '/diet/an'], ['afrikan', '/afrik/an/', '/afrik/an'], ['movadan', '/mov/ad/an/', '/mov/ad/an'], ['akcian', '/akci/an/', '/akci/an'], ['montaran', '/mont/ar/an/', '/mont/ar/an'], ['amerikan', '/amerik/an/', '/amerik/an'], ['regnan', '/regn/an/', '/regn/an'], ['dezertan', '/dezert/an/', '/dezert/an'], ['asocian', '/asoci/an/', '/asoci/an'], ['insulan', '/insul/an/', '/insul/an'], ['azian', '/azi/an/', '/azi/an'], ['ŝtatan', '/ŝtat/an/', '/ŝtat/an'], ['doman', '/dom/an/', '/dom/an'], ['montan', '/mont/an/', '/mont/an'], ['familian', '/famili/an/', '/famili/an'], ['urban', '/urb/an/', '/urb/an'], ['popolan', '/popol/an/', '/popol/an'], ['dekan', '/dekan/', '/dek/an'], ['partian', '/parti/an/', '/parti/an'], ['lokan', '/lok/an/', '/lok/an'], ['ŝipan', '/ŝip/an/', '/ŝip/an'], ['eklezian', '/eklezi/an/', '/eklezi/an'], ['landan', '/land/an/', '/land/an'], ['orientan', '/orient/an/', '/orient/an'], ['lernejan', '/lern/ej/an/', '/lern/ej/an'], ['enlandan', '/en/land/an/', '/en/land/an'], ['kalkan', '/kalkan/', '/kalk/an'], ['estraran', '/estr/ar/an/', '/estr/ar/an'], ['etnan', '/etn/an/', '/etn/an'], ['eŭropan', '/eŭrop/an/', '/eŭrop/an'], ['fazan', '/fazan/', '/faz/an'], ['polican', '/polic/an/', '/polic/an'], ['socian', '/soci/an/', '/soci/an'], ['societan', '/societ/an/', '/societ/an'], ['grupan', '/grup/an/', '/grup/an'], ['ligan', '/lig/an/', '/lig/an'], ['nacian', '/naci/an/', '/naci/an'], ['koran', '/koran/', '/kor/an'], ['religian', '/religi/an/', '/religi/an'], ['kuban', '/kub/an/', '/kub/an'], ['majoran', '/major/an/', '/major/an'], ['nordan', '/nord/an/', '/nord/an'], ['paran', 'paran', '/par/an'], ['parizan', '/pariz/an/', '/pariz/an'], ['parokan', '/parok/an/', '/parok/an'], ['podian', '/podi/an/', '/podi/an'], ['rusian', '/rus/i/an/', '/rus/ian'], ['satan', '/satan/', '/sat/an'], ['sektan', '/sekt/an/', '/sekt/an'], ['senatan', '/senat/an/', '/senat/an'], ['skisman', '/skism/an/', '/skism/an'], ['sudan', 'sudan', '/sud/an'], ['utopian', '/utopi/an/', '/utopi/an'], ['vilaĝan', '/vilaĝ/an/', '/vilaĝ/an'], ['arĝentan', '/arĝent/an/', '/arĝent/an']]
        ON=[['duon', '/du/on/', '/du/on'], ['okon', '/ok/on/', '/ok/on'], ['nombron', '/nombr/on/', '/nombr/on'], ['patron', '/patron/', '/patr/on'], ['karbon', '/karbon/', '/karb/on'], ['ciklon', '/ciklon/', '/cikl/on'], ['aldon', '/al/don/', '/ald/on'], ['balon', '/balon/', '/bal/on'], ['baron', '/baron/', '/bar/on'], ['baston', '/baston/', '/bast/on'], ['magneton', '/magnet/on/', '/magnet/on'], ['beton', 'beton', '/bet/on'], ['bombon', '/bombon/', '/bomb/on'], ['breton', 'breton', '/bret/on'], ['burĝon', '/burĝon/', '/burĝ/on'], ['centon', '/cent/on/', '/cent/on'], ['milon', '/mil/on/', '/mil/on'], ['kanton', '/kanton/', '/kant/on'], ['citron', '/citron/', '/citr/on'], ['platon', 'platon', '/plat/on'], ['dekon', '/dek/on/', '/dek/on'], ['kvaron', '/kvar/on/', '/kvar/on'], ['kvinon', '/kvin/on/', '/kvin/on'], ['seson', '/ses/on/', '/ses/on'], ['trion', '/tri/on/', '/tri/on'], ['karton', '/karton/', '/kart/on'], ['foton', '/fot/on/', '/fot/on'], ['peron', '/peron/', '/per/on'], ['elektron', '/elektr/on/', '/elektr/on'], ['drakon', 'drakon', '/drak/on'], ['mondon', '/mon/don/', '/mond/on'], ['pension', '/pension/', '/pensi/on'], ['ordon', '/ordon/', '/ord/on'], ['eskadron', 'eskadron', '/eskadr/on'], ['senton', '/sen/ton/', '/sent/on'], ['eston', 'eston', '/est/on'], ['fanfaron', '/fanfaron/', '/fanfar/on'], ['feston', '/feston/', '/fest/on'], ['flegmon', 'flegmon', '/flegm/on'], ['fronton', '/fronton/', '/front/on'], ['galon', '/galon/', '/gal/on'], ['mason', '/mason/', '/mas/on'], ['helikon', 'helikon', '/helik/on'], ['kanon', '/kanon/', '/kan/on'], ['kapon', '/kapon/', '/kap/on'], ['kokon', '/kokon/', '/kok/on'], ['kolon', '/kolon/', '/kol/on'], ['komision', '/komision/', '/komisi/on'], ['salon', '/salon/', '/sal/on'], ['ponton', '/ponton/', '/pont/on'], ['koton', '/koton/', '/kot/on'], ['kripton', 'kripton', '/kript/on'], ['kupon', '/kupon/', '/kup/on'], ['lakon', 'lakon', '/lak/on'], ['ludon', '/lu/don/', '/lud/on'], ['melon', '/melon/', '/mel/on'], ['menton', '/menton/', '/ment/on'], ['milion', '/milion/', '/mili/on'], ['milionon', '/milion/on/', '/milion/on'], ['naŭon', '/naŭ/on/', '/naŭ/on'], ['violon', '/violon/', '/viol/on'], ['trombon', '/trombon/', '/tromb/on'], ['senson', '/sen/son/', '/sens/on'], ['sepon', '/sep/on/', '/sep/on'], ['skadron', 'skadron', '/skadr/on'], ['stadion', '/stadion/', '/stadi/on'], ['tetraon', 'tetraon', '/tetra/on'], ['timon', '/timon/', '/tim/on'], ['valon', 'valon', '/val/on']]

        for an in AN:
            if an[1].endswith("/an/"):
                i2=an[1]
                i3 = re.sub(r"/an/$", "", i2)# 正規表現を使わないと、etn/a/n　において、etnのnまで削られてしまった。　ここの$は末尾を表す正規表現なので要注意。
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
                i3 = re.sub(r"/on/$", "", i2)# 正規表現を使わないと、etn/a/n　において、etnのnまで削られてしまった。　ここの$は末尾を表す正規表現なので要注意。
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

        # 外部ファイルを読み込む形式に変えた。行われている処理は全く同じ。
        # ★一番最初だけチェックして、説明用の項目を削除する
        if len(custom_stemming_setting_list) > 0:
            if len(custom_stemming_setting_list[0]) != 3:
                # 最初のリストの要素の数が3つでなければ、これを説明用の項目であると判断して削除する。
                custom_stemming_setting_list.pop(0)
                
        for i in custom_stemming_setting_list:
            if len(i)==3:
                try:
                    esperanto_Word_before_replacement = i[0].replace('/', '')
                    if i[1]=="dflt":
                        replacement_priority_by_length=len(esperanto_Word_before_replacement)*10000
                    elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):  # 整数または整数に変換可能な文字列
                        replacement_priority_by_length = int(i[1])  # 文字列の場合は整数に変換
                        
                    Replaced_String = safe_replace(i[0],temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                    if "ne" in i[2]:
                        pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                        i[2].remove("ne")#　これがあるので、再実行には要注意!(おそらく問題ない)
                    if "verbo_s1" in i[2]:
                        for k1,k2 in verb_suffix_2l_2.items():
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k1]=[Replaced_String+k2, replacement_priority_by_length+len(k1)*10000]
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ","i ","u","i"]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k]=[Replaced_String+k, replacement_priority_by_length+len(k)*10000]
                        i[2].remove("verbo_s2")
                    if len(i[2])>=1:
                        for j in i[2]:
                            j2 = j.replace('/', '')
                            j3 = safe_replace(j,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                            pre_replacements_dict_3[esperanto_Word_before_replacement + j2]=[Replaced_String + j3, replacement_priority_by_length+len(j2)*10000]
                    else:
                        pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                except:
                    continue


        # ★一番最初だけチェックして、説明用の項目を削除する
        if len(user_replacement_item_setting_list) > 0:
            if len(user_replacement_item_setting_list[0]) != 4:
                # 最初のリストの要素の数が4つでなければ、これを説明用の項目であると判断して削除する。
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
                        elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):  # 整数または整数に変換可能な文字列
                            replacement_priority_by_length = int(i[1])  # 文字列の場合は整数に変換
                        if "ne" in i[2]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                            i[2].remove("ne")#　これがあるので、再実行には要注意!(おそらく問題ない)
                        if "verbo_s1" in i[2]:
                            for k1,k2 in verb_suffix_2l_2.items():
                                pre_replacements_dict_3[esperanto_Word_before_replacement + k1]=[Replaced_String+k2, replacement_priority_by_length+len(k1)*10000]
                            i[2].remove("verbo_s1")
                        if "verbo_s2" in i[2]:
                            for k in ["u ","i ","u","i"]:
                                pre_replacements_dict_3[esperanto_Word_before_replacement + k]=[Replaced_String+k, replacement_priority_by_length+len(k)*10000]
                            i[2].remove("verbo_s2")
                        if len(i[2])>=1:
                            for j in i[2]:
                                j2 = j.replace('/', '')
                                j3 = safe_replace(j,temporary_replacements_list_final).replace("</rt></ruby>","%%%").replace('/', '').replace("%%%","</rt></ruby>")
                                pre_replacements_dict_3[esperanto_Word_before_replacement + j2]=[Replaced_String + j3, replacement_priority_by_length+len(j2)*10000]
                        else:
                            pre_replacements_dict_3[esperanto_Word_before_replacement]=[Replaced_String, replacement_priority_by_length]
                except:
                    continue

        # 辞書型をリスト型に戻す。置換優先順位の数字の大きさ順にソートするため。
        pre_replacements_list_1=[]
        for old,new in  pre_replacements_dict_3.items():
            if isinstance(new[1], int):
                pre_replacements_list_1.append((old,new[0],new[1]))

        pre_replacements_list_2= sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)# (置換優先順位の数字の大きさ順にソート!)

        # 'エスペラント語根'、'置換後文字列'、'placeholder(占位符)'の順に並べ、最終的な文字列(漢字)置換に用いる"replacements"リストの元を作成。
        pre_replacements_list_3=[]
        for kk in range(len(pre_replacements_list_2)):
            if len(pre_replacements_list_2[kk][0])>=3:# 3文字以上でいいのではないか(202412)  la対策として考案された。
                pre_replacements_list_3.append([pre_replacements_list_2[kk][0],pre_replacements_list_2[kk][1],imported_placeholders[kk]])

        # '大文字'、'小文字'、'文頭だけ大文字'の3パターンに対応。
        pre_replacements_list_4=[]
        if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换','HTML格式','HTML格式_汉字替换'):
            for old,new,place_holder in pre_replacements_list_3:
                pre_replacements_list_4.append((old,new,place_holder))
                pre_replacements_list_4.append((old.upper(),new.upper(),place_holder[:-1]+'up$'))# placeholderを少し変更する必要がある。
                if old[0]==' ':# 置換対象の文字列の語頭が空白の場合にも対応　語頭に空白を入れている置換対象は殆どない。二文字語根のみ。
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
            # 新しい変数で空白を追加した内容を保持
            modified_placeholder = place_holder
            if old.startswith(' '):
                modified_placeholder = ' ' + modified_placeholder  # 置換対象の文字列の語頭が空白の場合、placeholderの語頭にも空白を追加する。(空白の競合を防ぐため。)
                if not new.startswith(' '):
                    new = ' ' + new
            if old.endswith(' '):
                modified_placeholder = modified_placeholder + ' '  # 置換対象の文字列の語末が空白の場合、placeholderの語末にも空白を追加する。(空白の競合を防ぐため。)
                if not new.endswith(' '):
                    new = new + ' '
            # 結果をリストに追加
            replacements_final_list.append((old, new, modified_placeholder))


        suffix_2char_roots=['ad', 'ag', 'am', 'ar', 'as', 'at', 'av', 'di', 'ec', 'eg', 'ej', 'em', 'er', 'et', 'id', 'ig', 'il', 'in', 'ir', 'is', 'it', 'lu', 'nj', 'op', 'or', 'os', 'ot', 'ov', 'pi', 'te', 'uj', 'ul', 'um', 'us', 'uz','ĝu','aĵ','iĝ','aĉ','aĝ','ŝu','eĥ']
        prefix_2char_roots=['al', 'am', 'av', 'bo', 'di', 'du', 'ek', 'el', 'en', 'fi', 'ge', 'ir', 'lu', 'ne', 'ok', 'or', 'ov', 'pi', 're', 'te', 'uz','ĝu','aĉ','aĝ','ŝu','eĥ']
        standalone_2char_roots=['al', 'ci', 'da', 'de', 'di', 'do', 'du', 'el', 'en', 'fi', 'ha', 'he', 'ho', 'ia', 'ie', 'io', 'iu', 'ja', 'je', 'ju','ke', 'la', 'li', 'mi', 'ne', 'ni', 'nu', 'ok', 'ol', 'po', 'se', 'si', 've', 'vi','ŭa','aŭ','ĉe','ĝi','ŝi','ĉu']
        # an,onはなしにする。

        imported_placeholders_for_2char = import_placeholders('./Appの运行に使用する各类文件/占位符(placeholders)_$13246$-$19834$_二文字词根替换用.txt')# 文字列(漢字)置換時に用いる"placeholder"ファイルを予め読み込んでおく。

        replacements_list_for_suffix_2char_roots=[]
        for i in range(len(suffix_2char_roots)):
            replaced_suffix = safe_replace(suffix_2char_roots[i],temporary_replacements_list_final)
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i],"$"+replaced_suffix,"$"+imported_placeholders_for_2char[i]])
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].upper(),"$"+replaced_suffix.upper(),"$"+imported_placeholders_for_2char[i][:-1]+'up$'])
            replacements_list_for_suffix_2char_roots.append(["$"+suffix_2char_roots[i].capitalize(),"$"+capitalize_ruby_and_rt(replaced_suffix),"$"+imported_placeholders_for_2char[i][:-1]+'cap$'])

        replacements_list_for_prefix_2char_roots=[]
        for i in range(len(prefix_2char_roots)):
            replaced_prefix = safe_replace(prefix_2char_roots[i],temporary_replacements_list_final)
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i]+"$",replaced_prefix+"$",imported_placeholders_for_2char[i+1000]+"$"])
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].upper()+"$",replaced_prefix.upper()+"$",imported_placeholders_for_2char[i+1000][:-1]+'up$'+"$"])
            replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].capitalize()+"$",capitalize_ruby_and_rt(replaced_prefix)+"$",imported_placeholders_for_2char[i+1000][:-1]+'cap$'+"$"])

        replacements_list_for_standalone_2char_roots=[]
        for i in range(len(standalone_2char_roots)):
            replaced_standalone = safe_replace(standalone_2char_roots[i],temporary_replacements_list_final)
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i]+" "," "+replaced_standalone+" "," "+imported_placeholders_for_2char[i+2000]+" "])
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i].upper()+" "," "+replaced_standalone.upper()+" "," "+imported_placeholders_for_2char[i+2000][:-1]+'up$'+" "])
            replacements_list_for_standalone_2char_roots.append([" "+standalone_2char_roots[i].capitalize()+" "," "+capitalize_ruby_and_rt(replaced_standalone)+" "," "+imported_placeholders_for_2char[i+2000][:-1]+'cap$'+" "])

        replacements_list_for_2char=replacements_list_for_standalone_2char_roots+replacements_list_for_suffix_2char_roots+replacements_list_for_prefix_2char_roots


        # 局所的な文字列(漢字)置換には、最初の"CSV_data_imported"のみを使って作成した置換リストを用いる。

        pre_replacements_list_for_localized_string_1=[]
        for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
            if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):  # 条件を満たす行のみ処理
                pre_replacements_list_for_localized_string_1.append([E_root,output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict),len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.upper(),output_format(E_root.upper(), hanzi_or_meaning.upper(), format_type, char_widths_dict),len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.capitalize(),output_format(E_root.capitalize(), hanzi_or_meaning.capitalize(), format_type, char_widths_dict),len(E_root)])

        pre_replacements_list_for_localized_string_2 = sorted(pre_replacements_list_for_localized_string_1, key=lambda x: x[2], reverse=True)

        imported_placeholders = import_placeholders('./Appの运行に使用する各类文件/占位符(placeholders)_@20374@-@97648@_局部文字列替换用.txt')
        replacements_list_for_localized_string=[]
        for kk in range(len(pre_replacements_list_for_localized_string_2)):
            replacements_list_for_localized_string.append([pre_replacements_list_for_localized_string_2[kk][0],pre_replacements_list_for_localized_string_2[kk][1],imported_placeholders[kk]])



        # --- 結合する処理 ---
        combined_data = {}
        combined_data["全域替换用のリスト(列表)型配列(replacements_final_list)"] = replacements_final_list
        combined_data["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"] = replacements_list_for_2char
        combined_data["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"] = replacements_list_for_localized_string

        download_data = json.dumps(combined_data, ensure_ascii=False, indent=2)

        st.success("替换列表生成完成！")
        st.download_button(
            label="下载最终合并的替换用JSON文件 (合并3个JSON)",
            data=download_data,
            file_name="最终合并的替换用JSON文件(合并3个JSON).json",
            mime='application/json'
        )

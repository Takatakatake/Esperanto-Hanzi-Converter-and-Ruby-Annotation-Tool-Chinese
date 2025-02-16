"""
esp_text_replacement_module.py

本模块是“针对世界语文本进行字符串（汉字等）替换”的一系列工具函数。
主要功能：
1. 将各种世界语标记形式（带 x 的 cx, gx...、或带 ^ 的 c^, g^...）转换到字上符形式（ĉ, ĝ, ĥ 等）
2. 实现 %...%（跳过替换） 和 @...@（局部替换）的逻辑
3. safe_replace()：使用 placeholder（占位符）进行安全替换
4. orchestrate_comprehensive_esperanto_text_replacement()：综合替换流程的核心函数
5. parallel_process()：使用多进程来并行处理长文本

代码大体结构：
- 定义若干世界语字符转换的字典（如 x_to_circumflex 等）
- 提供若干辅助函数（unify_halfwidth_spaces, convert_to_circumflex...）
- 提供对 %...%、@...@ 的专门处理
- 提供 orchestrate_comprehensive_esperanto_text_replacement()，将多种替换整合起来
- parallel_process() / process_segment() 用于多进程并行处理长文本时的替换
"""

import re
import json
from typing import List, Tuple, Dict
import multiprocessing

# ================================
# 1) 世界语字符转换相关的字典
# ================================
x_to_circumflex = {'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ',
                   'Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ', 'Ux': 'Ŭ'}
circumflex_to_x = {'ĉ': 'cx', 'ĝ': 'gx', 'ĥ': 'hx', 'ĵ': 'jx', 'ŝ': 'sx', 'ŭ': 'ux',
                   'Ĉ': 'Cx', 'Ĝ': 'Gx', 'Ĥ': 'Hx', 'Ĵ': 'Jx', 'Ŝ': 'Sx', 'Ŭ': 'Ux'}

x_to_hat = {'cx': 'c^', 'gx': 'g^', 'hx': 'h^', 'jx': 'j^', 'sx': 's^', 'ux': 'u^',
            'Cx': 'C^', 'Gx': 'G^', 'Hx': 'H^', 'Jx': 'J^', 'Sx': 'S^', 'Ux': 'U^'}
hat_to_x = {'c^': 'cx', 'g^': 'gx', 'h^': 'hx', 'j^': 'jx', 's^': 'sx', 'u^': 'ux',
            'C^': 'Cx', 'G^': 'Gx', 'H^': 'Hx', 'J^': 'Jx', 'S^': 'Sx', 'U^': 'Ux'}

hat_to_circumflex = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ',
                     'C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'}
circumflex_to_hat = {'ĉ': 'c^', 'ĝ': 'g^', 'ĥ': 'h^', 'ĵ': 'j^', 'ŝ': 's^', 'ŭ': 'u^',
                     'Ĉ': 'C^', 'Ĝ': 'G^', 'Ĥ': 'H^', 'Ĵ': 'J^', 'Ŝ': 'S^', 'Ŭ': 'U^'}

# ================================
# 2) 基本的字符转换函数
# ================================
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    """
    将文本中的若干 key 替换为对应的 value。
    例如，{'cx': 'ĉ', ...} 可以把“cx”全部替换成“ĉ”。
    """
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text

def convert_to_circumflex(text: str) -> str:
    """
    将给定文本中的世界语特殊字母统一转换为字上符形式（ĉ, ĝ, ĥ, ĵ, ŝ, ŭ等）。
    实际包括两步：hat_to_circumflex（将 c^转为ĉ 等），x_to_circumflex（将 cx转为ĉ 等）。
    """
    text = replace_esperanto_chars(text, hat_to_circumflex)
    text = replace_esperanto_chars(text, x_to_circumflex)
    return text

def unify_halfwidth_spaces(text: str) -> str:
    """
    将文本中的各种半角空白（如 \u00A0, \u2002 等）统一为 ASCII 标准半角空格 (U+0020)。
    不处理全角空格 (U+3000)。
    """
    pattern = r"[\u00A0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A]"
    return re.sub(pattern, " ", text)

# ================================
# 3) 占位符（placeholder）相关
# ================================

def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """
    执行安全替换：replacements 列表中每个元素是 (old, new, placeholder)。
    先把 text 中的 old 全部替换为 placeholder，再把 placeholder 替换为 new。
    这样可避免重复替换或交叉覆盖的问题。
    """
    valid_replacements = {}
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text

def import_placeholders(filename: str) -> List[str]:
    """
    从指定文件读取 placeholder 列表。文件中每行一个 placeholder，返回一个列表。
    """
    with open(filename, 'r') as file:
        placeholders = [line.strip() for line in file if line.strip()]
    return placeholders

# -------------------------------
# 用于 %...% (跳过替换) 的逻辑
# -------------------------------
PERCENT_PATTERN = re.compile(r'%(.{1,50}?)%')
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """
    在文本中查找形如 %foo% 的片段（1~50 字符），返回匹配部分（不含 %）。
    """
    matches = []
    used_indices = set()

    for match in PERCENT_PATTERN.finditer(text):
        start, end = match.span()
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    """
    分析文本中的 %xxx% 段落，把它们映射到 placeholders。
    返回类似 [("%xxx%", placeholder), ...]
    """
    matches = find_percent_enclosed_strings_for_skipping_replacement(text)
    replacements_list_for_intact_parts = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replacements_list_for_intact_parts.append([f"%{match}%", placeholders[i]])
        else:
            break
    return replacements_list_for_intact_parts

# -------------------------------
# 用于 @...@ (局部替换) 的逻辑
# -------------------------------
AT_PATTERN = re.compile(r'@(.{1,18}?)@')
def find_at_enclosed_strings_for_localized_replacement(text: str) -> List[str]:
    """
    查找 @foo@ 的片段（1~18 字符），返回提取的 foo。
    """
    matches = []
    used_indices = set()

    for match in AT_PATTERN.finditer(text):
        start, end = match.span()
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_localized_replacement(
    text,
    placeholders: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]]
) -> List[List[str]]:
    """
    针对文本中出现的 @xxx@，用 replacements_list_for_localized_string 对其中的内容执行 safe_replace。
    最终返回 [("@xxx@", placeholder, replaced_xxx), ...] 形式。
    """
    matches = find_at_enclosed_strings_for_localized_replacement(text)
    tmp_replacements_list_for_localized_string = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replaced_match = safe_replace(match, replacements_list_for_localized_string)
            tmp_replacements_list_for_localized_string.append([f"@{match}@", placeholders[i], replaced_match])
        else:
            break
    return tmp_replacements_list_for_localized_string

# ================================
# 4) 综合替换主函数
# ================================
def orchestrate_comprehensive_esperanto_text_replacement(
    text,
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str
) -> str:
    """
    进行一系列替换操作：
      1) 统一半角空格
      2) 将 c^, cx 等转为 ĉ, ĝ 等
      3) 把 %...% 段落替换为占位符（跳过后续替换）
      4) 把 @...@ 段落提取、执行局部替换后再替换成占位符
      5) 对其余文本进行大范围替换（replacements_final_list）
      6) 针对 2字词根（replacements_list_for_2char）进行多次替换
      7) 恢复 placeholder
      8) 若是 HTML 形式，替换换行符为 <br>，空白处理等
    """
    text = unify_halfwidth_spaces(text)
    text = convert_to_circumflex(text)

    # 处理 %...% 跳过替换
    replacements_list_for_intact_parts = create_replacements_list_for_intact_parts(text, placeholders_for_skipping_replacements)
    sorted_replacements_list_for_intact_parts = sorted(replacements_list_for_intact_parts, key=lambda x: len(x[0]), reverse=True)
    for original, place_holder_ in sorted_replacements_list_for_intact_parts:
        text = text.replace(original, place_holder_)

    # 处理 @...@ 局部替换
    tmp_replacements_list_for_localized_string_2 = create_replacements_list_for_localized_replacement(text, placeholders_for_localized_replacement, replacements_list_for_localized_string)
    sorted_replacements_list_for_localized_string = sorted(tmp_replacements_list_for_localized_string_2, key=lambda x: len(x[0]), reverse=True)
    for original, place_holder_, replaced_original in sorted_replacements_list_for_localized_string:
        text = text.replace(original, place_holder_)

    # 大域替换
    valid_replacements = {}
    for old, new, placeholder in replacements_final_list:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new

    # 2 字母词根，两次替换
    valid_replacements_for_2char_roots = {}
    for old, new, placeholder in replacements_list_for_2char:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements_for_2char_roots[placeholder] = new

    valid_replacements_for_2char_roots_2 = {}
    for old, new, placeholder in replacements_list_for_2char:
        if old in text:
            place_holder_second = "!"+placeholder+"!"
            text = text.replace(old, place_holder_second)
            valid_replacements_for_2char_roots_2[place_holder_second] = new

    # 恢复 placeholder
    for place_holder_second, new in reversed(valid_replacements_for_2char_roots_2.items()):
        text = text.replace(place_holder_second, new)
    for placeholder, new in reversed(valid_replacements_for_2char_roots.items()):
        text = text.replace(placeholder, new)
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)

    for original, place_holder_, replaced_original in sorted_replacements_list_for_localized_string:
        text = text.replace(place_holder_, replaced_original.replace("@",""))
    for original, place_holder_ in sorted_replacements_list_for_intact_parts:
        text = text.replace(place_holder_, original.replace("%",""))

    # 如果是 HTML 形式，可替换换行符为 <br> 等
    if "HTML" in format_type:
        text = text.replace("\n", "<br>\n")
        text = re.sub(r"   ", "&nbsp;&nbsp;&nbsp;", text)
        text = re.sub(r"  ", "&nbsp;&nbsp;", text)

    return text

# ================================
# 5) 多进程处理长文本
# ================================
def process_segment(
    lines: List[str],
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str
) -> str:
    """
    用于并行处理的子函数：把若干行拼成一段，然后调用 orchestrate_comprehensive_esperanto_text_replacement。
    """
    segment = ''.join(lines)
    result = orchestrate_comprehensive_esperanto_text_replacement(
        segment,
        placeholders_for_skipping_replacements,
        replacements_list_for_localized_string,
        placeholders_for_localized_replacement,
        replacements_final_list,
        replacements_list_for_2char,
        format_type
    )
    return result

def parallel_process(
    text: str,
    num_processes: int,
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str
) -> str:
    """
    把文本按行拆分，分配给多个子进程并行处理（process_segment），然后再拼接结果。
    """
    if num_processes <= 1:
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type
        )

    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)
    if num_lines <= 1:
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type
        )

    lines_per_process = max(num_lines // num_processes, 1)
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(
            process_segment,
            [
                (
                    lines[start:end],
                    placeholders_for_skipping_replacements,
                    replacements_list_for_localized_string,
                    placeholders_for_localized_replacement,
                    replacements_final_list,
                    replacements_list_for_2char,
                    format_type
                )
                for (start, end) in ranges
            ]
        )

    return ''.join(results)

def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    """
    根据所选 format_type，为文本加上一段 HTML 头尾（主要是 <style> 设定等），
    用于在浏览器渲染时控制 Ruby 字体大小或样式。

    （如果不是 HTML 相关类型，返回原文即可）
    """
    if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
        ruby_style_head = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ruby 显示</title>
<style>
html, body {
  -webkit-text-size-adjust: 100%;
  -moz-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
  text-size-adjust: 100%;
}
:root {
  --ruby-color: blue;
  --ruby-font-size: 0.5em;
}
html {
  font-size: 100%;
}
.text-M_M {
  font-size: 1rem!important;
  font-family: Arial, sans-serif;
  line-height: 2.0 !important;
  display: block;
  position: relative;
}
ruby {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: top !important;
  line-height: 2.0 !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 1rem !important;
}
rt {
  display: block !important;
  font-size: var(--ruby-font-size);
  color: var(--ruby-color);
  line-height: 1.05;
  text-align: center;
}
rt.XXXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -8.3em !important;
  transform: translateY(-0em) !important;
}
rt.XXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -7.2em !important;
  transform: translateY(-0em) !important;
}
rt.XS_S {
  --ruby-font-size: 0.3em;
  margin-top: -6.1em !important;
  transform: translateY(-0em) !important;
}
rt.S_S {
  --ruby-font-size: 0.4em;
  margin-top: -4.85em !important;
  transform: translateY(-0em) !important;
}
rt.M_M {
  --ruby-font-size: 0.5em;
  margin-top: -4.00em !important;
  transform: translateY(-0.0em) !important;
}
rt.L_L {
  --ruby-font-size: 0.6em;
  margin-top: -3.55em !important;
  transform: translateY(-0.0em) !important;
}
rt.XL_L {
  --ruby-font-size: 0.7em;
  margin-top: -3.20em !important;
  transform: translateY(-0.0em) !important;
}
rt.XXL_L {
  --ruby-font-size: 0.8em;
  margin-top: -2.80em !important;
  transform: translateY(-0.0em) !important;
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
    
    return ruby_style_head + processed_text + ruby_style_tail

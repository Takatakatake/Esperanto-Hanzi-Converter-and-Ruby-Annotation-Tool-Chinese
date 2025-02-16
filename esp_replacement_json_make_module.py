"""
esp_replacement_json_make_module.py

此模块与 “esp_text_replacement_module.py” 类似，主要用于 JSON 构建时的一些辅助函数，
包括：
- 字符转换函数（convert_to_circumflex）
- output_format(...)：根据用户选择的输出类型，构建 <ruby> 结构 或 括号结构
- capitalize_ruby_and_rt(...)：在 HTML ruby 中将首字母大写
- 并行替换相关函数（process_chunk_for_pre_replacements, parallel_build_pre_replacements_dict）
- remove_redundant_ruby_if_identical(...)：如果 <ruby>文本 与 <rt>文本 完全相同，则去除重复

它与 esp_text_replacement_module.py 有所重叠/交叉，一部分函数实现思路类似，但为保持独立性可能重复定义。
"""

import re
import json
import multiprocessing
import pandas as pd
import os
from typing import List, Dict, Tuple, Optional

# ================================
# 1) 世界语字符转换用的字典
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
# 2) 字符转换函数
# ================================
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    """
    在 text 中，用 char_dict 做普通字符串替换。
    """
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text

def convert_to_circumflex(text: str) -> str:
    """
    将文本中的 c^, cx 等统一替换为 ĉ, ĝ 等。
    """
    text = replace_esperanto_chars(text, hat_to_circumflex)
    text = replace_esperanto_chars(text, x_to_circumflex)
    return text

# ================================
# 3) 文字宽度测量 & <br> 插入
# ================================
def measure_text_width_Arial16(text, char_widths_dict: Dict[str, int]) -> int:
    """
    利用从 JSON 中加载的 {char: width(px)}，计算 text 的总宽度像素值。
    如果 char 不在字典中，默认宽度 8。
    """
    total_width = 0
    for ch in text:
        char_width = char_widths_dict.get(ch, 8)
        total_width += char_width
    return total_width

def insert_br_at_half_width(text, char_widths_dict: Dict[str, int]) -> str:
    """
    测量 text 的宽度，找到中点位置附近，插入一个 <br>。
    """
    total_width = measure_text_width_Arial16(text, char_widths_dict)
    half_width = total_width / 2
    current_width = 0
    insert_index = None
    for i, ch in enumerate(text):
        char_width = char_widths_dict.get(ch, 8)
        current_width += char_width
        if current_width >= half_width:
            insert_index = i + 1
            break
    if insert_index is not None:
        result = text[:insert_index] + "<br>" + text[insert_index:]
    else:
        result = text
    return result

def insert_br_at_third_width(text, char_widths_dict: Dict[str, int]) -> str:
    """
    把 total_width / 3, 2/3 的位置各插一个 <br>，即插两处。
    """
    total_width = measure_text_width_Arial16(text, char_widths_dict)
    third_width = total_width / 3
    thresholds = [third_width, third_width * 2]
    current_width = 0
    insert_indices = []
    found_first = False
    for i, ch in enumerate(text):
        char_width = char_widths_dict.get(ch, 8)
        current_width += char_width
        if not found_first and current_width >= thresholds[0]:
            insert_indices.append(i + 1)
            found_first = True
        elif found_first and current_width >= thresholds[1]:
            insert_indices.append(i + 1)
            break
    result = text
    for idx in reversed(insert_indices):
        result = result[:idx] + "<br>" + result[idx:]
    return result

# ================================
# 4) output_format(...) 函数
# ================================
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    """
    根据用户选择的 format_type，不同方式组合 main_text 和 ruby_content。
    可能是 <ruby>main<rt>ruby</rt></ruby>，也可能是“main(ruby)”等。
    并对过长的 ruby 或 main_text 做 <br> 插入。
    """
    if format_type == 'HTML格式_Ruby文字_大小调整':
        width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
        width_main = measure_text_width_Arial16(main_text, char_widths_dict)
        ratio_1 = width_ruby / width_main
        if ratio_1 > 6:
            return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
        elif ratio_1 > (9/3):
            return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
        elif ratio_1 > (9/4):
            return f'<ruby>{main_text}<rt class="XS_S">{ruby_content}</rt></ruby>'
        elif ratio_1 > (9/5):
            return f'<ruby>{main_text}<rt class="S_S">{ruby_content}</rt></ruby>'
        elif ratio_1 > (9/6):
            return f'<ruby>{main_text}<rt class="M_M">{ruby_content}</rt></ruby>'
        elif ratio_1 > (9/7):
            return f'<ruby>{main_text}<rt class="L_L">{ruby_content}</rt></ruby>'
        elif ratio_1 > (9/8):
            return f'<ruby>{main_text}<rt class="XL_L">{ruby_content}</rt></ruby>'
        else:
            return f'<ruby>{main_text}<rt class="XXL_L">{ruby_content}</rt></ruby>'
    elif format_type == 'HTML格式_Ruby文字_大小调整_汉字替换':
        width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
        width_main = measure_text_width_Arial16(main_text, char_widths_dict)
        ratio_2 = width_main / width_ruby
        if ratio_2 > 6:
            return f'<ruby>{ruby_content}<rt class="XXXS_S">{insert_br_at_third_width(main_text, char_widths_dict)}</rt></ruby>'
        elif ratio_2 > (9/3):
            return f'<ruby>{ruby_content}<rt class="XXS_S">{insert_br_at_half_width(main_text, char_widths_dict)}</rt></ruby>'
        elif ratio_2 > (9/4):
            return f'<ruby>{ruby_content}<rt class="XS_S">{main_text}</rt></ruby>'
        elif ratio_2 > (9/5):
            return f'<ruby>{ruby_content}<rt class="S_S">{main_text}</rt></ruby>'
        elif ratio_2 > (9/6):
            return f'<ruby>{ruby_content}<rt class="M_M">{main_text}</rt></ruby>'
        elif ratio_2 > (9/7):
            return f'<ruby>{ruby_content}<rt class="L_L">{main_text}</rt></ruby>'
        elif ratio_2 > (9/8):
            return f'<ruby>{ruby_content}<rt class="XL_L">{main_text}</rt></ruby>'
        else:
            return f'<ruby>{ruby_content}<rt class="XXL_L">{main_text}</rt></ruby>'
    elif format_type == 'HTML格式':
        return f'<ruby>{main_text}<rt>{ruby_content}</rt></ruby>'
    elif format_type == 'HTML格式_汉字替换':
        return f'<ruby>{ruby_content}<rt>{main_text}</rt></ruby>'
    elif format_type == '括弧(号)格式':
        return f'{main_text}({ruby_content})'
    elif format_type == '括弧(号)格式_汉字替换':
        return f'{ruby_content}({main_text})'
    elif format_type == '替换后文字列のみ(仅)保留(简单替换)':
        return f'{ruby_content}'

# ================================
# 5) 其他辅助函数
# ================================
def contains_digit(s: str) -> bool:
    """
    判断字符串 s 中是否含有数字字符。
    """
    return any(char.isdigit() for char in s)

def import_placeholders(filename: str) -> List[str]:
    """
    从文件导入占位符。
    """
    with open(filename, 'r') as file:
        placeholders = [line.strip() for line in file if line.strip()]
    return placeholders

# -------------------------------
# capitalize_ruby_and_rt(...)
# -------------------------------
RUBY_PATTERN = re.compile(
    r'^'
    r'(.*?)'
    r'(<ruby>)'
    r'([^<]+)'
    r'(<rt[^>]*>)'
    r'([^<]*?(?:<br>[^<]*?){0,2})'
    r'(</rt>)'
    r'(</ruby>)?'
    r'(.*)'
    r'$'
)
def capitalize_ruby_and_rt(text: str) -> str:
    """
    当需要把 <ruby>xxx<rt>yyy</rt></ruby> 中的 xxx 或 yyy 首字母大写时使用。
    实际逻辑是先匹配，然后尝试做大写化。若没匹配到，就把整段做 text.capitalize()。
    """
    def replacer(match):
        g1 = match.group(1)
        g2 = match.group(2)
        g3 = match.group(3)
        g4 = match.group(4)
        g5 = match.group(5)
        g6 = match.group(6)
        g7 = match.group(7)
        g8 = match.group(8)
        if g1.strip():
            return g1.capitalize() + g2 + g3 + g4 + g5 + g6 + (g7 if g7 else '') + g8
        else:
            parent_text = g3.capitalize()
            rt_text = g5.capitalize()
            return g1 + g2 + parent_text + g4 + rt_text + g6 + (g7 if g7 else '') + g8

    replaced_text = RUBY_PATTERN.sub(replacer, text)
    if replaced_text == text:
        replaced_text = text.capitalize()
    return replaced_text

# ================================
# 6) 并行处理：用在创建 JSON 过程
# ================================
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    valid_replacements = {}
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text

def process_chunk_for_pre_replacements(
    chunk: List[List[str]],
    replacements: List[Tuple[str, str, str]]
) -> Dict[str, List[str]]:
    """
    针对 chunk（类似 [ [词根, 词性], ... ]）中的每个词根，执行 safe_replace。
    返回 { 词根: [ 替换后字符串, 合并词性 ], ... }。
    """
    local_dict = {}
    for item in chunk:
        if len(item) != 2:
            continue
        E_root, pos_info = item
        if len(E_root) < 2:
            continue
        if E_root in local_dict:
            replaced_stem, existing_pos_str = local_dict[E_root]
            existing_pos_list = existing_pos_str.split(',')
            if pos_info not in existing_pos_list:
                existing_pos_list.append(pos_info)
                merged_pos_str = ",".join(existing_pos_list)
                local_dict[E_root] = [replaced_stem, merged_pos_str]
        else:
            replaced = safe_replace(E_root, replacements)
            local_dict[E_root] = [replaced, pos_info]
    return local_dict

def parallel_build_pre_replacements_dict(
    E_stem_with_Part_Of_Speech_list: List[List[str]],
    replacements: List[Tuple[str, str, str]],
    num_processes: int = 4
) -> Dict[str, List[str]]:
    """
    把 E_stem_with_Part_Of_Speech_list 切成若干块并行处理，再合并。
    返回 { 词根: [ 替换后, 合并词性 ] }。
    """
    total_len = len(E_stem_with_Part_Of_Speech_list)
    if total_len == 0:
        return {}

    chunk_size = -(-total_len // num_processes)
    chunks = []
    start_index = 0
    for _ in range(num_processes):
        end_index = min(start_index + chunk_size, total_len)
        chunk = E_stem_with_Part_Of_Speech_list[start_index:end_index]
        chunks.append(chunk)
        start_index = end_index
        if start_index >= total_len:
            break

    with multiprocessing.Pool(num_processes) as pool:
        partial_dicts = pool.starmap(
            process_chunk_for_pre_replacements,
            [(chunk, replacements) for chunk in chunks]
        )

    merged_dict = {}
    for partial_d in partial_dicts:
        for E_root, val in partial_d.items():
            replaced_stem, pos_str = val
            if E_root not in merged_dict:
                merged_dict[E_root] = [replaced_stem, pos_str]
            else:
                existing_replaced_stem, existing_pos_str = merged_dict[E_root]
                existing_pos_list = existing_pos_str.split(',')
                new_pos_list = pos_str.split(',')
                pos_merged = list(set(existing_pos_list) | set(new_pos_list))
                pos_merged_str = ",".join(sorted(pos_merged))
                merged_dict[E_root] = [existing_replaced_stem, pos_merged_str]

    return merged_dict

# -------------------------------
# remove_redundant_ruby_if_identical
# -------------------------------
IDENTICAL_RUBY_PATTERN = re.compile(r'<ruby>([^<]+)<rt class="XXL_L">([^<]+)</rt></ruby>')
def remove_redundant_ruby_if_identical(text: str) -> str:
    """
    如果出现 <ruby>foo<rt class="XXL_L">foo</rt></ruby>，则去掉外层 <ruby>，只保留 foo。
    """
    def replacer(match: re.Match) -> str:
        group1 = match.group(1)
        group2 = match.group(2)
        if group1 == group2:
            return group1
        else:
            return match.group(0)
    replaced_text = IDENTICAL_RUBY_PATTERN.sub(replacer, text)
    return replaced_text

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"esp_text_replacement_module.py" から関数・定数等をインポートして、
エスペラント文の文字列(漢字)置換を実行する。
"""
# windowsでは、相対座標がうまく認識されないことがあるので、PATHの設定には注意が必要。何とかこのpythonファイルがあるディレクトリ上で実行する方法を模索する必要がある。
# Multi-processing が実行される行以降を  ""if __name__ == '__main__':"" ブロックインデント内に収め、同ブロック内にmultiprocessing.set_start_method('spawn', force=True)という設定行も追加することでうまく動作した。
# if __name__ == '__main__':
#     multiprocessing.set_start_method('spawn', force=True)

import os
import sys
import re
import json
import time
import multiprocessing
from typing import List, Tuple

# --- 1) ここがポイント: モジュールから必要な要素をインポート ---
from esp_text_replacement_module import (
    # 占位符読み込み
    import_placeholders,
    # 主要な置換ルールを実装した複合関数
    orchestrate_comprehensive_esperanto_text_replacement,
    # 行単位で並列処理するための関数
    parallel_process,
    # ルビHTML形式を出力テキストの前後に追加する関数。
    apply_ruby_html_header_and_footer
)

# --- 2) グローバル設定 (例: プロセス数やテキスト複製回数など) ---
num_processes = 8
text_repeat_times = 1
format_type = 'HTML格式_Ruby文字_大小调整'  # 例: "HTML格式_Ruby文字_大小调整"

# --- 3) JSONファイル および 占位符ファイルのパス ---
JSON_FILE = "最终的な替换用リスト(列表)(合并3个JSON文件).json"
PLACEHOLDER_SKIP_FILE = "占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"
PLACEHOLDER_LOCAL_FILE = "占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"

# --- 4) 入力テキストファイル (エスペラント文) ---
INPUT_TEXT_FILE = "例句_Esperanto文本.txt"

# --- 5) 出力先HTML ---
OUTPUT_HTML_FILE = "Esperanto_Text_Replacement_Result_Multiprocessing_windows.html"

def main():
    """
    メイン処理:
      1) JSON読み込み → 置換リスト3種を取得
      2) プレースホルダ読み込み (skip用 / localized用)
      3) 入力テキストを取得 (複製回数 text_repeat_times 回)
      4) parallel_process(...) を実行
      5) HTMLとして出力 (format_typeに応じてルビ等を付与)
    """
    # 1) JSONファイルから置換リストをロード
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        combined_3_replacements_lists = json.load(f)

    # キーごとに取得
    replacements_final_list = combined_3_replacements_lists.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    replacements_list_for_localized_string = combined_3_replacements_lists.get(
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []
    )
    replacements_list_for_2char = combined_3_replacements_lists.get(
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []
    )

    # 2) プレースホルダー (skip用 / localized用)
    placeholders_for_skipping_replacements = import_placeholders(PLACEHOLDER_SKIP_FILE)
    placeholders_for_localized_replacement = import_placeholders(PLACEHOLDER_LOCAL_FILE)

    # 3) テキスト読み込み & 繰り返し
    with open(INPUT_TEXT_FILE, "r", encoding="utf-8") as g:
        text0 = g.read() * text_repeat_times

    # 4) マルチプロセスによる文字列(漢字)置換処理を実行
    #    parallel_process(...) はモジュール内の関数。
    replaced_text = parallel_process(
        text=text0,
        num_processes=num_processes,
        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
        replacements_list_for_localized_string=replacements_list_for_localized_string,
        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
        replacements_final_list=replacements_final_list,
        replacements_list_for_2char=replacements_list_for_2char,
        format_type=format_type
    )

    # 5) 出力用HTMLの装飾 (format_type の内容によって変化)
    #    以下は元のコードを踏襲したルビ用CSSの追加例です。
    replaced_text = apply_ruby_html_header_and_footer(replaced_text, format_type)

    # 最終的にファイルへ書き出す
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as h:
        h.write(replaced_text)

    print(f"[完了] 変換結果を '{OUTPUT_HTML_FILE}' に保存しました。")


if __name__ == '__main__':
    # Windows などでマルチプロセスを正常に動かすため
    multiprocessing.set_start_method('spawn', force=True)

    main()

# Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Beta

下面是一份面向“已对本应用的 GUI 用法有一定了解、希望更深入理解其内部工作机制”的说明文档。它将从程序整体结构、各文件职责、核心逻辑流程、并行处理与占位符机制等角度做技术剖析，帮助您在阅读代码时更加透彻地把握其原理。为了便于对照代码阅读，下文将结合主要的函数和模块设计进行逐步分析。

---

# 1. 应用整体架构概述

本应用基于 **Streamlit**，包含四个主要的 `.py` 文件：
1. **`main.py`**  
   - Streamlit 主入口文件。也即实际可访问的前端交互页面（处理世界语→汉字的转换操作）。
   - 内部调用了一些底层功能函数（主要来自 `esp_text_replacement_module.py`）。
   - 处理顺序大致如下：
     1. 让用户选择替换规则 JSON；
     2. 读取与加载该 JSON；
     3. 让用户输入/上传需要被转换的世界语文本；
     4. 如果用户点击“提交”，则进行替换，最后在页面上显示、并可下载结果。

2. **`用于生成世界语文本(含汉字)替换的 JSON 文件工具.py`**  
   - Streamlit `pages/` 目录下的一个页面脚本，用于**生成**“替换规则 JSON 文件”。
   - 当用户需要定制更大规模或自定义的词根替换表时（通常要合并 CSV、用户自定义 JSON），此工具就会做大量数据处理，并最终生成 JSON 供 `main.py` 使用。
   - 底层依赖 `esp_text_replacement_module.py` 和 `esp_replacement_json_make_module.py` 中的并行处理、字符转换函数等。

3. **`esp_text_replacement_module.py`**  
   - 提供**核心替换逻辑**的功能模块，包括：  
     1. 世界语字符表记转换（`cx->ĉ`、`c^->ĉ` 等）；  
     2. `%...%` 跳过替换、`@...@` 局部替换等处理；  
     3. 分两步 `(old->placeholder->new)` 的安全替换机制；  
     4. `orchestrate_comprehensive_esperanto_text_replacement()` —— 面向主流程的一体化替换函数；  
     5. `parallel_process()` —— 并行处理大文本的方案。  

4. **`esp_replacement_json_make_module.py`**  
   - 与 `esp_text_replacement_module.py` 类似，但主要用于**生成 JSON** 时的大规模数据处理，比如：
     - 把 CSV 中的“世界语词根->汉字”合并到一个大词典内；
     - 针对二字词根(前缀/后缀)、动词活用词尾等进行优先级分配；
     - 多进程处理（借助 Python `multiprocessing`）；
     - `output_format()` 根据用户选择的“HTML/括号/仅替换”等输出形式来组装 `<ruby>` 或 `(...)` 等结构；  
     - 防止出现 `<ruby>xxx<rt>xxx</rt></ruby>` 这种多余标签，提供去重函数。

---

# 2. 核心流程分层解析

如果从**代码调用链**的角度看，该应用主要存在两条重要流程：

1. **在 `main.py` 中进行实际文本的转换**  
   - 读入 JSON 中的三种列表：
     1. `replacements_final_list`：大域替换列表；  
     2. `replacements_list_for_localized_string`：局部替换（@...@）列表；  
     3. `replacements_list_for_2char`：专门针对二字词根的替换列表。  
   - 读入占位符文件（`placeholders_for_skipping_replacements` / `placeholders_for_localized_replacement`）。  
   - 当用户点击提交：
     1. 将文本拆行（可并行）或单线程，把 `%...%`、`@...@` 等段落先行替换为占位符；  
     2. 在剩余文本中执行大域替换；  
     3. 补充二字词根的二次替换；  
     4. 还原 `%...%` 与 `@...@` 中的内容；  
     5. 如果是 HTML 格式，则插入 `<br>` 等处理；  
     6. 输出或下载最终结果。

2. **在 `用于生成世界语文本(含汉字)替换的 JSON 文件工具.py` 中生成 JSON**  
   - 先从 CSV 中读取“词根->汉字”字典，合并到一个中间结构；
   - 同时读入“词根分解自定义 JSON”（自动给特定词添加后缀等）；
   - 构造**placeholder** 替换列表（old->placeholder->new），避免交叉替换；
   - 如果勾选并行处理，利用 `multiprocessing` 加速大规模数据映射；
   - 最终得到三大列表【“全域替换”、“二字词根替换”、“局部替换”】，打包成 `.json` 文件。

## 2.1 “多进程” 与 “占位符” 在两处流程中的地位

- **多进程**：  
  1. 在 `main.py`，针对较长文本可以行级切分，将每段文本送去 `process_segment()` 执行替换，再拼接结果；  
  2. 在 `用于生成 JSON` 一侧，针对数万条词根，会分块处理以形成一个合并的预替换字典。

- **占位符(placeholder)**：  
  - 核心设计：将 `(old -> placeholder -> new)` 两步替换，能避免“old 的一部分与 new 的一部分再次发生替换冲突”。  
  - 比如，如果“cx -> ĉ”，但是 new 中可能又含有 “cx”，这样可能导致再次替换；而用 placeholder 中转可防止这种级联混乱。  
  - `%...%` 与 `@...@` 也借用了占位符机制：  
    - 先把 `%...%` 中的内容全部替换成独特的 placeholder（在全局替换时就不会被碰到）；
    - 替换完后再把 placeholder 还原回原始文本。

---

# 3. 文件级别解析

### 3.1 `main.py`

- **主要函数 / 关键段：**  
  1. `load_replacements_lists(json_path)`：  
     - 以 `@st.cache_data` 缓存方式加载 JSON，返回 `(replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char)` 三元组。  
     - `cache_data` 可以显著减少大 JSON 重复加载带来的性能损失。  

  2. 读取占位符文件：  
     - `placeholders_for_skipping_replacements` 用于 `%...%`  
     - `placeholders_for_localized_replacement` 用于 `@...@`  

  3. 用户 UI：`st.radio() / st.selectbox() / st.file_uploader()` 等 Streamlit 组件。  
  4. **并行处理**：  
     - 若勾选，调用 `parallel_process(...)`；否则调用 `orchestrate_comprehensive_esperanto_text_replacement(...)`。  
  5. “上标形式 / x 形式 / ^ 形式” 切换：  
     - 通过 `replace_esperanto_chars()` 再次做一次 `cx->ĉ` 或 `c^->ĉ` 等映射。  
  6. 最终将文本加上 `apply_ruby_html_header_and_footer()` 函数处理，比如插入 `<style>`。  

- **程序启动后**：  
  1. `st.set_page_config()` 设置标题、布局；  
  2. 程序会在浏览器形成 GUI；  
  3. 用户选择 JSON → 读取 → 输入文本 → 点击提交 → 调用替换函数 → 在页面渲染 + 提供下载。  

### 3.2 `用于生成世界语文本(含汉字)替换的 JSON 文件工具.py`

- 这是**辅助工具**，同样是个 Streamlit 页面，但放在 `pages/` 目录下：
  - `pages/` 是 streamlit 的一种多页面结构，只要在这里放 `.py` 文件就会在侧边栏多出一个可跳转页面。  

- **关键步骤**：
  1. CSV 上传或使用默认；  
  2. 选择“词根分解法 JSON”、“自定义替换后文字 JSON”（可选）；  
  3. 并行处理配置（`use_parallel`、`num_processes`）；  
  4. 点击 “生成并下载” 按钮后：  
     1. 从 `PEJVO(...)E_stem_with_Part_Of_Speech_list.json` 中加载数万单词；  
     2. 读入“世界语全部词根(约11137个)”，将每个词根初步做 `(old, new, priority)` 映射；  
     3. 用 CSV 覆盖其默认 “new” 值；  
     4. 排序后，将 old->placeholder->new 列表化；  
     5. 并行或单线程对 `E_stem_with_Part_Of_Speech_list` 做 safe_replace(…)，生成一个 `pre_replacements_dict_1`；  
     6. 基于自定义设置(动词后缀 or 特殊汉字) 进一步增补 / 修改优先级；  
     7. 整理成 `replacements_final_list`、`replacements_list_for_2char`、`replacements_list_for_localized_string` 三种；  
     8. 序列化为 JSON 并提供下载。

- **重点在于**：  
  - 这里会根据 CSV 中的词根，以及 JSON(词根分解、替换后文字)来**动态生成**大量“old->new”对；  
  - 还要处理 AN, ON, 动词词尾(as/is/us...) 等，自动给 `xxx` 拼接多个派生形；  
  - 每个派生形都带有一个优先级，用于之后做长词优先或短词优先处理。

### 3.3 `esp_text_replacement_module.py`

- 是**核心替换逻辑**的实现：

#### 3.3.1 字符转换

- `x_to_circumflex`、`hat_to_circumflex` 等字典，把 `cx->ĉ`、`c^->ĉ`、`u^->ŭ` 等。
- `replace_esperanto_chars(text, dict)`： 直接 `text.replace(old, new)` 循环。

#### 3.3.2 `%...%` 跳过机制

- 先通过正则 `PERCENT_PATTERN = re.compile(r'%(.{1,50}?)%')` 抓取 `%...%`。  
- 然后调用 `create_replacements_list_for_intact_parts(text, placeholders_for_skipping_replacements)`；把 `%xxx%` 替换成 placeholder（唯一字符串）。  
- 后续大替换时就不会再匹配 `%xxx%` 中间的文字了，最终再替换回来。

#### 3.3.3 `@...@` 局部替换

- 同理，通过正则 `AT_PATTERN = re.compile(r'@(.{1,18}?)@')`；  
- 每个匹配到的段落，也先用 placeholder 临时替换成保证不会被大替换污染；  
- 但局部替换中（`replacements_list_for_localized_string`）也会应用 `safe_replace()` 做相应映射。  
- 结束后再还原给大文本。

#### 3.3.4 大域替换 + 二字词根替换

- `replacements_final_list`：普通替换 `(old, new, placeholder)`；  
  - 先替换 old->placeholder，再 placeholder->new；  
  - 保证不会在替换过程中把“新生成的字符串”再度当成 old；  
- `replacements_list_for_2char`：专门处理 `$ar`, `$in` 等二字词根可在文本中出现两次。  
  - 这里会做两次循环，因为某些情况下第一次替换后还可能遗留下合适的场景。

#### 3.3.5 并行处理

- `parallel_process()`：
  1. 用正则 `re.findall(r'.*?\n|.+$', text)` 将文本按行切分；  
  2. 计算每个进程要处理的行数，构造 `ranges`；  
  3. 用 `multiprocessing.Pool` 的 `starmap` 调用 `process_segment()`；  
  4. 收集结果后 `''.join()` 返还给主线程。

---

### 3.4 `esp_replacement_json_make_module.py`

- 与 `esp_text_replacement_module.py` 相似，但更多关注**大规模 JSON 的合并**。
- **`output_format()`**：  
  - 根据用户选择，如 “HTML格式_Ruby文字_大小调整” 或 “括弧(号)格式_汉字替换” 等，对 `(main_text, ruby_content)` 做组装。  
  - 如果需要**自动换行**，还要测量文字宽度（`measure_text_width_Arial16()`）并在合适位置插入 `<br>`。  
- **`remove_redundant_ruby_if_identical()`**：若 `<ruby>xx<rt class="XXL_L">xx</rt></ruby>` 出现完全相同字符串，则只保留 `xx`。

---

# 4. 关键技术点详细解读

## 4.1 two-step safe_replace 机制

在字符串替换中，如果简单 `text.replace(old, new)`，有两大潜在问题：

1. **重复匹配**：例如 `cx -> ĉ`，但新生成的 `ĉ` 里，若后续还有别的规则也把 `ĉ` 替换，这就会形成意料之外的变化。  
2. **交叉覆盖**：如果 `oldA` 是 `cx`， `oldB` 是 `c`，那么先替换了 `c->xxx` 可能破坏了 `cx` 的完整性。

本应用通过 `(old->placeholder->new)`：  
- 第一次把所有 `old` 都变成唯一占位符（例如 `##PHxx102##`），这样不会与其他 `oldB` 冲突；  
- 待全部 `old->placeholder` 执行后，统一再把 placeholder->new；  
- 确保任何时刻都不会把 “new” 当成“old” 再次匹配上。

## 4.2 并行处理中的索引切分

在主流程或 JSON 生成时，都用类似思路：
- 把列表（或文本的行）切成 `num_processes` 份；  
- 用 Pool.starmap(...) 并行。  
- 处理完成后合并结果/字典。

值得留意：  
- 并行处理需要 **“spawn”** 启动方法（在 `main.py` 中显式 `multiprocessing.set_start_method("spawn")`）防止 streamlit 里出现 PicklingError。

## 4.3 大规模 JSON 生成中的派生形

在生成 JSON 时，对**一个词根**可自动附加多种派生形，例如：

- 动词语尾 (`as,is,os,us,at,it,ot,ad,ig,iĝ,ant,int,ont`)；  
- 后缀 an、on；  
- 2 字根的前缀、后缀（`$am`, `ek$` 等）；

应用中会先收集用户 CSV，“把 E_root->翻译”存到 `temporary_replacements_dict`，但后续再通过**词根分解**或**动词后缀**逻辑不断生成新的 `(old,new,priority)`。  
最终再存到  `replacements_final_list` 里，就得到海量替换条目了。

## 4.4 HTML 格式渲染与 Ruby 机制

- 如果用户选 HTML 形式，代码会把 `(main_text, ruby_content)` 生成 `<ruby>main_text<rt>ruby_content</rt></ruby>` 并在 `apply_ruby_html_header_and_footer()` 加上 `<style>` 定义。  
- `rt` 的大小或位置会根据 `ratio_1 = width_ruby / width_main` 进行精细调节。例如：  
  - 如果 ruby 部分太长，会使用 CSS `XXXS_S` 并在中途插入 `<br>` 以换行；  
  - 如果文字差不多大小，则可能仅调成 `M_M` / `L_L` 等样式。

---

# 5. 可能需要注意的实现细节

1. **`@st.cache_data`**：  
   - 对读取 JSON 功能做缓存，加快二次读写；  
   - 代码中若修改了 JSON 文件，需要清理 Streamlit 缓存或刷新，才能重新读取更新内容。

2. **空白字符统一**：  
   - `unify_halfwidth_spaces(text)` 会把 `\u00A0, \u2002...` 等非标准空格替换成 ASCII 空格；  
   - 全角空格 (`U+3000`) 不处理，保留原状。

3. **二字词根的二次替换**：  
   - 应用需要在文本中多次扫描 `$ar`, `$in` 等可能场景，所以有两轮扫描：
     1. `valid_replacements_for_2char_roots`；  
     2. `valid_replacements_for_2char_roots_2`。  
   - 避免一次替换后又能触发另一个二字根替换而遗漏。  

4. **CSV / JSON 格式约定**：  
   - CSV 需两列：第一列是世界语词根，第二列是翻译内容。  
   - JSON 要保存三大列表字段：`replacements_final_list`, `replacements_list_for_2char`, `replacements_list_for_localized_string`。  
   - 这些字段名是硬编码写在 `main.py` / `load_replacements_lists()` 中的。

---

# 6. 扩展或二次开发思路

如果您想在这套程序上进行深度定制：

1. **自定义更多占位符机制**  
   - 如果文本里出现与现有 placeholder 相同的字符串，可能会冲突。要确保 placeholder 不会自然出现在普通文本中。  
   - 可以通过自己生成足够随机、足够长的占位符来降低冲突概率。

2. **修改/增加替换顺序**  
   - 目前顺序是：  
     1. `%...%` 跳过  
     2. `@...@` 局部  
     3. 大域 (含二字词根)  
   - 如果需要增加更多自定义标签（如 `#...#`）可在 `esp_text_replacement_module.py` 类似地添加正则捕捉流程。

3. **文字大小/排版算法**  
   - `measure_text_width_Arial16()` 通过加载 JSON(`Unicode_BMP全范围文字幅(宽)_Arial16.json`)来计算像素；  
   - 如果需要支持其他字体/字号，可以另行测量或换一套宽度数据；  
   - 还可进一步自定义换行策略(不是只插 `<br>`，也可插 `<wbr>` 或用 CSS `word-wrap` 等方式)。

---

# 7. 总结

- 本应用的核心在于**安全替换**与**多层 placeholder** 以及**自动生成大规模替换规则**的机制。  
- `main.py` 作为前端主界面，只做**读取 JSON** + **文本替换** + **结果展示**；  
- `用于生成... JSON...py` 做**构建大替换表**；  
- `esp_text_replacement_module.py` / `esp_replacement_json_make_module.py` 提供各种**底层算法**：字符转换、并行、输出格式封装、placeholder 处理等。

**对中级程序员而言，最值得关注的几点**：  
1. [old->placeholder->new] 安全替换避免冲突的思路；  
2. `%...%` / `@...@` 等基于正则解析的局部替换；  
3. 二次(甚至多次)替换的执行顺序 (大域、局部、二字根)；  
4. 并行处理在 Streamlit 环境下的配置(`multiprocessing.set_start_method("spawn")`)；  
5. 通过 JSON 文件统一管理替换规则的可扩展性；  
6. 在前端(HTML格式)如何根据字符宽度/比率自动插入 `<br>` 并调整 `<rt>` 字体。

通过以上分析，相信您能在阅读代码、调试或扩展功能时，更快速地理解全局与细节。如需再次调优或添加自定义规则，重点可以在“生成 JSON 工具”页面进行深度修改。祝您在本应用的二次开发或深入学习中一切顺利!  

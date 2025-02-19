# Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese

以下是一份面向中国程序员的**深入技术说明**，主要着眼于这款由四个 Python 文件组成的 Streamlit 应用是**如何运作、如何实现**它所声称的“世界语文本 → 带汉字 / 注释标注文本”转换功能。  
请注意，这里的目标读者是对 Python 基础、Streamlit 框架、并行处理、多文件模块调用等已经有一定了解的人士。我们会针对应用的整体架构、各模块之间的依赖关系、数据处理流程、并行设计、占位符安全替换机制等进行**细节剖析**。  
（如果您对 GUI 端如何操作已经熟悉，则更能聚焦在本说明对核心代码与底层实现的讲解上。）

---

## 目录

1. [应用的整体架构总览](#应用的整体架构总览)  
2. [四个核心 Python 文件的作用与相互关系](#四个核心-python-文件的作用与相互关系)  
   1. [main.py](#mainpy)  
   2. [用于生成世界语文本(含汉字)替换的 JSON 文件工具.py](#用于生成世界语文本含汉字替换的-json-文件工具py)  
   3. [esp_text_replacement_module.py](#esp_text_replacement_modulepy)  
   4. [esp_replacement_json_make_module.py](#esp_replacement_json_make_modulepy)  
3. [替换流程的核心机制](#替换流程的核心机制)  
   1. [世界语特殊字母的统一化（cx → ĉ 等）](#世界语特殊字母的统一化cx--等)  
   2. [占位符 (Placeholder) 与安全替换 (safe_replace)](#占位符-placeholder-与安全替换-safe_replace)  
   3. [局部替换 (@...@) 与跳过替换 (%...%)](#局部替换---与跳过替换--)  
   4. [多进程并行处理 (parallel_process)](#多进程并行处理-parallel_process)  
   5. [2 字母词根与后缀、优先级处理](#2-字母词根与后缀优先级处理)  
4. [JSON 生成过程：从 CSV/自定义 JSON 到三合一 JSON 的合并思路](#json-生成过程从-csv自定义-json-到三合一-json-的合并思路)  
   1. [用户词根数据的导入与合并](#用户词根数据的导入与合并)  
   2. [优先级排序与占位符分配](#优先级排序与占位符分配)  
   3. [添加动词/名词/副词后缀逻辑](#添加动词名词副词后缀逻辑)  
   4. [最终写入 replacements_final_list / replacements_list_for_2char / replacements_list_for_localized_string](#最终写入-replacements_final_list--replacements_list_for_2char--replacements_list_for_localized_string)  
5. [关键数据结构与代码组织要点](#关键数据结构与代码组织要点)  
   1. [replacements_final_list, replacements_list_for_2char, replacements_list_for_localized_string 的结构](#replacements_final_list-replacements_list_for_2char-replacements_list_for_localized_string-的结构)  
   2. [占位符文件的组织及导入方式](#占位符文件的组织及导入方式)  
   3. [多次替换与恢复占位符的顺序约定](#多次替换与恢复占位符的顺序约定)  
6. [总结：如何在此基础上扩展或改造](#总结如何在此基础上扩展或改造)  

---

<a name="应用的整体架构总览"></a>

## 1. 应用的整体架构总览

这是一套基于 **Streamlit** 的前端 + 后端应用，目标是：

1. **对世界语文本执行注释/翻译**（添加汉字或中文释义）  
2. **生成或合并“世界语词根 → 替换后文字”规则的 JSON**，并供主程序调用  

用户在访问时，主要看到的是两个界面（两页）：

- **主页面** (`main.py`)：用于**加载**替换规则 JSON，并对**输入文本**做替换、输出结果。  
- **JSON 生成页面** (`用于生成世界语文本(含汉字)替换的 JSON 文件工具.py`)：用于将各种来源（CSV、词根分解 JSON、自定义替换 JSON 等）**合并**为一份大的 JSON。

背后有两个**辅助模块**：

- `esp_text_replacement_module.py`：集中处理世界语字符转换、局部替换、跳过替换、多进程切割处理等；  
- `esp_replacement_json_make_module.py`：在生成 JSON 过程中对词根列表做并行处理、后缀分解、优先级计算等。

整套应用运行后，**Streamlit** 会把 `main.py` 视为**首页**，把 `用于生成世界语文本(含汉字)替换的 JSON 文件工具.py` 视为**pages 子页面**。两个页面均可访问**相同**的辅助模块文件。

---

<a name="四个核心-python-文件的作用与相互关系"></a>

## 2. 四个核心 Python 文件的作用与相互关系

### 2.1. main.py

- **地位**：这是整个应用的**主页面脚本**。当我们在 Streamlit Cloud 或本地 `streamlit run main.py` 时，这个文件就是应用的入口。  
- **核心逻辑**：  
  1. 提供**选择 JSON 文件**的界面（默认 or 用户上传），并将其读入——这份 JSON 包含了 3 个列表：  
     - `replacements_final_list`（全局替换）  
     - `replacements_list_for_localized_string`（局部替换）  
     - `replacements_list_for_2char`（二字符词根替换）  
  2. 提供**文本输入**（手动 / 上传文件）、**并行处理**选项、**输出格式**（HTML/括号/仅替换）等选项。  
  3. 在用户点击“提交”后，会调用 `esp_text_replacement_module.py` 中的**核心替换流程**（`orchestrate_comprehensive_esperanto_text_replacement` 或并行版本 `parallel_process`）来对文本进行多阶段替换。  
  4. 最终渲染结果到前端：在 Streamlit 界面上**展示**转换后的文本、HTML 预览，以及**下载按钮**。

**要点**：  

- `@st.cache_data` 用于缓存默认 JSON 文件的加载，避免重复读取大文件。  
- 在替换完成后，如果输出类型含 “HTML”，会调用 `components.html()` 进行内嵌展示，或 `text_area` 进行源码展示。  
- 允许用户从下拉菜单切换**世界语字母显示形式**（上标/x/^）。

---

### 2.2. 用于生成世界语文本(含汉字)替换的 JSON 文件工具.py

- **地位**：这是放在 `streamlit/pages/` 目录中的第二个 Streamlit 页面脚本，功能是**生成或合并**“世界语→汉字替换规则 JSON”。  
- **主要逻辑**：  
  1. 读取或上传 CSV（世界语词根 - 汉字），并将其中的 cx / c^ 等统一转为 ĉ。  
  2. 可选地读取或上传**词根拆分法 JSON**、以及**自定义替换后文字 JSON**。  
  3. 决定是否使用并行处理，把世界语全部词根大列表等做拆分处理；  
  4. 经过多个步骤（先并行替换词根，再按优先级排布，最后生成三类列表）后，输出合并后的 JSON。  
  5. 在页面上提供**下载**该 JSON 的按钮。

**要点**：  

- 大规模的合并过程在内部会用到 `esp_replacement_json_make_module.py` 的函数，如 `parallel_build_pre_replacements_dict` 等。  
- 生成的 JSON 最终会包含三个 key：  
  - `全域替换用のリスト(列表)型配列(replacements_final_list)`  
  - `局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)`  
  - `二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)`  
- 这些 key 与 `main.py` 中所需的三大列表名称一一对应。

---

### 2.3. esp_text_replacement_module.py

- **地位**：这是**文本替换层**的核心模块。  
- **包含**：  
  - 用于**世界语字符转换**的字典与函数（`x_to_circumflex`, `hat_to_circumflex`, `convert_to_circumflex` 等）  
  - `%...%` 跳过替换、`@...@` 局部替换的识别正则和处理函数  
  - 占位符机制下的 `safe_replace()` 实现  
  - **综合替换函数** `orchestrate_comprehensive_esperanto_text_replacement()`：整合了**跳过替换**、**局部替换**、**全局替换**、**两字符替换**等步骤  
  - **多进程** `parallel_process()`：把文本按行数分段并行处理  

该文件基本上可以视为**纯替换逻辑**的集合——Streamlit 部分只负责收集用户输入，最后调用本模块中的核心函数进行替换并返回。

---

### 2.4. esp_replacement_json_make_module.py

- **地位**：用于**构建 JSON** 时的一些特殊操作函数集合。  
- **包含**：  
  - 与 `esp_text_replacement_module.py` 类似的世界语字符转换字典（为了独立性，部分函数有重复）  
  - `output_format(main_text, ruby_content, format_type, char_widths_dict)`：根据选定的输出格式（HTML/括号/仅汉字）去把 “(世界语, 汉字)” 拼成 `<ruby>...<rt>...</rt></ruby>` 等字符串  
  - 处理**多进程**合并词根的函数，比如 `process_chunk_for_pre_replacements()` 与 `parallel_build_pre_replacements_dict()`  
  - 用于去掉 `<ruby>xxx<rt class="XXL_L">xxx</rt></ruby>` 这种**冗余**（ruby 和 rt 内容一样）的函数 `remove_redundant_ruby_if_identical()`  
  - 在生成大规模词根替换列表时，会根据 CSV 数据、用户自定义 JSON、内置世界语词根库等做**优先级排序**、**合并**，然后分配占位符。

在“生成 JSON”页面需要调用的诸多处理函数大多定义在此文件中。

---

<a name="替换流程的核心机制"></a>

## 3. 替换流程的核心机制

从用户视角来看，输入世界语文本，点一下按钮，就能得出带汉字或注释的结果；但底层执行了多轮替换以及占位符保护。以下简要介绍最重要的几个步骤：

<a name="世界语特殊字母的统一化cx--等"></a>

### 3.1. 世界语特殊字母的统一化（cx → ĉ 等）

很多世界语用户使用 `cx`、`c^`、或直接 `ĉ` 表示相同的字母。为了**词根匹配**时不出问题，必须先**统一**这些形式。  

- 在 `esp_text_replacement_module.py` 里，`convert_to_circumflex()` 先把 `c^` 转为 `ĉ`、`cx` 转为 `ĉ`，以便后续匹配。  
- 最终输出时，若用户想要“x 形式”或“^ 形式”，则会再把这些 `ĉ` 转回 `cx`、`c^` 等。

这样做确保了数据库（JSON）和用户输入在同一“字符空间”中匹配，而不会出现 “cx == c^ == ĉ” 却无法对应的问题。

---

<a name="占位符-placeholder-与安全替换-safe_replace"></a>

### 3.2. 占位符 (Placeholder) 与安全替换 (safe_replace)

#### 为什么需要占位符？

假设我们用简单 `text.replace(old, new)` 来做替换：  

- 如果 `new` 中又出现了 `old`，可能造成意想不到的**二次替换**；  
- 或者**多个**“old” 部分重叠，或者一个替换结果会影响另一个替换。  

因此，常见做法是：  

1. **先**把所有匹配的 old 替换成一个**唯一**（或随机）的占位符（比如 `$PH12$`）  
2. **最后**再把占位符替换成 new。

这样即使 new 中包含了部分 old，也不会再被识别成要二次替换。

#### 实现细节

本项目有多个 `.txt` 文件存储了大量“占位符”，并在 JSON 生成或替换时一次性读入到 Python 里（如 `import_placeholders(filename: str)`）。  

- 在 `safe_replace(text, replacements)` 中，`replacements` 是若干 `(old, new, placeholder)` 三元组；  
- 代码先把 `old` → `placeholder`；  
- 最后再把 `placeholder` → `new`。  

如此就保证了替换的安全性和**互不干扰**。

---

<a name="局部替换---与跳过替换--"></a>

### 3.3. 局部替换 (@...@) 与跳过替换 (%...%)

- `@...@`：表明这段文本**只应用**“局部替换列表”(replacements_list_for_localized_string)，不适用全局替换。典型场景是只想让某些词在局部情境下有特殊替换，而不被全局规则覆盖。  
- `%...%`：这部分文本**跳过任何替换**，保留原样。可用来保护某些代码片段、特定标点或数字等等。  

这两者都使用相应的正则 (`AT_PATTERN`, `PERCENT_PATTERN`) 先**抓取**文本，再分别替换成占位符并在**后期**恢复。

---

<a name="多进程并行处理-parallel_process"></a>

### 3.4. 多进程并行处理 (parallel_process)

对于**较大的文本**，（特别是成百上千行的世界语文章）逐行替换可能比较耗时。为了提升性能，作者在 `esp_text_replacement_module.py` 中提供了 `parallel_process()` 函数实现多进程加速。

流程大致如下：  

1. 将输入文本按照行号分割成若干段（由 `num_processes` 决定段数）  
2. 每段使用 `multiprocessing.Pool` 去调用 `process_segment()`，后者内部会执行 `orchestrate_comprehensive_esperanto_text_replacement()` 做**局部替换 / 全局替换**等  
3. 最后再将各个段的结果**拼接**起来，返回给前端。

用户可在主页面里勾选 “使用并行处理”，并指定 `num_processes` (2~4~6)。这对纯 Python 替换能有显著提速。

---

<a name="2-字母词根与后缀优先级处理"></a>

### 3.5. 2 字母词根与后缀、优先级处理

#### 2 字母词根

如 `al`, `am`, `ar`, `du`, `ek` 等等。若用常规匹配，很容易出现它们被更长词根包含；也可能它们本身出现的位置很灵活。  
因此，系统在 JSON 里专门维护了 `replacements_list_for_2char`，进行**特殊处理**，并往往执行**两次**替换（因为可能要先替换 `$al` 再替换 `$am` 之类）。

#### 后缀 & 优先级

在“生成 JSON”的过程中，会自动给一些词根添加 `-o`, `-as`, `-a` 等世界语词性后缀，并设定不同的优先级，使更长的字符串在匹配时优先。这可避免像 “amiko” 被分成 “am” + “iko” 的尴尬；  
比如 `amiko` (5 个字母) 需要先配对占位符，再去匹配“am” (2 字母) 时才不会冲突。

---

<a name="json-生成过程从-csv自定义-json-到三合一-json-的合并思路"></a>

## 4. JSON 生成过程：从 CSV/自定义 JSON 到三合一 JSON 的合并思路

在第二个页面（即 “用于生成世界语文本(含汉字)替换的 JSON 文件工具.py”）中，对 CSV/JSON 进行合并的思路可归纳如下：

<a name="用户词根数据的导入与合并"></a>

### 4.1. 用户词根数据的导入与合并

1. 用户可能上传一个带两列的 CSV，内容大致是 `[世界语词根, 对应汉字/翻译]`。  
2. （可选）上传两个自定义 JSON：  
   - **词根分解 JSON**：如指定“这个词根要排除”，或“自动添加动词后缀 -as、-is、-os”。  
   - **自定义替换后文字 JSON**：如果想对某些词根强制替换为某种特殊形式。  
3. 系统还会读取**内置**的世界语大词典列表（数万词），和已有的 placeholders 文件。  

这些数据将被合并到一个大的 Python 字典或列表中，并依次做**覆盖**或**清洗**操作：

- CSV 中的同一词根会覆盖默认内置的处理；
- 词根分解 JSON 里指定了“不要替换”或“只加动词后缀”，则会进一步修改结果；
- 自定义替换后文字 JSON 里若指定了具体形式，也会在后期写入。

---

<a name="优先级排序与占位符分配"></a>

### 4.2. 优先级排序与占位符分配

在合并完后，会得到一个字典 `{词根: [替换后文本, 优先级]}` 之类。  

- 通常 `优先级 = len(词根) * 10000 + (某些额外值)`，越长的词根越先被匹配。  
- 排序完后，会**从大到小**生成 (old, new, placeholder) 三元组，比如 `[("amikon", "<ruby>...xxx</ruby>", "%PH_001%"), ...]`。  

因为**替换列表**是有顺序的——先把长串替换，然后再替换更短的，才能避免冲突。

---

<a name="添加动词名词副词后缀逻辑"></a>

### 4.3. 添加动词/名词/副词后缀逻辑

在合并时，如果检测到某些词是**动词**（从 CSV 或内置词典里的 POS 标记可知），就会自动添加 `-as`, `-is`, `-os`, `-us`；对于名词则添加 `-o, -oj, -on` 等，副词 `-e`，形容词 `-a, -an, -aj` 等。这些全部通过**字符串拼接** + **safe_replace**。  
如此可以一次性生成包含后缀的替换映射，而无需用户在世界语文本里写完后缀再额外配置。

---

<a name="最终写入-replacements_final_list--replacements_list_for_2char--replacements_list_for_localized_string"></a>

### 4.4. 最终写入 replacements_final_list / replacements_list_for_2char / replacements_list_for_localized_string

- `replacements_final_list`：主力的**全局替换**。  
- `replacements_list_for_2char`：专门为两字符词根 / 前后缀准备。  
- `replacements_list_for_localized_string`：局部替换；在 `@...@` 中才会用。  

生成完这三大列表后，就写到 JSON 里并让用户**下载**。随后 `main.py` 加载时只要按需解读这个 JSON，就能完成所有替换。

---

<a name="关键数据结构与代码组织要点"></a>

## 5. 关键数据结构与代码组织要点

<a name="replacements_final_list-replacements_list_for_2char-replacements_list_for_localized_string-的结构"></a>

### 5.1. replacements_final_list, replacements_list_for_2char, replacements_list_for_localized_string 的结构

在多个地方都可见，这类列表通常由三元组 `(old, new, placeholder)` 组成。例如：

```python
replacements_final_list = [
  ("amikon", "<ruby>amikon<rt>朋友</rt></ruby>", "#placeholder129#"),
  ("amiko", "<ruby>amiko<rt>朋友</rt></ruby>", "#placeholder130#"),
  ...
]
```

这意味着：  

1. 先 `old -> placeholder`  
2. 再 `placeholder -> new`  

**区别**：

- `replacements_final_list`：几乎涵盖全部常见词根+后缀；  
- `replacements_list_for_2char`：只针对 `$al`, `$am`, 前后缀 `$aj`, `$is` 等二字符场景；  
- `replacements_list_for_localized_string`：仅在局部替换时使用（比如 `@...@` 里面）。

---

<a name="占位符文件的组织及导入方式"></a>

### 5.2. 占位符文件的组织及导入方式

在 `./Appの运行に使用する各类文件/` 中，通常放置好若干 `.txt`，每行一个占位符（可能有上千行）：

```
$13246$Placeholder
$13247$Placeholder
...
```

然后在代码里用 `import_placeholders()` 读取成 Python 列表，以备后续构建替换列表。  
**好处**：保证每个替换 `old` 都能分配到一个**独一无二**的 placeholder，且不易与用户文本冲突。

---

<a name="多次替换与恢复占位符的顺序约定"></a>

### 5.3. 多次替换与恢复占位符的顺序约定

在 `orchestrate_comprehensive_esperanto_text_replacement()` 中，可以看到多次替换的**顺序**：

1. 先处理 `%...%`，把这些内容替换成**特殊**占位符，以“跳过替换”  
2. 再处理 `@...@`，把这些内容提取出来，用**局部**替换列表做一次 `safe_replace`，然后也替换成占位符  
3. 接下来对剩余文本做**全局替换**（`replacements_final_list`），然后**二字符替换**（`replacements_list_for_2char`）有时还要做两轮  
4. 最后**反向**恢复所有占位符（先恢复二字符占位符，再恢复全局占位符，再恢复局部占位符，再恢复跳过替换的部分），顺序**必**须与替换时相反。

如果顺序不对或少做一步恢复，就会导致最终文本残留 placeholder 乱码。

---

<a name="总结如何在此基础上扩展或改造"></a>

## 6. 总结：如何在此基础上扩展或改造

对于想要**加深理解或自行改造**的中级程序员而言，这套应用具有以下可拓展思路：

1. **精简或替换占位符机制**：如果你打算在更大的文本集上做替换，但想减少内存占用或 CPU 开销，可考虑修改 `safe_replace` 逻辑，或使用更高效的**流式处理**（不过需额外处理并行带来的复杂性）。

2. **替换阶段拆分**：目前“局部替换 → 全局替换 → 两字符替换 → 恢复”都在一个函数 `orchestrate_comprehensive_esperanto_text_replacement()` 里完成；可以把它拆分成**更细**的函数层级，针对不同需求插入额外规则。

3. **增加新的标记符**：除了 `%...%`、`@...@`，如果你需要更多条件的局部替换（比如 `[...#X]` 表示只在特定上下文做替换），可以仿照 `%...% / @...@` 的模式去实现类似逻辑——编写匹配正则、导入 placeholder 等。

4. **自定义后缀或词根拆分**：如果你对动词后缀（`-as`, `-is` 等）有别的划分，或想在 JSON 生成时按自己的词库处理，可以修改 `esp_replacement_json_make_module.py` 里的 `verb_suffix_2l`、`AN`, `ON` 等处理段落，让它支持**更多**或**更灵活**的拆分。

5. **前端布局微调**：目前 Streamlit 界面的布局比较直接，若你想要**更精细的 UI/UX**，可把提交按钮、上传组件等分别放在 `st.tabs()` 或 `st.sidebar` 等位置。  
   
   - 同时需要注意 Streamlit 的**状态回传**特性（`st.session_state`）以确保表单跨控件同步。

6. **国际化/多语言**：如果你需要支持**不仅仅是汉字**，比如将世界语注释成法语、英语等，其实只要把 CSV 换成“世界语词根→另一种文字/注释”，然后生成 JSON 即可无缝替换。核心流程并不会改变。

---

### 结语

通过阅读以上分析，您应该更能**深入理解**该应用在技术层面的设计：  

- 如何用多进程加速、  
- 如何使用占位符避免重叠替换、  
- 如何对世界语词根进行后缀拆分和优先级排序、  
- 如何在主页面和 JSON 生成页面里分别管理替换和数据合并。  

对于中国的中级 Python/Streamlit 程序员，如果再结合实际场景需求，做一些**配置**或**改造**，就能让这套世界语文本处理工具更贴合个人或团队的业务逻辑。  

希望本说明对您有所帮助，祝编程愉快、拓展顺利。

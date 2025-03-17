# 世界语汉字转换应用技术实现详解

## 目录
1. 应用架构概述
2. 核心模块分析
3. 数据流程与处理逻辑
4. 关键算法实现
5. 性能优化策略
6. 扩展与定制方法
7. 技术实现要点总结

## 1. 应用架构概述

本应用是基于Streamlit构建的世界语(Esperanto)文本处理系统，由四个核心Python文件组成：

- **main.py**：应用的主入口，实现GUI界面和主要流程控制
- **用于生成世界语文本(含汉字)替换的 JSON 文件工具.py**：专用于生成替换规则的JSON配置工具
- **esp_text_replacement_module.py**：文本替换核心功能模块
- **esp_replacement_json_make_module.py**：JSON生成支持模块

### 1.1 应用架构图

```
                   ┌─────────────────────┐
                   │      main.py        │
                   │  (应用主入口/GUI)    │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │esp_text_replacement_│
                   │     module.py       │
                   │  (文本替换核心模块)  │
                   └──────────┬──────────┘
                              │
┌────────────────────┐  ┌─────▼───────────────────┐
│用于生成世界语文本(含│  │esp_replacement_json_make│
│汉字)替换的JSON文件工│◄─┤      _module.py        │
│具.py (JSON生成工具) │  │ (JSON生成支持模块)      │
└────────────────────┘  └─────────────────────────┘
```

### 1.2 技术栈

- **前端**：Streamlit (Python Web应用框架)
- **后端**：Python 3.x
- **并行处理**：multiprocessing库
- **数据处理**：pandas, json
- **文本处理**：正则表达式(re)

## 2. 核心模块分析

### 2.1 main.py

main.py是整个应用的入口点，实现了以下功能：

```python
# 主要组件结构
1. 导入依赖库和自定义模块
2. 定义缓存函数load_replacements_lists加载JSON
3. 设置页面基本信息
4. 实现JSON选择逻辑(默认/上传)
5. 读取placeholder文件(用于安全替换)
6. 配置并行处理选项
7. 选择输出格式
8. 选择输入文本来源(手动/文件)
9. 创建文本输入表单及处理逻辑
10. 处理并展示结果
```

关键技术点：
- 使用`@st.cache_data`装饰器缓存JSON加载结果，提高性能
- 利用`multiprocessing.set_start_method("spawn")`确保跨平台兼容性
- 采用表单(st.form)收集用户输入，实现批处理
- 实现多种显示方式(HTML预览/源码/纯文本)的标签页(tabs)切换

### 2.2 esp_text_replacement_module.py

这是文本替换的核心模块，实现世界语字符转换和替换逻辑：

```python
# 模块主要组件
1. 世界语字符转换字典(x_to_circumflex等)
2. 字符转换基础函数(replace_esperanto_chars等)
3. 占位符(placeholder)处理函数
4. %...%(跳过替换)和@...@(局部替换)的处理逻辑
5. 核心替换函数orchestrate_comprehensive_esperanto_text_replacement
6. 并行处理相关函数(parallel_process, process_segment)
7. HTML样式应用函数(apply_ruby_html_header_and_footer)
```

核心算法：
- **安全替换算法(safe_replace)**：使用占位符进行两阶段替换，避免替换冲突
- **综合替换流程**：按照特定顺序执行多种替换，确保正确处理边缘情况
- **并行处理**：将长文本分割处理，提高性能

### 2.3 用于生成世界语文本(含汉字)替换的 JSON 文件工具.py

此模块是一个独立的Streamlit应用，专门用于生成替换规则JSON：

```python
# 主要组件结构
1. 导入依赖和自定义模块
2. 定义词缀(动词后缀、AN/ON特殊后缀等)相关变量
3. 加载placeholder和文字宽度数据
4. 设置Streamlit界面
5. 提供示例文件下载功能
6. 实现输出格式选择
7. CSV文件选择与加载
8. JSON文件(词根分解法/自定义替换)选择与加载
9. 并行处理配置
10. JSON生成与下载功能
```

技术要点：
- 利用多阶段处理构建替换规则
- 复杂的优先级调整逻辑
- 对AN、ON等特殊后缀的单独处理
- 自定义词根分解JSON的应用

### 2.4 esp_replacement_json_make_module.py

支持JSON生成工具的辅助模块：

```python
# 主要组件
1. 世界语字符转换相关字典和函数
2. 文字宽度测量与<br>插入函数
3. output_format格式化函数
4. 辅助函数(contains_digit等)
5. capitalize_ruby_and_rt处理函数
6. 并行处理相关函数
7. HTML处理函数(remove_redundant_ruby_if_identical)
```

关键技术：
- **文字宽度测量**：基于预加载的字符宽度计算文本宽度
- **Ruby格式化**：根据文本宽度比例自动调整样式
- **并行数据处理**：加速大规模替换表构建

## 3. 数据流程与处理逻辑

### 3.1 主程序(main.py)数据流

```
1. 加载替换规则JSON文件 
   ↓
2. 读取placeholder文件
   ↓
3. 用户选择参数和输入文本
   ↓
4. 根据是否选择并行处理:
   ↓                   ↓
5a. 直接调用文本替换   5b. 启动并行处理
   ↓                   ↓
6. 应用字母形式转换(x, ^, 上标等)
   ↓
7. 应用HTML头尾(如果选择HTML格式)
   ↓
8. 输出结果展示和下载
```

### 3.2 JSON生成工具数据流

```
1. 读取CSV文件(世界语词根→汉字/中文)
   ↓
2. 读取世界语全部词根和词性信息
   ↓
3. 用CSV数据覆盖临时字典
   ↓
4. 构建安全替换列表(old→placeholder→new)
   ↓
5. 批量处理E_stem_with_Part_Of_Speech_list
   ↓
6. 优先级调整和后缀处理
   ↓
7. 应用自定义词根分解JSON
   ↓
8. 应用"自定义替换后文字"JSON
   ↓
9. 添加大写/首字母大写版本
   ↓
10. 生成三种列表并保存到JSON
```

### 3.3 文本替换核心流程

```
1. 统一半角空格
   ↓
2. 转换世界语特殊字符(c^, cx → ĉ等)
   ↓
3. 处理%...%(跳过替换)段落
   ↓
4. 处理@...@(局部替换)段落
   ↓
5. 执行全局替换(replacements_final_list)
   ↓
6. 执行两次2字词根替换(replacements_list_for_2char)
   ↓
7. 恢复placeholder
   ↓
8. 根据输出格式处理HTML或其他格式要求
```

## 4. 关键算法实现

### 4.1 安全替换算法(safe_replace)

```python
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """
    执行安全替换：先将原文中所有old替换为placeholder，
    然后再将placeholder替换为new，避免替换冲突
    """
    valid_replacements = {}
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text
```

这个算法的关键在于：
1. 使用两阶段替换避免替换冲突和交叉替换问题
2. 仅处理实际存在于文本中的替换项，提高效率
3. 通过字典保存有效替换项，减少循环次数

### 4.2 并行文本处理算法

```python
def parallel_process(text: str, num_processes: int, ...其他参数...) -> str:
    # 按行拆分文本
    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)
    
    # 计算每个进程处理的行数，并分配范围
    lines_per_process = max(num_lines // num_processes, 1)
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) 
              for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)  # 调整最后一个范围
    
    # 启动进程池并行处理
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(
            process_segment,
            [
                (lines[start:end], ...其他参数...) 
                for (start, end) in ranges
            ]
        )
    
    # 合并结果
    return ''.join(results)
```

算法特点：
1. 按行分割文本，确保处理边界正确
2. 动态计算每个进程的工作负载
3. 使用multiprocessing.Pool管理进程
4. 通过starmap传递多个参数
5. 使用join合并最终结果

### 4.3 Ruby文字大小调整算法

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    if format_type == 'HTML格式_Ruby文字_大小调整':
        width_ruby = measure_text_width_Arial16(ruby_content, char_widths_dict)
        width_main = measure_text_width_Arial16(main_text, char_widths_dict)
        ratio_1 = width_ruby / width_main
        
        if ratio_1 > 6:
            # 当注释文字特别长时，插入多个换行符并使用最小字体
            return f'<ruby>{main_text}<rt class="XXXS_S">{insert_br_at_third_width(ruby_content, char_widths_dict)}</rt></ruby>'
        elif ratio_1 > (9/3):
            # 较长注释，插入一个换行，使用较小字体
            return f'<ruby>{main_text}<rt class="XXS_S">{insert_br_at_half_width(ruby_content, char_widths_dict)}</rt></ruby>'
        elif ratio_1 > (9/4):
            return f'<ruby>{main_text}<rt class="XS_S">{ruby_content}</rt></ruby>'
        
        # 以下省略其他字体大小选择分支...
```

算法核心：
1. 计算注释文本与主文本的宽度比例
2. 根据比例选择适当的CSS类(控制字体大小)
3. 对特别长的注释自动插入换行，提高可读性
4. 使用文字宽度字典获取精确的像素宽度

### 4.4 处理特殊标记的算法

```python
# %...% 跳过替换的处理
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    matches = []
    used_indices = set()
    for match in PERCENT_PATTERN.finditer(text):
        start, end = match.span()
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

# @...@ 局部替换的处理
def create_replacements_list_for_localized_replacement(
    text, placeholders: List[str], 
    replacements_list_for_localized_string: List[Tuple[str, str, str]]
) -> List[List[str]]:
    matches = find_at_enclosed_strings_for_localized_replacement(text)
    tmp_replacements_list_for_localized_string = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replaced_match = safe_replace(match, replacements_list_for_localized_string)
            tmp_replacements_list_for_localized_string.append(
                [f"@{match}@", placeholders[i], replaced_match]
            )
        else:
            break
    return tmp_replacements_list_for_localized_string
```

算法特点：
1. 使用正则表达式高效寻找标记文本
2. 使用set跟踪已处理索引，避免重复处理
3. 针对@...@局部替换，先提取内容，再应用局部替换规则
4. 为每个匹配项分配唯一placeholder

## 5. 性能优化策略

### 5.1 数据缓存

```python
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    缓存JSON文件的读取结果，避免重复读取
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    replacements_final_list = data.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    # 其他代码...
```

优化点：
- 使用Streamlit的缓存机制减少重复读取
- 针对大型JSON文件(约50MB)有明显性能提升
- 加载时间从约1.0秒减少到0.5秒

### 5.2 并行处理

应用两处采用了并行处理：

1. **文本替换**：
```python
if use_parallel:
    processed_text = parallel_process(
        text=text0,
        num_processes=num_processes,
        # 其他参数...
    )
else:
    processed_text = orchestrate_comprehensive_esperanto_text_replacement(
        text=text0,
        # 其他参数...
    )
```

2. **JSON生成**：
```python
if use_parallel:
    pre_replacements_dict_1 = parallel_build_pre_replacements_dict(
        E_stem_with_Part_Of_Speech_list,
        temporary_replacements_list_final,
        num_processes
    )
else:
    # 手动循环处理，显示进度条...
```

优化效果：
- 对大型文本或大规模替换规则构建，性能提升明显
- 利用多核CPU资源，减少处理时间
- 动态分配工作负载，提高资源利用率

### 5.3 按需替换

```python
valid_replacements = {}
for old, new, placeholder in replacements_final_list:
    if old in text:  # 只处理确实存在的替换项
        text = text.replace(old, placeholder)
        valid_replacements[placeholder] = new
```

优化点：
- 只对文本中实际存在的模式执行替换
- 减少不必要的字符串操作
- 使用字典缓存有效替换项

### 5.4 排序优化

```python
# 根据长度优先级排序，确保长词根先被替换
temporary_replacements_list_2 = sorted(
    temporary_replacements_list_1, 
    key=lambda x: x[2], 
    reverse=True
)
```

优化要点：
- 确保长词根优先替换，避免子字符串替换问题
- 根据优先级排序，处理特殊情况
- 按合理策略排序，提高替换准确性

## 6. 扩展与定制方法

### 6.1 替换规则定制

通过修改CSV文件和JSON配置，可以定制替换规则：

1. **基本词根替换**：在CSV中添加`[世界语词根, 汉字/含义]`对应关系
2. **词根分解定制**：在词根分解JSON中设置：
   ```json
   [
     "esperant",  // 世界语词根
     "dflt",      // 优先级设置("dflt"使用默认，或自定义数值)
     ["verbo_s1"] // 特殊处理标记："verbo_s1"自动添加动词词尾等
   ]
   ```
3. **汉字替换定制**：在替换后文字JSON中设置：
   ```json
   [
     "esper/ant",  // 带斜杠的世界语词根(表示分解)
     "dflt",       // 优先级
     ["ne"],       // 特殊处理标记
     "希望/者"      // 带斜杠的汉字(对应词根分解)
   ]
   ```

### 6.2 输出格式扩展

系统支持多种输出格式，可通过修改以下函数扩展更多格式：

```python
def output_format(main_text, ruby_content, format_type, char_widths_dict):
    # 现有格式处理...
    
    # 扩展新格式示例:
    elif format_type == '自定义格式':
        return f'<custom>{main_text}<note>{ruby_content}</note></custom>'
```

### 6.3 字符转换扩展

添加新的字符转换规则：

```python
# 添加新的转换字典
my_custom_conversion = {'aa': 'ā', 'ee': 'ē', 'ii': 'ī'}

# 在convert_to_circumflex函数之后添加自定义转换
def convert_with_custom_rules(text: str) -> str:
    text = convert_to_circumflex(text)
    text = replace_esperanto_chars(text, my_custom_conversion)
    return text
```

## 7. 技术实现要点总结

1. **安全替换机制**
   - 使用占位符进行两阶段替换，避免替换冲突
   - 通过优先级排序解决子串替换问题

2. **模块化设计**
   - 功能明确分离为多个模块
   - 核心替换逻辑与界面层分离，便于维护

3. **性能优化**
   - 数据缓存减少重复加载
   - 并行处理提高大文本处理性能
   - 按需替换减少不必要操作

4. **可扩展性**
   - 支持多种输出格式
   - 通过外部配置文件定制替换规则
   - 基础功能模块化，便于扩展

5. **健壮性处理**
   - 安全处理特殊标记(%...%和@...@)
   - 错误处理和中断机制
   - 大小写及首字母大写的正确处理

6. **Streamlit界面优化**
   - 使用表单收集批量用户输入
   - 通过expander和tabs优化界面
   - 提供进度反馈和状态提示

本应用展示了如何构建一个高效的文本处理系统，结合了并行计算、动态调整和用户友好界面，为世界语文本的汉字化处理提供了灵活而强大的解决方案。
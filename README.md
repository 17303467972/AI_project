# 🎬 AI 小说转剧本工具

将 **3 章以上**的小说文本自动转换为**结构化 YAML 剧本**，让作者快速获得可编辑、可打磨的剧本初稿。

---

## 功能特性

- 📖 **智能章节解析**：支持多种章节标记格式（"第X章"、"Chapter X"、数字序号等）
- 🤖 **双模式转换**：
  - **规则模式**：基于启发式规则，快速生成初稿（无需 API）
  - **AI 模式**：调用大语言模型，进行智能角色识别和场景重构
- 📐 **标准化 YAML Schema**：严格的层级结构（幕→场景→节拍），可机器解析、人类可读
- 🔍 **可追溯**：每个场景/节拍可追溯到原文章节段落
- ✅ **自动校验**：检测角色引用完整性、结构完整性
- 📊 **统计报告**：场景数、节拍数、角色台词分布等

---

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 基本用法

```bash
# 规则模式（快速，无需 API Key）
python main.py samples/sample_novel.txt -o output/screenplay.yaml

# 同时打印输出
python main.py samples/sample_novel.txt -o output/screenplay.yaml --print

# 仅查看统计
python main.py samples/sample_novel.txt --stats
```

### AI 模式（需要 DeepSeek API Key）

```bash
# 使用 API Key
python main.py samples/sample_novel.txt --mode ai --api-key sk-your-deepseek-key

# 或设置环境变量
set DEEPSEEK_API_KEY=sk-your-deepseek-key
python main.py samples/sample_novel.txt --mode ai
```

### 验证已有剧本

```bash
python main.py --validate output/screenplay.yaml
```

---

## 输入格式要求

输入的小说文本文件需满足：

1. **至少 3 章**（工具要求的最低章节数）
2. 章节使用明确标记，支持格式：
   - `第一章 xxx` / `第1章 xxx`
   - `Chapter 1 xxx`
   - `1. xxx` / `#1 xxx`
3. UTF-8 编码的纯文本文件

---

## 输出示例

生成的 YAML 剧本结构如下：

```yaml
screenplay:
  title: '《剑影江湖》剧本'
  original_work: '剑影江湖'
  original_chapter_count: 3
  metadata:
    genre: ['武侠', '剧情']
    tone: '紧张'
  characters:
    - id: 'CHAR_001'
      name: '凌云'
      role: 'protagonist'
      description: '北剑山庄遗孤，武功高强的年轻剑客'
  acts:
    - act_number: 1
      title: '建置'
      scenes:
        - scene_number: 1
          location: '洛水镇茶馆'
          location_type: 'INT'
          time: 'morning'
          beats:
            - beat_number: 1
              type: 'dialogue'
              character: 'CHAR_001'
              content: '来一壶龙井，两个馒头。'
```

---

## 项目结构

```
NovelToScreenplay/
├── main.py                  # 主入口（命令行界面）
├── SCHEMA.md                # YAML Schema 设计文档（含设计原因）
├── requirements.txt         # Python 依赖
├── README.md                # 本文件
├── src/
│   ├── __init__.py
│   ├── schema.py            # 剧本 Schema 定义、校验、序列化
│   ├── parser.py            # 小说文本解析（章节切分、对话提取）
│   └── converter.py         # 转换引擎（规则模式 + AI 模式）
├── samples/
│   └── sample_novel.txt     # 示例小说（3章武侠）
└── output/                  # 输出目录
```

---

## YAML Schema 文档

详细的 Schema 定义及设计原因请参阅 [SCHEMA.md](SCHEMA.md)

核心设计理念：

- **层级原则**：剧本 → 幕 → 场景 → 节拍
- **分离原则**：内容与元数据分离
- **可追溯原则**：每个节拍可追溯到原文章节段落
- **最小化原则**：非必要不添加字段

---

## 进阶用法

### 作为 Python 库使用

```python
from src.parser import NovelParser
from src.converter import RuleBasedConverter

# 解析小说
novel = NovelParser.parse("my_novel.txt")

# 转换
converter = RuleBasedConverter()
screenplay = converter.convert(novel)

# 校验
issues = screenplay.validate()

# 统计
stats = screenplay.get_statistics()
print(f"场景数: {stats['scenes']}, 节拍数: {stats['beats']}")

# 保存
screenplay.save("output/my_screenplay.yaml")
```

### 自定义 AI 端点

默认使用 DeepSeek API，也支持任何 OpenAI 兼容 API：

```bash
python main.py novel.txt --mode ai \
  --api-base https://api.deepseek.com/v1 \
  --api-key your-key \
  --model deepseek-chat
```

---

## 许可

MIT License

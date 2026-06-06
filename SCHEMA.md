# 剧本 YAML Schema 设计文档

> **AI 小说转剧本工具** — 结构化剧本数据交换格式规范 v1.0

---

## 目录

1. [概述](#1-概述)
2. [设计原则](#2-设计原则)
3. [完整 Schema 定义](#3-完整-schema-定义)
4. [字段详解与设计原因](#4-字段详解与设计原因)
5. [完整示例](#5-完整示例)
6. [扩展性考虑](#6-扩展性考虑)
7. [与行业标准的关系](#7-与行业标准的关系)

---

## 1. 概述

### 1.1 背景

在影视工业化流程中，剧本是最核心的交付物。传统剧本以 PDF/FDX（Final Draft）或纯文本格式流转，这些格式虽然适合人类阅读，但对程序化处理极不友好。当我们需要：

- 用 AI 自动生成或改编剧本
- 对剧本进行版本管理（Git diff）
- 做统计分析（角色台词量、场景分布）
- 与其他系统（分镜、拍摄计划、预算）对接
- 支持多人协作编辑

……时，纯文本或 PDF 格式的局限性就暴露无遗。

**YAML** 是一种人类可读、机器可解析的数据序列化格式。选择 YAML 作为剧本的交换格式，兼顾了"人类可编辑"和"程序可处理"两个核心需求。

### 1.2 设计目标

| 目标           | 描述                                             |
| -------------- | ------------------------------------------------ |
| **人类友好**   | 作者可以直接用文本编辑器打开 YAML 阅读和修改剧本 |
| **机器可解析** | 程序可以精确地读取、修改、校验每个字段           |
| **版本可控**   | 结构化文本天然适合 Git diff，支持分支协作        |
| **层级清晰**   | 剧本的层级关系（幕→场景→节拍）在缩进中一目了然   |
| **可追溯**     | 每个节拍可追溯到来源章节和段落，便于验证改编质量 |
| **可扩展**     | 支持自定义元数据，不影响核心结构                 |

---

## 2. 设计原则

### 2.1 层级原则：从宏观到微观

剧本有天然的层级结构，我们的 Schema 严格遵循这一层级：

```
Screenplay (剧本)
  └─ Act (幕)
      └─ Scene (场景)
          └─ Beat (节拍)
```

**设计原因**：这种层级结构不仅符合编剧的创作思维（先有大纲、再分幕、再写场景、最后打磨节拍），也与影视制作流程对齐（导演看幕结构、制片看场景数、演员看节拍中的对白）。

每一层都有明确的职责边界：

- **幕**：承担戏剧结构功能（建置/对抗/结局）
- **场景**：定义时空统一性（何时、何地、何人）
- **节拍**：承载最小叙事单元（一句对白、一个动作）

### 2.2 分离原则：内容与元数据分离

Schema 区分两类信息：

- **核心叙事内容**：幕、场景、节拍（这是剧本的"正文"）
- **元数据**：角色库、改编备注、统计信息（这是剧本的"附录"）

**设计原因**：

1. 角色定义（characters）独立于场景中的"出场列表"，避免冗余，也方便统一修改角色信息
2. 改编备注独立存储，不影响剧本正文的纯净性
3. 元数据可以独立维护和版本管理

### 2.3 可追溯原则

每个 Scene 和 Beat 都带有 `source_chapter` 和 `source_paragraph` 字段：

```yaml
beat_number: 12
type: dialogue
character: CHAR_001
content: '光天化日之下，纵马行凶，你们的胆子不小。'
source_chapter: 1 # 来自第 1 章
source_paragraph: 15 # 来自第 15 段
```

**设计原因**：

- AI 改编时可能合并、拆分、重排原文内容，追溯字段确保每个改编决策可验证
- 作者可以快速定位到原文，对比改编前后的差异
- 便于质量审核：审核者可以逐条检查 AI 的改编是否忠实于原作

### 2.4 最小化原则

每个字段都遵循"非必要不添加"原则：

- 只有对剧本创作或后续流程有实际意义的字段才会被纳入
- 可选字段（Optional）与必填字段严格区分
- 所有枚举值尽可能收窄，减少歧义

---

## 3. 完整 Schema 定义

### 3.1 顶层结构

```yaml
screenplay:
  title: string # 必填，剧本标题
  original_work: string # 原著名称
  original_author: string # 原著作者
  adapted_by: string # 改编者
  version: string # 版本号（语义化版本）
  created_date: date # 创建日期 (YYYY-MM-DD)
  original_chapter_count: int # 原著章节数

  metadata: Metadata # 剧本元数据
  characters: [Character] # 角色列表
  acts: [Act] # 幕列表
  adaptation_notes: [AdaptationNote] # 改编备注
  unresolved_issues: [string] # 待解决问题
```

### 3.2 Metadata（元数据）

```yaml
metadata:
  genre: [string] # 类型标签，如 ["武侠", "剧情"]
  tone: string # 整体基调，如 "沉重"、"轻松"、"紧张"
  target_audience: string # 目标观众，如 "全年龄"、"成人"
  estimated_duration: string # 预估时长，如 "60-90 分钟"
  content_warnings: [string] # 内容警告，如 ["暴力", "血腥"]
  keywords: [string] # 关键词/标签
```

### 3.3 Character（角色）

```yaml
characters:
  - id: string # 必填，唯一标识，如 "CHAR_001"
    name: string # 必填，角色姓名
    role:
      enum # 必填，角色类型
      #   protagonist | antagonist | supporting | minor | cameo
    aliases: [string] # 别名/昵称列表
    description: string # 角色描述
    traits: [string] # 性格特征
    background: string # 可选，背景故事
    motivation: string # 可选，角色动机
    arc: string # 可选，角色弧线描述
    relationships: # 可选，角色关系列表
      - target_id: string #   关系对象 ID
        relation: string #   关系类型（如 "父子"、"仇敌"）
        description: string #   关系详述
    first_appearance_scene: int # 可选，首次出场场景号
    last_appearance_scene: int # 可选，末次出场场景号
```

### 3.4 Act（幕）

```yaml
acts:
  - act_number: int # 必填，幕序号（从 1 开始）
    title: string # 幕标题
    description: string # 幕概述
    dramatic_function: string # 可选，戏剧功能
    scenes: [Scene] # 场景列表
```

### 3.5 Scene（场景）

```yaml
scenes:
  - scene_number: int           # 必填，场景序号（全局递增）
    location: string            # 地点名称，如 "洛水镇茶馆"
    location_type: enum         # 地点类型: INT | EXT | INT/EXT
    time: string                # 时间，如 "morning", "night"
    setting_description: string # 环境描述
    characters_present: [string]# 出场角色 ID 列表
    summary: string             # 可选，场景摘要
    page_estimate: float        # 可选，预估页数
    source_chapter: int         # 可选，来源章节号
    beats: [Beat]               # 节拍列表
```

### 3.6 Beat（节拍）— 最小叙事单元

```yaml
beats:
  - beat_number: int # 必填，节拍序号（场景内递增）
    type:
      enum # 必填，节拍类型:
      #   action       - 动作描写
      #   dialogue     - 对白
      #   monologue    - 独白
      #   voiceover    - 画外音 (V.O.)
      #   transition   - 转场
      #   description  - 场景/环境描述
      #   parenthetical - 括号动作指示
      #   sound        - 音效提示
    character: string # 可选，关联角色 ID（dialogue/monologue 时必填）
    content: string # 必填，内容文本
    parenthetical: string # 可选，括号指示，如 "(冷笑)"
    emotion: string # 可选，情感标注
    duration_seconds: int # 可选，预估时长（秒）
    notes: string # 可选，备注
    source_chapter: int # 可选，来源章节
    source_paragraph: int # 可选，来源段落
```

### 3.7 AdaptationNote（改编备注）

```yaml
adaptation_notes:
  - chapter: int # 对应原著章节
    type:
      enum # 改编类型:
      #   cut       - 删减
      #   merged    - 合并
      #   expanded  - 扩展
      #   reordered - 重排
      #   invented  - 原创新增
    description: string # 改编说明
    rationale: string # 可选，改编理由
```

---

## 4. 字段详解与设计原因

### 4.1 为什么选择 Beat（节拍）作为最小单元？

在编剧理论中，"Beat"（节拍/比特）是剧本中最小的戏剧动作单元。这个概念源自斯坦尼斯拉夫斯基体系，后来被好莱坞编剧广泛采用。

**我们选择 Beat 而非"行"或"句子"的原因：**

1. **语义完整性**：一个 Beat 是一个完整的戏剧动作，可能是"张三推门进来"（action）或"李四说：我恨你"（dialogue）。它比句子大，比段落小，是编剧创作时的"原子单元"。

2. **跨格式兼容**：
   - 电影剧本中，一个 action beat 对应一个描写段落
   - 电视剧本中，一个 dialogue beat 就是一句台词
   - 舞台剧本中，一个 beat 可能包含括号动作指示

3. **便于统计和规划**：
   - 可以精确统计每种类型 beat 的数量
   - 可以估算时长（对话 beat 约 3-5 秒，动作 beat 约 5-15 秒）
   - 演员可以按 beat 划分表演单元

### 4.2 Beat Type 的 8 种类型

| 类型            | 对应剧本格式  | 使用场景               |
| --------------- | ------------- | ---------------------- |
| `action`        | 动作描写段落  | "张三拔剑冲向对手"     |
| `dialogue`      | 角色对白      | 张三："我不会放弃的。" |
| `monologue`     | 独白          | 大段的内心表达         |
| `voiceover`     | 画外音 (V.O.) | 旁白、回忆中的声音     |
| `transition`    | 转场指示      | "CUT TO:" / "淡入"     |
| `description`   | 场景描写      | "房间里弥漫着烟雾"     |
| `parenthetical` | 括号指示      | "(冷笑)"、"(低声)"     |
| `sound`         | 音效          | "远处传来雷声"         |

**设计原因**：这 8 种类型完整覆盖了标准剧本格式中的所有元素。分类粒度适中——太少则信息损失（如把 dialogue 和 monologue 混为一谈），太多则使用复杂。

### 4.3 为什么角色 ID 使用 `CHAR_001` 格式？

角色标识采用 `CHAR_` 前缀 + 数字序号，而非直接用角色名：

**设计原因**：

1. **唯一性**：同名角色（如两个"张三"）不会冲突
2. **稳定性**：角色改名时，只需修改 `name` 字段，所有引用不受影响
3. **可排序**：数字 ID 便于排序和检索
4. **可读性**：`CHAR_001` 比纯 UUID 更人类友好

### 4.4 为什么 Scene 的 `scene_number` 是全局递增的？

场景序号采用全局递增（跨幕连续编号），而非每个幕内重新编号：

**设计原因**：

1. **唯一引用**：制片方说"第 23 场"，不需要追问"哪一幕的第几场"
2. **拍摄排期**：拍摄计划按场景号排序时，全局序号直接可用
3. **统计方便**：一眼可知全剧共多少场

### 4.5 为什么分离 `characters_present` 和 `beat.character`？

两个字段看似冗余，但各有不同用途：

| 字段                       | 粒度   | 用途                           |
| -------------------------- | ------ | ------------------------------ |
| `scene.characters_present` | 场景级 | 拍摄时确定该场需要哪些演员到场 |
| `beat.character`           | 节拍级 | 确定每句台词/每个动作的执行者  |

**设计原因**：

- 演员调度只看 `characters_present`（知道这场戏需要到场）
- 台词统计只看 `beat.character`（计算每个角色的台词量）
- 有些节拍（如 `description`、`transition`）不需要角色，但场景仍然需要知道谁在场

### 4.6 为什么包含 `adaptation_notes`？

改编备注记录 AI 在转换过程中做的关键决策：

```yaml
adaptation_notes:
  - chapter: 2
    type: expanded
    description: '第2章内心独白较多，已转换为场景动作和对话'
    rationale: '剧本应聚焦于可视化内容，大幅内心独白不适合影视呈现'
  - chapter: 3
    type: reordered
    description: '将结尾的回忆段落提前到场景开头作为闪回'
    rationale: '增强戏剧张力，先展示冲突后果再揭示原因'
```

**设计原因**：

- 作者可以快速了解 AI 做了哪些改编
- 如果不同意某条改编，可以直接定位修改
- 积累改编经验，持续优化 AI 模型

### 4.7 为什么 Scene 和 Beat 都有 `source_chapter`？

两者粒度不同：

- `scene.source_chapter`：场景级别的来源追踪（这个场景改编自哪一章）
- `beat.source_chapter` + `beat.source_paragraph`：节拍级别的精确定位

**设计原因**：当 AI 将一章拆分为多个场景时，场景级追溯就够了；但当 AI 将一个段落的对话拆分到不同节拍时，节拍级追溯才能精确定位。

---

## 5. 完整示例

以下是一个简化但完整的剧本 YAML 示例：

```yaml
screenplay:
  title: '《剑影江湖》剧本'
  original_work: '剑影江湖'
  original_author: '佚名'
  adapted_by: 'AI Screenplay Assistant'
  version: '1.0.0'
  created_date: '2026-06-06'
  original_chapter_count: 3

  metadata:
    genre: ['武侠', '剧情']
    tone: '紧张'
    target_audience: '全年龄'
    estimated_duration: '45-75 分钟'
    keywords: ['江湖', '复仇', '剑客', '幽冥教']

  characters:
    - id: 'CHAR_001'
      name: '凌云'
      role: 'protagonist'
      aliases: []
      description: '北剑山庄遗孤，武功高强的年轻剑客'
      traits: ['沉稳', '坚毅', '隐忍']
      background: '十年前北剑山庄被灭门，他侥幸逃生，十年来一直在追查真相'
      motivation: '为父母报仇，查明北剑山庄灭门真相'
      arc: '从复仇者成长为心怀大义的真正剑客'
      relationships:
        - target_id: 'CHAR_002'
          relation: '恩人'
          description: '柳风在关键时刻给予凌云重要线索'
        - target_id: 'CHAR_004'
          relation: '仇敌'
          description: '幽冥教杀害了凌云父母'
      first_appearance_scene: 1
      last_appearance_scene: 5

    - id: 'CHAR_002'
      name: '柳风'
      role: 'supporting'
      description: '洛水镇的隐世老者，知晓十年前的秘密'
      traits: ['睿智', '神秘', '善良']

    - id: 'CHAR_003'
      name: '熊天霸'
      role: 'minor'
      description: '黑风寨寨主，幽冥教的外围爪牙'
      traits: ['凶狠', '欺软怕硬']

    - id: 'CHAR_004'
      name: '影煞'
      role: 'antagonist'
      description: '幽冥教左使，武功高强的神秘人物'
      traits: ['阴险', '冷静', '深不可测']
      motivation: '替幽冥教教主夺取天剑秘境地图'

  acts:
    - act_number: 1
      title: '建置'
      description: '介绍主要角色、世界观和核心冲突的起点'
      dramatic_function: '建立冲突与人物关系'
      scenes:
        - scene_number: 1
          location: '洛水镇茶馆'
          location_type: 'INT'
          time: 'morning'
          setting_description: '清晨的茶馆，炊烟和馒头香气弥漫'
          characters_present: ['CHAR_001', 'CHAR_002']
          source_chapter: 1
          beats:
            - beat_number: 1
              type: 'description'
              content: '清晨的阳光洒在青石街道上，空气中弥漫着炊烟香气。'
              source_chapter: 1
            - beat_number: 2
              type: 'action'
              content: '凌云提着行囊踏入洛水镇，走进茶馆靠窗坐下。'
              character: 'CHAR_001'
              source_chapter: 1
            - beat_number: 3
              type: 'dialogue'
              character: 'CHAR_001'
              content: '来一壶龙井，两个馒头。'
              source_chapter: 1

        - scene_number: 2
          location: '洛水镇街道'
          location_type: 'EXT'
          time: 'morning'
          setting_description: '青石街道，阳光明媚'
          characters_present: ['CHAR_001']
          source_chapter: 1
          beats:
            - beat_number: 1
              type: 'sound'
              content: '远处传来急促的马蹄声。'
              source_chapter: 1
            - beat_number: 2
              type: 'action'
              content: '三匹快马冲入街道，为首壮汉挥鞭驱赶行人。'
              source_chapter: 1
            - beat_number: 3
              type: 'action'
              content: '凌云从窗口掠出，抱起街中央的小女孩闪到路边。'
              character: 'CHAR_001'
              source_chapter: 1
            - beat_number: 4
              type: 'dialogue'
              character: 'CHAR_001'
              content: '光天化日之下，纵马行凶，你们的胆子不小。'
              emotion: '愤怒'
              source_chapter: 1
            - beat_number: 5
              type: 'dialogue'
              character: 'CHAR_001'
              content: '黑风寨？正好，我找的就是你们。'
              emotion: '冷静'
              source_chapter: 1
            - beat_number: 6
              type: 'action'
              content: '凌云手腕一抖，马鞭应声而断，一掌将壮汉摔下马。'
              character: 'CHAR_001'
              source_chapter: 1
            - beat_number: 7
              type: 'action'
              content: '两个喽啰挥刀冲来，被凌云两掌击飞。'
              character: 'CHAR_001'
              source_chapter: 1

        - scene_number: 3
          location: '洛水镇茶馆'
          location_type: 'INT'
          time: 'morning'
          setting_description: '茶馆内，阳光透过窗户洒在桌上'
          characters_present: ['CHAR_001', 'CHAR_002']
          source_chapter: 1
          beats:
            - beat_number: 1
              type: 'dialogue'
              character: 'CHAR_002'
              content: '年轻人，你这一身功夫，不简单啊。'
              source_chapter: 1
            - beat_number: 2
              type: 'dialogue'
              character: 'CHAR_002'
              content: '凌云？可是十年前，北剑山庄的那个凌云？'
              emotion: '惊讶'
              source_chapter: 1
            - beat_number: 3
              type: 'dialogue'
              character: 'CHAR_001'
              content: '正是。'
              emotion: '沉重'
              source_chapter: 1
            - beat_number: 4
              type: 'action'
              content: '柳风从怀中取出一块铜牌递给凌云。'
              character: 'CHAR_002'
              source_chapter: 1
            - beat_number: 5
              type: 'dialogue'
              character: 'CHAR_002'
              content: '这个符号，是幽冥教的标记。北剑山庄的灭门案，很可能与他们有关。'
              source_chapter: 1
            - beat_number: 6
              type: 'action'
              content: '凌云看到铜牌上的符号，瞳孔猛地一缩——这个符号，他在十年前那个血腥的夜晚见过。'
              character: 'CHAR_001'
              emotion: '震惊'
              source_chapter: 1

    - act_number: 2
      title: '对抗'
      description: '冲突升级，角色面临最大挑战'
      dramatic_function: '深化冲突，推向高潮'
      scenes:
        - scene_number: 4
          location: '黑风寨议事厅'
          location_type: 'INT'
          time: 'night'
          setting_description: '深夜，寨内火把通明'
          characters_present: ['CHAR_001', 'CHAR_003', 'CHAR_004']
          source_chapter: 2
          beats:
            - beat_number: 1
              type: 'description'
              content: '夜色如墨。凌云伏在寨外大树上，观察寨内动静。'
              source_chapter: 2
            - beat_number: 2
              type: 'action'
              content: '凌云趁哨兵换岗，无声地掠过寨墙。'
              character: 'CHAR_001'
              source_chapter: 2
            - beat_number: 3
              type: 'action'
              content: '凌云掀开屋顶瓦片，窥视屋内。熊天霸正对黑袍人汇报。'
              character: 'CHAR_001'
              source_chapter: 2
            - beat_number: 4
              type: 'dialogue'
              character: 'CHAR_004'
              content: '十年前为什么要灭北剑山庄？因为他知道了不该知道的事——天剑秘境的地图。'
              source_chapter: 2
            - beat_number: 5
              type: 'action'
              content: '凌云听到这里，心中杀意翻涌，屋顶发出轻响。'
              character: 'CHAR_001'
              emotion: '愤怒'
              source_chapter: 2
            - beat_number: 6
              type: 'sound'
              content: '警钟大作！'
              source_chapter: 2
            - beat_number: 7
              type: 'action'
              content: '凌云拔剑跃下，数十个寨丁围上来。'
              character: 'CHAR_001'
              source_chapter: 2
            - beat_number: 8
              type: 'dialogue'
              character: 'CHAR_001'
              content: '今日，就让你们见识一下北剑山庄的剑法。'
              emotion: '愤怒'
              source_chapter: 2
            - beat_number: 9
              type: 'action'
              content: '凌云剑光如虹，击飞三名寨丁兵器。黑袍人抬手凝聚黑雾。'
              source_chapter: 2
            - beat_number: 10
              type: 'dialogue'
              character: 'CHAR_004'
              content: '北剑十三式？可惜，你还差得远。'
              source_chapter: 2
            - beat_number: 11
              type: 'action'
              content: '黑袍人打出一团黑雾，身形消失。凌云三招击败熊天霸。'
              character: 'CHAR_001'
              source_chapter: 2
            - beat_number: 12
              type: 'dialogue'
              character: 'CHAR_001'
              content: '说！幽冥教的总坛在哪里？'
              emotion: '愤怒'
              source_chapter: 2
            - beat_number: 13
              type: 'action'
              content: '凌云在密室找到密信——第三份地图碎片在落日峰无心崖。'
              character: 'CHAR_001'
              source_chapter: 2

    - act_number: 3
      title: '结局'
      description: '真相揭晓，角色做出最终选择'
      dramatic_function: '高潮与解决'
      scenes:
        - scene_number: 5
          location: '落日峰无心崖石室'
          location_type: 'INT'
          time: 'dusk'
          setting_description: '石室中央有一座石台，上面放着铁匣子。夕阳余晖从洞口射入。'
          characters_present: ['CHAR_001', 'CHAR_004']
          source_chapter: 3
          beats:
            - beat_number: 1
              type: 'description'
              content: '落日峰山势险峻，晚霞将山峰染成金红色。'
              source_chapter: 3
            - beat_number: 2
              type: 'action'
              content: '凌云踏上宽不过一尺的栈道，来到隐蔽山洞。'
              character: 'CHAR_001'
              source_chapter: 3
            - beat_number: 3
              type: 'dialogue'
              character: 'CHAR_001'
              content: '出来吧。'
              source_chapter: 3
            - beat_number: 4
              type: 'action'
              content: '影煞从暗处走出，掀开兜帽。'
              character: 'CHAR_004'
              source_chapter: 3
            - beat_number: 5
              type: 'dialogue'
              character: 'CHAR_004'
              content: '那封密信是我故意留给你的。你的成长速度超出了教主的预期——他要亲自见你。'
              source_chapter: 3
            - beat_number: 6
              type: 'dialogue'
              character: 'CHAR_004'
              content: '十八年前，你的父亲凌云天是我们幽冥教的护法。是他发现了天剑秘境的地图。'
              source_chapter: 3
            - beat_number: 7
              type: 'action'
              content: '凌云震惊，颤抖着手打开铁匣子。里面是地图碎片和父亲的绝笔信。'
              character: 'CHAR_001'
              emotion: '震惊'
              source_chapter: 3
            - beat_number: 8
              type: 'voiceover'
              character: 'CHAR_001'
              content: '吾儿凌云：若你看到这封信，说明父亲已经不在了。天剑秘境的真正力量不是剑法，而是人心。'
              source_chapter: 3
            - beat_number: 9
              type: 'dialogue'
              character: 'CHAR_004'
              content: '教主说了，只要你愿意交出三份地图，幽冥教可以既往不咎。'
              source_chapter: 3
            - beat_number: 10
              type: 'dialogue'
              character: 'CHAR_001'
              content: '你回去告诉你们的教主——北剑山庄的血债，终有一天要血偿。'
              emotion: '坚定'
              source_chapter: 3
            - beat_number: 11
              type: 'action'
              content: '影煞双手一翻，两把短刃出现在手中。石室之中，一场恶战即将爆发。'
              source_chapter: 3

  adaptation_notes:
    - chapter: 1
      type: 'expanded'
      description: '将小镇环境描写扩展为具象的场景设定'
      rationale: '小说以文字营造氛围，剧本需要可拍摄的场景描述'
    - chapter: 2
      type: 'cut'
      description: '精简了黑风寨中部分内心独白'
      rationale: '影视化时，内心活动需要通过表情和动作外化'
    - chapter: 3
      type: 'invented'
      description: '增加了影煞与凌云对峙时的动作描写'
      rationale: '强化视觉张力，将书信阅读转化为可拍摄的 voiceover 节拍'

  unresolved_issues:
    - '幽冥教教主的身份尚未揭示，需在续集中展开'
    - '天剑秘境的另外两份地图碎片下落不明'
    - '凌云的剑法成长线可以更加细化'
```

---

## 6. 扩展性考虑

### 6.1 自定义元数据

如需添加剧本格式之外的字段（如分镜信息、预算估算），可以利用 `metadata` 中的自由字段，或通过 YAML 的 `<<:` 合并语法扩展：

```yaml
# 扩展：添加分镜信息
scenes:
  - scene_number: 1
    location: '洛水镇茶馆'
    # ... 标准字段 ...
    # 扩展字段（自定义命名空间）
    x_storyboard:
      shot_count: 5
      camera_notes: '多用中景，突出茶馆氛围'
```

### 6.2 多版本管理

Schema 中的 `version` 字段 + YAML 的文本特性，天然支持 Git 分支协作：

```bash
# 创建改编分支
git checkout -b adaptation/v2-dark-tone

# 修改 tone 字段
# metadata:
#   tone: "沉重"  →  "黑暗"

git commit -m "将基调从'沉重'调整为'黑暗'"
```

### 6.3 与其他格式互转

Schema 的层级结构可以无损转换为：

- **Final Draft (FDX)**：XML 格式，场景→段落→文本的映射清晰
- **Fountain**：Markdown-like 剧本格式，可逐节拍渲染
- **JSON**：直接序列化，用于 API 传输

---

## 7. 与行业标准的关系

| 标准/格式             | 用途               | 与本 Schema 的关系                                                   |
| --------------------- | ------------------ | -------------------------------------------------------------------- |
| **Final Draft (FDX)** | 好莱坞标准剧本格式 | 本 Schema 可无损转换为 FDX；FDX 更适合排版，本 Schema 更适合数据处理 |
| **Fountain**          | 纯文本剧本标记语言 | 同级别的语义表达；Fountain 更适合手写，本 Schema 更适合程序生成      |
| **Dublin Core**       | 通用元数据标准     | metadata 块的字段设计参考了 Dublin Core 的思路                       |
| **Screenplay JSON**   | 社区剧本 JSON 格式 | 本 Schema 是 YAML 原生设计，层级关系更直观                           |
| **ScriptXML**         | 剧本 XML 交换格式  | 本 Schema 更轻量，更适合现代 DevOps 工具链                           |

---

## 附录 A：Schema 版本历史

| 版本  | 日期       | 变更                   |
| ----- | ---------- | ---------------------- |
| 1.0.0 | 2026-06-06 | 初始版本，定义核心结构 |

## 附录 B：贡献指南

如需对此 Schema 提出修改建议，请遵循以下原则：

1. 向后兼容：新增字段应为 Optional
2. 枚举值可扩展但不可删除
3. 字段语义变更需增加版本号

---

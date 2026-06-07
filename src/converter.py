"""
AI 转换引擎

负责将解析后的小说内容转换为结构化剧本。
支持两种模式：
1. 规则模式 (RuleBased)：基于启发式规则的快速转换
2. AI 模式 (AIMode)：调用大语言模型进行智能转换
"""

import re
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple

from .parser import ParsedNovel, Chapter
from .schema import (
    Screenplay, ScreenplayMetadata, Character, CharacterRole,
    CharacterRelationship, Act, Scene, Beat, BeatType,
    LocationType, AdaptationNote,
)


# ============================================================
# 抽象基类
# ============================================================

class BaseConverter(ABC):
    """转换器抽象基类"""

    @abstractmethod
    def convert(self, novel: ParsedNovel) -> Screenplay:
        """将小说转换为剧本"""
        ...


# ============================================================
# 规则模式转换器
# ============================================================

class RuleBasedConverter(BaseConverter):
    """
    基于启发式规则的转换器

    适用于快速原型验证。规则包括：
    - 角色识别：通过名称频率、对话分布推断
    - 场景切分：根据地点关键词、时间变化
    - 节拍生成：对话→DIALOGUE、动作描写→ACTION
    - 幕结构：按章节或情节转折点分组
    """

    # 常见地点关键词
    LOCATION_KEYWORDS = [
        '房间', '大厅', '卧室', '客厅', '厨房', '书房', '院子', '花园',
        '街道', '广场', '市场', '商店', '饭店', '茶馆', '酒楼',
        '宫殿', '大殿', '朝堂', '衙门', '府邸', '宅院',
        '山', '林', '河', '湖', '海', '崖', '谷', '洞',
        '学校', '教室', '办公室', '医院', '车站', '机场',
        '酒馆', '客栈', '寺庙', '道观', '教堂',
    ]

    # 时间关键词
    TIME_KEYWORDS = {
        '清晨': 'dawn', '早晨': 'morning', '早上': 'morning',
        '上午': 'morning', '中午': 'noon', '午后': 'afternoon',
        '下午': 'afternoon', '傍晚': 'dusk', '黄昏': 'dusk',
        '晚上': 'evening', '夜晚': 'night', '深夜': 'late_night',
        '半夜': 'late_night', '凌晨': 'dawn',
    }

    # 动作动词（用于识别动作节拍）
    ACTION_VERBS = [
        '走', '跑', '跳', '坐', '站', '躺', '拿', '放', '推', '拉',
        '打开', '关闭', '举起', '放下', '转身', '回头', '点头', '摇头',
        '挥手', '握手', '拥抱', '踢', '打', '敲', '按', '拔', '抽',
        '冲', '闯', '奔', '跃', '飞', '爬', '摔', '倒', '跪',
        '微笑', '大笑', '哭泣', '叹息', '皱眉', '瞪', '望', '盯',
        '拔出', '抽出', '挥动', '刺', '砍', '劈',
    ]

    def __init__(self):
        self._char_id_counter = 0

    def _gen_char_id(self) -> str:
        self._char_id_counter += 1
        return f"CHAR_{self._char_id_counter:03d}"

    def convert(self, novel: ParsedNovel) -> Screenplay:
        """执行规则转换"""
        screenplay = Screenplay(
            title=f"《{novel.title}》剧本",
            original_work=novel.title,
            original_author=novel.author,
            original_chapter_count=novel.chapter_count,
        )

        # 1. 提取角色
        screenplay.characters = self._extract_characters(novel)
        char_name_to_id = {c.name: c.id for c in screenplay.characters}
        # 也建立别名映射
        for c in screenplay.characters:
            for alias in c.aliases:
                char_name_to_id[alias] = c.id

        # 2. 推断元数据
        screenplay.metadata = self._infer_metadata(novel)

        # 3. 构建幕/场景/节拍
        screenplay.acts = self._build_acts(novel, char_name_to_id)

        # 4. 更新角色出场信息
        self._update_character_appearances(screenplay)

        # 5. 生成改编备注
        screenplay.adaptation_notes = self._generate_adaptation_notes(novel)

        return screenplay

    def _extract_characters(self, novel: ParsedNovel) -> List[Character]:
        """从小说中提取角色"""
        # 统计人名出现频率
        name_counts: Dict[str, int] = {}
        # 中文人名模式：2-4个汉字，常见姓氏开头
        surname_pattern = re.compile(
            r'[王李张刘陈杨黄赵周吴徐孙马胡朱郭何罗高林郑梁谢唐许冯宋韩邓彭曹曾田萧潘袁蔡蒋余于杜叶程魏苏吕丁任卢姚钟姜崔谭陆范汪廖石金韦贾夏付方邹熊孟秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤温康'
            r'柳凌沈白苏叶方顾萧丁]'
            r'[\u4e00-\u9fff]{1,2}'  # 收紧为1-2字，减少误匹配
        )
        # 复姓模式
        compound_surname_pattern = re.compile(
            r'(欧阳|慕容|上官|司徒|司马|独孤|夏侯|诸葛|东方|西门|南宫|公孙|令狐|尉迟|长孙|宇文|端木|皇甫)'
            r'[\u4e00-\u9fff]{1,2}'
        )
        # 也匹配常见称呼（先生、小姐、大人、师傅等）
        title_pattern = re.compile(r'([\u4e00-\u9fff]{1,4})(先生|小姐|女士|大人|师傅|老板|兄|弟|姐|妹|爷|娘|官人)')

        for ch in novel.chapters:
            for para in ch.paragraphs:
                for m in surname_pattern.finditer(para):
                    name = m.group()
                    # 过滤非人名（常见动词/名词）
                    if not self._is_likely_person_name(name):
                        continue
                    # 加权：出现在对话引导词附近的名字更可能是角色
                    weight = 1
                    if self._is_near_dialogue_marker(para, m.start()):
                        weight = 3
                    name_counts[name] = name_counts.get(name, 0) + weight
                for m in compound_surname_pattern.finditer(para):
                    name = m.group()
                    if self._is_likely_person_name(name):
                        weight = 1
                        if self._is_near_dialogue_marker(para, m.start()):
                            weight = 3
                        name_counts[name] = name_counts.get(name, 0) + weight
                for m in title_pattern.finditer(para):
                    name = m.group(1) + m.group(2)  # 保留称呼
                    if self._is_likely_person_name(m.group(1)):
                        name_counts[name] = name_counts.get(name, 0) + 2

        # 后处理：清理候选名（去掉尾部非名常用字）并补充短名形式
        cleaned_counts: Dict[str, int] = {}
        # 可以被截断的尾部字符（常跟人名后但非人名部分）
        trim_suffixes = re.compile(r'[提着拿放推拉走跑跳飞去看听说问道叫喊答言曰讲叹笑哭泣怒骂指跟在和对向从到把被让给没不也还就又才只沉冷]$')
        for name, count in name_counts.items():
            # 尝试截断尾部非名字符
            cleaned = name
            while len(cleaned) >= 3 and trim_suffixes.search(cleaned[-1]):
                cleaned = cleaned[:-1]
            cleaned_counts[cleaned] = cleaned_counts.get(cleaned, 0) + count
            # 同时保留原始名（以防截断错误）
            if cleaned != name:
                cleaned_counts[name] = cleaned_counts.get(name, 0) + count

        # 合并变体名：如果短名是长名的子串，将长名合并到短名（短名更可能是真名）
        merged_counts: Dict[str, int] = dict(cleaned_counts)
        names_by_len = sorted(cleaned_counts.keys(), key=lambda n: (len(n), -cleaned_counts.get(n, 0)))
        for short_name in names_by_len:
            if merged_counts.get(short_name, 0) <= 0:
                continue
            for long_name in names_by_len:
                if long_name == short_name:
                    continue
                if len(long_name) > len(short_name) and short_name in long_name:
                    # 将长名计数合并到短名
                    if merged_counts.get(long_name, 0) > 0:
                        merged_counts[short_name] = merged_counts.get(short_name, 0) + merged_counts[long_name]
                        merged_counts[long_name] = 0

        # 移除被合并的条目
        cleaned_counts = {k: v for k, v in merged_counts.items() if v > 0}

        # 过滤低频候选（加权分 >= 3 才考虑）
        min_weight = 3
        filtered_names = {k: v for k, v in cleaned_counts.items() if v >= min_weight}
        if not filtered_names:
            # 放宽条件
            filtered_names = {k: v for k, v in cleaned_counts.items() if v >= 2}
        if not filtered_names and cleaned_counts:
            filtered_names = dict(sorted(cleaned_counts.items(), key=lambda x: x[1], reverse=True)[:5])

        # 取出现次数最多的前 15 个作为角色
        sorted_names = sorted(filtered_names.items(), key=lambda x: x[1], reverse=True)[:15]

        if not sorted_names:
            # 极端情况：至少返回一个占位角色
            return [Character(
                id=self._gen_char_id(),
                name="主角",
                role=CharacterRole.PROTAGONIST,
                description="请手动补充角色信息",
            )]

        characters = []
        for idx, (name, count) in enumerate(sorted_names):
            role = CharacterRole.SUPPORTING
            if idx == 0:
                role = CharacterRole.PROTAGONIST
            elif idx == 1 and count > sorted_names[0][1] * 0.5:
                role = CharacterRole.ANTAGONIST
            elif idx <= 4:
                role = CharacterRole.SUPPORTING
            else:
                role = CharacterRole.MINOR

            char = Character(
                id=self._gen_char_id(),
                name=name,
                role=role,
                aliases=[],
                description=f"出现 {count} 次",
                traits=[],
            )
            characters.append(char)

        # 建立简单的关系（基于共现）
        if len(characters) >= 2:
            # 主角和第二个角色默认为某种关系
            characters[0].relationships.append(CharacterRelationship(
                target_id=characters[1].id,
                relation="故事关联",
                description="主要互动对象",
            ))

        return characters

    def _is_near_dialogue_marker(self, paragraph: str, pos: int) -> bool:
        """检查该位置是否在对话引导词附近"""
        nearby = paragraph[max(0, pos-15):pos+5]
        return bool(re.search(r'(说|道|问|喊|叫|答|言|曰|讲|叹)', nearby))

    def _is_likely_person_name(self, text: str) -> bool:
        """判断是否可能是人名"""
        # 过滤明显的非人名
        non_person = {
            '什么', '怎么', '为什么', '可以', '然后', '因为', '所以', '但是',
            '如果', '虽然', '不过', '已经', '还是', '这个', '那个', '哪里',
            '他们', '我们', '你们', '自己', '没有', '知道', '觉得', '看见',
            '听到', '下来', '起来', '出来', '过来', '回去', '上去', '下去',
            '忽然', '突然', '终于', '还是', '于是', '接着', '另外', '旁边',
            '时候', '地方', '东西', '事情', '先生', '小姐', '女士', '大人',
            '师傅', '老板', '一声', '一下', '一阵', '一眼', '一天',
        }
        if text in non_person:
            return False
        # 过滤以常见非人名词结尾的词组
        non_person_suffixes = (
            '声', '鞭', '马', '刀', '剑', '枪', '拳', '掌', '脚', '步',
            '桌', '椅', '窗', '门', '屋', '房', '楼', '街', '路', '道',
            '茶', '酒', '饭', '菜', '花', '草', '树', '石', '山', '水',
            '铺', '店', '寨', '镇', '村', '都', '城',
            '的', '了', '着', '过', '得', '地',
            '里', '上', '下', '中', '前', '后', '旁', '边', '外', '内',
            '口', '头', '手', '心', '身', '面', '色', '气', '光', '影',
            '坐', '走', '跑', '跳', '飞', '来', '去', '出', '进',
            '看', '听', '说', '问', '答', '道', '叫', '喊', '笑', '哭',
            '抽', '打', '拍', '推', '拉', '拿', '放', '举',
            '指', '望', '想', '记', '忘', '知',
        )
        if text[-1] in non_person_suffixes:
            return False
        # 过滤包含非人名常用字的词组
        non_name_chars = set('的就着了过也得把被让给向从到在对以')
        if text[-1] in non_name_chars:
            return False
        # 长度 2-4 个汉字
        if len(text) < 2 or len(text) > 4:
            return False
        # 必须全部是汉字
        if not all('\u4e00' <= ch <= '\u9fff' for ch in text):
            return False
        return True

    def _infer_metadata(self, novel: ParsedNovel) -> ScreenplayMetadata:
        """推断剧本元数据"""
        full_text = novel.raw_text
        genres = []

        # 基于关键词推断类型
        genre_keywords = {
            '武侠': ['武功', '内功', '剑', '刀', '江湖', '门派', '大侠', '轻功'],
            '玄幻': ['修炼', '灵力', '仙人', '魔', '神', '异界', '丹田', '元婴'],
            '言情': ['爱情', '恋爱', '喜欢', '爱', '心疼', '相思', '痴情'],
            '悬疑': ['案件', '凶手', '侦探', '线索', '谜', '谋杀', '秘密', '真相'],
            '都市': ['公司', '老板', '上班', '城市', '公寓', '手机', '电脑'],
            '历史': ['皇帝', '将军', '丞相', '殿下', '陛下', '朝代', '宫廷'],
            '科幻': ['飞船', '星球', '宇宙', '科技', '机器人', 'AI', '未来'],
        }
        for genre, keywords in genre_keywords.items():
            if any(kw in full_text for kw in keywords):
                genres.append(genre)

        if not genres:
            genres = ['剧情']

        # 推断基调
        tone_keywords = {
            '轻松': ['笑', '幽默', '搞笑', '风趣', '欢乐'],
            '沉重': ['痛苦', '悲伤', '绝望', '死亡', '血', '泪'],
            '紧张': ['危机', '危险', '紧迫', '紧张', '恐惧'],
            '温馨': ['温暖', '感动', '家', '友情', '亲情', '幸福'],
        }
        tone = '中性'
        max_tone_score = 0
        for t, kws in tone_keywords.items():
            score = sum(full_text.count(kw) for kw in kws)
            if score > max_tone_score:
                max_tone_score = score
                tone = t

        return ScreenplayMetadata(
            genre=genres,
            tone=tone,
            estimated_duration=f"{novel.chapter_count * 15}-{novel.chapter_count * 25} 分钟",
            keywords=list(genre_keywords.get(genres[0], []))[:5] if genres else [],
        )

    def _build_acts(
        self, novel: ParsedNovel, char_name_to_id: Dict[str, str]
    ) -> List[Act]:
        """构建幕/场景/节拍结构"""
        acts = []

        # 经典三幕结构映射 (如果章节 >= 3)
        act_structure = self._map_chapters_to_acts(novel.chapter_count)

        scene_counter = 0

        for act_idx, (act_num, ch_range) in enumerate(act_structure):
            act = Act(
                act_number=act_num,
                title=self._get_act_title(act_num),
                description=self._get_act_description(act_num),
                dramatic_function=self._get_dramatic_function(act_num),
            )

            for ch_num in ch_range:
                if ch_num - 1 < len(novel.chapters):
                    ch = novel.chapters[ch_num - 1]
                    scenes = self._chapter_to_scenes(
                        ch, char_name_to_id, scene_counter
                    )
                    act.scenes.extend(scenes)
                    scene_counter += len(scenes)

            acts.append(act)

        return acts

    def _map_chapters_to_acts(self, chapter_count: int) -> List[Tuple[int, List[int]]]:
        """
        将章节映射到三幕结构
        返回: [(幕号, [章节号列表]), ...]
        """
        if chapter_count <= 3:
            # 每章一幕
            return [(i + 1, [i + 1]) for i in range(chapter_count)]

        # 经典三幕结构：25% / 50% / 25%
        act1_end = max(1, chapter_count // 4)
        act2_end = max(act1_end + 1, chapter_count * 3 // 4)

        return [
            (1, list(range(1, act1_end + 1))),
            (2, list(range(act1_end + 1, act2_end + 1))),
            (3, list(range(act2_end + 1, chapter_count + 1))),
        ]

    def _get_act_title(self, act_num: int) -> str:
        titles = {1: "建置", 2: "对抗", 3: "结局"}
        return titles.get(act_num, f"第{act_num}幕")

    def _get_act_description(self, act_num: int) -> str:
        descriptions = {
            1: "介绍主要角色、世界观和核心冲突的起点",
            2: "冲突升级，角色面临最大挑战，情节曲折发展",
            3: "冲突解决，角色完成成长弧线，故事收束",
        }
        return descriptions.get(act_num, "")

    def _get_dramatic_function(self, act_num: int) -> str:
        functions = {
            1: "建立冲突与人物关系",
            2: "深化冲突，推向高潮",
            3: "高潮与解决",
        }
        return functions.get(act_num, "")

    def _chapter_to_scenes(
        self, chapter: Chapter, char_name_to_id: Dict[str, str],
        start_scene_num: int
    ) -> List[Scene]:
        """将单个章节转换为场景列表"""
        scenes = []
        current_scene = None
        scene_num = start_scene_num

        for para in chapter.paragraphs:
            # 检测场景切换（地点/时间变化）
            new_location = self._detect_location(para)
            new_time = self._detect_time(para)

            if new_location or new_time or current_scene is None:
                # 保存当前场景
                if current_scene and current_scene.beats:
                    scenes.append(current_scene)
                    scene_num += 1

                # 创建新场景
                current_scene = Scene(
                    scene_number=scene_num,
                    location=new_location or (current_scene.location if current_scene else "未知地点"),
                    location_type=LocationType.INTERIOR if self._is_interior(new_location or "") else LocationType.EXTERIOR,
                    time=new_time or "day",
                    setting_description=para[:100] if (new_location or not current_scene) else "",
                    source_chapter=chapter.number,
                )

            # 解析节拍
            beats = self._para_to_beats(para, char_name_to_id, chapter.number)
            if current_scene:
                current_scene.beats.extend(beats)
                # 更新出场角色
                for beat in beats:
                    if beat.character and beat.character not in current_scene.characters_present:
                        current_scene.characters_present.append(beat.character)

        # 保存最后一个场景
        if current_scene and current_scene.beats:
            scenes.append(current_scene)

        return scenes

    def _detect_location(self, text: str) -> Optional[str]:
        """检测文本中包含的地点"""
        for loc in self.LOCATION_KEYWORDS:
            if loc in text:
                # 提取包含该关键词的短语
                idx = text.find(loc)
                start = max(0, idx - 10)
                end = min(len(text), idx + len(loc) + 5)
                phrase = text[start:end]
                # 截取合理的长度
                return phrase.strip()[:20]
        return None

    def _detect_time(self, text: str) -> Optional[str]:
        """检测文本中的时间"""
        for kw, tm in self.TIME_KEYWORDS.items():
            if kw in text[:50]:  # 只看段落开头
                return tm
        return None

    def _is_interior(self, location: str) -> bool:
        """判断是否为内景"""
        interior_kw = ['房间', '厅', '室', '内', '里', '殿', '堂', '楼']
        return any(kw in location for kw in interior_kw)

    def _para_to_beats(
        self, paragraph: str, char_name_to_id: Dict[str, str],
        chapter_num: int
    ) -> List[Beat]:
        """将段落转换为节拍列表"""
        beats = []
        beat_num = 0

        # 1. 检测对话
        dialogue_patterns = [
            (re.compile(r'「([^」]+)」'), '「」'),
            (re.compile(r'"([^"]+)"'), '""'),
            (re.compile(r'["""]([^"""]+)["""]'), '""'),
        ]

        found_dialogue = False
        for pattern, _ in dialogue_patterns:
            for m in pattern.finditer(paragraph):
                found_dialogue = True
                dialogue_text = m.group(1).strip()
                if len(dialogue_text) < 2:
                    continue

                # 推断说话人
                speaker = self._infer_speaker_from_para(paragraph, m.start())
                char_id = char_name_to_id.get(speaker)

                beat_num += 1
                beats.append(Beat(
                    beat_number=beat_num,
                    type=BeatType.DIALOGUE,
                    character=char_id,
                    content=dialogue_text,
                    emotion=self._detect_emotion(paragraph, m.start()),
                    source_chapter=chapter_num,
                ))

        # 2. 如果没有对话，判断是否是动作/描述
        if not found_dialogue:
            # 检测动作动词
            action_count = sum(1 for v in self.ACTION_VERBS if v in paragraph)
            if action_count >= 2:
                beat_num += 1
                beats.append(Beat(
                    beat_number=beat_num,
                    type=BeatType.ACTION,
                    content=paragraph[:200],
                    source_chapter=chapter_num,
                ))
            else:
                # 默认为场景描述
                beat_num += 1
                beats.append(Beat(
                    beat_number=beat_num,
                    type=BeatType.DESCRIPTION,
                    content=paragraph[:200],
                    source_chapter=chapter_num,
                ))

        return beats

    def _infer_speaker_from_para(self, paragraph: str, quote_pos: int) -> str:
        """从段落中推断说话人"""
        before = paragraph[:quote_pos]
        # 匹配 "XX说"、"XX道"、"XX问" 等
        m = re.search(r'(\S{1,4})(?:说|道|问|喊|叫|答|言|曰|讲|叹|笑|怒|骂|喝道|冷声道|淡淡道|低声道|大声道)', before)
        if m:
            return m.group(1)
        # 匹配 "XX：" 或 "XX:"
        m = re.search(r'(\S{1,4})[：:]$', before.rstrip())
        if m:
            return m.group(1)
        return "未知"

    def _detect_emotion(self, paragraph: str, pos: int) -> Optional[str]:
        """检测对话情感"""
        context = paragraph[max(0, pos-30):pos]
        emotions = {
            '愤怒': ['怒', '愤', '气'],
            '悲伤': ['悲', '伤', '哭', '泪', '痛'],
            '喜悦': ['笑', '喜', '乐', '欢', '欣'],
            '惊讶': ['惊', '愣', '愕', '呆'],
            '恐惧': ['怕', '恐', '惧', '畏'],
            '冷静': ['冷', '淡', '静', '沉'],
            '温柔': ['柔', '温', '软', '轻'],
        }
        for emotion, kws in emotions.items():
            if any(kw in context for kw in kws):
                return emotion
        return None

    def _update_character_appearances(self, screenplay: Screenplay) -> None:
        """更新角色首次/末次出场场景"""
        scene_char_map: Dict[str, Tuple[int, int]] = {}
        for act in screenplay.acts:
            for scene in act.scenes:
                for cid in scene.characters_present:
                    if cid not in scene_char_map:
                        scene_char_map[cid] = (scene.scene_number, scene.scene_number)
                    else:
                        first, _ = scene_char_map[cid]
                        scene_char_map[cid] = (first, scene.scene_number)

        for char in screenplay.characters:
            if char.id in scene_char_map:
                char.first_appearance_scene = scene_char_map[char.id][0]
                char.last_appearance_scene = scene_char_map[char.id][1]

    def _generate_adaptation_notes(self, novel: ParsedNovel) -> List[AdaptationNote]:
        """生成改编备注"""
        notes = []
        for ch in novel.chapters:
            if ch.word_count < 500:
                notes.append(AdaptationNote(
                    chapter=ch.number,
                    type="expanded",
                    description=f"第{ch.number}章内容较少（{ch.word_count}字），建议扩充场景细节",
                    rationale="剧本需要足够的视觉和动作描写",
                ))
            elif ch.word_count > 5000:
                notes.append(AdaptationNote(
                    chapter=ch.number,
                    type="cut",
                    description=f"第{ch.number}章内容较长（{ch.word_count}字），建议精简部分内心独白",
                    rationale="剧本应聚焦于可视化内容",
                ))
        return notes


# ============================================================
# AI 模式转换器 (基于 API 调用)
# ============================================================

class AIConverter(BaseConverter):
    """
    基于大语言模型的智能转换器

    支持 OpenAI API 兼容接口，通过结构化 Prompt
    让 LLM 将小说内容转换为剧本 YAML。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        temperature: float = 0.3,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.temperature = temperature

    def convert(self, novel: ParsedNovel) -> Screenplay:
        """
        AI 模式转换

        策略：将长文本分章节发送给 LLM 处理，
        然后合并结果。如果 API 不可用，回退到规则模式。
        """
        if not self.api_key:
            print("⚠️  未设置 API Key，回退到规则模式")
            return RuleBasedConverter().convert(novel)

        try:
            return self._ai_convert(novel)
        except Exception as e:
            print(f"⚠️  AI 转换失败 ({e})，回退到规则模式")
            return RuleBasedConverter().convert(novel)

    def _ai_convert(self, novel: ParsedNovel) -> Screenplay:
        """
        分章节调用 AI 进行转换
        """
        # 首先用 AI 做全局分析
        global_analysis = self._call_ai_global_analysis(novel)

        # 初始化剧本
        screenplay = Screenplay(
            title=global_analysis.get("title", f"《{novel.title}》剧本"),
            original_work=novel.title,
            original_author=novel.author,
            original_chapter_count=novel.chapter_count,
            metadata=ScreenplayMetadata(
                genre=global_analysis.get("genre", []),
                tone=global_analysis.get("tone", ""),
                estimated_duration=global_analysis.get("estimated_duration", ""),
            ),
        )

        # 解析 AI 返回的角色
        for c_data in global_analysis.get("characters", []):
            char = Character(
                id=c_data.get("id", f"CHAR_{len(screenplay.characters)+1:03d}"),
                name=c_data.get("name", ""),
                role=CharacterRole(c_data.get("role", "supporting")),
                description=c_data.get("description", ""),
                traits=c_data.get("traits", []),
                motivation=c_data.get("motivation"),
                arc=c_data.get("arc"),
            )
            screenplay.characters.append(char)

        # 逐章转换场景
        all_scenes = []
        for ch in novel.chapters:
            ch_scenes = self._call_ai_chapter_convert(ch, screenplay.characters)
            all_scenes.extend(ch_scenes)

        # 组织成三幕结构
        acts = self._organize_scenes_into_acts(all_scenes, novel.chapter_count)
        screenplay.acts = acts

        return screenplay

    def _call_ai_global_analysis(self, novel: ParsedNovel) -> Dict[str, Any]:
        """
        调用 AI 进行全局分析
        返回包含 title、genre、tone、characters 等的字典
        """
        # 构建 prompt（只发送前几章的摘要，控制 token）
        summary_parts = []
        for ch in novel.chapters[:5]:  # 最多取前 5 章
            summary_parts.append(
                f"第{ch.number}章 {ch.title}: {ch.raw_text[:500]}..."
            )
        summary = "\n\n".join(summary_parts)

        prompt = f"""你是一个专业的剧本改编顾问。请分析以下小说片段，提取关键信息。
返回格式为严格的 JSON，不要包含 markdown 标记。

小说信息：
{summary}

请返回如下 JSON：
{{
  "title": "建议的剧本标题",
  "genre": ["类型1", "类型2"],
  "tone": "整体基调（如：轻松/沉重/紧张/温馨/中性）",
  "estimated_duration": "预估时长",
  "characters": [
    {{
      "id": "CHAR_001",
      "name": "角色名",
      "role": "protagonist|antagonist|supporting|minor",
      "description": "角色描述",
      "traits": ["性格特征"],
      "motivation": "动机",
      "arc": "角色弧线"
    }}
  ]
}}

请只返回 JSON，不要有任何其他文字。"""

        return self._call_ai_api(prompt, expect_json=True)

    def _call_ai_chapter_convert(
        self, chapter: Chapter, characters: List[Character]
    ) -> List[Scene]:
        """
        调用 AI 转换单个章节为场景
        """
        char_list = "\n".join(
            f"- {c.id}: {c.name} ({c.role.value})" for c in characters
        )

        prompt = f"""你是一个剧本格式转换专家。请将以下小说章节转换为剧本场景格式。
返回格式为严格的 JSON，不要包含 markdown 标记。

可用角色：
{char_list}

章节内容：
{chapter.raw_text[:2000]}

请返回如下 JSON 对象：
{{
  "scenes": [
    {{
      "scene_number": 1,
      "location": "场景地点",
      "location_type": "INT|EXT|INT/EXT",
      "time": "时间",
      "setting_description": "环境描述",
      "characters_present": ["CHAR_001"],
      "beats": [
        {{
          "beat_number": 1,
          "type": "action|dialogue|monologue|voiceover|transition|description|sound",
          "character": "CHAR_001 (仅对话/独白类型需要)",
          "content": "内容",
          "parenthetical": "(可选的动作提示)",
          "emotion": "情感标注"
        }}
      ]
    }}
  ]
}}

注意：
1. 对话类型 (dialogue) 的 beat 必须指定 character
2. 只返回 JSON 对象，不要有任何其他文字
3. 每个场景的 beats 至少 2 个"""

        raw_result = self._call_ai_api(prompt, expect_json=True)

        # 将 AI 返回的 dict 转换为 Scene 对象
        raw_scenes = raw_result.get("scenes", []) if isinstance(raw_result, dict) else []
        scenes: List[Scene] = []
        if isinstance(raw_scenes, list):
            for s_data in raw_scenes:
                # 转换 beats
                beats = []
                for b_data in s_data.get("beats", []):
                    beat_type_str = b_data.get("type", "description")
                    try:
                        beat_type = BeatType(beat_type_str)
                    except ValueError:
                        beat_type = BeatType.DESCRIPTION
                    beat = Beat(
                        beat_number=b_data.get("beat_number", len(beats) + 1),
                        type=beat_type,
                        character=b_data.get("character"),
                        content=b_data.get("content", ""),
                        parenthetical=b_data.get("parenthetical"),
                        emotion=b_data.get("emotion"),
                        source_chapter=chapter.number,
                    )
                    beats.append(beat)

                # 转换 location_type
                loc_type_str = s_data.get("location_type", "INT")
                try:
                    loc_type = LocationType(loc_type_str)
                except ValueError:
                    loc_type = LocationType.INTERIOR

                scene = Scene(
                    scene_number=s_data.get("scene_number", len(scenes) + 1),
                    location=s_data.get("location", ""),
                    location_type=loc_type,
                    time=s_data.get("time", "day"),
                    setting_description=s_data.get("setting_description", ""),
                    characters_present=s_data.get("characters_present", []),
                    beats=beats,
                    source_chapter=chapter.number,
                )
                scenes.append(scene)

        return scenes

    def _organize_scenes_into_acts(
        self, scenes: List[Scene], chapter_count: int
    ) -> List[Act]:
        """将场景组织成三幕结构"""
        if not scenes:
            # 空场景返回默认结构
            return [
                Act(act_number=1, title="建置", description="第一幕"),
                Act(act_number=2, title="对抗", description="第二幕"),
                Act(act_number=3, title="结局", description="第三幕"),
            ]

        # 按 25%/50%/25% 分配场景
        total = len(scenes)
        split1 = max(1, total // 4)
        split2 = max(split1 + 1, total * 3 // 4)

        acts = [
            Act(
                act_number=1,
                title="建置",
                description="介绍主要角色、世界观和核心冲突的起点",
                dramatic_function="建立冲突与人物关系",
                scenes=scenes[:split1],
            ),
            Act(
                act_number=2,
                title="对抗",
                description="冲突升级，角色面临最大挑战",
                dramatic_function="深化冲突，推向高潮",
                scenes=scenes[split1:split2],
            ),
            Act(
                act_number=3,
                title="结局",
                description="冲突解决，故事收束",
                dramatic_function="高潮与解决",
                scenes=scenes[split2:],
            ),
        ]

        return acts

    def _call_ai_api(self, prompt: str, expect_json: bool = False) -> Any:
        """
        调用 OpenAI 兼容 API

        这是一个占位实现。实际使用需要安装 openai 包并配置 API Key。
        """
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的剧本改编 AI 助手。请始终返回有效的 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"} if expect_json else None,
            )

            content = response.choices[0].message.content
            if expect_json and content:
                # 清理可能的 markdown 代码块标记
                content = re.sub(r'^```(?:json)?\s*', '', content.strip())
                content = re.sub(r'\s*```$', '', content.strip())
                return json.loads(content)
            return content

        except ImportError:
            raise RuntimeError(
                "使用 AI 模式需要安装 openai 包：pip install openai"
            )
        except Exception as e:
            err_msg = str(e)
            # 提供更友好的错误提示
            if "Connection" in err_msg or "connect" in err_msg.lower():
                raise RuntimeError(
                    f"无法连接到 AI API ({self.api_base})。"
                    "请检查网络连接、代理设置，或确认 API Base URL 正确。"
                )
            elif "auth" in err_msg.lower() or "401" in err_msg or "403" in err_msg:
                raise RuntimeError(
                    "API Key 无效或已过期。请检查密钥是否正确。"
                )
            elif "model" in err_msg.lower():
                raise RuntimeError(
                    f"模型 '{self.model}' 不可用。请检查模型名称是否正确。"
                )
            else:
                raise RuntimeError(f"AI API 调用失败: {e}")


# ============================================================
# 工厂函数
# ============================================================

def create_converter(mode: str = "rule", **kwargs) -> BaseConverter:
    """
    创建转换器实例

    Args:
        mode: "rule" 或 "ai"
        **kwargs: 传递给 AI 转换器的参数

    Returns:
        BaseConverter 实例
    """
    if mode == "ai":
        return AIConverter(**kwargs)
    return RuleBasedConverter()

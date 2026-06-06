"""
剧本 YAML Schema 定义与校验模块

本模块定义了小说转剧本工具的核心数据结构，
包含完整的剧本 YAML Schema 及验证逻辑。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import date
import yaml


# ============================================================
# 枚举定义
# ============================================================

class CharacterRole(Enum):
    """角色类型"""
    PROTAGONIST = "protagonist"       # 主角
    ANTAGONIST = "antagonist"         # 反派/对手
    SUPPORTING = "supporting"         # 配角
    MINOR = "minor"                   # 次要角色
    CAMEO = "cameo"                   # 客串


class BeatType(Enum):
    """节拍类型 — 剧本的最小叙事单元"""
    ACTION = "action"                 # 动作描写
    DIALOGUE = "dialogue"             # 对白
    MONOLOGUE = "monologue"           # 独白
    VOICEOVER = "voiceover"           # 画外音
    TRANSITION = "transition"         # 转场
    DESCRIPTION = "description"       # 场景/环境描述
    PARENTHETICAL = "parenthetical"   # 括号指示（动作提示）
    SOUND = "sound"                   # 音效提示


class SceneTime(Enum):
    """场景时间"""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"
    UNKNOWN = "unknown"


class LocationType(Enum):
    """场景地点类型"""
    INTERIOR = "INT"    # 内景
    EXTERIOR = "EXT"    # 外景
    INT_EXT = "INT/EXT" # 内外结合


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class CharacterRelationship:
    """角色关系"""
    target_id: str                              # 关系对象 ID
    relation: str                               # 关系描述（如 "父子"、"恋人"、"仇敌"）
    description: Optional[str] = None           # 关系详述


@dataclass
class Character:
    """角色定义"""
    id: str                                     # 唯一标识
    name: str                                   # 角色姓名
    role: CharacterRole = CharacterRole.SUPPORTING
    aliases: List[str] = field(default_factory=list)  # 别名/昵称
    description: str = ""                       # 角色描述
    traits: List[str] = field(default_factory=list)   # 性格特征
    background: Optional[str] = None            # 背景故事
    motivation: Optional[str] = None            # 动机
    arc: Optional[str] = None                   # 角色弧线
    relationships: List[CharacterRelationship] = field(default_factory=list)
    first_appearance_scene: Optional[int] = None
    last_appearance_scene: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "aliases": self.aliases,
            "description": self.description,
            "traits": self.traits,
        }
        if self.background:
            d["background"] = self.background
        if self.motivation:
            d["motivation"] = self.motivation
        if self.arc:
            d["arc"] = self.arc
        if self.relationships:
            d["relationships"] = [
                {"target_id": r.target_id, "relation": r.relation,
                 "description": r.description} for r in self.relationships
            ]
        if self.first_appearance_scene is not None:
            d["first_appearance_scene"] = self.first_appearance_scene
        if self.last_appearance_scene is not None:
            d["last_appearance_scene"] = self.last_appearance_scene
        return d


@dataclass
class Beat:
    """节拍 — 剧本的最小叙事单元"""
    beat_number: int                            # 节拍序号
    type: BeatType                              # 节拍类型
    character: Optional[str] = None             # 关联角色 ID（对白/独白/动作）
    content: str = ""                           # 内容文本
    parenthetical: Optional[str] = None         # 括号指示（如 "(冷笑)"）
    emotion: Optional[str] = None               # 情感标注
    duration_seconds: Optional[int] = None      # 预估时长（秒）
    notes: Optional[str] = None                 # 备注
    source_chapter: Optional[int] = None        # 来源章节（可追溯）
    source_paragraph: Optional[int] = None      # 来源段落（可追溯）

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "beat_number": self.beat_number,
            "type": self.type.value,
            "content": self.content,
        }
        if self.character:
            d["character"] = self.character
        if self.parenthetical:
            d["parenthetical"] = self.parenthetical
        if self.emotion:
            d["emotion"] = self.emotion
        if self.duration_seconds:
            d["duration_seconds"] = self.duration_seconds
        if self.notes:
            d["notes"] = self.notes
        if self.source_chapter:
            d["source_chapter"] = self.source_chapter
        return d


@dataclass
class Scene:
    """场景"""
    scene_number: int                           # 场景序号
    location: str = ""                          # 地点名称
    location_type: LocationType = LocationType.INTERIOR
    time: str = "day"                           # 时间
    setting_description: str = ""               # 场景环境描述
    characters_present: List[str] = field(default_factory=list)  # 出场角色 ID 列表
    beats: List[Beat] = field(default_factory=list)
    summary: Optional[str] = None               # 场景摘要
    page_estimate: Optional[float] = None       # 预估页数
    source_chapter: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "scene_number": self.scene_number,
            "location": self.location,
            "location_type": self.location_type.value,
            "time": self.time,
            "setting_description": self.setting_description,
            "characters_present": self.characters_present,
            "beats": [b.to_dict() for b in self.beats],
        }
        if self.summary:
            d["summary"] = self.summary
        if self.page_estimate:
            d["page_estimate"] = self.page_estimate
        if self.source_chapter is not None:
            d["source_chapter"] = self.source_chapter
        return d


@dataclass
class Act:
    """幕"""
    act_number: int                             # 幕序号
    title: str = ""                             # 幕标题
    description: str = ""                       # 幕描述
    scenes: List[Scene] = field(default_factory=list)
    dramatic_function: Optional[str] = None     # 戏剧功能（如 "建立冲突"、"高潮"、"结局"）

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "act_number": self.act_number,
            "title": self.title,
            "description": self.description,
            "scenes": [s.to_dict() for s in self.scenes],
        }
        if self.dramatic_function:
            d["dramatic_function"] = self.dramatic_function
        return d


@dataclass
class ScreenplayMetadata:
    """剧本元数据"""
    genre: List[str] = field(default_factory=list)
    tone: str = ""
    target_audience: str = ""
    estimated_duration: str = ""
    content_warnings: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.genre:
            d["genre"] = self.genre
        if self.tone:
            d["tone"] = self.tone
        if self.target_audience:
            d["target_audience"] = self.target_audience
        if self.estimated_duration:
            d["estimated_duration"] = self.estimated_duration
        if self.content_warnings:
            d["content_warnings"] = self.content_warnings
        if self.keywords:
            d["keywords"] = self.keywords
        return d


@dataclass
class AdaptationNote:
    """改编备注"""
    chapter: int
    type: str                                   # "cut" | "merged" | "expanded" | "reordered" | "invented"
    description: str
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "chapter": self.chapter,
            "type": self.type,
            "description": self.description,
        }
        if self.rationale:
            d["rationale"] = self.rationale
        return d


@dataclass
class Screenplay:
    """完整的剧本数据结构"""
    title: str
    original_work: str = ""                     # 原著名称
    original_author: str = ""                   # 原著作者
    adapted_by: str = "AI Screenplay Assistant" # 改编者
    version: str = "1.0.0"
    created_date: str = field(default_factory=lambda: date.today().isoformat())
    metadata: ScreenplayMetadata = field(default_factory=ScreenplayMetadata)
    characters: List[Character] = field(default_factory=list)
    acts: List[Act] = field(default_factory=list)
    adaptation_notes: List[AdaptationNote] = field(default_factory=list)
    unresolved_issues: List[str] = field(default_factory=list)
    original_chapter_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """将剧本对象序列化为符合 Schema 的字典"""
        return {
            "screenplay": {
                "title": self.title,
                "original_work": self.original_work,
                "original_author": self.original_author,
                "adapted_by": self.adapted_by,
                "version": self.version,
                "created_date": self.created_date,
                "metadata": self.metadata.to_dict(),
                "characters": [c.to_dict() for c in self.characters],
                "acts": [a.to_dict() for a in self.acts],
                "adaptation_notes": [n.to_dict() for n in self.adaptation_notes],
                "unresolved_issues": self.unresolved_issues,
                "original_chapter_count": self.original_chapter_count,
            }
        }

    def to_yaml(self) -> str:
        """导出为 YAML 字符串"""
        return yaml.dump(
            self.to_dict(),
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
        )

    def save(self, filepath: str) -> None:
        """保存剧本到 YAML 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())
        print(f"✅ 剧本已保存至: {filepath}")

    @staticmethod
    def load(filepath: str) -> "Screenplay":
        """从 YAML 文件加载剧本"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Screenplay.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Screenplay":
        """从字典反序列化剧本对象（简化实现）"""
        sp_data = data.get("screenplay", data)
        sp = Screenplay(
            title=sp_data.get("title", "Untitled"),
            original_work=sp_data.get("original_work", ""),
            original_author=sp_data.get("original_author", ""),
            adapted_by=sp_data.get("adapted_by", ""),
            version=sp_data.get("version", "1.0.0"),
            created_date=sp_data.get("created_date", ""),
            original_chapter_count=sp_data.get("original_chapter_count", 0),
        )
        # 解析 metadata
        meta = sp_data.get("metadata", {})
        sp.metadata = ScreenplayMetadata(
            genre=meta.get("genre", []),
            tone=meta.get("tone", ""),
            target_audience=meta.get("target_audience", ""),
            estimated_duration=meta.get("estimated_duration", ""),
            content_warnings=meta.get("content_warnings", []),
            keywords=meta.get("keywords", []),
        )
        # 解析 characters
        for c_data in sp_data.get("characters", []):
            char = Character(
                id=c_data["id"],
                name=c_data["name"],
                role=CharacterRole(c_data.get("role", "supporting")),
                aliases=c_data.get("aliases", []),
                description=c_data.get("description", ""),
                traits=c_data.get("traits", []),
                background=c_data.get("background"),
                motivation=c_data.get("motivation"),
                arc=c_data.get("arc"),
                first_appearance_scene=c_data.get("first_appearance_scene"),
                last_appearance_scene=c_data.get("last_appearance_scene"),
            )
            for r in c_data.get("relationships", []):
                char.relationships.append(CharacterRelationship(
                    target_id=r["target_id"],
                    relation=r["relation"],
                    description=r.get("description"),
                ))
            sp.characters.append(char)
        # 解析 acts/scenes/beats
        for a_data in sp_data.get("acts", []):
            act = Act(
                act_number=a_data["act_number"],
                title=a_data.get("title", ""),
                description=a_data.get("description", ""),
                dramatic_function=a_data.get("dramatic_function"),
            )
            for s_data in a_data.get("scenes", []):
                scene = Scene(
                    scene_number=s_data["scene_number"],
                    location=s_data.get("location", ""),
                    location_type=LocationType(s_data.get("location_type", "INT")),
                    time=s_data.get("time", "day"),
                    setting_description=s_data.get("setting_description", ""),
                    characters_present=s_data.get("characters_present", []),
                    summary=s_data.get("summary"),
                    page_estimate=s_data.get("page_estimate"),
                    source_chapter=s_data.get("source_chapter"),
                )
                for b_data in s_data.get("beats", []):
                    beat = Beat(
                        beat_number=b_data["beat_number"],
                        type=BeatType(b_data["type"]),
                        character=b_data.get("character"),
                        content=b_data.get("content", ""),
                        parenthetical=b_data.get("parenthetical"),
                        emotion=b_data.get("emotion"),
                        duration_seconds=b_data.get("duration_seconds"),
                        notes=b_data.get("notes"),
                        source_chapter=b_data.get("source_chapter"),
                        source_paragraph=b_data.get("source_paragraph"),
                    )
                    scene.beats.append(beat)
                act.scenes.append(scene)
            sp.acts.append(act)
        # 解析 adaptation_notes
        for n_data in sp_data.get("adaptation_notes", []):
            sp.adaptation_notes.append(AdaptationNote(
                chapter=n_data["chapter"],
                type=n_data["type"],
                description=n_data["description"],
                rationale=n_data.get("rationale"),
            ))
        sp.unresolved_issues = sp_data.get("unresolved_issues", [])
        return sp

    def validate(self) -> List[str]:
        """校验剧本数据完整性，返回问题列表"""
        issues: List[str] = []

        if not self.title:
            issues.append("剧本标题不能为空")
        if not self.acts:
            issues.append("剧本至少需要一个幕（Act）")

        char_ids = {c.id for c in self.characters}
        for c in self.characters:
            for r in c.relationships:
                if r.target_id not in char_ids:
                    issues.append(f"角色 '{c.id}' 的关系引用了不存在的角色 '{r.target_id}'")

        for act in self.acts:
            if not act.scenes:
                issues.append(f"第 {act.act_number} 幕没有场景")
            for scene in act.scenes:
                for cid in scene.characters_present:
                    if cid not in char_ids:
                        issues.append(f"场景 {scene.scene_number} 引用了未定义的角色 '{cid}'")
                for beat in scene.beats:
                    if beat.character and beat.character not in char_ids:
                        issues.append(
                            f"场景 {scene.scene_number} 节拍 {beat.beat_number} "
                            f"引用了未定义的角色 '{beat.character}'"
                        )

        return issues

    def get_statistics(self) -> Dict[str, Any]:
        """获取剧本统计信息"""
        total_scenes = sum(len(act.scenes) for act in self.acts)
        total_beats = sum(len(scene.beats) for act in self.acts for scene in act.scenes)
        dialogue_beats = sum(
            1 for act in self.acts for scene in act.scenes
            for beat in scene.beats
            if beat.type in (BeatType.DIALOGUE, BeatType.MONOLOGUE, BeatType.VOICEOVER)
        )
        action_beats = sum(
            1 for act in self.acts for scene in act.scenes
            for beat in scene.beats
            if beat.type == BeatType.ACTION
        )

        char_dialogue_counts: Dict[str, int] = {}
        for act in self.acts:
            for scene in act.scenes:
                for beat in scene.beats:
                    if beat.character and beat.type in (BeatType.DIALOGUE, BeatType.MONOLOGUE):
                        char_name = next(
                            (c.name for c in self.characters if c.id == beat.character),
                            beat.character
                        )
                        char_dialogue_counts[char_name] = char_dialogue_counts.get(char_name, 0) + 1

        return {
            "title": self.title,
            "acts": len(self.acts),
            "scenes": total_scenes,
            "beats": total_beats,
            "dialogue_beats": dialogue_beats,
            "action_beats": action_beats,
            "characters": len(self.characters),
            "character_dialogue_distribution": dict(
                sorted(char_dialogue_counts.items(), key=lambda x: x[1], reverse=True)
            ),
            "source_chapters": self.original_chapter_count,
        }

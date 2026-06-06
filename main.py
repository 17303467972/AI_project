#!/usr/bin/env python3
"""
AI 小说转剧本工具 — 主入口

用法:
    # 规则模式（快速）
    python main.py samples/sample_novel.txt -o output/screenplay.yaml

    # AI 模式（需要 API Key）
    python main.py samples/sample_novel.txt -o output/screenplay.yaml --mode ai --api-key sk-xxx

    # 打印统计信息
    python main.py samples/sample_novel.txt --stats

    # 验证已有剧本
    python main.py --validate output/screenplay.yaml
"""

import argparse
import sys
import os
from pathlib import Path

# 将 src 加入路径
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import NovelParser
from src.converter import create_converter
from src.schema import Screenplay


def main():
    parser = argparse.ArgumentParser(
        description="AI 小说转剧本工具 - 将 3 章以上小说文本自动转换为结构化 YAML 剧本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py novel.txt -o screenplay.yaml
  python main.py novel.txt --mode ai --api-key sk-xxx
  python main.py novel.txt --stats
  python main.py --validate screenplay.yaml
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="小说文本文件路径 (至少包含 3 章)",
    )
    parser.add_argument(
        "-o", "--output",
        default="output/screenplay.yaml",
        help="输出 YAML 文件路径 (默认: output/screenplay.yaml)",
    )
    parser.add_argument(
        "--mode",
        choices=["rule", "ai"],
        default="rule",
        help="转换模式: rule=规则模式(默认), ai=AI模式",
    )
    parser.add_argument(
        "--api-key",
        help="AI 模式的 API Key (也可通过 DEEPSEEK_API_KEY 环境变量设置)",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.deepseek.com/v1",
        help="API Base URL (默认: https://api.deepseek.com/v1)",
    )
    parser.add_argument(
        "--model",
        default="deepseek-chat",
        help="AI 模型 (默认: deepseek-chat)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="仅打印解析统计，不生成剧本",
    )
    parser.add_argument(
        "--validate",
        help="验证已有的剧本 YAML 文件",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_output",
        help="在终端打印生成的 YAML",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="AI 小说转剧本工具 v1.0.0",
    )

    args = parser.parse_args()

    # 验证模式
    if args.validate:
        return cmd_validate(args.validate)

    # 需要输入文件
    if not args.input:
        parser.print_help()
        print("\n❌ 错误: 请提供小说文本文件路径")
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"❌ 错误: 文件不存在 — {args.input}")
        sys.exit(1)

    # 执行转换
    return cmd_convert(args)


def cmd_convert(args) -> int:
    """执行小说→剧本转换"""
    print(f"\n{'='*60}")
    print(f"🎬 AI 小说转剧本工具 v1.0.0")
    print(f"{'='*60}")
    print(f"📥 输入文件: {args.input}")
    print(f"📤 输出文件: {args.output}")
    print(f"🔧 转换模式: {args.mode.upper()}")
    print(f"{'='*60}\n")

    # 1. 解析小说
    print("📖 正在解析小说文本...")
    try:
        novel = NovelParser.parse(args.input)
    except ValueError as e:
        print(f"❌ 解析失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return 1

    NovelParser.print_summary(novel)

    if args.stats:
        print("📊 仅统计模式，跳过剧本生成。")
        return 0

    # 2. 转换
    print("🔄 正在转换为剧本...")
    converter_kwargs = {}
    if args.mode == "ai":
        api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("⚠️  未提供 API Key，将回退到规则模式")
            args.mode = "rule"
        else:
            converter_kwargs = {
                "api_key": api_key,
                "api_base": args.api_base,
                "model": args.model,
            }

    converter = create_converter(mode=args.mode, **converter_kwargs)
    screenplay = converter.convert(novel)

    # 3. 校验
    print("\n🔍 正在校验剧本...")
    issues = screenplay.validate()
    if issues:
        print(f"⚠️  发现 {len(issues)} 个潜在问题：")
        for issue in issues:
            print(f"   - {issue}")
        screenplay.unresolved_issues = issues
    else:
        print("✅ 校验通过，未发现问题")

    # 4. 统计
    stats = screenplay.get_statistics()
    print(f"\n📊 剧本统计：")
    print(f"   标题: {stats['title']}")
    print(f"   幕数: {stats['acts']}")
    print(f"   场景数: {stats['scenes']}")
    print(f"   节拍数: {stats['beats']} (对话: {stats['dialogue_beats']}, 动作: {stats['action_beats']})")
    print(f"   角色数: {stats['characters']}")
    if stats.get('character_dialogue_distribution'):
        print(f"   角色对话分布:")
        for name, count in list(stats['character_dialogue_distribution'].items())[:5]:
            print(f"     - {name}: {count} 句")

    # 5. 保存
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    screenplay.save(args.output)

    # 6. 可选打印
    if args.print_output:
        print(f"\n{'─'*60}")
        print(screenplay.to_yaml())
        print(f"{'─'*60}")

    print(f"\n🎉 转换完成！")
    print(f"💡 提示: 剧本已保存为 YAML 格式，可使用任何文本编辑器或 YAML 工具编辑打磨。")
    return 0


def cmd_validate(filepath: str) -> int:
    """验证已有剧本 YAML 文件"""
    print(f"\n🔍 正在验证剧本: {filepath}")
    try:
        screenplay = Screenplay.load(filepath)
    except Exception as e:
        print(f"❌ 读取剧本失败: {e}")
        return 1

    print(f"📖 剧本标题: {screenplay.title}")
    print(f"   原著: {screenplay.original_work}")
    print(f"   幕数: {len(screenplay.acts)}")
    print(f"   角色数: {len(screenplay.characters)}")

    issues = screenplay.validate()
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个问题：")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    else:
        print(f"\n✅ 剧本校验通过！")
        stats = screenplay.get_statistics()
        print(f"   场景总数: {stats['scenes']}")
        print(f"   节拍总数: {stats['beats']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

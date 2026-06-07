"""
Flask Web 应用 — 剧本编辑器

提供小说上传转换、YAML 剧本可视化编辑（增删改查）、下载等功能。
"""

import os
import io
import json
import tempfile
from pathlib import Path
from typing import Optional

from flask import (
    Flask, render_template, request, jsonify, send_file,
    session, redirect, url_for,
)

from src.parser import NovelParser
from src.converter import create_converter
from src.schema import Screenplay


# ============================================================
# Flask 应用初始化
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "novel-to-screenplay-dev-key")

# 全局状态：当前剧本（单用户模式）
_current_screenplay: Optional[Screenplay] = None
_current_novel_title: str = ""


# ============================================================
# 页面路由
# ============================================================

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


# ============================================================
# API: 转换
# ============================================================

@app.route("/api/convert", methods=["POST"])
def api_convert():
    """
    上传小说文件并转换为剧本
    
    FormData:
        file: 小说 .txt 文件
        mode: "rule" | "ai"
        api_key: (可选) AI 模式 API Key
    """
    global _current_screenplay, _current_novel_title

    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名为空"}), 400

    mode = request.form.get("mode", "rule")
    api_key = request.form.get("api_key", "").strip()

    # 保存上传文件到临时目录
    suffix = Path(file.filename).suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w", encoding="utf-8") as tmp:
        content = file.read().decode("utf-8")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 解析小说
        novel = NovelParser.parse(tmp_path)
        _current_novel_title = novel.title

        # 创建转换器
        converter_kwargs = {}
        if mode == "ai":
            api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
            converter_kwargs = {
                "api_key": api_key,
                "api_base": request.form.get("api_base", "https://api.deepseek.com/v1"),
                "model": request.form.get("model", "deepseek-chat"),
            }

        converter = create_converter(mode=mode, **converter_kwargs)
        screenplay = converter.convert(novel)
        _current_screenplay = screenplay

        return jsonify({
            "success": True,
            "data": screenplay.to_dict(),
            "stats": screenplay.get_statistics(),
            "mode": mode,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ============================================================
# API: 剧本 CRUD
# ============================================================

@app.route("/api/screenplay", methods=["GET"])
def api_get_screenplay():
    """获取当前剧本完整数据"""
    global _current_screenplay
    if _current_screenplay is None:
        return jsonify({"success": False, "error": "还没有转换剧本"}), 404

    return jsonify({
        "success": True,
        "data": _current_screenplay.to_dict(),
        "stats": _current_screenplay.get_statistics(),
    })


@app.route("/api/screenplay", methods=["PUT"])
def api_update_screenplay():
    """
    从 JSON 整体更新剧本（前端编辑后回存）
    
    Body: 完整的 screenplay dict
    """
    global _current_screenplay
    if _current_screenplay is None:
        return jsonify({"success": False, "error": "还没有转换剧本"}), 404

    try:
        data = request.get_json(force=True)
        _current_screenplay = Screenplay.from_dict(data)
        return jsonify({"success": True, "message": "剧本已更新"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/screenplay/validate", methods=["POST"])
def api_validate():
    """校验当前剧本"""
    global _current_screenplay
    if _current_screenplay is None:
        return jsonify({"success": False, "error": "还没有转换剧本"}), 404

    issues = _current_screenplay.validate()
    return jsonify({
        "success": True,
        "valid": len(issues) == 0,
        "issues": issues,
    })


@app.route("/api/screenplay/download", methods=["GET"])
def api_download():
    """下载当前剧本为 YAML 文件"""
    global _current_screenplay
    if _current_screenplay is None:
        return jsonify({"success": False, "error": "还没有转换剧本"}), 404

    yaml_content = _current_screenplay.to_yaml()

    return send_file(
        io.BytesIO(yaml_content.encode("utf-8")),
        mimetype="application/x-yaml",
        as_attachment=True,
        download_name=f"{_current_novel_title or 'screenplay'}.yaml",
    )


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  🎬 AI 小说转剧本工具 — Web 编辑器")
    print("=" * 55)
    print(f"  🌐 打开浏览器访问: http://127.0.0.1:5000")
    print(f"  📋 按 Ctrl+C 停止服务器")
    print("=" * 55 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)

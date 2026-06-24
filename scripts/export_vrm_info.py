"""解析 VRM（GLB / 二進位 glTF）模型，導出角色相關的所有資料到單一 .txt。

導出內容包含：
- 檔案與 glTF asset 基本資訊
- VRM meta（角色名稱、作者、授權條款等）
- humanoid 骨骼對應表（VRM 骨骼名 -> glTF node 名 / index）
- 表情 / BlendShape（VRM0 blendShapeGroups 或 VRM1 expressions）
- firstPerson / lookAt 設定
- 材質、網格、貼圖、節點清單摘要

用法：
    python scripts/export_vrm_info.py [vrm路徑] [輸出txt路徑]
不帶參數時，預設解析 static/app_dashboard/vrm/1077_Narita_Top_Road.vrm。
"""

from __future__ import annotations

import json
import struct
import sys
from datetime import datetime
from pathlib import Path

# GLB chunk 類型常數
GLB_MAGIC = 0x46546C67  # "glTF"
CHUNK_JSON = 0x4E4F534A  # "JSON"
CHUNK_BIN = 0x004E4942   # "BIN\0"


def parse_glb(file_path: Path) -> dict:
    """讀取 GLB 檔案並回傳其 JSON chunk（dict）。"""
    with file_path.open("rb") as fp:
        header = fp.read(12)
        magic, version, total_length = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            raise ValueError("不是合法的 GLB 檔（magic 不符），可能是純文字 glTF。")

        json_data = None
        while fp.tell() < total_length:
            chunk_header = fp.read(8)
            if len(chunk_header) < 8:
                break
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            chunk_data = fp.read(chunk_length)
            if chunk_type == CHUNK_JSON:
                json_data = json.loads(chunk_data.decode("utf-8"))
                break  # 只需要 JSON chunk

        if json_data is None:
            raise ValueError("找不到 JSON chunk。")
        return json_data


def node_label(gltf: dict, index) -> str:
    """將 node index 轉為「名稱 (#index)」可讀字串。"""
    if index is None:
        return "（無）"
    nodes = gltf.get("nodes", [])
    if isinstance(index, int) and 0 <= index < len(nodes):
        name = nodes[index].get("name", "<未命名>")
        return f"{name} (#{index})"
    return f"#{index}"


def section(title: str) -> str:
    line = "=" * 70
    return f"\n{line}\n{title}\n{line}"


def dump_meta(meta: dict, lines: list, is_vrm1: bool) -> None:
    lines.append(section("VRM Meta（角色 / 授權資訊）"))
    if not meta:
        lines.append("（無 meta 資料）")
        return
    # VRM0 與 VRM1 欄位名稱不同，這裡直接全列出，保留原始 key。
    for key, value in meta.items():
        lines.append(f"- {key}: {value}")


def dump_humanoid(gltf: dict, vrm_ext: dict, lines: list, is_vrm1: bool) -> None:
    lines.append(section("Humanoid 骨骼對應表（VRM 骨骼 -> glTF node）"))
    humanoid = vrm_ext.get("humanoid", {})
    if is_vrm1:
        human_bones = humanoid.get("humanBones", {})
        if not human_bones:
            lines.append("（無 humanBones）")
            return
        for bone_name, info in human_bones.items():
            node_idx = info.get("node") if isinstance(info, dict) else info
            lines.append(f"- {bone_name:<18} -> {node_label(gltf, node_idx)}")
    else:
        human_bones = humanoid.get("humanBones", [])
        if not human_bones:
            lines.append("（無 humanBones）")
            return
        for info in human_bones:
            bone_name = info.get("bone", "<未知>")
            node_idx = info.get("node")
            lines.append(f"- {bone_name:<18} -> {node_label(gltf, node_idx)}")


def dump_expressions(gltf: dict, vrm_ext: dict, vrm1_exp_ext, lines: list, is_vrm1: bool) -> None:
    lines.append(section("表情 / BlendShape 清單"))
    if is_vrm1:
        expressions = (vrm1_exp_ext or {})
        preset = expressions.get("preset", {})
        custom = expressions.get("custom", {})
        if preset:
            lines.append("[Preset 預設表情]")
            for name in preset.keys():
                lines.append(f"- {name}")
        if custom:
            lines.append("[Custom 自訂表情]")
            for name in custom.keys():
                lines.append(f"- {name}")
        if not preset and not custom:
            lines.append("（無表情資料）")
    else:
        groups = vrm_ext.get("blendShapeMaster", {}).get("blendShapeGroups", [])
        if not groups:
            lines.append("（無 blendShapeGroups）")
            return
        for grp in groups:
            name = grp.get("name", "<未命名>")
            preset = grp.get("presetName", "-")
            binds = grp.get("binds", [])
            lines.append(f"- name={name} | presetName={preset} | binds={len(binds)}")


def dump_first_person(vrm_ext: dict, lines: list, is_vrm1: bool, vrm1_lookat=None) -> None:
    lines.append(section("FirstPerson / LookAt"))
    if is_vrm1:
        lines.append(f"lookAt: {json.dumps(vrm1_lookat, ensure_ascii=False) if vrm1_lookat else '（無）'}")
    else:
        fp = vrm_ext.get("firstPerson", {})
        lines.append(f"firstPersonBone: {fp.get('firstPersonBone')}")
        lines.append(f"lookAtTypeName: {fp.get('lookAtTypeName')}")


def dump_collections(gltf: dict, lines: list) -> None:
    lines.append(section("glTF 資源摘要"))
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    materials = gltf.get("materials", [])
    textures = gltf.get("textures", [])
    images = gltf.get("images", [])
    skins = gltf.get("skins", [])
    lines.append(f"node 數量   : {len(nodes)}")
    lines.append(f"mesh 數量   : {len(meshes)}")
    lines.append(f"material 數 : {len(materials)}")
    lines.append(f"texture 數  : {len(textures)}")
    lines.append(f"image 數    : {len(images)}")
    lines.append(f"skin 數     : {len(skins)}")

    lines.append("\n[Mesh 名稱]")
    for i, mesh in enumerate(meshes):
        lines.append(f"  #{i}: {mesh.get('name', '<未命名>')}")

    lines.append("\n[Material 名稱]")
    for i, mat in enumerate(materials):
        lines.append(f"  #{i}: {mat.get('name', '<未命名>')}")

    lines.append("\n[全部 Node 名稱]")
    for i, node in enumerate(nodes):
        lines.append(f"  #{i}: {node.get('name', '<未命名>')}")


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    default_vrm = project_root / "static" / "app_dashboard" / "vrm" / "1077_Narita_Top_Road.vrm"
    default_out = project_root / "narita-top-road-vrm-data.txt"

    vrm_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_vrm
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else default_out

    if not vrm_path.exists():
        print(f"[錯誤] 找不到 VRM 檔案：{vrm_path}")
        return 1

    print(f"[INFO] 解析中：{vrm_path}")
    gltf = parse_glb(vrm_path)

    extensions = gltf.get("extensions", {})
    is_vrm1 = "VRMC_vrm" in extensions
    if is_vrm1:
        vrm_ext = extensions.get("VRMC_vrm", {})
        meta = vrm_ext.get("meta", {})
        vrm1_exp_ext = vrm_ext.get("expressions", {})
        vrm1_lookat = vrm_ext.get("lookAt", {})
    else:
        vrm_ext = extensions.get("VRM", {})
        meta = vrm_ext.get("meta", {})
        vrm1_exp_ext = None
        vrm1_lookat = None

    lines: list[str] = []
    lines.append("賽馬娘客服「成田路」3D 角色（VRM）資料導出")
    lines.append(f"導出時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（台北時間）")
    lines.append(section("檔案資訊"))
    size_mb = vrm_path.stat().st_size / (1024 * 1024)
    lines.append(f"檔名      : {vrm_path.name}")
    lines.append(f"路徑      : {vrm_path}")
    lines.append(f"檔案大小  : {size_mb:.2f} MB")
    lines.append(f"VRM 版本  : {'VRM 1.0 (VRMC_vrm)' if is_vrm1 else 'VRM 0.x (VRM)'}")
    asset = gltf.get("asset", {})
    lines.append(f"glTF asset: generator={asset.get('generator')} | version={asset.get('version')}")
    lines.append(f"全部 extensions: {', '.join(extensions.keys()) or '（無）'}")

    dump_meta(meta, lines, is_vrm1)
    dump_humanoid(gltf, vrm_ext, lines, is_vrm1)
    dump_expressions(gltf, vrm_ext, vrm1_exp_ext, lines, is_vrm1)
    dump_first_person(vrm_ext, lines, is_vrm1, vrm1_lookat)
    dump_collections(gltf, lines)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[完成] 已導出：{out_path}")
    print(f"[完成] 共 {len(lines)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

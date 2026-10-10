"""P3 探针：把 image_gate 跑在两张入库测试图上，把结果落成 evidence JSON（判据 P3-3）。

跑法（不打网络，产物字节可复现）::

    python skills/douyin-pro/scripts/p3_probe.py

输出：
- ``routes/news/evidence/2026-10-10-p3-probe/probe-result.json`` —— 每张图的
  detector_available / hits / floor / 连通域 / sha 摘要。
- 反-反例：gear-01.jpg 跑黑名单（frontalface_default + upperbody）出假阳计数，
  证明黑名单不是摆设（判据 P3-2）。

自检（``path_b_selftest``）会直接调 image_gate 做同样断言，本脚本只负责把结论
落盘 —— 这样「探针绿」和「selftest 绿」用的是**同一份实现**，不留第二条实现路径。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import image_gate as gate  # noqa: E402

FIXTURE_DIR = (Path(__file__).resolve().parents[3]
               / "routes" / "news" / "evidence" / "2026-10-10-p3-probe")
FACE = FIXTURE_DIR / "face-01.jpg"
GEAR = FIXTURE_DIR / "gear-01.jpg"
RESULT = FIXTURE_DIR / "probe-result.json"


def _entry(path: Path, *, cascade_names: tuple[str, ...] = gate._ALLOWED_CASCADES) -> dict:
    result = gate.detect_faces(path, cascade_names=cascade_names)
    return {
        "file": path.name,
        "sha256_short": gate.digest_bytes(path),
        "detector_available": result.detector_available,
        "floor": result.floor,
        "hits": len(result.faces),
        "boxes": [list(b.to_tuple()) for b in result.faces],
        "cascades": list(cascade_names),
    }


def main() -> int:
    if not gate.capability_ok():
        print("[p3_probe] image_gate 能力未就绪（cv2 或 cascade 缺失）", file=sys.stderr)
        return 1
    payload = {
        "capability_ok": True,
        "min_short_edge": gate.MIN_SHORT_EDGE,
        "min_neighbors": gate.MIN_NEIGHBORS,
        "min_size_px": gate.MIN_SIZE_PX,
        "allowed_cascades": list(gate._ALLOWED_CASCADES),
        "denied_cascades": list(gate._DENIED_CASCADES),
        "primary": [_entry(FACE), _entry(GEAR)],
        "blacklist_control": [_entry(
            GEAR, cascade_names=gate._DENIED_CASCADES)],
    }
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"[p3_probe] 写入 {RESULT.relative_to(FIXTURE_DIR.parents[2])}")
    for row in payload["primary"]:
        print(f"  {row['file']:15s} floor={row['floor']} hits={row['hits']}")
    for row in payload["blacklist_control"]:
        print(f"  反-反例 {row['file']} 上黑名单命中 {row['hits']} 处 "
              f"（证明黑名单必须显式拒绝，不是'没被选中'）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

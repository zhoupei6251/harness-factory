"""P3 图片门禁 · 本地零网络的人脸检测器（设计文档 §2）。

**这里只判"有没有可指认的脸"** —— 检出 = floor=G0，检不出 = floor=None。
G1/G2 的场景可推断性本轮不可测，交给作者声明（设计 §3），检测器不越权。

四条硬法则，都由 selftest 或探针的产物钉住：

1. **四通道并集**：``{frontalface_alt2, profileface} × {原图, 水平镜像}``，
   ``minNeighbors≥3``、``minSize≥24px``。镜像那一维不是可选：测得 Obama 官像
   ``frontalface_alt2`` 原图 1 命中 / 镜像 2 命中 —— 侧向脸只在镜像侧起效。
2. **黑名单硬编码**：``frontalface_default``（齿轮图上跑 4 次假阳）、
   ``upperbody``（同一张图 2 次假阳）。测于 2026-10-10 的两张入库测试图
   （``routes/news/evidence/2026-10-10-p3-probe/``），
   探针必须含一条**反-反例**证明黑名单不是摆设（判据 P3-2）。
3. **确定性**：检测是图字节的纯函数 —— 同图同档、同图同命中框。判据 4a
   对视频流的字节一致要求，就靠这条守住：构建期取到同一张 Commons 缩略图，
   两次跑 grade 必一致。
4. **短边定标**：``minSize≥24px`` 依赖像素尺度，同图不同尺寸 grade 会翻。
   ``detect_faces`` 入口把缩略图归一到 ``MIN_SHORT_EDGE=720``（对齐
   ``commons_media.MIN_SHORT_EDGE``）再检 —— 产线和探针共用这一个常数。

失效口径（设计 §6.5 硬规则 3）：**cv2 装不上 / cascade 加载不出 / 图字节读不出，
一律当"检测器不可用"（`detector_available=False`）** —— 由调用方（`compose_grade`）
把这一档抬到 G0。本模块只提供判据事实，不做保守合成；`compose_grade` 是同模块的
纯函数合成层，产线与探针都走它，不各写一份。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

#: 检测输入定标基线。与 commons_media.MIN_SHORT_EDGE 同值 —— 不是巧合，是"喂进检测器
#: 的图就是产线下载的缩略图"这条链的锚：产线下的图短边 720，检测器归一化到 720，
#: minSize=24px 落在同一个尺度上。改一处就要改另一处，否则 minNeighbors 阈值语义漂了。
MIN_SHORT_EDGE = 720
#: Haar 检出的两参数 —— 阈值在 2026-10-10 的两张入库图上校准（见模块 docstring 法则 1/2）。
#: minNeighbors 用 3 不用默认 5：Obama 官像的 alt2 在 5 上仍命中，但镜像侧降到 4-5 之间会
#: 漏，24 起 3 是唯一同时保住"真脸全中"和"齿轮零假阳"的位置。
MIN_NEIGHBORS = 3
MIN_SIZE_PX = 24

#: 白名单 —— 只有这两张 cascade 参与判定。
_ALLOWED_CASCADES = ("frontalface_alt2", "profileface")
#: 黑名单 —— 显式列出、显式拒绝（不是"没被选中"，是"不许被选中"）。探针会独立跑它们
#: 出反-反例（P3-2），产线永远不碰。
_DENIED_CASCADES = ("frontalface_default", "upperbody")


@dataclass(frozen=True)
class Box:
    """检测到的连通域（原图坐标系，非归一化坐标）。裁剪复检要用回原图尺度。"""
    x: int
    y: int
    w: int
    h: int

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)


@dataclass(frozen=True)
class GradeResult:
    """一次检测的完整结论。``floor`` 只有检测器能给的档：G0 或 None。

    ``detector_available=False`` → ``floor`` **必为 None**（检测器没结果，不硬造），
    保守合成由调用方（grade 合成的 ``max(author, floor)``）完成，见设计 §3。
    """
    detector_available: bool
    faces: tuple[Box, ...]
    floor: str | None

    @property
    def hit(self) -> bool:
        return bool(self.faces)


def _cascade_paths() -> dict[str, Path]:
    """返回 6 张 cascade（4 允许 + 2 拒绝黑名单）的路径。

    黑名单里列的两张也解析路径，是为了**让探针能独立跑它们出反-反例**（P3-2）——
    产线的 ``detect_faces`` 不看它们；这里的"看得见"不是"能用"。
    """
    try:
        import cv2  # noqa: F401  只为拿包内 data/ 目录
    except ImportError:
        return {}
    import cv2 as _cv2
    data = Path(_cv2.data.haarcascades)
    out: dict[str, Path] = {}
    for name in _ALLOWED_CASCADES + _DENIED_CASCADES:
        p = data / f"haarcascade_{name}.xml"
        if p.exists():
            out[name] = p
    return out


def capability_ok() -> bool:
    """检测器这个**能力**是否就绪：cv2 可 import ∧ 两张白名单 cascade 都在。

    黑名单不参与本判定 —— 它们是"要证明无效"的对照组，缺了不影响检测能力，
    只影响反-反例探针能不能跑（那个是 evidence 层的检查，不进产线闸门）。
    """
    paths = _cascade_paths()
    return all(name in paths for name in _ALLOWED_CASCADES)


def _normalize(img, base: int = MIN_SHORT_EDGE):
    """把输入图短边缩放到 ``base``；cv2 返回 None 或空图原样回传。"""
    import cv2
    h, w = img.shape[:2]
    if min(h, w) == base:
        return img
    scale = base / min(h, w)
    return cv2.resize(img, (int(round(w * scale)), int(round(h * scale))))


def _load_gray(path: Path):
    """按字节读图 → 灰度。返回 None 表示文件缺失或不是可读图像。

    不做直方图均衡： Obama / 齿轮图两组实测（2026-10-10）在均衡前后一致，均衡会让
    一些低对比照片虚高假阳 —— 保守方向应该"宁可漏检也不误认脸"？反过来：漏检把
    人脸当无脸→G2 满屏更危险。**保留均衡**、把保守留给合成层：这里检出多少脸就报多少，
    detector 失效或漏检由 floor 语义（G0 只由"真检出"或"检测器不可用"给）承担。
    """
    import cv2
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _detect_on(gray, cascade, *, flip: bool) -> list[Box]:
    """在一个（原图或镜像）通道上跑一张 cascade，返回归一化尺度下的框。"""
    import cv2
    buf = cv2.flip(gray, 1) if flip else gray
    buf = cv2.equalizeHist(buf)
    hits = cascade.detectMultiScale(
        buf, scaleFactor=1.1, minNeighbors=MIN_NEIGHBORS,
        minSize=(MIN_SIZE_PX, MIN_SIZE_PX))
    if hits is None:
        return []
    boxes = [Box(int(x), int(y), int(w), int(h)) for (x, y, w, h) in hits]
    if flip:
        # 镜像框回到原图横坐标：x' = W − x − w
        width = gray.shape[1]
        boxes = [Box(width - b.x - b.w, b.y, b.w, b.h) for b in boxes]
    return boxes


def detect_faces(image_path: str | Path,
                 *, cascade_names: tuple[str, ...] = _ALLOWED_CASCADES) -> GradeResult:
    """对一张图跑「(白名单 ∪ 指定对照) × {原图, 镜像}」四通道并集，返回 grade 事实。

    ``cascade_names`` 参数化只为**探针能显式指定黑名单出反-反例**（P3-2），
    产线调用不传该参数、行为等同于只跑白名单四通道。传黑名单项时要求文件存在，
    否则该通道被跳过（不当作假阳也不当作"文件缺失"）。
    """
    paths = _cascade_paths()
    if not paths:
        return GradeResult(detector_available=False, faces=(), floor=None)
    try:
        import cv2
    except ImportError:
        return GradeResult(detector_available=False, faces=(), floor=None)

    cascades = []
    for name in cascade_names:
        p = paths.get(name)
        if p is None:
            continue
        clf = cv2.CascadeClassifier(str(p))
        if clf.empty():
            continue
        cascades.append(clf)
    if not cascades:
        # 指定了 cascade_names 但一张也加载不出来 —— 不是能力缺失，是入参错。
        # 让调用方自己判定：产线路径永远传默认白名单，走到这里说明 cv2 或 xml 坏了。
        return GradeResult(detector_available=False, faces=(), floor=None)

    path = Path(image_path)
    gray = _load_gray(path)
    if gray is None:
        # 图字节读不出来 —— 这**不是** detector_available=False（能力还在），
        # 只是这一张图检不了；保守由调用方处理，不在此发明档。
        return GradeResult(detector_available=True, faces=(), floor=None)

    norm = _normalize(gray)
    boxes: list[Box] = []
    for clf in cascades:
        for flip in (False, True):
            boxes.extend(_detect_on(norm, clf, flip=flip))
    # 归一化尺度 → 原图像素尺度（crop_and_recheck 要用原图坐标 mask 掉连通域）
    scale = MIN_SHORT_EDGE / min(gray.shape[:2])
    if scale and scale != 1.0:
        boxes = [Box(int(b.x / scale), int(b.y / scale),
                     int(b.w / scale), int(b.h / scale)) for b in boxes]
    # 去重（同脸被 orig/mirror 两路各报一次时视为一次；用整数框本身做键，纯字节可复现）
    uniq = sorted({b.to_tuple() for b in boxes})
    faces = tuple(Box(*t) for t in uniq)
    return GradeResult(detector_available=True, faces=faces,
                       floor=("G0" if faces else None))


def crop_and_recheck(image_path: str | Path, faces: tuple[Box, ...]) -> bool:
    """把 faces 连通域 mask 成中灰（haar 认不出结构）后**再检一次**，仍命中 → True。

    设计 §7：G0 想用只能"裁掉脸再复检"，仍命中就弃图。这里用"填中灰"而非"crop 掉"——
    裁走会挪动其余脸的坐标、破坏连通域关系；掩平不留假边。返回值语义：
    True = 掩完还有脸（应弃图），False = 掩干净了（可用）。
    """
    import cv2
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        return True                     # 读不出就当作"仍命中"，宁可弃
    for b in faces:
        x2 = min(img.shape[1], b.x + b.w)
        y2 = min(img.shape[0], b.y + b.h)
        img[b.y:y2, b.x:x2] = (128, 128, 128)
    tmp = Path(image_path).with_suffix(".mask-probe.png")
    cv2.imwrite(str(tmp), img)
    try:
        result = detect_faces(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return result.hit


def digest_bytes(path: str | Path) -> str:
    """测试图字节摘要，进 evidence 记录 —— 同 sha 同档是判据 4a 的静态锚。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


# ---------------------------------------------------------------- 档合成（设计 §3）

#: 序 G0 > G1 > G2（**越靠左越受限**），合成用 `max(…，key=档位)`。
GRADE_ORDER = ("G2", "G1", "G0")
#: 作者合同 `imageGrade` 的取值 → 内部档字符串。作者**不能**声明 G0（那是机器事实）。
AUTHOR_GRADE_TO_CODE = {"scene": "G1", "material": "G2"}
#: 未声明时的默认档。设计 §3："作者没写 imageGrade → 默认 G1，不是 G0"。
#: 默认 G0 会让"作者漏标一次就永久丢图"，过苛；G1 仍强制裁切+压色去识别，安全且可用。
DEFAULT_AUTHOR_GRADE = "scene"


def synth_grade(author_grade: str | None, detector: GradeResult) -> str:
    """`final = max(author_grade, detector_floor)`，序 G0 > G1 > G2。

    - ``author_grade`` 只认 ``"scene"|"material"``；``None`` → ``"scene"``（G1 默认）。
      传别的字符串**抛 ValueError** —— 静默默认会让拼错的作者合同被当成"没写"，
      判据 P3-4 的"未声明→G1"就变成"任何非 scene/material 输入→G1"。
    - ``detector.detector_available=False`` → floor 硬抬到 G0（§6.5 硬规则 3：
      检测器坏 = 不能相信"没测到脸"，按最坏当可指认）。
    - ``detector.floor`` 是 ``"G0"`` 或 ``None``（True/False 的语义在 §2 定死），
      None 表示"检不出脸，floor 不参与合成"。
    """
    key = (author_grade if author_grade is not None else DEFAULT_AUTHOR_GRADE)
    if not isinstance(key, str) or key not in AUTHOR_GRADE_TO_CODE:
        raise ValueError(
            f"作者档只能是 'scene'/'material'/None（未声明），收到 {author_grade!r} —— "
            "G0 是机器事实不是作者选项，拼错静默回落会把合同缺陷藏成生产数据")
    author_code = AUTHOR_GRADE_TO_CODE[key]
    if not detector.detector_available:
        floor_code = "G0"
    elif detector.floor is None:
        floor_code = None
    else:
        floor_code = detector.floor
    if floor_code is None:
        return author_code
    return max((author_code, floor_code), key=GRADE_ORDER.index)


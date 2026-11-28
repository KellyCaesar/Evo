"""对局模式（`matches.mode` 存的值）：有哪几种、显示成什么名字、哪种用排位那套（RP、段位、六维图）。

页面和统计里一共四种（2026-11-28 用户定的）：
- ranked 排位、pubs 匹配：开局横幅读出来的（config/match_start.json 的 modes）
- wildcard 外卡：大逃杀的一种轮换玩法（2026-11-23 起）。结算页最后两行是"最后幸存""自我急救"，不是给予急救、
  给予重生（见 config/summary.json 的 wildcard），所以外卡局自己和队友的 revives / respawns 都留空
- other 其他：除了上面三种的局都算这里：认出是别的玩法的（存的是 other），没认出模式的（存的是 None，
  数据库里照原样留空，只是统计、筛选时算进"其他"），还有历史数据里不认识的值
只有排位用 RP、段位、校准和六维图（六维图只算排位局，见 radar.py）。

加一种新玩法：`MODES` 里加一条，再把横幅文字写进 config/match_start.json 的 modes、参照图写进 config/screens.json、
结算页最后两行的标签（结算页上能和普通局分开时）写进 config/summary.json 的同名段落和各语言配置。
结算页兜底认模式（summary_page.detect_mode）、跳过不写的字段（skip_fields）、统计、页面筛选会自动用上；
服务器（server/stats/worker.js 的 modeGroup）要另外加上，部署以后才有这种模式的"全体玩家"汇总。

属性（`MODES` 的每一项）：
- label：显示的名字（战绩页、数据页、分享卡、录像页都用它）
- ranked：用不用排位那套（RP、段位、校准、六维图）
- summary：config/summary.json 里的段落名（结算页最后两行对得上就认成这个模式）；None = 没有结算页标签

只用标准库：面板会导入它，不能带上识别引擎（见 tests/test_light.py）。
"""

RANKED, PUBS, WILDCARD, OTHER = "ranked", "pubs", "wildcard", "other"

# 顺序就是页面上按钮的顺序
MODES = {
    RANKED: {"label": "排位", "ranked": True, "summary": None},
    PUBS: {"label": "匹配", "ranked": False, "summary": None},
    WILDCARD: {"label": "外卡", "ranked": False, "summary": "wildcard"},
    OTHER: {"label": "其他", "ranked": False, "summary": None},
}

# 模式的值 → 显示的名字（也是战绩页修改表单、各页模式筛选的选项）
LABELS = {mode: spec["label"] for mode, spec in MODES.items()}


def group(mode):
    """这一局在筛选、统计里算哪种模式：排位、匹配、外卡照原样，其余的（None、other、历史数据里不认识的值）算"其他"。
    和服务器 server/stats/worker.js 的 modeGroup 一样。"""
    return mode if mode in MODES else OTHER


def label(mode, unknown="—"):
    """数据库里存的模式 → 显示的名字。没认出（None）返回 unknown，没登记的值算"其他"。"""
    if mode is None:
        return unknown
    return MODES[group(mode)]["label"]


def is_ranked(mode):
    """要不要用排位那套（RP、段位、校准、六维图）。"""
    return bool((MODES.get(mode) or {}).get("ranked"))


def summary_key(mode):
    """这个模式在 config/summary.json 里的段落名（结算页兜底认模式用）；没有返回 None。"""
    return (MODES.get(mode) or {}).get("summary")


def summary_modes():
    """有结算页标签的模式：{config/summary.json 的段落名: 模式值}。"""
    return {spec["summary"]: mode for mode, spec in MODES.items() if spec["summary"]}


def is_rotational(mode):
    """是不是有自己结算页标签的轮换玩法（外卡……）：这类模式最后两项不是急救、重生。"""
    return summary_key(mode) is not None


def where(key):
    """筛选键（MODES 里的一个）→ (SQL 条件, 参数)，战绩页的 SQL 筛选用（storage._where）。和 group 同一套口径。"""
    if key == OTHER:
        known = [mode for mode in MODES if mode != OTHER]
        return f"(mode IS NULL OR mode NOT IN ({', '.join('?' for _ in known)}))", known
    return "mode = ?", [key]

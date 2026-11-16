"""Command-line interface. All commands accept ``--json`` anywhere in argv."""

import argparse
import getpass
import json
import sys

from . import config as config_module
from .auth import Authenticator
from .client import build_reserver
from .errors import CcnuError, NotConfigured, UpstreamBlocked, UsageError
from .reservation import validate_window
from .session_cache import SessionCache
from .spaces import SPACE_CODES
from .timeutil import Window


def _window(args):
    return Window.from_strings(args.date, args.start, args.end)


def _hhmm(minutes):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def _resolve_building(catalog, needle):
    if needle:
        matches = [
            building
            for building in catalog.buildings
            if building.id == needle or needle in building.name
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise UsageError(
                "未找到馆舍 %s；可选：%s"
                % (needle, "、".join(building.name for building in catalog.buildings))
            )
        raise UsageError(
            "馆舍名称不唯一：%s"
            % "、".join("%s(%s)" % (building.name, building.id) for building in matches)
        )
    if len(catalog.buildings) == 1:
        return catalog.buildings[0]
    matches = [
        building for building in catalog.buildings if "南湖" in building.name
    ]
    if len(matches) == 1:
        return matches[0]
    raise UsageError(
        "请用 --building 指定馆舍；可选：%s"
        % "、".join(building.name for building in catalog.buildings)
    )


def _resolve_floor(building, needle):
    if needle:
        matches = [
            floor
            for floor in building.floors
            if floor.id == needle or needle in floor.name
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise UsageError(
                "未找到楼层 %s；可选：%s"
                % (needle, "、".join(floor.name for floor in building.floors))
            )
        raise UsageError(
            "楼层名称不唯一：%s"
            % "、".join("%s(%s)" % (floor.name, floor.id) for floor in matches)
        )
    if len(building.floors) == 1:
        return building.floors[0]
    raise UsageError(
        "请用 --floor 指定楼层；可选：%s"
        % "、".join(floor.name for floor in building.floors)
    )


def _resolve_space(reserver, needle, window):
    if needle in SPACE_CODES:
        return SPACE_CODES[needle]["id"]
    if needle.isdigit():
        return needle
    catalog = reserver.catalog()
    hits = []
    for building in catalog.buildings:
        for floor in building.floors:
            for space in reserver.list_spaces(building.id, floor.id, window):
                if needle in space.name:
                    hits.append(space)
    if len(hits) == 1:
        return hits[0].id
    if not hits:
        raise UsageError("未找到 Space %s；先运行 ccnu spaces 查看" % needle)
    raise UsageError(
        "Space 名称不唯一：%s"
        % "、".join("%s(%s)" % (space.name, space.id) for space in hits)
    )


def cmd_status(args):
    try:
        credentials = config_module.load_credentials()
    except NotConfigured:
        return (
            {
                "configured": False,
                "config_path": config_module.default_config_path(),
            },
            "未配置凭据。请运行 ccnu login。",
        )
    masked = config_module.mask_student_id(credentials.stu_id)
    return (
        {
            "configured": True,
            "stu_id": masked,
            "source": credentials.source,
            "config_path": config_module.default_config_path(),
        },
        "已配置凭据：%s（来源 %s）" % (masked, credentials.source),
    )


def _prompt_student_id(args, existing):
    if args.stu_id:
        return args.stu_id.strip()
    if args.password_stdin:
        if existing is None:
            raise UsageError("--password-stdin 需要配合 --stu-id 使用")
        return existing.stu_id
    if not sys.stdin.isatty():
        raise UsageError(
            "当前没有可交互终端：去掉 --tty 用浏览器登录，或使用 --stu-id 和 --password-stdin"
        )
    if existing is not None:
        entered = input(
            "学号 [%s]: " % config_module.mask_student_id(existing.stu_id)
        ).strip()
        return entered or existing.stu_id
    return input("学号: ").strip()


def _read_password(args):
    if args.password_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    if not sys.stdin.isatty():
        raise UsageError(
            "当前没有可交互终端：去掉 --tty 用浏览器登录，或使用 --password-stdin"
        )
    return getpass.getpass("密码: ")


def cmd_login(args):
    selected = [flag for flag in (args.web, args.tty, args.password_stdin) if flag]
    if len(selected) > 1:
        raise UsageError("--web、--tty、--password-stdin 只能选一个")
    use_web = args.web or not (args.tty or args.password_stdin)
    try:
        existing = config_module.load_credentials()
    except NotConfigured:
        existing = None

    if use_web:
        from .web_login import prompt_credentials

        hint = args.stu_id or (existing.stu_id if existing else "")
        credentials = prompt_credentials(hint, timeout=args.web_timeout)
        if credentials is None:
            raise UsageError("登录页等待超时，请重试")
        stu_id, password = credentials
    else:
        stu_id = _prompt_student_id(args, existing)
        password = _read_password(args)

    if not stu_id or not password:
        raise UsageError("学号和密码不能为空")

    token = None
    verification = "skipped"
    if not args.no_verify:
        try:
            token = Authenticator().login(stu_id, password)
            verification = "verified"
        except UpstreamBlocked:
            # The site closes overnight; keep the credentials so the user does
            # not have to type them again tomorrow.
            verification = "unavailable"
    path = config_module.save_credentials(stu_id, password)
    if token:
        # Reuse the verification login for the first command.
        SessionCache().save(stu_id, token)
    masked = config_module.mask_student_id(stu_id)
    if verification == "verified":
        text = "凭据已保存并验证：%s" % masked
    elif verification == "unavailable":
        text = "凭据已保存；预约系统当前不可用（可能夜间关闭），白天会自动验证：%s" % masked
    else:
        text = "凭据已保存（未验证）：%s" % masked
    return (
        {
            "configured": True,
            "stu_id": masked,
            "config_path": path,
            "verification": verification,
        },
        text,
    )


def cmd_catalog(args):
    catalog = build_reserver().catalog()
    payload = {
        "buildings": [
            {
                "id": building.id,
                "name": building.name,
                "floors": [
                    {"id": floor.id, "name": floor.name, "building_id": floor.building_id}
                    for floor in building.floors
                ],
            }
            for building in catalog.buildings
        ],
        "dates": catalog.dates,
    }
    lines = []
    for building in catalog.buildings:
        lines.append(building.name)
        for floor in building.floors:
            lines.append("  - %s  id=%s" % (floor.name, floor.id))
    lines.append("可选日期：" + "、".join(catalog.dates))
    return payload, "\n".join(lines)


def cmd_spaces(args):
    window = _window(args)
    reserver = build_reserver()
    catalog = reserver.catalog()
    building = _resolve_building(catalog, args.building)
    floor = _resolve_floor(building, args.floor)
    spaces = reserver.list_spaces(building.id, floor.id, window)
    payload = {
        "date": window.date_string,
        "start_minute": window.start_minute,
        "end_minute": window.end_minute,
        "building": {"id": building.id, "name": building.name},
        "floor": {"id": floor.id, "name": floor.name},
        "spaces": [
            {
                "id": space.id,
                "name": space.name,
                "seat_total": space.seat_total,
                "seat_free": space.seat_free,
            }
            for space in spaces
        ],
    }
    lines = [
        "%s  %d/%d 空闲  id=%s"
        % (space.name, space.seat_free, space.seat_total, space.id)
        for space in spaces
    ]
    return payload, "\n".join(lines) or "该时段没有可用 Space。"


def cmd_seats(args):
    window = _window(args)
    reserver = build_reserver()
    space_id = _resolve_space(reserver, args.space, window)
    seats = reserver.list_free_seats(space_id, window)
    payload = {
        "space_id": space_id,
        "date": window.date_string,
        "start_minute": window.start_minute,
        "end_minute": window.end_minute,
        "count": len(seats),
        "seats": [
            {"id": seat.id, "label": seat.label, "name": seat.name} for seat in seats
        ],
    }
    lines = [
        "%s  id=%s" % (seat.label or seat.name or seat.id, seat.id) for seat in seats
    ]
    return payload, "\n".join(lines) or "该时段没有空位。"


def cmd_reserve(args):
    window = _window(args)
    reserver = build_reserver()
    info = reserver.system_info()
    validate_window(window, info.step, info.max_duration)
    base = {
        "seat_id": args.seat,
        "date": window.date_string,
        "start_minute": window.start_minute,
        "end_minute": window.end_minute,
        "duration_minutes": window.duration_minutes,
        "step_minute": info.step,
        "max_minute": info.max_duration,
    }
    when = "%s %s-%s" % (
        window.date_string,
        _hhmm(window.start_minute),
        _hhmm(window.end_minute),
    )
    if not args.yes:
        payload = dict(base)
        payload["dry_run"] = True
        return (
            payload,
            "演练：将预约 seat %s，%s（%d 分钟）。用户明确确认后加 --yes。"
            % (args.seat, when, window.duration_minutes),
        )
    reservation = reserver.reserve(args.seat, window)
    payload = dict(base)
    payload.update({"dry_run": False, "reservation_id": reservation.id})
    return (
        payload,
        "已预约：seat %s，%s，reservation id=%s"
        % (args.seat, when, reservation.id),
    )


def cmd_cancel(args):
    reserver = build_reserver()
    if not args.yes:
        return (
            {"dry_run": True, "reservation_id": args.reservation_id},
            "演练：将取消预约 %s。用户明确确认后加 --yes。"
            % args.reservation_id,
        )
    reserver.cancel(args.reservation_id)
    return (
        {
            "dry_run": False,
            "reservation_id": args.reservation_id,
            "cancelled": True,
        },
        "已取消预约 %s。" % args.reservation_id,
    )


def cmd_last(args):
    records = build_reserver().last_make()
    lines = []
    for record in records:
        lines.append(
            "id=%s  seatId=%s  makeDate=%s"
            % (
                record.get("id", ""),
                record.get("seatId", ""),
                record.get("makeDate", ""),
            )
        )
    return {"reservations": records}, "\n".join(lines) or "没有最近预约。"


def cmd_me(args):
    info = build_reserver().user_info()
    username = info.get("username") or ""
    return {"username": username}, "用户：%s" % (username or "(未知)")


def cmd_rules(args):
    info = build_reserver().system_info()
    payload = {
        "step_minute": info.step,
        "max_minute": info.max_duration,
        "future_make_day": info.future_make_day,
        "hmac": info.hmac,
    }
    return (
        payload,
        "Step=%d 分钟，Max Duration=%d 分钟，可约未来 %d 天"
        % (info.step, info.max_duration, info.future_make_day),
    )


def cmd_history(args):
    records = build_reserver().history(args.page_size, args.page)
    payload = {
        "page": args.page,
        "page_size": args.page_size,
        "records": records,
    }
    return payload, "共 %d 条记录" % len(records)


def _add_window_args(parser):
    parser.add_argument("--date", required=True, help="日期，YYYY-MM-DD（Asia/Shanghai）")
    parser.add_argument("--start", required=True, help="开始时间，HH:MM")
    parser.add_argument("--end", required=True, help="结束时间，HH:MM")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ccnu",
        description="CCNU 图书馆座位预约（所有命令都支持 --json）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="查看是否已配置凭据")
    status.set_defaults(func=cmd_status)

    login = subparsers.add_parser("login", help="保存学号和密码（默认打开浏览器登录页）")
    login.add_argument("--stu-id", help="学号（默认沿用已保存的学号）")
    login.add_argument(
        "--password-stdin", action="store_true", help="从 stdin 读取密码"
    )
    login.add_argument(
        "--web", action="store_true", help="打开本机浏览器登录页（默认行为）"
    )
    login.add_argument(
        "--tty", action="store_true", help="在终端隐藏输入密码（需要可交互终端）"
    )
    login.add_argument(
        "--web-timeout", type=int, default=180, help="登录页等待秒数（默认 180）"
    )
    login.add_argument("--no-verify", action="store_true", help="保存前不验证登录")
    login.set_defaults(func=cmd_login)

    catalog = subparsers.add_parser("catalog", help="列出馆舍、楼层和可选日期")
    catalog.set_defaults(func=cmd_catalog)

    spaces = subparsers.add_parser("spaces", help="查看楼层内各 Space 的空位数")
    _add_window_args(spaces)
    spaces.add_argument("--building", help="馆舍名称或 ID（默认南湖分馆）")
    spaces.add_argument("--floor", help="楼层名称或 ID")
    spaces.set_defaults(func=cmd_spaces)

    seats = subparsers.add_parser("seats", help="查看整个时段的 Free Seats")
    _add_window_args(seats)
    seats.add_argument("--space", required=True, help="Space code、ID 或名称")
    seats.set_defaults(func=cmd_seats)

    reserve = subparsers.add_parser("reserve", help="预约座位（默认演练）")
    _add_window_args(reserve)
    reserve.add_argument("--seat", required=True, help="Seat ID")
    reserve.add_argument("--yes", action="store_true", help="真实下单")
    reserve.set_defaults(func=cmd_reserve)

    cancel = subparsers.add_parser("cancel", help="取消预约（默认演练）")
    cancel.add_argument("reservation_id", help="Reservation ID")
    cancel.add_argument("--yes", action="store_true", help="真实取消")
    cancel.set_defaults(func=cmd_cancel)

    last = subparsers.add_parser("last", help="最近预约")
    last.set_defaults(func=cmd_last)

    me = subparsers.add_parser("me", help="当前用户")
    me.set_defaults(func=cmd_me)

    rules = subparsers.add_parser("rules", help="Step / Max Duration 等系统规则")
    rules.set_defaults(func=cmd_rules)

    history = subparsers.add_parser("history", help="预约历史")
    history.add_argument("--page-size", type=int, default=20)
    history.add_argument("--page", type=int, default=1)
    history.set_defaults(func=cmd_history)

    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in argv
    argv = [item for item in argv if item != "--json"]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload, text = args.func(args)
    except CcnuError as exc:
        if json_mode:
            json.dump({"ok": False, "error": exc.to_dict()}, sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
        else:
            sys.stderr.write("错误：%s\n" % exc.message)
        return 1
    if json_mode:
        output = {"ok": True}
        output.update(payload)
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

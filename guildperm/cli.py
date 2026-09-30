"""命令行入口：跑公会权限样例。"""

import argparse

from .core import Guild, PermError


def build_parser():
    parser = argparse.ArgumentParser(prog="guild-permission", description="公会权限")
    parser.add_argument("--sample", default="inherit", help="inherit / deny / cache / cycle / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "inherit":
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("member", "guest", {})
        guild.set_role("p", "member")
        print("allowed=%s" % str(guild.can("p", "chat")).lower())
    elif args.sample == "deny":
        guild = Guild()
        guild.add_role("guest", None, {"chat": False})
        guild.add_role("member", "guest", {"chat": True})
        guild.set_role("p", "member")
        print("allowed=%s" % str(guild.can("p", "chat")).lower())
    elif args.sample == "cache":
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("mute", None, {"chat": False})
        guild.set_role("p", "guest")
        first = guild.can("p", "chat")
        guild.set_role("p", "mute")
        second = guild.can("p", "chat")
        print("first=%s second=%s" % (str(first).lower(), str(second).lower()))
    elif args.sample == "cycle":
        guild = Guild()
        guild.add_role("a", "b", {})
        try:
            guild.add_role("b", "a", {})
            print("cycle=false")
        except PermError:
            print("cycle=true")
    elif args.sample == "scan":
        guild = Guild()
        for index in range(2000):
            guild.add_role("r-%d" % index, None, {"chat": True})
        guild.set_role("p", "r-1999")
        for _ in range(2000):
            guild.cache.clear()
            guild.can("p", "chat")
        print("scanned=%d" % guild.scanned_count())
    else:
        raise SystemExit("需要 --sample inherit|deny|cache|cycle|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

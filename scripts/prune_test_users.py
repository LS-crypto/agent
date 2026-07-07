"""清理 pytest / 内测脚本产生的测试账号，保留管理员与真实用户。

用法：
  uv run python scripts/prune_test_users.py              # 预览
  uv run python scripts/prune_test_users.py --apply      # 执行删除
  uv run python scripts/prune_test_users.py --apply --keep user@real.com

规则：始终保留 role=admin；保留 ADMIN_EMAIL（若 .env 已配置）；
      保留 --keep 指定邮箱；删除匹配测试模式的账号。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.paths import RUNTIME_ROOT
from core.user.paths import admin_dir, runtime_db_path

# 测试文件里写死的邮箱
_STATIC_TEST_EMAILS = {
    "alice@example.com",
    "auto-deny@example.com",
    "chat-auto@example.com",
    "models-user@example.com",
    "deepseek-user@example.com",
    "ws@example.com",
    "ws-miss@example.com",
    "isolated@example.com",
    "alice-db@example.com",
    "bob-db@example.com",
    "alice-isolation@example.com",
    "bob-isolation@example.com",
    "dup@example.com",
    "profile@example.com",
    "boss@example.com",
    "folder@example.com",
    "cap1@example.com",
    "cap2@example.com",
    "cap3@example.com",
    "no-key@example.com",
    "byok@example.com",
    "encrypt@example.com",
    "del-key@example.com",
    "not-admin@example.com",
    "mirror@example.com",
    "regular@example.com",
    "asker@example.com",
    "admin2@example.com",
    "detail@example.com",
    "admin3@example.com",
    "bad-key@example.com",
    "legacy-default@local",
}

_TEST_EMAIL_PATTERNS = (
    re.compile(r"@test\.local$", re.I),
    re.compile(r"^user-[a-f0-9]{6,}@example\.com$", re.I),
    re.compile(r"^verify-[a-z0-9-]+@(test\.local|example\.com)$", re.I),
    re.compile(r"^ui-verify-[0-9]+@test\.local$", re.I),
)


def _load_keep_emails(extra: list[str]) -> set[str]:
    keep = {e.strip().lower() for e in extra if e.strip()}
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if admin_email:
        keep.add(admin_email)
    return keep


def is_test_user(email: str, role: str, keep: set[str]) -> bool:
    normalized = email.strip().lower()
    if role == "admin":
        return False
    if normalized in keep:
        return False
    if normalized in _STATIC_TEST_EMAILS:
        return True
    for pat in _TEST_EMAIL_PATTERNS:
        if pat.search(normalized):
            return True
    return False


def _remove_user_runtime(user_id: str, runtime_root: Path | None = None) -> None:
    root = runtime_root or RUNTIME_ROOT
    ws = root / "workspaces" / user_id
    if ws.is_dir():
        shutil.rmtree(ws, ignore_errors=True)
    admin_file = root / "admin" / "users" / f"{user_id}.json"
    if admin_file.is_file():
        admin_file.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="清理测试用户账号")
    parser.add_argument("--apply", action="store_true", help="执行删除（默认仅预览）")
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        help="额外保留的邮箱，可多次指定",
    )
    parser.add_argument(
        "--runtime",
        default="",
        help="runtime 目录（ECS 宿主机如 /opt/sheldon-agent/runtime）",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    runtime_override = args.runtime.strip()
    runtime_root = Path(runtime_override) if runtime_override else None
    db_path = (runtime_root / "db" / "auth.sqlite") if runtime_root else runtime_db_path()
    if not db_path.is_file():
        print(f"未找到数据库: {db_path}")
        return 1

    keep = _load_keep_emails(args.keep)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, email, role, created_at, last_login_at FROM users ORDER BY created_at"
    ).fetchall()

    to_delete: list[sqlite3.Row] = []
    to_keep: list[sqlite3.Row] = []
    for row in rows:
        if is_test_user(row["email"], row["role"], keep):
            to_delete.append(row)
        else:
            to_keep.append(row)

    print(f"数据库: {db_path}")
    print(f"总用户: {len(rows)} · 保留: {len(to_keep)} · 将删: {len(to_delete)}")
    if keep:
        print(f"强制保留邮箱: {', '.join(sorted(keep))}")

    if to_keep:
        print("\n保留:")
        for row in to_keep:
            login = row["last_login_at"] or "从未登录"
            print(f"  · {row['email']} ({row['role']}) — {login}")

    if to_delete:
        print("\n将删除（测试账号）:")
        for row in to_delete:
            print(f"  · {row['email']} ({row['role']})")

    if not args.apply:
        print("\n预览模式。确认后加 --apply 执行删除。")
        return 0

    if not to_delete:
        print("无需删除。")
        return 0

    for row in to_delete:
        uid = row["id"]
        conn.execute("DELETE FROM user_secrets WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        _remove_user_runtime(uid, runtime_root)
    conn.commit()
    conn.close()

    if runtime_root:
        index_path = runtime_root / "admin" / "users" / "index.json"
    else:
        index_path = admin_dir() / "users" / "index.json"
    if index_path.is_file():
        index_path.unlink(missing_ok=True)

    print(f"\n已删除 {len(to_delete)} 个测试账号。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

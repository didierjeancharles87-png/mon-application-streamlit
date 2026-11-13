"""
manage_users.py — fitaovana mpitantana ny mpampiana ny "Rapport École du Sabbat".

Fampiharana (ao amin'ny dossier-ny app):

    python manage_users.py list
    python manage_users.py add admin              # manoratra mpampianatra vaovao
    python manage_users.py add secretariat --role editeur
    python manage_users.py passwd admin           # ovay ny password
    python manage_users.py role admin admin      # ovay ny rol
    python manage_users.py delete secretariat
    python manage_users.py setup-code             # jereo ny code fanombohana

Ny password dia tsy voatahiry en clair: PBKDF2-HMAC-SHA256 (600 000 iterations).
"""
from __future__ import annotations

import argparse
import getpass
import sys

import auth


def _ask_password(label: str = "Password: ") -> str:
    return getpass.getpass(label)


def cmd_list() -> int:
    users = auth.list_users()
    if not users:
        print("Tsy mbola misy mpampiana. Ampiso ny 'add' na ny 'setup-code'.")
        return 0
    print(f"{'Utilisateur':<20} {'Rôle':<12} {'Créé le':<20} Dernière connexion")
    print("-" * 80)
    for name, rec in users.items():
        print(f"{name:<20} {rec.get('role', ''):<12} {rec.get('created', ''):<20} "
              f"{rec.get('last_login', '') or '—'}")
    return 0


def cmd_add(args) -> int:
    pwd = _ask_password("Password vaovao: ")
    pwd2 = _ask_password("Hamerina ny password: ")
    if pwd != pwd2:
        print("Tsy mitovy ny password roa.")
        return 1
    ok, msg = auth.create_user(args.username, pwd, args.role)
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


def cmd_passwd(args) -> int:
    pwd = _ask_password("Password vaovao: ")
    pwd2 = _ask_password("Hamerina ny password: ")
    if pwd != pwd2:
        print("Tsy mitovy ny password roa.")
        return 1
    ok, msg = auth.set_password(args.username, pwd)
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


def cmd_role(args) -> int:
    ok, msg = auth.set_role(args.username, args.role)
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


def cmd_delete(args) -> int:
    ok, msg = auth.delete_user(args.username)
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


def cmd_setup_code() -> int:
    if auth.users_configured():
        print("Efa misy mpampiana — tsy ilay ny code fanombohana intsony.")
        return 0
    code = auth.ensure_setup_code()
    if code is None:
        print("Misy code fanombohana efa voatahiry (jereo ny terminal-n'ny serveur).")
        return 0
    print("=" * 60)
    print("  CODE FANOMBOHANA (raha mbola tsy misy mpampiana):")
    print(f"      {code}")
    print("  Ampidiro ity ao amin'ny pejy fidirana ny app.")
    print("=" * 60)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Mpitantana ny mpampiana ny Rapport École du Sabbat")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Jereo ny lisitry ny mpampiana").set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Mamorona ny mpampiana")
    p_add.add_argument("username")
    p_add.add_argument("--role", default="admin", choices=list(auth.ROLES))
    p_add.set_defaults(func=cmd_add)

    p_pwd = sub.add_parser("passwd", help="Ovay ny password")
    p_pwd.add_argument("username")
    p_pwd.set_defaults(func=cmd_passwd)

    p_role = sub.add_parser("role", help="Ovay ny rol")
    p_role.add_argument("username")
    p_role.add_argument("role", choices=list(auth.ROLES))
    p_role.set_defaults(func=cmd_role)

    p_del = sub.add_parser("delete", help="Fafao ny mpampiana")
    p_del.add_argument("username")
    p_del.set_defaults(func=cmd_delete)

    sub.add_parser("setup-code", help="Jereo ny code fanombohana").set_defaults(func=cmd_setup_code)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

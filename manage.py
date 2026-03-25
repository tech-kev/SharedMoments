#!/usr/bin/env python3
"""SharedMoments CLI — User management tool.

Usage:
    python manage.py list-users
    python manage.py set-password <email> [--password <pw>]
    python manage.py update-user <email> [--first-name X] [--last-name X] [--email X] [--birthdate YYYY-MM-DD]
"""

import argparse
import getpass
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import User, SessionLocal
from app.db_queries import get_user_by_email, get_all_users, update_user_password, get_user_roles_list, get_all_roles


def cmd_list_users(args):
    """List all users with ID, name, email and roles."""
    users = get_all_users()
    roles = {r.id: r.roleName for r in get_all_roles()}

    if not users:
        print('No users found.')
        return

    # Header
    print(f'{"ID":<5} {"Name":<25} {"E-Mail":<35} {"Roles"}')
    print('-' * 90)

    for user in users:
        name = f'{user.firstName or ""} {user.lastName or ""}'.strip() or '—'
        email = user.email or '—'
        user_role_ids = get_user_roles_list(user.id)
        role_names = ', '.join(roles.get(rid, f'#{rid}') for rid in user_role_ids) or '—'
        print(f'{user.id:<5} {name:<25} {email:<35} {role_names}')

    print(f'\nTotal: {len(users)} user(s)')


def cmd_set_password(args):
    """Set a new password for a user."""
    user = get_user_by_email(args.email)
    if not user:
        print(f'Error: No user found with email "{args.email}"')
        sys.exit(1)

    if args.password:
        new_password = args.password
    else:
        new_password = getpass.getpass('New password: ')
        confirm = getpass.getpass('Confirm password: ')
        if new_password != confirm:
            print('Error: Passwords do not match.')
            sys.exit(1)

    password_hash, password_salt = user.hash_password(new_password)
    update_user_password(user.id, password_hash, password_salt)
    print(f'Password updated for {user.firstName} {user.lastName} ({user.email})')


def cmd_update_user(args):
    """Update user fields."""
    user = get_user_by_email(args.email)
    if not user:
        print(f'Error: No user found with email "{args.email}"')
        sys.exit(1)

    session = SessionLocal()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        changes = []

        if args.first_name is not None:
            db_user.firstName = args.first_name
            changes.append(f'firstName → {args.first_name}')

        if args.last_name is not None:
            db_user.lastName = args.last_name
            changes.append(f'lastName → {args.last_name}')

        if args.new_email is not None:
            existing = get_user_by_email(args.new_email)
            if existing and existing.id != user.id:
                print(f'Error: Email "{args.new_email}" is already in use.')
                sys.exit(1)
            db_user.email = args.new_email
            changes.append(f'email → {args.new_email}')

        if args.birthdate is not None:
            from datetime import datetime
            try:
                db_user.birthDate = datetime.strptime(args.birthdate, '%Y-%m-%d').date()
                changes.append(f'birthDate → {args.birthdate}')
            except ValueError:
                print('Error: Invalid date format. Use YYYY-MM-DD.')
                sys.exit(1)

        if not changes:
            print('Nothing to update. Use --first-name, --last-name, --email, or --birthdate.')
            return

        session.commit()
        print(f'Updated user {user.email}:')
        for c in changes:
            print(f'  {c}')
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description='SharedMoments CLI — User management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list-users
    subparsers.add_parser('list-users', help='List all users')

    # set-password
    sp = subparsers.add_parser('set-password', help='Set password for a user')
    sp.add_argument('email', help='User email address')
    sp.add_argument('--password', '-p', help='New password (prompted if omitted)')

    # update-user
    up = subparsers.add_parser('update-user', help='Update user details')
    up.add_argument('email', help='User email address')
    up.add_argument('--first-name', help='New first name')
    up.add_argument('--last-name', help='New last name')
    up.add_argument('--email', dest='new_email', help='New email address')
    up.add_argument('--birthdate', help='New birth date (YYYY-MM-DD)')

    args = parser.parse_args()

    commands = {
        'list-users': cmd_list_users,
        'set-password': cmd_set_password,
        'update-user': cmd_update_user,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()

"""Create, validate and restore a Job Finder local database backup."""

from __future__ import annotations

import argparse
from pathlib import Path

from job_finder.backup import BackupError, create_backup, restore_backup, validate_backup
from job_finder.settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "validate", "restore"))
    parser.add_argument("backup", nargs="?", type=Path)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--retention", type=int, default=5)
    args = parser.parse_args()
    data_dir = args.data_dir or get_settings().data_dir

    try:
        if args.command == "create":
            result = create_backup(data_dir, retention=args.retention)
            print(f"Backup criado: {result.path}")
            print(f"Schema: {result.manifest.schema_revision or 'desconhecido'}")
            print(f"SHA-256: {result.manifest.database_sha256}")
        elif args.command == "validate":
            if args.backup is None:
                parser.error("validate exige o caminho do backup")
            manifest = validate_backup(args.backup)
            print(f"Backup válido: {args.backup}")
            print(f"Schema: {manifest.schema_revision or 'desconhecido'}")
        else:
            if args.backup is None:
                parser.error("restore exige o caminho do backup")
            restored = restore_backup(data_dir, args.backup)
            print(f"Banco restaurado: {restored}")
    except BackupError as error:
        parser.exit(1, f"Erro de backup: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

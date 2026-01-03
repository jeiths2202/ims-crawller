"""
Migration Script: Old Structure → UserID-based Structure

Migrates existing crawl session data from:
  data/crawl_sessions/{session_id}/
  data/attachments/{issue_id}/

To:
  data/users/{userid}/sessions/{session_id}/issues/
  data/users/{userid}/sessions/{session_id}/attachments/

Creates metadata.json for each session based on available information.
"""
import sys
import io
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

from crawler.user_repository import UserRepository, SessionMetadata


class DataMigrator:
    """Migrates existing data to userid-based structure"""

    def __init__(self, user_id: str, dry_run: bool = False):
        """
        Initialize migrator

        Args:
            user_id: Target user ID (from .env IMS_USERNAME)
            dry_run: If True, only show what would be done without actually migrating
        """
        self.user_id = user_id
        self.dry_run = dry_run

        # Paths
        self.old_sessions_dir = Path("data/crawl_sessions")
        self.old_attachments_dir = Path("data/attachments")

        # User repository
        self.repo = UserRepository(user_id)

        # Statistics
        self.stats = {
            "sessions_found": 0,
            "sessions_migrated": 0,
            "issues_migrated": 0,
            "attachments_migrated": 0,
            "errors": []
        }

    def analyze(self) -> Dict[str, Any]:
        """Analyze existing data structure"""
        print("=" * 80)
        print("📊 Analyzing existing data structure...")
        print("=" * 80)

        # Check old sessions directory
        if not self.old_sessions_dir.exists():
            print(f"\n❌ Old sessions directory not found: {self.old_sessions_dir}")
            print("   Nothing to migrate.")
            return self.stats

        # List all session directories
        session_dirs = [
            d for d in self.old_sessions_dir.iterdir()
            if d.is_dir()
        ]

        self.stats["sessions_found"] = len(session_dirs)

        print(f"\n✅ Found {len(session_dirs)} session directories")

        for session_dir in session_dirs:
            # Count JSON files (issues)
            json_files = list(session_dir.glob("*.json"))
            print(f"\n  📁 {session_dir.name}")
            print(f"     Issues: {len(json_files)} JSON files")

            # Check attachments subdirectory
            session_attachments = session_dir / "attachments"
            if session_attachments.exists():
                attach_count = sum(1 for _ in session_attachments.rglob("*") if _.is_file())
                print(f"     Attachments: {attach_count} files in {session_dir.name}/attachments/")

        # Check global attachments directory
        if self.old_attachments_dir.exists():
            global_attach_dirs = [
                d for d in self.old_attachments_dir.iterdir()
                if d.is_dir()
            ]
            print(f"\n  📦 Global attachments directory: {len(global_attach_dirs)} issue folders")

        return self.stats

    def migrate_session(self, old_session_dir: Path) -> bool:
        """
        Migrate a single session

        Args:
            old_session_dir: Path to old session directory

        Returns:
            True if successful, False otherwise
        """
        session_id = old_session_dir.name

        print(f"\n{'[DRY RUN] ' if self.dry_run else ''}Migrating session: {session_id}")

        try:
            # Create new session in user repository
            new_session = self.repo.create_session(session_id)

            # Parse session info from directory name
            session_info = self._parse_session_id(session_id)

            # Find all JSON files (issues)
            json_files = list(old_session_dir.glob("*.json"))

            if not json_files:
                print(f"  ⚠️  No JSON files found, skipping...")
                return False

            # Extract issue IDs
            issue_ids = []
            for json_file in json_files:
                issue_id = json_file.stem.split('_')[0]  # e.g., "347863_20260103_121000.json" → "347863"
                issue_ids.append(issue_id)

            # Initialize metadata
            if not self.dry_run:
                new_session.init_metadata(
                    product=session_info.get("product", "Unknown"),
                    original_query=session_info.get("query", ""),
                    parsed_query=session_info.get("query", ""),
                    language=session_info.get("language", "en"),
                    max_results=len(json_files),
                    crawl_related=False
                )

                # Update results
                new_session.update_results(
                    total_issues=len(json_files),
                    issues_crawled=len(json_files)
                )

                # Add issue IDs
                for issue_id in issue_ids:
                    new_session.add_issue_id(issue_id)

            # Migrate JSON files
            print(f"  📄 Migrating {len(json_files)} issue files...")
            for json_file in json_files:
                issue_id = json_file.stem.split('_')[0]

                if not self.dry_run:
                    # Copy JSON file to new location
                    new_path = new_session.get_issue_path(issue_id)
                    shutil.copy2(json_file, new_path)

                self.stats["issues_migrated"] += 1

            # Migrate session-specific attachments
            session_attachments_dir = old_session_dir / "attachments"
            if session_attachments_dir.exists():
                print(f"  📎 Migrating session attachments...")
                if not self.dry_run:
                    self._migrate_attachments(session_attachments_dir, new_session.attachments_dir)

            # Migrate global attachments for issues in this session
            if self.old_attachments_dir.exists():
                for issue_id in issue_ids:
                    old_attach_dir = self.old_attachments_dir / issue_id
                    if old_attach_dir.exists():
                        print(f"  📎 Migrating attachments for issue {issue_id}...")
                        if not self.dry_run:
                            new_attach_dir = new_session.get_attachment_dir(issue_id)
                            self._migrate_attachments(old_attach_dir, new_attach_dir)

            # Mark session as completed (use directory modification time)
            if not self.dry_run:
                mtime = datetime.fromtimestamp(old_session_dir.stat().st_mtime)
                new_session.complete(mtime)

            self.stats["sessions_migrated"] += 1
            print(f"  ✅ Session migrated successfully")
            return True

        except Exception as e:
            error_msg = f"Error migrating session {session_id}: {e}"
            print(f"  ❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return False

    def _parse_session_id(self, session_id: str) -> Dict[str, str]:
        """
        Parse session ID to extract metadata

        Examples:
          "OpenFrame_TPETIME_error_에러_오류_20260103_120855"
          "All_347863_20260103_043733"
          "OpenFrame_347863_20260103_043630"
        """
        parts = session_id.split('_')

        # Extract product (first part)
        product = parts[0] if parts else "Unknown"

        # Extract query components (everything between product and timestamp)
        query_parts = []
        for part in parts[1:-2]:  # Skip product and last 2 parts (date + time)
            if not part.isdigit() or len(part) < 6:  # Not a date
                query_parts.append(part)

        query = ' '.join(query_parts) if query_parts else ""

        # Detect language (rough heuristic)
        language = "ko" if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in query) else "en"

        return {
            "product": product,
            "query": query,
            "language": language
        }

    def _migrate_attachments(self, src_dir: Path, dest_dir: Path):
        """Migrate attachments directory"""
        if not src_dir.exists():
            return

        for item in src_dir.rglob("*"):
            if item.is_file():
                # Preserve directory structure
                rel_path = item.relative_to(src_dir)
                dest_path = dest_dir / rel_path

                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(item, dest_path)
                self.stats["attachments_migrated"] += 1

    def migrate_all(self):
        """Migrate all sessions"""
        print("\n" + "=" * 80)
        print(f"🚀 {'[DRY RUN] ' if self.dry_run else ''}Starting migration...")
        print("=" * 80)
        print(f"\nTarget user: {self.user_id}")
        print(f"Target directory: {self.repo.root}")

        if not self.old_sessions_dir.exists():
            print(f"\n❌ Old sessions directory not found: {self.old_sessions_dir}")
            return

        # Get all session directories
        session_dirs = sorted(
            [d for d in self.old_sessions_dir.iterdir() if d.is_dir()],
            key=lambda p: p.name
        )

        if not session_dirs:
            print("\n❌ No sessions found to migrate")
            return

        print(f"\nFound {len(session_dirs)} sessions to migrate\n")

        # Migrate each session
        for i, session_dir in enumerate(session_dirs, 1):
            print(f"\n[{i}/{len(session_dirs)}]", end=" ")
            self.migrate_session(session_dir)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 80)
        print("📊 Migration Summary")
        print("=" * 80)

        print(f"\n{'[DRY RUN] ' if self.dry_run else ''}Results:")
        print(f"  Sessions found:     {self.stats['sessions_found']}")
        print(f"  Sessions migrated:  {self.stats['sessions_migrated']}")
        print(f"  Issues migrated:    {self.stats['issues_migrated']}")
        print(f"  Attachments moved:  {self.stats['attachments_migrated']}")

        if self.stats["errors"]:
            print(f"\n⚠️  Errors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"]:
                print(f"  - {error}")
        else:
            print(f"\n✅ No errors")

        if self.dry_run:
            print("\n💡 This was a dry run. No files were actually moved.")
            print("   Run without --dry-run to perform the actual migration.")
        else:
            print(f"\n✅ Migration completed!")
            print(f"\nNew data location: {self.repo.root}")
            print(f"\n💡 You can now safely delete the old directories:")
            print(f"   - {self.old_sessions_dir}")
            print(f"   - {self.old_attachments_dir} (if all attachments were migrated)")

    def create_backup(self):
        """Create backup of old data before migration"""
        if self.dry_run:
            print("\n[DRY RUN] Would create backup...")
            return

        backup_dir = Path(f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"\n💾 Creating backup: {backup_dir}")

        # Backup crawl_sessions
        if self.old_sessions_dir.exists():
            shutil.copytree(self.old_sessions_dir, backup_dir / "crawl_sessions")
            print(f"  ✅ Backed up: crawl_sessions")

        # Backup attachments
        if self.old_attachments_dir.exists():
            shutil.copytree(self.old_attachments_dir, backup_dir / "attachments")
            print(f"  ✅ Backed up: attachments")

        print(f"\n✅ Backup created: {backup_dir}")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate crawl data to userid-based structure"
    )
    parser.add_argument(
        "--user-id",
        help="User ID (default: from IMS_USERNAME in .env)",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually migrating"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze existing data without migrating"
    )

    args = parser.parse_args()

    # Get user ID
    user_id = args.user_id or os.getenv("IMS_USERNAME")
    if not user_id:
        print("❌ Error: No user ID provided and IMS_USERNAME not found in .env")
        sys.exit(1)

    # Create migrator
    migrator = DataMigrator(user_id=user_id, dry_run=args.dry_run)

    # Analyze only
    if args.analyze_only:
        migrator.analyze()
        return

    # Create backup if requested
    if args.backup:
        migrator.create_backup()

    # Perform migration
    migrator.analyze()
    migrator.migrate_all()


if __name__ == "__main__":
    main()

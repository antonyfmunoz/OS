"""EmailFolderStore — canonical write API for the email_folders table."""

from state.storage.db import get_conn


class EmailFolderStore:

    def seed_folders(
        self,
        org_id: str,
        folders: list[dict],
    ) -> None:
        """Bulk insert folder definitions. ON CONFLICT does nothing."""
        with get_conn(org_id) as cur:
            for folder in folders:
                cur.execute(
                    """
                    INSERT INTO email_folders (
                        org_id, name, purpose, examples, auto_actions)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (org_id, name) DO NOTHING
                    """,
                    (
                        org_id,
                        folder["name"],
                        folder["purpose"],
                        folder["examples"],
                        folder["auto_actions"],
                    ),
                )

    def update_purpose(
        self,
        org_id: str,
        folder_name: str,
        new_purpose: str,
    ) -> None:
        """Update a folder's purpose text."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE email_folders
                SET purpose = %s, updated_at = NOW()
                WHERE org_id = %s AND name = %s
                """,
                (new_purpose, org_id, folder_name),
            )

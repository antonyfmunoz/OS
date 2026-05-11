"""
TransactionWorkflow — end-to-end transaction lifecycle.

lead → client → transaction → fulfillment

Each step writes to Neon. The full cycle proves one company
can take a contact from first touch to delivered result.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.db import get_conn

ORG_ID = "72727be3-e24d-48f2-bcea-de760ecb4c23"


class TransactionWorkflow:
    """Executes and verifies the full transaction lifecycle for a venture."""

    def __init__(self, org_id: str = ORG_ID):
        self.org_id = org_id

    def create_lead(
        self,
        venture_id: str,
        name: str,
        email: str,
        source: str = "direct_outreach",
        phone: str | None = None,
        notes: str = "",
    ) -> str:
        """Insert a lead into clients table. Returns client_id."""
        with get_conn(self.org_id) as cur:
            cur.execute(
                """INSERT INTO clients (org_id, venture_id, name, email, phone, status, source, notes)
                   VALUES (%s, %s, %s, %s, %s, 'lead', %s, %s)
                   RETURNING id""",
                (self.org_id, venture_id, name, email, phone, source, notes),
            )
            row = cur.fetchone()
            return str(row["id"])

    def promote_to_client(self, client_id: str) -> bool:
        """Move a lead to client status. Returns True on success."""
        with get_conn(self.org_id) as cur:
            cur.execute(
                """UPDATE clients SET status = 'client', updated_at = now()
                   WHERE id = %s::uuid AND status IN ('lead', 'prospect')""",
                (client_id,),
            )
            return cur.rowcount > 0

    def create_transaction(
        self,
        venture_id: str,
        client_id: str,
        product_name: str,
        amount_cents: int,
        template_instance_id: str | None = None,
        notes: str = "",
    ) -> str:
        """Record a transaction. Returns transaction_id."""
        with get_conn(self.org_id) as cur:
            cur.execute(
                """INSERT INTO transactions
                   (org_id, venture_id, client_id, product_name, amount_cents,
                    status, fulfillment_status, template_instance_id, notes, payment_date)
                   VALUES (%s, %s, %s::uuid, %s, %s, 'paid', 'not_started', %s, %s, now())
                   RETURNING id""",
                (
                    self.org_id,
                    venture_id,
                    client_id,
                    product_name,
                    amount_cents,
                    template_instance_id,
                    notes,
                ),
            )
            row = cur.fetchone()
            return str(row["id"])

    def record_fulfillment(
        self,
        venture_id: str,
        transaction_id: str,
        description: str,
        completed_by: str = "system",
        evidence_url: str | None = None,
    ) -> str:
        """Record a fulfillment event. Returns event_id."""
        with get_conn(self.org_id) as cur:
            cur.execute(
                """INSERT INTO fulfillment_events
                   (org_id, venture_id, transaction_id, description, completed_by, evidence_url)
                   VALUES (%s, %s, %s::uuid, %s, %s, %s)
                   RETURNING id""",
                (
                    self.org_id,
                    venture_id,
                    transaction_id,
                    description,
                    completed_by,
                    evidence_url,
                ),
            )
            row = cur.fetchone()
            # update transaction fulfillment status
            cur.execute(
                """UPDATE transactions SET fulfillment_status = 'in_progress'
                   WHERE id = %s::uuid AND fulfillment_status = 'not_started'""",
                (transaction_id,),
            )
            return str(row["id"])

    def complete_fulfillment(self, transaction_id: str) -> bool:
        """Mark a transaction as fully fulfilled. Updates client to 'fulfilled'."""
        with get_conn(self.org_id) as cur:
            cur.execute(
                """UPDATE transactions SET fulfillment_status = 'completed'
                   WHERE id = %s::uuid""",
                (transaction_id,),
            )
            if cur.rowcount == 0:
                return False
            cur.execute(
                """UPDATE clients SET status = 'fulfilled', updated_at = now()
                   WHERE id = (SELECT client_id FROM transactions WHERE id = %s::uuid)""",
                (transaction_id,),
            )
            return True

    def run_synthetic_cycle(
        self,
        venture_id: str,
        client_name: str,
        client_email: str,
        product_name: str,
        amount_cents: int,
        fulfillment_desc: str,
        template_instance_id: str | None = None,
    ) -> dict:
        """Execute a complete lead→client→transaction→fulfillment cycle. Returns all IDs."""
        client_id = self.create_lead(
            venture_id, client_name, client_email, source="synthetic_test"
        )
        self.promote_to_client(client_id)
        tx_id = self.create_transaction(
            venture_id,
            client_id,
            product_name,
            amount_cents,
            template_instance_id,
        )
        event_id = self.record_fulfillment(venture_id, tx_id, fulfillment_desc)
        self.complete_fulfillment(tx_id)
        return {
            "venture_id": venture_id,
            "client_id": client_id,
            "transaction_id": tx_id,
            "fulfillment_event_id": event_id,
        }

    def verify_cycle(self, result: dict) -> dict:
        """Verify all rows exist and have correct statuses."""
        checks = {}
        with get_conn(self.org_id) as cur:
            cur.execute(
                "SELECT status FROM clients WHERE id = %s::uuid", (result["client_id"],)
            )
            row = cur.fetchone()
            checks["client_status"] = row["status"] if row else "MISSING"

            cur.execute(
                "SELECT status, fulfillment_status FROM transactions WHERE id = %s::uuid",
                (result["transaction_id"],),
            )
            row = cur.fetchone()
            if row:
                checks["tx_status"] = row["status"]
                checks["tx_fulfillment"] = row["fulfillment_status"]
            else:
                checks["tx_status"] = "MISSING"
                checks["tx_fulfillment"] = "MISSING"

            cur.execute(
                "SELECT id FROM fulfillment_events WHERE transaction_id = %s::uuid",
                (result["transaction_id"],),
            )
            checks["fulfillment_events"] = len(cur.fetchall())

        checks["valid"] = (
            checks["client_status"] == "fulfilled"
            and checks["tx_status"] == "paid"
            and checks["tx_fulfillment"] == "completed"
            and checks["fulfillment_events"] >= 1
        )
        return checks

    def cleanup_synthetic(self, results: list[dict]) -> int:
        """Delete synthetic test data. Returns count of clients deleted (cascades to tx + events)."""
        deleted = 0
        with get_conn(self.org_id) as cur:
            for r in results:
                cur.execute(
                    "DELETE FROM clients WHERE id = %s::uuid", (r["client_id"],)
                )
                deleted += cur.rowcount
        return deleted


# ─── Synthetic test for all 6 companies ─────────────────────────────────────

SYNTHETIC_CYCLES = [
    {
        "venture_id": "ost",
        "client_name": "Test Founder",
        "client_email": "test@ost.example.com",
        "product_name": "EntrepreneurOS Monthly",
        "amount_cents": 29700,
        "fulfillment_desc": "Account provisioned, onboarding complete",
    },
    {
        "venture_id": "empyrean_creative",
        "client_name": "Test B2B Client",
        "client_email": "test@empyrean.example.com",
        "product_name": "AI Infrastructure Project",
        "amount_cents": 300000,
        "fulfillment_desc": "AI system built and handed off to client",
    },
    {
        "venture_id": "lyfe_institute",
        "client_name": "Test Initiate",
        "client_email": "test@lyfe.example.com",
        "product_name": "Initiate Arena",
        "amount_cents": 75000,
        "fulfillment_desc": "90-day program completed, exit interview done",
    },
    {
        "venture_id": "personal_brand",
        "client_name": "Test Follower",
        "client_email": "test@brand.example.com",
        "product_name": "Content Audience",
        "amount_cents": 0,
        "fulfillment_desc": "Converted to pipeline lead for Lyfe Institute",
    },
    {
        "venture_id": "lyfe_spectrum",
        "client_name": "Test Buyer",
        "client_email": "test@spectrum.example.com",
        "product_name": "Lyfe Spectrum Tee",
        "amount_cents": 4500,
        "fulfillment_desc": "Order shipped and delivered",
    },
    {
        "venture_id": "select_developments",
        "client_name": "Test Property Buyer",
        "client_email": "test@select.example.com",
        "product_name": "Fix and Flip Project",
        "amount_cents": 0,
        "fulfillment_desc": "Property renovated and listed for sale",
    },
]


if __name__ == "__main__":
    wf = TransactionWorkflow()

    print("Running 6 synthetic transaction cycles...")
    results = []
    for cycle in SYNTHETIC_CYCLES:
        r = wf.run_synthetic_cycle(**cycle)
        results.append(r)
        v = wf.verify_cycle(r)
        status = "PASS" if v["valid"] else "FAIL"
        print(
            f"  {cycle['venture_id']}: {status} — client={v['client_status']}, tx={v['tx_status']}, fulfillment={v['tx_fulfillment']}"
        )

    print(f"\nAll 6 cycles complete. Cleaning up synthetic data...")
    deleted = wf.cleanup_synthetic(results)
    print(f"Cleaned up {deleted} synthetic clients (cascaded to transactions + events)")

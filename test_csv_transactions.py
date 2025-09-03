# test_csv_transactions.py
import os
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta

from csv_transactions import (
    create_transaction, read_transactions, get_transaction,
    update_transaction, delete_transaction, get_totals,
    get_total_income, get_total_expenses, get_net_savings,
    get_category_totals, validate_transaction
)

class TestCsvTransactions(unittest.TestCase):
    def setUp(self):
        # temp directory and CSV path for isolation
        self.tmpdir = tempfile.mkdtemp(prefix="tx_tests_")
        self.csv_path = os.path.join(self.tmpdir, "transactions.csv")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_sample_data(self):
        """
        Create a few transactions:
          + 1000.00 income (Salary)
          - 200.00 expense (Groceries)
          -  50.00 expense (Dining)
        """
        t1 = create_transaction(
            self.csv_path,
            datetime_str="2024-01-15 10:00:00",
            category="Salary",
            amount_str="1000.00",
            description="Monthly salary",
        )
        t2 = create_transaction(
            self.csv_path,
            datetime_str="2024-01-16 12:30:00",
            category="Groceries",
            amount_str="-200.00",
            description="Food store",
        )
        t3 = create_transaction(
            self.csv_path,
            datetime_str="2024-01-17 19:45:00",
            category="Dining",
            amount_str="-50.00",
            description="Dinner out",
        )
        return t1, t2, t3

    # ---------- Validation ----------

    def test_validate_transaction_disallow_future(self):
        future_dt = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        ok, errs, _ = validate_transaction(
            datetime_str=future_dt,
            category="Test",
            amount_str="10.00",
            description="Future test",
        )
        self.assertFalse(ok)
        self.assertTrue(any("future" in e.lower() for e in errs))

    def test_validate_transaction_bad_amount(self):
        ok, errs, _ = validate_transaction(
            datetime_str="2024-01-15 10:00:00",
            category="Misc",
            amount_str="abc",
            description="Bad amount",
        )
        self.assertFalse(ok)
        self.assertTrue(any("valid number" in e.lower() for e in errs))

    def test_validate_transaction_allowed_categories(self):
        allowed = {"Income", "Groceries", "Dining"}
        ok1, errs1, _ = validate_transaction(
            datetime_str="2024-01-15 10:00:00",
            category="Income",
            amount_str="100.00",
            description="OK",
            allowed_categories=allowed,
        )
        self.assertTrue(ok1)
        ok2, errs2, _ = validate_transaction(
            datetime_str="2024-01-15 10:00:00",
            category="NotAllowed",
            amount_str="10.00",
            description="Nope",
            allowed_categories=allowed,
        )
        self.assertFalse(ok2)
        self.assertTrue(any("allowed set" in e.lower() for e in errs2))

    # ---------- CRUD ----------

    def test_create_and_read(self):
        t1, t2, t3 = self._seed_sample_data()
        all_rows = read_transactions(self.csv_path)
        self.assertEqual(len(all_rows), 3)
        self.assertTrue(any(r.id == t1.id for r in all_rows))
        self.assertTrue(any(r.id == t2.id for r in all_rows))
        self.assertTrue(any(r.id == t3.id for r in all_rows))

    def test_get_transaction(self):
        t1, _, _ = self._seed_sample_data()
        got = get_transaction(self.csv_path, t1.id)
        self.assertIsNotNone(got)
        self.assertEqual(got.id, t1.id)
        self.assertIsNone(get_transaction(self.csv_path, "does-not-exist"))

    def test_update_transaction(self):
        t1, _, _ = self._seed_sample_data()
        updated = update_transaction(
            self.csv_path,
            t1.id,
            amount_str="1200.00",
            description="Adjusted salary",
        )
        self.assertEqual(updated.amount, "1200.00")
        self.assertEqual(updated.description, "Adjusted salary")
        # ensure persisted
        again = get_transaction(self.csv_path, t1.id)
        self.assertEqual(again.amount, "1200.00")

    def test_delete_transaction(self):
        t1, t2, t3 = self._seed_sample_data()
        ok = delete_transaction(self.csv_path, t2.id)
        self.assertTrue(ok)
        remaining = read_transactions(self.csv_path)
        self.assertEqual(len(remaining), 2)
        self.assertFalse(any(r.id == t2.id for r in remaining))
        # Deleting non-existent returns False
        self.assertFalse(delete_transaction(self.csv_path, "nope"))

    # ---------- Totals & Category Summaries ----------

    def test_totals(self):
        self._seed_sample_data()
        totals = get_totals(self.csv_path)
        self.assertAlmostEqual(totals["income"], 1000.00, places=2)
        self.assertAlmostEqual(totals["expenses"], 250.00, places=2)
        self.assertAlmostEqual(totals["net"], 750.00, places=2)
        # single-purpose helpers
        self.assertAlmostEqual(get_total_income(self.csv_path), 1000.00, places=2)
        self.assertAlmostEqual(get_total_expenses(self.csv_path), 250.00, places=2)
        self.assertAlmostEqual(get_net_savings(self.csv_path), 750.00, places=2)

    def test_category_totals(self):
        self._seed_sample_data()
        cats = get_category_totals(self.csv_path)
        # Salary: +1000
        self.assertIn("Salary", cats)
        self.assertAlmostEqual(cats["Salary"]["income"], 1000.00, places=2)
        self.assertAlmostEqual(cats["Salary"]["expenses"], 0.00, places=2)
        self.assertAlmostEqual(cats["Salary"]["net"], 1000.00, places=2)
        # Groceries: -200
        self.assertIn("Groceries", cats)
        self.assertAlmostEqual(cats["Groceries"]["income"], 0.00, places=2)
        self.assertAlmostEqual(cats["Groceries"]["expenses"], 200.00, places=2)
        self.assertAlmostEqual(cats["Groceries"]["net"], -200.00, places=2)
        # Dining: -50
        self.assertIn("Dining", cats)
        self.assertAlmostEqual(cats["Dining"]["income"], 0.00, places=2)
        self.assertAlmostEqual(cats["Dining"]["expenses"], 50.00, places=2)
        self.assertAlmostEqual(cats["Dining"]["net"], -50.00, places=2)

if __name__ == "__main__":
    # Run tests directly:  python test_csv_transactions.py
    unittest.main(verbosity=2)

"""
csv_transactions.py

CSV-backed CRUD for personal finance transactions with validation and reporting.

Schema (CSV headers):
    id, datetime, category, amount, description

- id:        UUID string
- datetime:  ISO 8601 (e.g., "2025-09-02T14:30:00")
- category:  non-empty string (optionally validated against an allowed set)
- amount:    decimal string, exactly 2 fractional digits (negative or positive)
- description: non-empty string

Notes:
- Writes are atomic: data is written to a temp file then replaced.
- Amounts are validated with Decimal (no float rounding issues).
- Datetimes are validated and normalized to ISO 8601 (no timezone attached).
"""

from __future__ import annotations

import csv
import os
import tempfile
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate

CSV_HEADERS = ["id", "datetime", "category", "amount", "description"]

# Optional: define an allowed set of categories. Set to None to allow any string.
DEFAULT_ALLOWED_CATEGORIES: Optional[Iterable[str]] = None
# Example:
# DEFAULT_ALLOWED_CATEGORIES = {"Income", "Groceries", "Rent", "Utilities", "Dining", "Transport", "Entertainment", "Savings"}


@dataclass
class Transaction:
    id: str
    datetime: str   # ISO 8601 string
    category: str
    amount: str     # Decimal as string (e.g., "-12.34")
    description: str


# main function - the start of the program
def main():
    run_cli_menu("transactions.csv")



# ---------- Utilities ----------

def _ensure_csv_exists(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def _atomic_write_rows(csv_path: str, rows: List[Dict[str, str]]) -> None:
    """Safely write all rows to CSV atomically."""
    dir_name = os.path.dirname(os.path.abspath(csv_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="tx_", suffix=".csv", dir=dir_name)
    os.close(fd)
    try:
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        os.replace(tmp_path, csv_path)
    except Exception:
        # Clean up temp file if something goes wrong
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _read_all(csv_path: str) -> List[Transaction]:
    _ensure_csv_exists(csv_path)
    out: List[Transaction] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Be tolerant to missing columns (but we keep the schema strict on write)
            tx = Transaction(
                id=row.get("id", "").strip(),
                datetime=row.get("datetime", "").strip(),
                category=row.get("category", "").strip(),
                amount=row.get("amount", "").strip(),
                description=row.get("description", "").strip(),
            )
            out.append(tx)
    return out


def _write_all(csv_path: str, txs: List[Transaction]) -> None:
    rows = [asdict(t) for t in txs]
    _atomic_write_rows(csv_path, rows)


# ---------- Validation ----------

def _parse_and_normalize_datetime(dt_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Accept a few common formats and normalize to ISO 8601 'YYYY-MM-DDTHH:MM:SS'.
    Returns (normalized_str, error) where one will be None.
    """
    s = (dt_str or "").strip()
    candidates = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",  # will normalize to midnight if date only
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(s, fmt)
            # Normalize to full seconds, ISO 8601
            norm = dt.strftime("%Y-%m-%dT%H:%M:%S")
            return norm, None
        except ValueError:
            continue
    return None, f"Invalid datetime format: '{dt_str}'. Expected ISO-like (e.g., 2025-09-02T14:30:00)."


def _validate_amount(amount_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate amount as Decimal with up to 2 fractional digits.
    Returns (normalized_str, error) where one will be None.
    """
    s = (amount_str or "").strip()
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        return None, f"Amount is not a valid number: '{amount_str}'."

    # Normalize to string with exactly 2 decimal places (no scientific notation)
    quantized = d.quantize(Decimal("0.01"))
    return f"{quantized:.2f}", None


def validate_transaction(
    *,
    datetime_str: str,
    category: str,
    amount_str: str,
    description: str,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
    disallow_future: bool = True,
) -> Tuple[bool, List[str], Dict[str, str]]:
    """
    Validate fields and return (is_valid, errors, normalized_dict).
    normalized_dict has 'datetime', 'category', 'amount', 'description'.
    """
    errors: List[str] = []
    normalized: Dict[str, str] = {}

    # datetime
    norm_dt, err_dt = _parse_and_normalize_datetime(datetime_str)
    if err_dt:
        errors.append(err_dt)
    else:
        if disallow_future:
            dt_obj = datetime.strptime(norm_dt, "%Y-%m-%dT%H:%M:%S")
            if dt_obj > datetime.now():
                errors.append("Datetime cannot be in the future.")
        normalized["datetime"] = norm_dt

    # category
    cat = (category or "").strip()
    if not cat:
        errors.append("Category is required.")
    else:
        if allowed_categories is not None:
            allowed = {c.strip() for c in allowed_categories}
            if cat not in allowed:
                errors.append(f"Category '{cat}' is not in the allowed set: {sorted(allowed)}")
        normalized["category"] = cat

    # amount
    norm_amt, err_amt = _validate_amount(amount_str)
    if err_amt:
        errors.append(err_amt)
    else:
        normalized["amount"] = norm_amt

    # description
    desc = (description or "").strip()
    if not desc:
        errors.append("Description is required.")
    else:
        normalized["description"] = desc

    return len(errors) == 0, errors, normalized


# ---------- CRUD ----------

def create_transaction(
    csv_path: str,
    *,
    datetime_str: str,
    category: str,
    amount_str: str,
    description: str,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
) -> Transaction:
    """
    Create a transaction and append it to CSV (returns the created Transaction).
    Raises ValueError on validation failure.
    """
    ok, errs, normalized = validate_transaction(
        datetime_str=datetime_str,
        category=category,
        amount_str=amount_str,
        description=description,
        allowed_categories=allowed_categories,
    )
    if not ok:
        raise ValueError(f"Validation errors: {errs}")

    tx_id = str(uuid.uuid4())
    tx = Transaction(
        id=tx_id,
        datetime=normalized["datetime"],
        category=normalized["category"],
        amount=normalized["amount"],
        description=normalized["description"],
    )

    _ensure_csv_exists(csv_path)
    # Append row
    rows = _read_all(csv_path)
    rows.append(tx)
    _write_all(csv_path, rows)
    return tx


def read_transactions(csv_path: str) -> List[Transaction]:
    """Return all transactions (as Transaction dataclass instances)."""
    return _read_all(csv_path)


def get_transaction(csv_path: str, tx_id: str) -> Optional[Transaction]:
    """Return a transaction by id, or None if not found."""
    for tx in _read_all(csv_path):
        if tx.id == tx_id:
            return tx
    return None


def update_transaction(
    csv_path: str,
    tx_id: str,
    *,
    datetime_str: Optional[str] = None,
    category: Optional[str] = None,
    amount_str: Optional[str] = None,
    description: Optional[str] = None,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
) -> Transaction:
    """
    Update fields on an existing transaction.
    Any provided field will be updated and re-validated.
    Raises KeyError if id not found; ValueError on validation errors.
    Returns the updated Transaction.
    """
    all_txs = _read_all(csv_path)
    for idx, tx in enumerate(all_txs):
        if tx.id == tx_id:
            # Merge changes over current values
            new_dt = datetime_str if datetime_str is not None else tx.datetime
            new_cat = category if category is not None else tx.category
            new_amt = amount_str if amount_str is not None else tx.amount
            new_desc = description if description is not None else tx.description

            ok, errs, normalized = validate_transaction(
                datetime_str=new_dt,
                category=new_cat,
                amount_str=new_amt,
                description=new_desc,
                allowed_categories=allowed_categories,
            )
            if not ok:
                raise ValueError(f"Validation errors: {errs}")

            updated = Transaction(
                id=tx.id,
                datetime=normalized["datetime"],
                category=normalized["category"],
                amount=normalized["amount"],
                description=normalized["description"],
            )
            all_txs[idx] = updated
            _write_all(csv_path, all_txs)
            return updated

    raise KeyError(f"Transaction with id '{tx_id}' not found.")


def delete_transaction(csv_path: str, tx_id: str) -> bool:
    """
    Delete a transaction by id.
    Returns True if a row was deleted, False if not found.
    """
    all_txs = _read_all(csv_path)
    new_txs = [t for t in all_txs if t.id != tx_id]
    if len(new_txs) == len(all_txs):
        return False
    _write_all(csv_path, new_txs)
    return True


# ---------- Reporting (overall) ----------

def get_totals(csv_path: str) -> dict:
    """
    Compute totals from all transactions.
    Returns a dict with keys: 'income', 'expenses', 'net'.
    
    - Income: sum of all positive amounts
    - Expenses: sum of all negative amounts (absolute value)
    - Net: income - expenses
    """
    txs = read_transactions(csv_path)
    income = Decimal("0.00")
    expenses = Decimal("0.00")

    for tx in txs:
        try:
            amt = Decimal(tx.amount)
        except Exception:
            continue  # skip invalid numbers silently

        if amt > 0:
            income += amt
        elif amt < 0:
            expenses += abs(amt)

    net = income - expenses
    return {
        "income": float(income),
        "expenses": float(expenses),
        "net": float(net),
    }


def get_total_income(csv_path: str) -> float:
    """Return total income (sum of positive amounts)."""
    return get_totals(csv_path)["income"]


def get_total_expenses(csv_path: str) -> float:
    """Return total expenses (sum of absolute values of negative amounts)."""
    return get_totals(csv_path)["expenses"]


def get_net_savings(csv_path: str) -> float:
    """Return net savings (income - expenses)."""
    return get_totals(csv_path)["net"]


# ---------- Category-level Reporting ----------

def get_category_totals(csv_path: str) -> dict:
    """
    Returns a dictionary with category-level totals.

    Example:
    {
        "Groceries": {"income": 0.0, "expenses": 245.50, "net": -245.50},
        "Salary":    {"income": 5000.0, "expenses": 0.0, "net": 5000.0},
        "Dining":    {"income": 0.0, "expenses": 120.75, "net": -120.75},
        ...
    }
    """
    txs = read_transactions(csv_path)
    category_totals = defaultdict(lambda: {"income": Decimal("0.00"),
                                           "expenses": Decimal("0.00"),
                                           "net": Decimal("0.00")})

    for tx in txs:
        try:
            amt = Decimal(tx.amount)
        except Exception:
            continue  # skip invalid rows silently

        cat = tx.category or "Uncategorized"

        if amt > 0:
            category_totals[cat]["income"] += amt
        elif amt < 0:
            category_totals[cat]["expenses"] += abs(amt)

        # Net = income - expenses
        category_totals[cat]["net"] = (
            category_totals[cat]["income"] - category_totals[cat]["expenses"]
        )

    # Convert Decimals to floats for easy JSON/export use
    return {
        cat: {k: float(v) for k, v in totals.items()}
        for cat, totals in category_totals.items()
    }


def print_category_summary(csv_path: str) -> None:
    """
    Pretty-print category totals in a simple table.
    """
    totals = get_category_totals(csv_path)

    print(f"{'Category':<20} {'Income':>10} {'Expenses':>10} {'Net':>10}")
    print("-" * 55)
    for cat, vals in totals.items():
        print(f"{cat:<20} {vals['income']:>10.2f} {vals['expenses']:>10.2f} {vals['net']:>10.2f}")


# MENU FLOW BEGIN

def _render_transactions_table(csv_path: str) -> None:
    """Pretty-print all transactions (truncate long descriptions)."""
    txs = read_transactions(csv_path)
    rows = []
    for t in txs:
        desc = t.description if len(t.description) <= 40 else t.description[:37] + "..."
        rows.append({
            "id": t.id,
            "datetime": t.datetime,
            "category": t.category,
            "amount": f"{Decimal(t.amount):.2f}",
            "description": desc,
        })
    if rows:
        print(tabulate(rows, headers="keys", floatfmt=".2f"))
    else:
        print("No transactions found.")


def _prompt_nonempty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("Value cannot be empty. Please try again.")


def _prompt_amount(prompt: str) -> str:
    """Prompt until a valid decimal with 2 places is entered."""
    while True:
        s = input(prompt).strip()
        try:
            d = Decimal(s)
            return f"{d.quantize(Decimal('0.01')):.2f}"
        except Exception:
            print("Invalid amount. Example formats: 12.34, -45.00, 0")


def _prompt_datetime(prompt: str) -> str:
    """Accept a few common formats; normalize via your validator."""
    while True:
        s = input(prompt).strip()
        norm, err = _parse_and_normalize_datetime(s)
        if not err:
            return norm
        print(err)


def _enter_transaction_flow(csv_path: str) -> None:
    """Interactive entry for a single transaction."""
    print("\nEnter a new transaction")
    print("-" * 30)
    dt = _prompt_datetime(
        "Datetime (e.g., 2025-09-02 14:30 or 2025-09-02T14:30): "
    )
    cat = _prompt_nonempty("Category: ")
    amt = _prompt_amount("Amount (neg for expense, pos for income): ")
    desc = _prompt_nonempty("Description: ")

    try:
        create_transaction(
            csv_path,
            datetime_str=dt,
            category=cat,
            amount_str=amt,
            description=desc,
        )
        print("✔ Transaction saved.")
    except ValueError as ex:
        print(f"✖ Validation errors: {ex}")
    except Exception as ex:
        print(f"✖ Unexpected error: {ex}")


def _render_totals(csv_path: str) -> None:
    totals = get_totals(csv_path)
    # Show a one-row table
    print(tabulate([totals], headers="keys", floatfmt=".2f"))


def run_cli_menu(csv_path: str = "transactions.csv") -> None:
    """
    Interactive CLI menu to view transactions, enter a transaction,
    or view totals/category summary. Loops until user exits.
    """
    _ensure_csv_exists(csv_path)

    MENU = (
        "\n=== Personal Finance Tracker ===\n"
        "1) View transactions\n"
        "2) Enter a transaction\n"
        "3) View totals (Income / Expenses / Net)\n"
        "4) View category summary\n"
        "0) Exit\n"
        "Choose an option: "
    )

    while True:
        choice = input(MENU).strip()

        if choice == "1":
            _render_transactions_table(csv_path)
        elif choice == "2":
            _enter_transaction_flow(csv_path)
        elif choice == "3":
            _render_totals(csv_path)
        elif choice == "4":
            print_category_summary(csv_path)
        elif choice == "0":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid option. Please choose 0–4.")


# MENU FLOW END



if __name__ == "__main__":
    # call main
    main()
    pass

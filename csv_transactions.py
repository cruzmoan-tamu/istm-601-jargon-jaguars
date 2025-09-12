"""
csv_transactions.py

CSV-backed CRUD for personal finance transactions with validation and reporting.

Schema (CSV headers):
    id, datetime, category, amount, type, description
"""

from __future__ import annotations

import csv
import os
import tempfile
import uuid
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, List, Optional, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate

CSV_HEADERS = ["id", "datetime", "category", "amount", "type", "description"]

# Optional: define an allowed set of categories. Set to None to allow any string.
DEFAULT_ALLOWED_CATEGORIES: Optional[Iterable[str]] = None
TYPE_ALLOWED = {"income", "expense"}

@dataclass
class Transaction:
    id: str
    datetime: str  # ISO 8601 string
    category: str
    amount: str    # Decimal as string (e.g., "-12.34")
    type: str      # "income" or "expense"
    description: str


def main():
    run_cli_menu("transactions.csv")


# ---------- Utilities ----------

def _ensure_csv_exists(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def _atomic_write_rows(csv_path: str, rows: List[Dict[str, str]]) -> None:
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
            tx = Transaction(
                id=(row.get("id", "") or "").strip(),
                datetime=(row.get("datetime", "") or "").strip(),
                category=(row.get("category", "") or "").strip(),
                amount=(row.get("amount", "") or "").strip(),
                type=(row.get("type", "") or "").strip(),
                description=(row.get("description", "") or "").strip(),
            )
            out.append(tx)
    return out


def _write_all(csv_path: str, txs: List[Transaction]) -> None:
    rows = [asdict(t) for t in txs]
    _atomic_write_rows(csv_path, rows)


# ---------- Validation ----------

def _parse_and_normalize_datetime(dt_str: str) -> Tuple[Optional[str], Optional[str]]:
    s = (dt_str or "").strip()
    candidates = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S"), None
        except ValueError:
            continue
    return None, f"Invalid datetime format: '{dt_str}'. Expected ISO-like (e.g., 2025-09-02T14:30:00)."


def _fmt2(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _validate_amount_raw(amount_str: str) -> Tuple[Optional[Decimal], Optional[str]]:
    s = (amount_str or "").strip()
    try:
        return Decimal(s), None
    except (InvalidOperation, ValueError):
        return None, f"Amount is not a valid number: '{amount_str}'."


def _normalize_amount_by_type(d: Decimal, t: str) -> Decimal:
    if t == "income":
        return abs(d)
    if t == "expense":
        return -abs(d)
    return d


def validate_transaction(
    *,
    datetime_str: str,
    category: str,
    amount_str: str,
    type_str: str,
    description: str,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
    disallow_future: bool = True,
) -> Tuple[bool, List[str], Dict[str, str]]:
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

    # type
    t = (type_str or "").strip().lower()
    if t not in TYPE_ALLOWED:
        errors.append(f"Type must be one of {sorted(TYPE_ALLOWED)}.")
    else:
        normalized["type"] = t

    # amount
    d, err_amt = _validate_amount_raw(amount_str)
    if err_amt:
        errors.append(err_amt)
    else:
        d = _normalize_amount_by_type(d, normalized.get("type", t))
        normalized["amount"] = _fmt2(d)

    # type
    type = (type or "").strip()
    if not type:
        errors.append("Type is required.")
    else:
        normalized["type"] = type

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
    type: str,
    description: str,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
) -> Transaction:
    ok, errs, normalized = validate_transaction(
        datetime_str=datetime_str,
        category=category,
        amount=amount_str,
        type=type,
        description=description,
        allowed_categories=allowed_categories,
    )
    if not ok:
        raise ValueError(f"Validation errors: {errs}")

    tx = Transaction(
        id=str(uuid.uuid4()),
        datetime=normalized["datetime"],
        category=normalized["category"],
        amount=normalized["amount"],
        type=normalized["type"],
        description=normalized["description"],
    )

    rows = _read_all(csv_path)
    rows.append(tx)
    _write_all(csv_path, rows)
    return tx


def read_transactions(csv_path: str) -> List[Transaction]:
    return _read_all(csv_path)


def get_transaction(csv_path: str, tx_id: str) -> Optional[Transaction]:
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
    type_str: Optional[str] = None,
    description: Optional[str] = None,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
) -> Transaction:
    """
    Merge provided fields over the existing row and re-validate.
    If type is changed, the amount sign is re-normalized to match.
    Raises:
      - KeyError if the ID doesn't exist
      - ValueError on validation failures
    """
    all_txs = _read_all(csv_path)

    for idx, tx in enumerate(all_txs):
        if tx.id == tx_id:
            # New values fallback to existing persisted values
            new_dt = datetime_str if datetime_str is not None else tx.datetime
            new_cat = category if category is not None else tx.category
            new_amt = amount_str if amount_str is not None else tx.amount
            new_type = type_str if type_str is not None else tx.type
            new_desc = description if description is not None else tx.description

            ok, errs, normalized = validate_transaction(
                datetime_str=new_dt,
                category=new_cat,
                amount_str=new_amt,
                type_str=new_type,
                description=new_desc,
                allowed_categories=allowed_categories,
            )
            if not ok:
                raise ValueError(f"Validation errors: {errs}")

            updated = Transaction(
                id=tx.id,  # ID never changes
                datetime=normalized["datetime"],
                category=normalized["category"],
                amount=normalized["amount"],
                type=normalized["type"],
                description=normalized["description"],
            )
            all_txs[idx] = updated
            _write_all(csv_path, all_txs)
            return updated

    # No row matched the given ID
    raise KeyError(f"Transaction with id '{tx_id}' not found.")


def delete_transaction(csv_path: str, tx_id: str) -> bool:
    all_txs = _read_all(csv_path)
    new_txs = [t for t in all_txs if t.id != tx_id]
    if len(new_txs) == len(all_txs):
        return False
    _write_all(csv_path, new_txs)
    return True


# ---------- Reporting ----------

def get_totals(csv_path: str) -> dict:
    txs = read_transactions(csv_path)
    income = Decimal("0.00")
    expenses = Decimal("0.00")

    for tx in txs:
        try:
            amt = Decimal(tx.amount)
        except Exception:
            continue
        if amt > 0:
            income += amt
        elif amt < 0:
            expenses += -amt

    net = income - expenses
    return {"income": float(income), "expenses": float(expenses), "net": float(net)}


def get_total_income(csv_path: str) -> float:
    return get_totals(csv_path)["income"]


def get_total_expenses(csv_path: str) -> float:
    return get_totals(csv_path)["expenses"]


def get_net_savings(csv_path: str) -> float:
    return get_totals(csv_path)["net"]


def get_category_totals(csv_path: str) -> dict:
    txs = read_transactions(csv_path)
    category_totals = defaultdict(lambda: {"income": Decimal("0.00"),
                                           "expenses": Decimal("0.00"),
                                           "net": Decimal("0.00")})

    for tx in txs:
        try:
            amt = Decimal(tx.amount)
        except Exception:
            continue

        cat = tx.category or "Uncategorized"
        if amt > 0:
            category_totals[cat]["income"] += amt
        elif amt < 0:
            category_totals[cat]["expenses"] += -amt

        category_totals[cat]["net"] = (
            category_totals[cat]["income"] - category_totals[cat]["expenses"]
        )

    return {
        cat: {k: float(v) for k, v in totals.items()}
        for cat, totals in category_totals.items()
    }


def print_category_summary(csv_path: str) -> None:
    totals = get_category_totals(csv_path)
    print(f"{'Category':<20} {'Income':>10} {'Expenses':>10} {'Net':>10}")
    print("-" * 55)
    for cat, vals in totals.items():
        print(
                f"{cat:<20} {vals['income']:>10.2f} "
                f"{vals['expenses']:>10.2f} {vals['net']:>10.2f}"
            )



# UPDATE CSV BEGIN

def date():
    
    pattern = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"

    while True:
        date = input("Enter transaction date (yyyy-mm-dd): ")
            
        if not re.match(pattern,date):
            print("Invalid format. Please enter date in mm-dd-yy format.")
            continue
            
        try:
            datetime.strptime(date, "%m-%d-%y")
            print("Date entered:", date)
            return date
        except ValueError:
            print("Invalid date! That day doesn't exist. Please try again.")
            continue
            
def description():
    while True:
        description = input("Enter transaction description: ")
            
        if len(description) == 0:
            print("Description cannot be empty")
            continue
        elif len(description) > 75:
            print("Invalid! Too many characters.")
            continue
        else:
            print("Description entered:", description)
            return description
            
            
def category():
    categories = {
        "1": "Living Expenses",
        "2": "Food and Dining",
        "3": "Personal & Lifestyle",
        "4": "Healthcare & Insurance",
        "5": "Family & Education",
        "6": "Miscellaneous",
        "7": "Earned Income",
        "8": "Unearned Income"
    }
    while True:
        category = input(
            "Enter category by number:\n"
            "1 - Living Expenses\n"
            "2 - Food and Dining\n"
            "3 - Personal & Lifestyle\n"
            "4 - Healthcare & Insurance\n"
            "5 - Family & Education\n"
            "6 - Miscellaneous\n"
            "7 - Earned Income\n"
            "8 - Unearned Income\n"
                
        ).strip()
            
        if category in categories:
            print("Category selected: ", categories[category])
            return categories[category]
        else:
            print("Invalid input! Please enter a number 1 to 8.")
   
def amount():
    while True:
        amount = input("Enter transaction amount: ")
             
        try:
            value = float(amount)
            if value < 0:
                print("Amount cannot be negative.")
                continue
            print("Amount entered:", f"{value:.2f}")
            return value 
        except ValueError:
            print("Invalid input. Please enter numbers only.")       
    
    
def typed():
    types = {
        "1": "Income",
        "2": "Expense",
    }
    while True:
        typed = input(
            "Enter category by number:\n"
            "1 - Income\n"
            "2 - Expense\n"
        ).strip()
            
        if typed in types:
            print("Category selected: ", types[typed])
            return types[typed]
        else:
            print("Invalid input! Please enter a number 1 or 2.")

# UPDATE CSV END


# UPDATE CSV BEGIN

def update_transaction(
    csv_path: str,
    tx_id: str,
    *,
    datetime_str: Optional[str] = None,
    category: Optional[str] = None,
    amount_str: Optional[str] = None,
    description: Optional[str] = None,
    type_str: Optional[str] = None,
    allowed_categories: Optional[Iterable[str]] = DEFAULT_ALLOWED_CATEGORIES,
) -> Transaction:
    """
    Update fields on an existing transaction.

    - Any provided field will be updated and re-validated.
    - If type_str is provided, amount sign is normalized to match it.
    - Raises KeyError if id not found.
    - Raises ValueError on validation errors.
    - Returns the updated Transaction dataclass instance.
    """
    # Load all existing transactions
    all_txs = _read_all(csv_path)

    # Find the transaction with the matching ID
    for idx, tx in enumerate(all_txs):
        if tx.id == tx_id:
            # Merge user-provided values with current ones.
            # If a new value is provided, use it; otherwise keep the old one.
            new_dt   = datetime_str if datetime_str is not None else tx.datetime
            new_cat  = category    if category    is not None else tx.category
            new_amt  = amount_str  if amount_str  is not None else tx.amount
            new_desc = description if description is not None else tx.description
            new_type = type_str    if type_str    is not None else tx.type

            # Validate the merged data (datetime, category, amount, type, description).
            # Also ensures amount sign matches the type.
            ok, errs, normalized = validate_transaction(
                datetime_str=new_dt,
                category=new_cat,
                amount=new_amt,
                description=new_desc,
                type=new_type,
                allowed_categories=allowed_categories,
            )
            if not ok:
                # Abort update if validation fails
                raise ValueError(f"Validation errors: {errs}")

            # Create a new Transaction object with normalized values
            updated = Transaction(
                id=tx.id,
                datetime=normalized["datetime"],
                category=normalized["category"],
                amount=normalized["amount"],
                type=normalized["type"],
                description=normalized["description"],
            )

            # Replace the old transaction with the updated one in the list
            all_txs[idx] = updated

            # Atomically write the updated list back to CSV
            _write_all(csv_path, all_txs)

            # Return the updated transaction to caller
            return updated

    # If no transaction was found with the given ID, raise an error
    raise KeyError(f"Transaction with id '{tx_id}' not found.")

# UPDATE CSV END



# ---------- CLI Helpers & Menu ----------

def _render_transactions_table(csv_path: str) -> None:
    txs = read_transactions(csv_path)
    rows = []
    for t in txs:
        desc = t.description if len(t.description) <= 40 else t.description[:37] + "..."
        rows.append({
            "id": t.id,
            "datetime": t.datetime,
            "category": t.category,
            "type": t.type,
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
    while True:
        s = input(prompt).strip()
        try:
            d = Decimal(s)
            return _fmt2(d)
        except Exception:
            print("Invalid amount. Example formats: 12.34, -45.00, 0")


def _prompt_datetime(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        norm, err = _parse_and_normalize_datetime(s)
        if not err:
            return norm
        print(err)


def _prompt_type(prompt: str = "Type (income/expense) [i/e]: ") -> str:
    while True:
        s = input(prompt).strip().lower()
        if s in TYPE_ALLOWED:
            return s
        if s in {"i", "inc", "+"}:
            return "income"
        if s in {"e", "exp", "-"}:
            return "expense"
        print("Please enter 'income' (i) or 'expense' (e).")


def _enter_transaction_flow(csv_path: str) -> None:
    """Interactive entry for a single transaction."""
    while True:
        date_value = date()  
        description_value = description()
        category_value = category() 
        amount_value = amount()
        typed_value = typed()  

        # commit to CSV
        try:
            create_transaction(
                csv_path,
                datetime_str=date_value,
                category=category_value,
                amount_str=amount_value,
                type=typed_value,
                description=description_value,
            )
            print("✔ Transaction saved.")
        except ValueError as ex:
            print(f"✖ Validation errors: {ex}")
        except Exception as ex:
            print(f"✖ Unexpected error: {ex}")
        
        # remove extra spaces and convert word to lower case
        again = input("Do you want to enter another transaction? (yes/no): ").strip().lower()
        
        if again == "no":
            print("Thanks and Gig 'Em")
            break
            
        elif again == "yes":
            continue
        else:
            print("Invalid input. Please enter yes or no.")

    


def _render_totals(csv_path: str) -> None:
    totals = get_totals(csv_path)
    print(tabulate([totals], headers="keys", floatfmt=".2f"))


def run_cli_menu(csv_path: str = "transactions.csv") -> None:
    _ensure_csv_exists(csv_path)

    MENU = (
        "\n=== SHOW ME THE MONEY!!! ===\n"
        "\n=== Personal Finance Tracker ===\n"
        "1) View transactions\n"
        "2) Enter a transaction\n"
        "3) View totals (Income / Expenses / Net)\n"
        "4) View category summary\n"
        "5) Edit a transaction\n"
        "6) Delete a transaction\n"
        "0) Exit and Gig'em\n"
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
        elif choice == "5":
            _edit_transaction_flow(csv_path)
        elif choice == "6":
            tx_id = input("Enter ID of the transaction to delete: ").strip()
            confirmed = input("Are you sure you want to delete this transaction? (y/n): ").strip().lower()
            if confirmed == "y":
                print("Transaction deleted." if delete_transaction(csv_path, tx_id) else "Transaction not found.")
            else:
                print("Deletion cancelled.")
        elif choice == "0":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid option. Please choose 0–6.")


if __name__ == "__main__":
    main()
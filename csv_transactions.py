# PROGRAM:      Show Me The Money Financial Tracker
# PURPOSE:      Allows user to track financial transactions
# INPUT:        Transaction data
# PROCESS:      Creates, Reads, Updates, and Deletes financial transactions
# OUTPUT:       Tabulate aligned data and reports
# HONOR CODE:   On my honor, as an Aggie, I have neither given nor received 
#               unauthorized aid on this academic work.

from __future__ import annotations

import csv
import os
import tempfile
import uuid
import re #checks date matches the yyyy-mm-dd pattern
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass, asdict
from datetime import datetime #used to check date is valid
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate
from turtle import title
import calendar


# The headers in the CSV file for financial transactions
# These are used in both the display and data validation
CSV_HEADERS = ["id", "datetime", "category", "amount", "type", "description"]

# Optional: define an allowed set of categories.Set to None to allow any string.
# We will add in our allowed cetefories here
DEFAULT_ALLOWED_CATEGORIES: Optional[Iterable[str]] = None
# Example:
# DEFAULT_ALLOWED_CATEGORIES = {"Income", "Groceries", "Rent", "Utilities", 
# "Dining", "Transport", "Entertainment", "Savings"}


# The transaction class.  This allows for scricly defined properties
# for a financial transaction
@dataclass
class Transaction:
    id: str
    datetime: str   # ISO 8601 string
    category: str
    amount: str     # Decimal as string (e.g., "-12.34")
    type: str
    description: str


# main function - the start of the program
# Update main() to pass categories path
def main():
    run_cli_menu("transactions.csv", "categories.csv")



# ---------- Utilities ----------
# Validates the CSV files exists, with the proper headers
def _ensure_csv_exists(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


# writes the transactions row(s) to the csv file,
# using the headers that are configured
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


# Reads the CSV file into the transaction class, setting the appropriate
# properties
def _read_all(csv_path: str) -> List[Transaction]:
    _ensure_csv_exists(csv_path)
    out: List[Transaction] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Be tolerant to missing columns 
            # (but we keep the schema strict on write)
            tx = Transaction(
                id=row.get("id", "").strip(),
                datetime=row.get("datetime", "").strip(),
                category=row.get("category", "").strip(),
                amount=row.get("amount", "").strip(),
                type = row.get("type", "").strip(),
                description=row.get("description", "").strip(),
            )
            out.append(tx)
    return out

# ---------- Categories CSV Utilities ----------

CATEGORIES_HEADERS = ["name", "type"]  # type is 'income' or 'expense'

def _ensure_categories_csv_exists(categories_path: str) -> None:
    if not os.path.exists(categories_path):
        with open(categories_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CATEGORIES_HEADERS)
            writer.writeheader()
            defaults = [
                {"name": "Living Expenses", "type": "expense"},
                {"name": "Food and Dining", "type": "expense"},
                {"name": "Personal & Lifestyle", "type": "expense"},
                {"name": "Healthcare & Insurance", "type": "expense"},
                {"name": "Family & Education", "type": "expense"},
                {"name": "Miscellaneous", "type": "expense"},
                {"name": "Other", "type": "expense"},
                {"name": "Earned Income", "type": "income"},
                {"name": "Unearned Income", "type": "income"},
                {"name": "Other", "type": "income"},
            ]
            writer.writerows(defaults)

def _read_categories(categories_path: str) -> List[Dict[str, str]]:
    _ensure_categories_csv_exists(categories_path)
    out: List[Dict[str, str]] = []
    with open(categories_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            typ = (row.get("type") or "").strip().lower()
            if name and typ in {"income", "expense"}:
                out.append({"name": name, "type": typ})
    return out

def _write_categories(categories_path: str, rows: List[Dict[str, str]]) -> None:
    dir_name = os.path.dirname(os.path.abspath(categories_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="cat_", suffix=".csv", dir=dir_name)
    os.close(fd)
    try:
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CATEGORIES_HEADERS)
            writer.writeheader()
            for r in rows:
                writer.writerow({"name": r["name"], "type": r["type"]})
        os.replace(tmp_path, categories_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

def _list_categories_by_type(categories_path: str, typ: str) -> List[str]:
    cats = [c["name"] for c in _read_categories(categories_path) if c["type"] == typ]
    if "Other" not in cats:
        cats.append("Other")
    return sorted(cats, key=str.lower)

def _all_category_names(categories_path: str) -> List[str]:
    return sorted({c["name"] for c in _read_categories(categories_path)}, key=str.lower)

def _category_in_use(csv_path: str, name: str) -> bool:
    for tx in _read_all(csv_path):
        if (tx.category or "").strip().lower() == name.strip().lower():
            return True
    return False

# ---------- Categories CSV Utilities ----------



# Writes the transaction classes to dictionary rows and then
# passes the values into _atomic_write_rows
def _write_all(csv_path: str, txs: List[Transaction]) -> None:
    rows = [asdict(t) for t in txs]
    _atomic_write_rows(csv_path, rows)


# ---------- Validation ----------

# converts a datetime value to ISO 8601 'YYYY-MM-DDTHH:MM:SS'
def _parse_and_normalize_datetime(
    dt_str: str)->Tuple[Optional[str],Optional[str]]:
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
    return None, f"Invalid datetime format: '{dt_str}'. " \
                  "Expected ISO-like (e.g., 2025-09-02T14:30:00)."

# validation for amount, ensures its a float with 2 decimal places
def _validate_amount(amount_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate amount as Decimal with up to 2 fractional digits.
    Returns (normalized_str, error) where one will be None.
    """
    
    try:
        d = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        return None, f"Amount is not a valid number: '{amount_str}'."

    # Normalize to string with exactly 2 decimal places (no scientific notation)
    quantized = d.quantize(Decimal("0.01"))
    return f"{quantized:.2f}", None

# validates the values of a transaction
def validate_transaction(
    *,
    datetime_str: str,
    category: str,
    amount: str,
    type: str,
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
                errors.append(f"Category '{cat}' is not in the allowed " \
                               "set: {sorted(allowed)}")
        normalized["category"] = cat

    # amount
    norm_amt, err_amt = _validate_amount(amount)
    if err_amt:
        errors.append(err_amt)
    else:
        normalized["amount"] = norm_amt

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
# Creates a transactions and writes it to the CSV file
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
    """
    Create a transaction and append it to CSV (returns the created Transaction).
    Raises ValueError on validation failure.
    """
    
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

    # make sure type is lower
    normalized["type"] = normalized["type"].lower()

    # make sure amount "sign" is correct based on transaction type
    if (normalized["type"] == "expense" and float(normalized["amount"]) > 0):
        normalized["amount"] = float(normalized["amount"]) * -1

    if (normalized["type"] == "income" and float(normalized["amount"]) < 0):
        normalized["amount"] = float(normalized["amount"]) * -1

    tx_id = str(uuid.uuid4())
    tx = Transaction(
        id=tx_id,
        datetime=normalized["datetime"],
        category=normalized["category"],
        amount=normalized["amount"],
        type=normalized["type"],
        description=normalized["description"],
    )

    _ensure_csv_exists(csv_path)
    # Append row
    rows = _read_all(csv_path)
    rows.append(tx)
    _write_all(csv_path, rows)
    return tx

# reads transaactions and returns a list of transaction classes
def read_transactions(csv_path: str) -> List[Transaction]:
    """Return all transactions (as Transaction dataclass instances)."""
    return _read_all(csv_path)

# reads the transaction file and returns a transaction class with the 
# given transaction id
def get_transaction(csv_path: str, tx_id: str) -> Optional[Transaction]:
    """Return a transaction by id, or None if not found."""
    for tx in _read_all(csv_path):
        if tx.id == tx_id:
            return tx
    return None

# deletes a transaction from the transaction file where the transaction
# matches the transaction id - returns true if successful
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
        print(
                f"{cat:<20} {vals['income']:>10.2f} "
                f"{vals['expenses']:>10.2f} {vals['net']:>10.2f}"
            )



# INSERT CSV BEGIN - used to create a transaction
# asks user for date value - used in the CLI
def date():
    pattern = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$" #year is 4 digits, month is between 01-12, day is between 01-31
        
    while True:
        date = input("Enter transaction date (yyyy-mm-dd): ") #get date from user
            
        if not re.match(pattern,date):
            print("Invalid format. Please enter date in yyyy-mm-dd format.") #states that the input was invalid
            continue
            
        try:
            datetime.strptime(date, "%Y-%m-%d") #checks that the date exists
            print("Date entered:", date) #confirms the date entered
            return date
        except ValueError:
            print("Invalid date! That day doesn't exist. Please try again.") #states that the date was invalid
            continue

# asks user for description value - used in the CLI          
def description():
    while True:
        description = input("Enter transaction description: ") #gets the description
            
        if len(description) == 0: #description cannot be blank
            print("Description cannot be empty")
            continue
        elif len(description) > 75: #description is limited to 75 characters
            print("Invalid! Too many characters.")
            continue
        else:
            print("Description entered:", description) #state the description entered
            return description
            
                           
#REPLACE — Old category(t) picker with file-driven picker

def _select_category_from_file(categories_path: str, tx_type: str) -> str:
    """
    Show numbered list of categories from categories.csv filtered by tx_type.
    Returns the chosen category name.
    """
    tx_type = (tx_type or "").strip().lower()
    if tx_type not in {"income", "expense"}:
        raise ValueError("Invalid transaction type for category selection.")

    cats = _list_categories_by_type(categories_path, tx_type)
    while True:
        print("Enter category by number:")
        for idx, name in enumerate(cats, start=1):
            print(f"{idx} - {name}")
        choice = input("Choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(cats):
            chosen = cats[int(choice) - 1]
            print("Category selected:", chosen)
            return chosen
        print("Invalid input! Please enter a valid number.")

#REPLACE — Old category(t) picker with file-driven picker

   
# asks user for amount value - used in the CLI
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
            print("Invalid input! Please enter a number 1 to 8.")    #user did not enter number between 1-8
    
# asks user for type value - used in the CLI
def typed():
#types dictionary
    types = {
        "1": "Income",
        "2": "Expense",
    }

    #user chooses type
    while True:
        typed = input(
            "Enter Type by number:\n"
            "1 - Income\n"
            "2 - Expense\n"
        ).strip()
            
        if typed in types:
            print("Type selected: ", types[typed])
            return types[typed]
        else:
            print("Invalid input! Please enter a number 1 or 2.") #user did not enter numbers 1 or 2

# INSERT CSV END


# UPDATE CSV BEGIN

# Iterate through all transactions to find the one matching the given ID
# Merge new values with existing ones (keep old if user didn’t provide new)
# Validate the merged transaction fields (date, category, amount, type, description)
# Abort and raise ValueError if validation fails
# Normalize type to lowercase and adjust amount sign based on income/expense rules
# Build a new Transaction object with validated, normalized values
# Replace the old transaction in the list with the updated one
# Save all transactions back to CSV atomically
# Return the updated transaction to the caller
# Raise KeyError if no transaction exists with the given ID

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
            new_dt = datetime_str if datetime_str is not None else tx.datetime
            new_cat = category if category is not None else tx.category
            new_amt = amount_str if amount_str is not None else tx.amount
            new_desc = description if description is not None else tx.description
            new_type = type_str if type_str is not None else tx.type

            # Validate merged data
            ok, errs, normalized = validate_transaction(
                datetime_str=new_dt,
                category=new_cat,
                amount=new_amt,
                description=new_desc,
                type=new_type,
                allowed_categories=allowed_categories,
            )
            if not ok:
                raise ValueError(f"Validation errors: {errs}")

            # Normalize type casing
            norm_type = normalized["type"].lower()

            # Normalize amount sign to match type
            amt_val = float(normalized["amount"])
            if norm_type == "expense" and amt_val > 0:
                amt_val = -amt_val
            elif norm_type == "income" and amt_val < 0:
                amt_val = -amt_val
            norm_amount_str = f"{amt_val:.2f}"

            # Create a new Transaction object with normalized values
            updated = Transaction(
                id=tx.id,
                datetime=normalized["datetime"],
                category=normalized["category"],
                amount=norm_amount_str,
                type=norm_type,
                description=normalized["description"],
            )

            # Replace and persist
            all_txs[idx] = updated
            _write_all(csv_path, all_txs)
            return updated

    # If no transaction was found with the given ID, raise an error
    raise KeyError(f"Transaction with id '{tx_id}' not found.")

# UPDATE CSV END



# MENU FLOW BEGIN

# renders a list of transactions - called by the menu in the CLI
def _render_transactions_table(csv_path: str) -> None:
    """Pretty-print all transactions (truncate long descriptions)."""
    txs = read_transactions(csv_path)
    rows = []
    for t in txs:
        desc = (
                    t.description if len(t.description) <= 40
                    else t.description[:37] + "..."
                )

        rows.append({
            "id": t.id,
            "datetime": t.datetime,
            "category": t.category,
            "amount": f"{Decimal(t.amount):.2f}",
            "type": t.type,
            "description": desc,
        })
    if rows:
        print(tabulate(rows, headers="keys", floatfmt=".2f"))
    else:
        print("No transactions found.")

# validates an empty promp when the user does not enter a value
def _prompt_nonempty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("Value cannot be empty. Please try again.")

# used by the CLI prompt to get the amount value
def _prompt_amount(prompt: str) -> str:
    """Prompt until a valid decimal with 2 places is entered."""
    while True:
        s = input(prompt).strip()
        try:
            d = Decimal(s)
            return f"{d.quantize(Decimal('0.01')):.2f}"
        except Exception:
            print("Invalid amount. Example formats: 12.34, -45.00, 0")

# used by the CLI prompt to get the datetime value
def _prompt_datetime(prompt: str) -> str:
    """Accept a few common formats; normalize via your validator."""
    while True:
        s = input(prompt).strip()
        norm, err = _parse_and_normalize_datetime(s)
        if not err:
            return norm
        print(err)

# creates a transaction
#Wire categories into the transaction flows

def _enter_transaction_flow(csv_path: str, categories_path: str) -> None:
    """Interactive entry for a single transaction (uses categories.csv)."""
    _ensure_categories_csv_exists(categories_path)
    while True:
        date_value = date()
        typed_value = typed()  # returns "Income" or "Expense"
        tx_type_norm = typed_value.strip().lower()

        category_value = _select_category_from_file(categories_path, tx_type_norm)
        description_value = description()
        amount_value = amount()  # returns string "12.34"

        # Build allowed categories (names only) for validation
        allowed = _all_category_names(categories_path)

        try:
            create_transaction(
                csv_path,
                datetime_str=date_value,
                category=category_value,
                amount_str=amount_value,
                type=typed_value,
                description=description_value,
                allowed_categories=allowed,
            )
            print("✔ Transaction saved.")
        except ValueError as ex:
            print(f"✖ Validation errors: {ex}")
        except Exception as ex:
            print(f"✖ Unexpected error: {ex}")

        again = input("Do you want to enter another transaction? (yes/no): ").strip().lower()
        if again == "no":
            print("Thanks and Gig 'Em")
            break
        elif again != "yes":
            print("Invalid input. Please enter yes or no.")

# edits a transaction

# Ask the user which transaction to edit by ID, retrieve it, or exit if not found
# Provide a fixed menu of allowed categories (no free-text entry)
# Show current values and let user press Enter to keep each one
# For datetime: accept a new value or keep the old one
# For category: show a numbered list (1–8), user picks by number or presses Enter to keep current
# For type: accept full word or shorthand (i/e, +/−), normalize to "income" or "expense"
# For amount and description: accept new value or keep current if blank
# After collecting new values, call update_transaction with them
# Validate against the same fixed categories list
# If update succeeds, print the updated transaction in a table
# Handle errors gracefully:
#   - ValueError if validation fails (e.g., bad amount/date/category)
#   - KeyError if transaction not found
#   - Generic Exception for unexpected errors

#Wire categories into the transaction edit

def _edit_transaction_flow(csv_path: str, categories_path: str) -> None:
    _ensure_categories_csv_exists(categories_path)
    tx_id = input("Enter ID of the transaction to edit: ").strip()
    tx = get_transaction(csv_path, tx_id)
    if not tx:
        print("Transaction not found.")
        return

    print("\nLeave a field blank to keep current value.")

    print(f"Current datetime:   {tx.datetime}")
    new_dt = input("New datetime: ").strip() or None

    print(f"Current type:       {tx.type}")
    new_type = input("New type (income/expense or i/e): ").strip().lower() or None
    if new_type is not None:
        if new_type in {"i", "inc", "+"}:
            new_type = "income"
        elif new_type in {"e", "exp", "-"}:
            new_type = "expense"
        elif new_type not in {"income", "expense"}:
            print("Invalid type. Use income/expense (or i/e). Keeping current.")
            new_type = None

    effective_type = (new_type or tx.type).strip().lower()
    current_cat = tx.category
    print(f"Current category:   {current_cat}")
    print("Select a new category (Enter to keep current):")
    cats = _list_categories_by_type(categories_path, effective_type)
    for i, c in enumerate(cats, start=1):
        print(f"{i} - {c}")
    raw = input("Choice [number or blank]: ").strip()
    if raw == "":
        new_cat = None
    elif raw.isdigit() and 1 <= int(raw) <= len(cats):
        new_cat = cats[int(raw) - 1]
    else:
        print("Invalid choice. Keeping current.")
        new_cat = None

    print(f"Current amount:     {tx.amount}")
    new_amt = input("New amount: ").strip() or None

    print(f"Current description: {tx.description}")
    new_desc = input("New description: ").strip() or None

    # Allowed categories for validation
    allowed = _all_category_names(categories_path)

    try:
        updated = update_transaction(
            csv_path,
            tx_id,
            datetime_str=new_dt,
            category=new_cat,
            amount_str=new_amt,
            type_str=new_type,
            description=new_desc,
            allowed_categories=allowed,
        )
        print("✔ Updated:")
        print(tabulate([asdict(updated)], headers="keys", floatfmt=".2f"))
    except ValueError as ex:
        print(f"✖ Validation errors: {ex}")
    except KeyError as ex:
        print(f"✖ {ex}")
    except Exception as ex:
        print(f"✖ Unexpected error: {ex}")

# reports to the CLI income, expenses, and net savings
def _render_totals(csv_path: str) -> None:
    # totals = get_totals(csv_path)
    # # Show a one-row table
    # print(tabulate([totals], headers="keys", floatfmt=".2f"))

    # Load CSV
    DataFrame = pd.read_csv("transactions.csv")

    # Ensure amounts are numeric
    DataFrame['amount'] = pd.to_numeric(
        DataFrame['amount'], errors='coerce'
    )

    # Total income
    TotalIncome = DataFrame[
        DataFrame['type'].str.lower() == 'income'
    ]['amount'].sum()

    # Total expenses (absolute value of negatives)
    TotalExpenses = DataFrame[
        DataFrame['type'].str.lower() == 'expense'
    ]['amount'].sum()

    # Net savings
    NetSavings = TotalIncome + TotalExpenses

    # Format and print results
    print("===== Financial Summary =====")
    print(f"Total Income:   ${TotalIncome:,.2f}")
    print(f"Total Expenses: ${abs(TotalExpenses):,.2f}")
    print(f"Net Savings:    ${NetSavings:,.2f}")

    return TotalIncome, TotalExpenses, NetSavings


# REPORTING GRAPHS BEGIN
# Takes in parameters of csv file name, start date range, and end date range
def plot_financials(csv_file, freq="M", start_date=None, end_date=None):
    """
    Plots income, expenses, and net balance over time from a financial CSV.

    Parameters:
        csv_file (str): Path to the CSV file.
        freq (str): Resampling frequency (D=daily, W=weekly, M=monthly, Y=yearly).
    """
    # Ask user for date range to filter income, expense, and net balance
    if not start_date:
        start_date = input("Enter start date (YYYY-MM-DD) or press Enter for earliest: ").strip()
        start_date = start_date if start_date else None
    if not end_date:
        end_date = input("Enter end date (YYYY-MM-DD) or press Enter for latest: ").strip()
        end_date = end_date if end_date else None

    # Load CSV
    df = pd.read_csv(csv_file, parse_dates=["datetime"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Apply date range filter if provided
    if start_date:
        df = df[df["datetime"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["datetime"] <= pd.to_datetime(end_date)]

    if df.empty:
        print("No transactions found in the given date range.")
        return None

    # Group by time & type
    summary = df.groupby(
        [pd.Grouper(key="datetime", freq=freq), "type"]
    )["amount"].sum().unstack(fill_value=0)

    # Ensure both columns exist
    summary = summary.reindex(columns=["income", "expense"], fill_value=0)

    # Net balance
    summary["net"] = summary["income"] + summary["expense"]  # (expenses are negative)

    # Plot
    plt.figure(figsize=(10,6))
    plt.plot(summary.index, summary["income"], marker="o", label="Income", color="green")
    plt.plot(summary.index, summary["expense"], marker="o", label="Expense", color="red")
    plt.plot(summary.index, summary["net"], marker="o", label="Net", color="blue")

    plt.title(f"Financial Report ({freq})")
    plt.xlabel("Date")
    plt.ylabel("Amount ($)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return summary


def plot_category_summary(csv_file):
    """
    Plots total income and expenses by category from a financial CSV.
    Expenses are shown as positive values for easier comparison.
    
    Parameters:
        csv_file (str): Path to the CSV file.
    """
    # Load CSV
    df = pd.read_csv(csv_file, parse_dates=["datetime"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Adjust amounts: make expenses positive
    df["amount_display"] = df.apply(
        lambda row: -row["amount"] if row["type"] == "expense" else row["amount"],
        axis=1
    )

    # Group by category
    category_summary = df.groupby("category")["amount_display"].sum().sort_values()

    # Plot bar chart
    plt.figure(figsize=(10, 5))
    colors = ["red" if v > 0 and cat in df[df["type"]=="expense"]["category"].unique() else "green"
              for cat, v in category_summary.items()]
    
    category_summary.plot(kind="bar", color=colors)

    plt.title("Total Income & Expenses by Category")
    plt.ylabel("Amount ($)")
    plt.xlabel("Category")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()

    return category_summary

class NoDataError(Exception):
    pass

def monthlysavings():
    # Load CSV with all relevant columns
    df = pd.read_csv(
        "transactions.csv",
        names=['id', 'datetime', 'category', 'amount', 'type', 'description'],
        header=0,
        parse_dates=['datetime']
    )

    # Ensure type and category columns are clean strings
    df['type'] = df['type'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip()

    # Prompt user for month and year
    choice = input("Enter year and month (YYYY-MM): ").strip()
    try:
        year, month = map(int, choice.split('-'))
    except ValueError:
        raise ValueError("Invalid format. Use YYYY-MM")
       
    # Filter by month
    df_month = df[(df['datetime'].dt.year == year) & (df['datetime'].dt.month == month)] 

    if df_month.empty:
        raise NoDataError(f"No data for the specified {choice}.")

    # Calculate totals
    incometotal = df_month[df_month['type'].str.lower() == 'income']['amount'].sum()
    expensestotal = df_month[df_month['type'].str.lower() == 'expense']['amount'].sum()
    savings = incometotal + expensestotal

    if savings <= 0:
        raise NoDataError(f"No savings for the specified {choice}.")

    month_name = calendar.month_name[month]
    title = f"{month_name} {year}"

    # Prepare pie chart
    fig, ax = plt.subplots(figsize=(6,6))
    values = [abs(expensestotal), max(savings, 0)]
    labels = ['Expenses', 'Savings']

   
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=['gray', 'maroon'])
    ax.set_title(f"Monthly Income & Savings for {title}\n(Total Savings: ${savings:,.2f})")
    plt.show()

# REPORTING GRAPHS END

#Manage Categories Nested MENU START

def _menu_manage_categories(categories_path: str, csv_path: str) -> None:
    """
    Nested menu to list/add/rename/delete categories stored in categories.csv.
    """
    _ensure_categories_csv_exists(categories_path)

    MENU = (
        "\n=== Manage Categories ===\n"
        "1) List categories\n"
        "2) Add category\n"
        "3) Rename category\n"
        "4) Delete category\n"
        "0) Back\n"
        "Choose an option: "
    )

    while True:
        choice = input(MENU).strip()

        if choice == "1":
            cats = _read_categories(categories_path)
            if not cats:
                print("No categories found.")
            else:
                rows = [{"name": c["name"], "type": c["type"]} for c in cats]
                print(tabulate(rows, headers="keys"))
        elif choice == "2":
            name = input("New category name: ").strip()
            typ = input("Type (income/expense): ").strip().lower()
            if not name:
                print("Name cannot be empty.")
                continue
            if typ not in {"income", "expense"}:
                print("Type must be 'income' or 'expense'.")
                continue
            all_rows = _read_categories(categories_path)
            if any(r["name"].lower() == name.lower() and r["type"] == typ for r in all_rows):
                print("Category already exists with that type.")
                continue
            all_rows.append({"name": name, "type": typ})
            _write_categories(categories_path, all_rows)
            print("✔ Category added.")
        elif choice == "3":
            cats = _read_categories(categories_path)
            if not cats:
                print("No categories to rename.")
                continue
            print("Select a category to rename:")
            for i, c in enumerate(cats, start=1):
                print(f"{i} - {c['name']} ({c['type']})")
            raw = input("Choice: ").strip()
            if not raw.isdigit() or not (1 <= int(raw) <= len(cats)):
                print("Invalid choice.")
                continue
            idx = int(raw) - 1
            old = cats[idx]
            new_name = input(f"New name for '{old['name']}' (blank = cancel): ").strip()
            if not new_name:
                print("Rename cancelled.")
                continue
            if any(r["name"].lower() == new_name.lower() and r["type"] == old["type"] for r in cats):
                print("A category with that name and type already exists.")
                continue
            if _category_in_use(csv_path, old["name"]):
                print("This category is used by existing transactions.")
                print("Renaming will change how those appear in reports.")
                confirm = input("Proceed? (y/n): ").strip().lower()
                if confirm != "y":
                    print("Rename cancelled.")
                    continue
            cats[idx]["name"] = new_name
            _write_categories(categories_path, cats)
            print("✔ Category renamed.")
        elif choice == "4":
            cats = _read_categories(categories_path)
            if not cats:
                print("No categories to delete.")
                continue
            print("Select a category to delete:")
            for i, c in enumerate(cats, start=1):
                print(f"{i} - {c['name']} ({c['type']})")
            raw = input("Choice: ").strip()
            if not raw.isdigit() or not (1 <= int(raw) <= len(cats)):
                print("Invalid choice.")
                continue
            idx = int(raw) - 1
            victim = cats[idx]
            if victim["name"].lower() == "other":
                print("Cannot delete the reserved 'Other' category.")
                continue
            if _category_in_use(csv_path, victim["name"]):
                print("This category is used by existing transactions and cannot be deleted.")
                print("Tip: rename it instead, or change those transactions first.")
                continue
            del cats[idx]
            _write_categories(categories_path, cats)
            print("✔ Category deleted.")
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose 0–4.")

#Manage Categories Nested MENU END


#Manage Transactions Nested MENU START

def _menu_manage_transactions(csv_path: str, categories_path: str) -> None:
    MENU = (
        "\n=== Manage Transactions ===\n"
        "1) View transactions\n"
        "2) Add transaction\n"
        "3) Edit transaction\n"
        "4) Delete transaction\n"
        "0) Back\n"
        "Choose an option: "
    )
    while True:
        choice = input(MENU).strip()
        if choice == "1":
            _render_transactions_table(csv_path)
        elif choice == "2":
            _enter_transaction_flow(csv_path, categories_path)
        elif choice == "3":
            _edit_transaction_flow(csv_path, categories_path)
        elif choice == "4":
            tx_id = input("Enter ID of the transcation to delete: ").strip()
            tx = get_transaction(csv_path, tx_id)
            if not tx:
                print("Transaction not found.")
                continue
            print("\nTransaction to delete:")
            print(tabulate([asdict(tx)], headers="keys", floatfmt=".2f"))
            confirmed = input("Are you sure you want to delete this transaction? (y/n): ").strip().lower()
            if confirmed == "y":
                success = delete_transaction(csv_path, tx_id)
                print("Transaction deleted." if success else "Transaction not found.")
            else:
                print("Deletion cancelled.")
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose 0–4.")

#Manage Transactions Nested MENU END

#Manage Report Nested MENU START

def _menu_reports(csv_path: str) -> None:
    MENU = (
        "\n=== Reports ===\n"
        "1) Totals (Income / Expenses / Net)\n"
        "2) Category summary (table)\n"
        "3) Income/Expenses/Net over time (line chart)\n"
        "4) Category summary (bar chart)\n"
        "0) Back\n"
        "Choose an option: "
    )
    while True:
        choice = input(MENU).strip()
        if choice == "1":
            _render_totals(csv_path)
        elif choice == "2":
            print_category_summary(csv_path)
        elif choice == "3":
            plot_financials(csv_path, freq="M")  # month end
        elif choice == "4":
            plot_category_summary(csv_path)
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose 0–4.")

#Manage Report Nested MENU END


# renders the menu in the CLI
# Added Top-level nested menu

def run_cli_menu(csv_path: str = "transactions.csv", categories_path: str = "categories.csv") -> None:
    _ensure_csv_exists(csv_path)
    _ensure_categories_csv_exists(categories_path)

    MENU = (
        "\n=== SHOW ME THE MONEY!!! ===\n"
        "1) Manage transactions\n"
        "2) Manage categories\n"
        "3) Reports\n"
        "0) Exit and Gig'em\n"
        "Choose an option: "
    )

    while True:
        choice = input(MENU).strip()
        if choice == "1":
            _menu_manage_transactions(csv_path, categories_path)
        elif choice == "2":
            _menu_manage_categories(categories_path, csv_path)
        elif choice == "3":
            _menu_reports(csv_path)
        elif choice == "0":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid option. Please choose 0–3.")

# MENU FLOW END



if __name__ == "__main__":
    try:
        monthlysavings()
    except NoDataError as e:
        print(e)
    except Exception as e:
        print("Error:", e)
    # call main
    main()
    pass

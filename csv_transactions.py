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
from dataclasses import dataclass, asdict
from datetime import datetime #used to check date is valid
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional, Tuple, Dict
from collections import defaultdict
from tabulate import tabulate

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
def main():
    run_cli_menu("transactions.csv")



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
            
                           
def category(t):
        categories = {
            "Expense": {
            "1": "Living Expenses",
            "2": "Food and Dining",
            "3": "Personal & Lifestyle",
            "4": "Healthcare & Insurance",
            "5": "Family & Education",
            "6": "Miscellaneous"},
            
            "Income": {
            "7": "Earned Income",
            "8": "Unearned Income"}
        }
        
        while True:
            print("Enter category by number:")
            for num, name in categories[t].items():
                print(f"{num} - {name}")
                
            typed = input().strip()
            
            if typed in categories[t]:
                print("Category selected: ", categories[t][typed])
                return categories[t][typed]
            else:
                print("Invalid input! Please enter a valid number.")
   
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
# updates a transaction with the values passed in where the transactionid
# equals the given transaction id
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
            new_dt  = datetime_str if datetime_str is not None else tx.datetime
            new_cat = category    if category    is not None else tx.category
            new_amt = amount_str  if amount_str  is not None else tx.amount
            new_desc=description if description is not None else tx.description
            new_type=type_str    if type_str    is not None else tx.type

            # Validate the merged data 
            # (datetime, category, amount, type, description).
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
def _enter_transaction_flow(csv_path: str) -> None:
    """Interactive entry for a single transaction."""
    while True:
        date_value = date()  
        typed_value = typed()          
        category_value = category(typed_value) 
        description_value = description()
        amount_value = amount()  

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
        again = input(
        "Do you want to enter another transaction? (yes/no): ").strip().lower()
        
        if again == "no":
            print("Thanks and Gig 'Em")
            break
            
        elif again == "yes":
            continue
        else:
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

def _edit_transaction_flow(csv_path: str) -> None:
    tx_id = input("Enter ID of the transaction to edit: ").strip()
    tx = get_transaction(csv_path, tx_id)
    if not tx:
        print("Transaction not found.")
        return

    # Fixed category menu
    CATEGORIES = [
        "Living Expenses",
        "Food and Dining",
        "Personal & Lifestyle",
        "Healthcare & Insurance",
        "Family & Education",
        "Miscellaneous",
        "Earned Income",
        "Unearned Income",
    ]

    print("\nLeave a field blank to keep current value.")

    print(f"Current datetime:   {tx.datetime}")
    new_dt = input("New datetime: ").strip() or None

    # Category selection by number only
    print(f"Current category:   {tx.category}")
    print("Enter category by number (blank = keep current):")
    for i, c in enumerate(CATEGORIES, start=1):
        print(f"{i} - {c}")
    while True:
        raw = input("Choice [1-8 or blank]: ").strip()
        if raw == "":
            new_cat = None  # keep current
            break
        if raw.isdigit() and 1 <= int(raw) <= len(CATEGORIES):
            new_cat = CATEGORIES[int(raw) - 1]
            break
        print("Invalid choice. Please enter 1-8 or press Enter to keep current.")

    print(f"Current type:       {tx.type}")
    new_type = input("New type (income/expense or i/e): ").strip().lower() or None
    if new_type is not None:
        if new_type in {"i", "inc", "+"}:
            new_type = "income"
        elif new_type in {"e", "exp", "-"}:
            new_type = "expense"

    print(f"Current amount:     {tx.amount}")
    new_amt = input("New amount: ").strip() or None

    print(f"Current description: {tx.description}")
    new_desc = input("New description: ").strip() or None

    try:
        updated = update_transaction(
            csv_path,
            tx_id,
            datetime_str=new_dt,
            category=new_cat,
            amount_str=new_amt,
            type_str=new_type,
            description=new_desc,
            allowed_categories=CATEGORIES,  # enforce same list during validation
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

# renders the menu in the CLI
def run_cli_menu(csv_path: str = "transactions.csv") -> None:
    """
    Interactive CLI menu to view transactions, enter a transaction,
    or view totals/category summary. Loops until user exits.
    """
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
        elif choice == "6": # Delete option
            tx_id = input("Enter ID of the transcation to delete: ").strip()
            tx = get_transaction(csv_path, tx_id)
            if not tx:
                print("Transaction not found.")
            print("\nTransaction to delete:")
            print(tabulate([asdict(tx)], headers="keys", floatfmt=".2f"))
            confirmed = input("Are you sure you want to delete this transaction? (y/n): ").strip().lower()
            if confirmed == "y":
                # Calls the delete function from above
                success = delete_transaction(csv_path, tx_id)
                if success == True:
                    print("Transaction deleted.")
                else:
                    print("Transaction not found.")
            else:
                print("Deletion cancelled.")
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

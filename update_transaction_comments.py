# UPDATE CSV BEGIN

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
    # Read the full list of transactions from the CSV
    all_txs = _read_all(csv_path)

    # Loop through transactions to find the one that matches the given ID
    for idx, tx in enumerate(all_txs):
        if tx.id == tx_id:
            # Use new values if provided, otherwise keep the old ones
            new_dt   = datetime_str if datetime_str is not None else tx.datetime
            new_cat  = category     if category     is not None else tx.category
            new_amt  = amount_str   if amount_str   is not None else tx.amount
            new_type = type_str     if type_str     is not None else tx.type
            new_desc = description  if description  is not None else tx.description

            # Validate and normalize the updated transaction
            ok, errs, normalized = validate_transaction(
                datetime_str=new_dt,
                category=new_cat,
                amount_str=new_amt,   # match validator’s parameter
                type_str=new_type,    # match validator’s parameter
                description=new_desc,
                allowed_categories=allowed_categories,
            )
            if not ok:
                # Stop if validation failed
                raise ValueError(f"Validation errors: {errs}")

            # Construct a new Transaction object with normalized values
            updated = Transaction(
                id=tx.id,
                datetime=normalized["datetime"],
                category=normalized["category"],
                amount=normalized["amount"],
                type=normalized["type"],
                description=normalized["description"],
            )
            # Replace the old transaction in the list and save everything back to CSV
            all_txs[idx] = updated
            _write_all(csv_path, all_txs)
            return updated

    # If the ID was not found, raise an error
    raise KeyError(f"Transaction with id '{tx_id}' not found.")


def _edit_transaction_flow(csv_path: str) -> None:
    """
    Interactive CLI flow for editing an existing transaction.
    Prompts the user for new values and leaves fields unchanged if left blank.
    """
    tx_id = input("Enter the ID of the transaction to edit: ").strip()
    tx = get_transaction(csv_path, tx_id)
    if not tx:
        print("Transaction not found.")
        return

    # Show current values and prompt for updates
    print("\nLeave a field blank to keep the current value.")
    print(f"Current datetime: {tx.datetime}")
    new_dt = input("New datetime (e.g., 2025-09-02T14:30:00): ").strip()

    print(f"Current category: {tx.category}")
    new_cat = input("New category: ").strip()

    print(f"Current amount: {tx.amount}")
    new_amt = input("New amount (e.g., 12.34 or -45.00): ").strip()

    print(f"Current type: {tx.type}")
    new_type = input("New type (income/expense): ").strip().lower()

    print(f"Current description: {tx.description}")
    new_desc = input("New description: ").strip()

    # Helper: treat blank input as None so update_transaction keeps the old value
    def blank_to_none(s: str) -> Optional[str]:
        return s if s else None

    try:
        # Apply updates and persist changes
        updated = update_transaction(
            csv_path,
            tx_id,
            datetime_str=blank_to_none(new_dt),
            category=blank_to_none(new_cat),
            amount_str=blank_to_none(new_amt),
            type_str=blank_to_none(new_type),
            description=blank_to_none(new_desc),
        )
        # Display the updated transaction in a table
        print("✔ Updated:")
        print(tabulate([asdict(updated)], headers="keys"))
    except (KeyError, ValueError) as e:
        # Show user-friendly error message
        print(f"✖ {e}")


# UPDATE CSV END

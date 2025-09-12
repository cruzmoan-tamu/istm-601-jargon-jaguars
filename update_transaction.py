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
                amount_str=new_amt,
                description=new_desc,
                type_str=new_type,
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


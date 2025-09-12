import pandas as pd

def CalculateTotals():
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


# Run the function
CalculateTotals()

from turtle import title
import pandas as pd
import matplotlib.pyplot as plt
import calendar

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

# Run function safely
if __name__ == "__main__":
    try:
        monthlysavings()
    except NoDataError as e:
        print(e)
    except Exception as e:
        print("Error:", e)

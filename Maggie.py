from datetime import datetime
import re

def main():
    
    def date():
        pattern = r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])-\d{2}$"
        
        while True:
            date = input("Enter transaction date (mm-dd-yy): ")
            
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
                
    while True:
        date_value = date()  
        description_value = description()
        category_value = category() 
        amount_value = amount()
        typed_value = typed()  
        
        # remove extra spaces and convert word to lower case
        again = input("Do you want to enter another transaction? (yes/no): ").strip().lower()
        
        if again == "no":
            print("Thanks and Gig 'Em")
            break
            
        elif again == "yes":
            continue
        else:
            print("Invalid input. Please enter yes or no.")
    

if __name__ == "__main__":
    main()
    
    
    
    
    
    
    

    

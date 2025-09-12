from datetime import datetime #used to check date is valid
import re #checks date matches the yyyy-mm-dd pattern

def main():
    
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
            
            
    def amount():
         while True:
             amount = input("Enter transaction amount: ") #gets the amount from user
             
             try:
                 value = float(amount) #converts to float
                 if value < 0: #amount cannot be negative
                     print("Amount cannot be negative.")
                     continue
                 print("Amount entered:", f"{value:.2f}") #adds 2 decimal points for whole numbers and confirms amount
                 return value 
             except ValueError:
                 print("Invalid input. Please enter numbers only.") #Invalid input
                 
    def category():
        #categories dictionary
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
        #user chooses category
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
                print("Category selected: ", categories[category]) #confirm category selected
                return categories[category]
            else:
                print("Invalid input! Please enter a number 1 to 8.")    #user did not enter number between 1-8
    
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
    
    
    
    
    
    
    

    



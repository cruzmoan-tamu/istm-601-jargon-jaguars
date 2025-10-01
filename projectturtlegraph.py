import turtle
import random

# Function to draw a single bar
def draw_bar(t, height, label, color):
    t.fillcolor(color)
    t.begin_fill()
    t.left(90)
    t.forward(height)   # Draw bar up
    t.write(f" ${height:.2f}", font=("Arial", 10, "normal"))  # Label amount on top
    t.right(90)
    t.forward(40)       # Bar width
    t.right(90)
    t.forward(height)   # Back down
    t.left(90)
    t.end_fill()

    # Write category label under the bar
    t.forward(10)
    t.write(label, align="center", font=("Arial", 10, "bold"))
    t.back(10)

# Main program
def main():
    # Collect user data
    categories = []
    expenses = []

    # Time frame input
    start_date = input("Enter start date (MM-DD-YYYY): ")
    end_date = input("Enter end date (MM-DD-YYYY): ")

    n = int(input("How many expense categories do you want to enter? "))

    for i in range(n):
        cat = input(f"Enter category {i+1} name: ")
        amt = float(input(f"Enter expense amount for {cat}: "))
        categories.append(cat)
        expenses.append(amt)

    # Setup turtle screen
    wn = turtle.Screen()
    wn.title("Expense Bar Graph")
    wn.bgcolor("white")

    t = turtle.Turtle()
    t.speed(0)
    t.penup()
    t.goto(-200, -200)  # Starting position
    t.pendown()

    # Scale values so graph fits screen
    max_height = max(expenses)
    scale_factor = 200 / max_height if max_height != 0 else 1

    # Draw title with time frame
    title_turtle = turtle.Turtle()
    title_turtle.hideturtle()
    title_turtle.penup()
    title_turtle.goto(0, 220)
    title_turtle.write(
        f"Expenses from {start_date} to {end_date}",
        align="center",
        font=("Arial", 16, "bold")
    )

    # Draw bars
    for i in range(n):
        height = expenses[i] * scale_factor
        color = (random.random(), random.random(), random.random())  # random color
        draw_bar(t, height, categories[i], color)
        t.forward(50)  # spacing between bars

    wn.mainloop()

if __name__ == "__main__":
    main()
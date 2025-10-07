# ...existing code...
-import calendar
-from turtle import title
+import calendar
+import turtle as t
# ...existing code...

# ...existing code...
def plot_category_summary(csv_file):
    # ...existing code ...
    return category_summary

# New: Turtle-based category totals bar chart with per-bar colors
def turtle_category_bars(csv_file: str) -> None:
    """
    Draw a bar chart of category totals (net) using turtle graphics.
    Each category bar uses a different color from a fixed palette.
    """
    totals = get_category_totals(csv_file)
    if not totals:
        print("No category data found.")
        return

    # Sort categories by absolute net value descending for visual balance
    items = sorted(totals.items(), key=lambda kv: abs(kv[1]["net"]), reverse=True)
    values = [v["net"] for _, v in items]
    max_abs = max(abs(v) for v in values) if values else 0.0
    if max_abs == 0:
        print("All category totals are zero; nothing to plot.")
        return

    # Layout
    BAR_W = 50
    SPACING = 20
    MARGIN = 60
    MAX_BAR_HEIGHT = 300  # pixels for the largest absolute value

    n = len(items)
    canvas_width = MARGIN * 2 + n * (BAR_W + SPACING)
    canvas_height = MARGIN * 2 + MAX_BAR_HEIGHT * 2

    screen = t.Screen()
    screen.setup(width=min(1200, int(canvas_width)), height=min(800, int(canvas_height)))
    screen.title("Category Totals (Turtle Bar Chart)")

    pen = t.Turtle()
    pen.hideturtle()
    pen.speed(0)
    pen.penup()

    baseline_y = -MAX_BAR_HEIGHT / 2
    start_x = -canvas_width / 2 + MARGIN

    # Draw baseline
    pen.goto(start_x - 10, baseline_y)
    pen.pendown()
    pen.pensize(2)
    pen.forward(n * (BAR_W + SPACING) + 20)
    pen.penup()
    pen.pensize(1)

    # Palette: distinct colors per bar (will cycle if more categories)
    palette = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
        "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ac"
    ]

    x = start_x
    for i, (name, vals) in enumerate(items):
        net = float(vals["net"])
        # Scale to pixels
        height_px = (net / max_abs) * MAX_BAR_HEIGHT

        # Choose color from palette
        color = palette[i % len(palette)]

        # Draw bar (rectangle) from baseline up or down
        pen.goto(x, baseline_y)
        pen.setheading(90)
        pen.fillcolor(color)
        pen.pendown()
        pen.begin_fill()
        if net >= 0:
            pen.forward(abs(height_px))
            pen.right(90)
            pen.forward(BAR_W)
            pen.right(90)
            pen.forward(abs(height_px))
            pen.right(90)
            pen.forward(BAR_W)
        else:
            # draw downward
            pen.backward(abs(height_px))
            pen.left(90)
            pen.forward(BAR_W)
            pen.left(90)
            pen.forward(abs(height_px))
            pen.left(90)
            pen.forward(BAR_W)
        pen.end_fill()
        pen.penup()

        # Category label
        pen.goto(x + BAR_W / 2, baseline_y - 14)
        pen.setheading(0)
        pen.write(name, align="center", font=("Arial", 8, "normal"))

        # Value label (above/below bar)
        if net >= 0:
            value_y = baseline_y + height_px + 6
        else:
            value_y = baseline_y - height_px - 20
        pen.goto(x + BAR_W / 2, value_y)
        pen.write(f"{net:.2f}", align="center", font=("Arial", 8, "normal"))

        x += BAR_W + SPACING

    # Wait for user to close (click)
    screen.exitonclick()
# ...existing code...

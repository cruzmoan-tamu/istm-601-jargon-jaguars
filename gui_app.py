# gui_app.py
# Tkinter GUI for "Show Me The Money" — uses the existing CSV/CRUD/validation logic.
# Run with: python gui_app.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
from decimal import Decimal



# Matplotlib embedding
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from typing import Optional

# === IMPORT YOUR BACKEND ===
# If your file is named differently, change this import to match.
from csv_transactions import (
    # data structures
    Transaction,

    # csv + categories utilities
    _ensure_csv_exists,
    _ensure_categories_csv_exists,
    _read_categories,
    _write_categories,
    _all_category_names,
    _list_categories_by_type,
    _category_in_use,

    # core CRUD + validation
    _parse_and_normalize_datetime,
    create_transaction,
    read_transactions,
    get_transaction,
    delete_transaction,
    update_transaction,

    # reports
    get_totals,
    get_category_totals,
)

DEFAULT_TX_CSV = "transactions.csv"
DEFAULT_CAT_CSV = "categories.csv"


class App(tk.Tk):
    def __init__(self, csv_path=DEFAULT_TX_CSV, categories_path=DEFAULT_CAT_CSV):
        super().__init__()
        self.title("Show Me The Money — Financial Tracker")
        self.geometry("1100x720")

        self.csv_path = csv_path
        self.categories_path = categories_path

        _ensure_csv_exists(self.csv_path)
        _ensure_categories_csv_exists(self.categories_path)

        self._build_ui()

    # ---------- helpers ----------
    def toast(self, msg: str):
        messagebox.showinfo("Info", msg, parent=self)

    def warn(self, msg: str):
        messagebox.showwarning("Warning", msg, parent=self)

    def errbox(self, msg: str):
        messagebox.showerror("Error", msg, parent=self)

    def confirm(self, msg: str) -> bool:
        return messagebox.askyesno("Confirm", msg, parent=self)

    def prompt_date(self, initial: str = "") -> Optional[str]:
        while True:
            val = simpledialog.askstring(
                "Date",
                "Enter date (YYYY-MM-DD):",
                initialvalue=initial,
                parent=self,
            )
            if val is None:
                return None
            norm, e = _parse_and_normalize_datetime(val.strip())
            if e:
                self.errbox(e)
            else:
                return norm[:10]

    # # ----- Report Helpers ---
    # def _run_cli_totals(self):
    #     # prints to console
    #     totals = get_totals(self.csv_path)
    #     self.toast(f"Income: {totals['income']:.2f}\nExpenses: {totals['expenses']:.2f}\nNet: {totals['net']:.2f}")

    # def _run_cli_cat_tbl(self):
    #     # uses your existing pretty-printer if you prefer, or just reuse get_category_totals
    #     data = get_category_totals(self.csv_path)
    #     self.toast(f"Categories: {len(data)} (see console)")
    #     # optionally print to console:
    #     for k, v in data.items():
    #         print(k, v)

    # def _run_cli_line(self):
    #     from csv_transactions import plot_financials
    #     plot_financials(self.csv_path, freq="M", start_date=None, end_date=None)

    # def _run_cli_bar(self):
    #     from csv_transactions import plot_category_summary
    #     plot_category_summary(self.csv_path)

    # def _run_cli_pie(self):
    #     from csv_transactions import monthlysavings
    #     monthlysavings(self.csv_path)


    # ---------- UI ----------
    def _build_ui(self):
        # menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Transactions CSV…", command=self.open_csv)
        filemenu.add_command(label="Export CSV Copy…", command=self.export_csv_copy)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=lambda: self.toast("Show Me The Money — Tkinter GUI\nGig 'Em!"))
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.config(menu=menubar)

        # # add reports to menu
        # reportmenu = tk.Menu(menubar, tearoff=0)
        # reportmenu.add_command(label="CLI Totals (print)", command=lambda: self._run_cli_totals())
        # reportmenu.add_command(label="CLI Category Summary (print)", command=lambda: self._run_cli_cat_tbl())
        # reportmenu.add_command(label="CLI Line Chart (prompts)", command=lambda: self._run_cli_line())
        # reportmenu.add_command(label="CLI Category Bar", command=lambda: self._run_cli_bar())
        # reportmenu.add_command(label="CLI Monthly Pie (prompts YYYY-MM)", command=lambda: self._run_cli_pie())
        # menubar.add_cascade(label="Run CLI Reports", menu=reportmenu)

        # tabs
        self.nb = ttk.Notebook(self)
        self.tab_tx = ttk.Frame(self.nb)
        self.tab_cat = ttk.Frame(self.nb)
        self.tab_rep = ttk.Frame(self.nb)
        self.nb.add(self.tab_tx, text="Transactions")
        self.nb.add(self.tab_cat, text="Categories")
        self.nb.add(self.tab_rep, text="Reports")
        self.nb.pack(fill="both", expand=True)

        self._build_transactions_tab()
        self._build_categories_tab()
        self._build_reports_tab()

    # ===== Transactions tab =====
    def _build_transactions_tab(self):
        top = ttk.Frame(self.tab_tx)
        top.pack(fill="x", padx=10, pady=6)

        ttk.Label(top, text="Type:").pack(side="left")
        self.tx_filter_type = ttk.Combobox(top, width=10, state="readonly", values=["All", "income", "expense"])
        self.tx_filter_type.current(0)
        self.tx_filter_type.pack(side="left", padx=(4, 12))

        ttk.Label(top, text="Category:").pack(side="left")
        self.tx_filter_cat = ttk.Combobox(top, width=24, state="readonly", values=["All"])
        self.tx_filter_cat.current(0)
        self.tx_filter_cat.pack(side="left", padx=(4, 12))

        ttk.Button(top, text="Open CSV…", command=self.open_csv).pack(side="left")

        self.tx_tree = ttk.Treeview(
            self.tab_tx,
            columns=("id", "datetime", "type", "category", "amount", "description"),
            show="headings",
            selectmode="browse",
        )
        for c, w in [("id", 260), ("datetime", 140), ("type", 90), ("category", 180), ("amount", 100), ("description", 360)]:
            self.tx_tree.heading(c, text=c.capitalize())
            self.tx_tree.column(c, width=w, anchor="w")
        self.tx_tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tx_tree.bind("<<TreeviewSelect>>", self._tx_populate_form_from_selection)

        form = ttk.LabelFrame(self.tab_tx, text="Add / Edit Transaction")
        form.pack(fill="x", padx=10, pady=8)

        def labeled(parent, label, width=22):
            f = ttk.Frame(parent)
            ttk.Label(f, text=label, width=16, anchor="e").pack(side="left")
            e = ttk.Entry(f, width=width)
            e.pack(side="left", padx=6)
            f.pack(side="left", padx=8, pady=6)
            return e

        self.e_date = labeled(form, "Date (yyyy-mm-dd):")
        self.e_type = ttk.Combobox(form, width=20, state="readonly", values=["income", "expense"])
        self.e_type.set("income")
        self.e_type.pack(side="left", padx=6)

        cat_frame = ttk.Frame(form)
        ttk.Label(cat_frame, text="Category:", width=16, anchor="e").pack(side="left")
        self.e_cat = ttk.Combobox(cat_frame, width=24, state="readonly",
                                  values=_list_categories_by_type(self.categories_path, "income"))
        self.e_cat.pack(side="left", padx=6)
        cat_frame.pack(side="left", padx=8, pady=6)

        self.e_amount = labeled(form, "Amount:")
        self.e_desc = labeled(form, "Description:", width=38)

        self.selected_tx_id = None

        self.e_type.bind("<<ComboboxSelected>>", lambda e: self._sync_cats_to_type())

        btns = ttk.Frame(self.tab_tx)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Save (Add/Update)", command=self._tx_add_or_update).pack(side="left")
        ttk.Button(btns, text="Delete Selected", command=self._tx_delete_selected).pack(side="left", padx=8)
        ttk.Button(btns, text="Clear Form", command=self._tx_clear_form).pack(side="left", padx=8)
        ttk.Button(btns, text="Refresh", command=self.refresh_tx_table).pack(side="left", padx=8)

        ttk.Separator(self.tab_tx, orient="horizontal").pack(fill="x", padx=10, pady=6)

        self.tx_filter_type.bind("<<ComboboxSelected>>", lambda e: self.refresh_tx_table())
        self.tx_filter_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh_tx_table())

        self._tx_clear_form()
        self._refresh_category_filter()
        self.refresh_tx_table()

    def _tx_clear_form(self):
        self.selected_tx_id = None
        self.e_date.delete(0, tk.END)
        self.e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.e_type.set("income")
        self._sync_cats_to_type()
        self.e_amount.delete(0, tk.END)
        self.e_desc.delete(0, tk.END)

    def _sync_cats_to_type(self):
        typ = self.e_type.get().strip().lower()
        cats = _list_categories_by_type(self.categories_path, typ if typ in ("income", "expense") else "income")
        self.e_cat.configure(values=cats)
        if cats and self.e_cat.get() not in cats:
            self.e_cat.set(cats[0])

    def _refresh_category_filter(self):
        names = ["All"] + _all_category_names(self.categories_path)
        self.tx_filter_cat.configure(values=names)
        if self.tx_filter_cat.get() not in names:
            self.tx_filter_cat.current(0)

    def _tx_populate_form_from_selection(self, _evt=None):
        sel = self.tx_tree.selection()
        if not sel:
            return
        item = self.tx_tree.item(sel[0])["values"]
        self.selected_tx_id = item[0]
        self.e_date.delete(0, tk.END); self.e_date.insert(0, item[1][:10])
        self.e_type.set(item[2]); self._sync_cats_to_type()
        self.e_cat.set(item[3])
        self.e_amount.delete(0, tk.END); self.e_amount.insert(0, str(item[4]))
        self.e_desc.delete(0, tk.END); self.e_desc.insert(0, item[5])

    def _tx_add_or_update(self):
        dt = self.e_date.get().strip()
        typ = self.e_type.get().strip().lower()
        cat = self.e_cat.get().strip()
        amt = self.e_amount.get().strip()
        desc = self.e_desc.get().strip()

        allowed = _all_category_names(self.categories_path)
        try:
            if self.selected_tx_id is None:
                create_transaction(
                    self.csv_path,
                    datetime_str=dt,
                    category=cat,
                    amount_str=amt,
                    type=typ,
                    description=desc,
                    allowed_categories=allowed,
                )
                self.toast("Transaction added.")
            else:
                update_transaction(
                    self.csv_path,
                    self.selected_tx_id,
                    datetime_str=dt,
                    category=cat,
                    amount_str=amt,
                    type_str=typ,
                    description=desc,
                    allowed_categories=allowed,
                )
                self.toast("Transaction updated.")
            self.refresh_tx_table()
            self._tx_clear_form()
        except ValueError as ex:
            self.errbox(str(ex))
        except Exception as ex:
            self.errbox(f"Unexpected error: {ex}")

    def _tx_delete_selected(self):
        sel = self.tx_tree.selection()
        if not sel:
            self.warn("Select a transaction first.")
            return
        tx_id = self.tx_tree.item(sel[0])["values"][0]
        if self.confirm("Delete the selected transaction? This cannot be undone."):
            ok = delete_transaction(self.csv_path, tx_id)
            if ok:
                self.refresh_tx_table()
                self._tx_clear_form()
                self.toast("Deleted.")
            else:
                self.warn("Transaction not found (already deleted).")

    def refresh_tx_table(self):
        # clear
        for r in self.tx_tree.get_children():
            self.tx_tree.delete(r)
        # filters
        f_type = self.tx_filter_type.get()
        f_cat = self.tx_filter_cat.get()

        for t in read_transactions(self.csv_path):
            if f_type != "All" and t.type != f_type:
                continue
            if f_cat != "All" and t.category != f_cat:
                continue
            try:
                amt = f"{Decimal(t.amount):.2f}"
            except Exception:
                amt = t.amount
            self.tx_tree.insert("", "end", values=(t.id, t.datetime, t.type, t.category, amt, t.description))

    # ===== Categories tab =====
    def _build_categories_tab(self):
        top = ttk.Frame(self.tab_cat)
        top.pack(fill="x", padx=10, pady=6)

        self.cat_type_filter = ttk.Combobox(top, width=12, state="readonly", values=["income", "expense", "All"])
        self.cat_type_filter.current(2)
        self.cat_type_filter.pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_categories).pack(side="left", padx=8)

        self.cat_tree = ttk.Treeview(self.tab_cat, columns=("name", "type"), show="headings", selectmode="browse")
        self.cat_tree.heading("name", text="Name"); self.cat_tree.column("name", width=320, anchor="w")
        self.cat_tree.heading("type", text="Type"); self.cat_tree.column("type", width=120, anchor="w")
        self.cat_tree.pack(fill="both", expand=True, padx=10, pady=6)

        bar = ttk.Frame(self.tab_cat)
        bar.pack(fill="x", padx=10, pady=8)
        ttk.Button(bar, text="Add", command=self.add_category).pack(side="left")
        ttk.Button(bar, text="Rename", command=self.rename_category).pack(side="left", padx=8)
        ttk.Button(bar, text="Delete", command=self.delete_category).pack(side="left", padx=8)

        self.refresh_categories()

    def refresh_categories(self):
        for r in self.cat_tree.get_children():
            self.cat_tree.delete(r)
        rows = _read_categories(self.categories_path)
        ft = self.cat_type_filter.get()
        for r in rows:
            if ft != "All" and r["type"] != ft:
                continue
            self.cat_tree.insert("", "end", values=(r["name"], r["type"]))
        self._refresh_category_filter()
        self._sync_cats_to_type()

    def add_category(self):
        name = simpledialog.askstring("New Category", "Category name:", parent=self)
        if not name:
            return
        typ = simpledialog.askstring("Category Type", "Type (income/expense):", parent=self)
        if not typ:
            return
        typ = typ.strip().lower()
        if typ not in {"income", "expense"}:
            self.errbox("Type must be 'income' or 'expense'.")
            return
        rows = _read_categories(self.categories_path)
        if any(r["name"].lower() == name.strip().lower() and r["type"] == typ for r in rows):
            self.errbox("That category already exists for that type.")
            return
        rows.append({"name": name.strip(), "type": typ})
        _write_categories(self.categories_path, rows)
        self.toast("Category added.")
        self.refresh_categories()

    def rename_category(self):
        sel = self.cat_tree.selection()
        if not sel:
            self.warn("Select a category first.")
            return
        name, typ = self.cat_tree.item(sel[0])["values"]
        new_name = simpledialog.askstring(
            "Rename Category", f"New name for '{name}' ({typ}):", parent=self, initialvalue=name
        )
        if not new_name or new_name.strip() == name:
            return
        rows = _read_categories(self.categories_path)
        if any(r["name"].lower() == new_name.strip().lower() and r["type"] == typ for r in rows):
            self.errbox("A category with that name and type already exists.")
            return
        if _category_in_use(self.csv_path, name):
            if not self.confirm("This category is used by existing transactions. Rename anyway?"):
                return
        for r in rows:
            if r["name"] == name and r["type"] == typ:
                r["name"] = new_name.strip()
                break
        _write_categories(self.categories_path, rows)
        self.toast("Category renamed.")
        self.refresh_categories()
        self.refresh_tx_table()

    def delete_category(self):
        sel = self.cat_tree.selection()
        if not sel:
            self.warn("Select a category first.")
            return
        name, typ = self.cat_tree.item(sel[0])["values"]
        if name.lower() == "other":
            self.warn("You cannot delete the reserved 'Other' category.")
            return
        if _category_in_use(self.csv_path, name):
            self.warn("Category is used by existing transactions. Change those first or rename instead.")
            return
        if self.confirm(f"Delete category '{name}' ({typ})?"):
            rows = [r for r in _read_categories(self.categories_path) if not (r["name"] == name and r["type"] == typ)]
            _write_categories(self.categories_path, rows)
            self.toast("Deleted.")
            self.refresh_categories()

    # ===== Reports tab =====
    def _build_reports_tab(self):
        top = ttk.Frame(self.tab_rep)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Show Totals (Table)", command=self.show_totals_table).pack(side="left")
        ttk.Button(top, text="Category Summary (Table)", command=self.show_category_table).pack(side="left", padx=8)
        ttk.Button(top, text="Line Chart (Income/Expense/Net)", command=self.draw_line_chart).pack(side="left", padx=8)
        ttk.Button(top, text="Bar Chart (Categories)", command=self.draw_category_bar).pack(side="left", padx=8)
        ttk.Button(top, text="Monthly Pie (Savings)", command=self.draw_monthly_pie).pack(side="left", padx=8)

        self.rep_body = ttk.Frame(self.tab_rep)
        self.rep_body.pack(fill="both", expand=True, padx=10, pady=6)

    def _rep_clear(self):
        for w in self.rep_body.winfo_children():
            w.destroy()

    def _rep_table(self, rows: list[dict]):
        self._rep_clear()
        if not rows:
            ttk.Label(self.rep_body, text="No data.").pack()
            return
        columns = list(rows[0].keys())
        tv = ttk.Treeview(self.rep_body, columns=columns, show="headings")
        for c in columns:
            tv.heading(c, text=c.capitalize())
            tv.column(c, width=max(100, int(900 / len(columns))), anchor="w")
        tv.pack(fill="both", expand=True)
        for r in rows:
            tv.insert("", "end", values=[r[c] for c in columns])

    def _embed_fig(self, fig: Figure):
        self._rep_clear()
        canvas = FigureCanvasTkAgg(fig, master=self.rep_body)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_totals_table(self):
        totals = get_totals(self.csv_path)
        self._rep_table([{
            "income": f"{totals['income']:.2f}",
            "expenses": f"{totals['expenses']:.2f}",
            "net": f"{totals['net']:.2f}",
        }])

    def show_category_table(self):
        data = get_category_totals(self.csv_path)
        rows = []
        for cat, vals in sorted(data.items(), key=lambda kv: kv[0].lower()):
            rows.append({
                "category": cat,
                "income": f"{vals['income']:.2f}",
                "expenses": f"{vals['expenses']:.2f}",
                "net": f"{vals['net']:.2f}",
            })
        self._rep_table(rows)

    def draw_line_chart(self):
        import pandas as pd
        df = pd.read_csv(self.csv_path, parse_dates=["datetime"])
        if df.empty:
            self.warn("No data to plot.")
            return
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        summary = df.groupby([pd.Grouper(key="datetime", freq="M"), "type"])["amount"].sum().unstack(fill_value=0)
        for col in ("income", "expense"):
            if col not in summary.columns:
                summary[col] = 0
        summary["net"] = summary["income"] + summary["expense"]

        fig = Figure(figsize=(8.8, 5.2))
        ax = fig.add_subplot(111)
        ax.plot(summary.index, summary["income"], marker="o", label="Income")
        ax.plot(summary.index, summary["expense"], marker="o", label="Expense")
        ax.plot(summary.index, summary["net"], marker="o", label="Net")
        ax.set_title("Financial Report (Monthly)")
        ax.set_xlabel("Date"); ax.set_ylabel("Amount ($)")
        ax.grid(True); ax.legend()
        fig.tight_layout()
        self._embed_fig(fig)

    def draw_category_bar(self):
        import pandas as pd
        df = pd.read_csv(self.csv_path, parse_dates=["datetime"])
        if df.empty:
            self.warn("No data to plot.")
            return
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["amount_display"] = df.apply(
            lambda r: -r["amount"] if str(r["type"]).strip().lower() == "expense" else r["amount"],
            axis=1
        )
        series = df.groupby("category")["amount_display"].sum().sort_values(ascending=False)
        if series.empty:
            self.warn("No data to plot.")
            return
        fig = Figure(figsize=(8.8, 5.2))
        ax = fig.add_subplot(111)
        ax.bar(series.index.astype(str), series.values)
        ax.set_title("Total Income & Expenses by Category")
        ax.set_ylabel("Amount ($)")
        ax.set_xticklabels(series.index.astype(str), rotation=45, ha="right")
        fig.tight_layout()
        self._embed_fig(fig)

    def draw_monthly_pie(self):
        ym = simpledialog.askstring("Month", "Enter year and month (YYYY-MM):", parent=self)
        if not ym:
            return
        import pandas as pd, calendar as _cal
        try:
            year, month = map(int, ym.split("-"))
        except Exception:
            self.errbox("Invalid format. Use YYYY-MM.")
            return
        df = pd.read_csv(self.csv_path, parse_dates=["datetime"])
        if df.empty:
            self.warn("No data.")
            return
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["type"] = df["type"].astype(str).str.strip().str.lower()

        dfm = df[(df["datetime"].dt.year == year) & (df["datetime"].dt.month == month)]
        if dfm.empty:
            self.warn("No data for that month.")
            return
        income = dfm[dfm["type"] == "income"]["amount"].sum()
        expense = dfm[dfm["type"] == "expense"]["amount"].sum()
        savings = income + expense
        if savings <= 0:
            self.warn("No positive savings for that month.")
            return

        fig = Figure(figsize=(6, 6))
        ax = fig.add_subplot(111)
        values = [abs(expense), max(savings, 0)]
        labels = ["Expenses", "Savings"]
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(f"Monthly Income & Savings for {_cal.month_name[month]} {year}\n(Total Savings: ${savings:,.2f})")
        self._embed_fig(fig)

    # ===== file actions =====
    def open_csv(self):
        path = filedialog.askopenfilename(
            title="Open transactions CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self,
        )
        if path:
            self.csv_path = path
            _ensure_csv_exists(self.csv_path)
            self._refresh_category_filter()
            self.refresh_tx_table()

    def export_csv_copy(self):
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save a copy of transactions.csv",
            parent=self,
        )
        if not dest:
            return
        try:
            with open(self.csv_path, "r", encoding="utf-8") as src, open(dest, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            self.toast("Exported.")
        except Exception as ex:
            self.errbox(f"Export failed: {ex}")


if __name__ == "__main__":
    app = App()
    app.mainloop()

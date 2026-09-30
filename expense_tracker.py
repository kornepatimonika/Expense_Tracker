"""
🌈 Expense Tracker  (Streamlit + JSON storage)
----------------------------------------------------
Run it from Command Prompt (NOT from IDLE):

    python -m streamlit run expense_tracker.py

Features
  - Personal title  ->  "<Name>'s Expense Tracker"  + greeting
  - Colorful rainbow design with Light and Dark mode
  - CRUD: Create, Read, Update, Delete expenses
  - Data saved in local JSON files (no database)
  - Input validation (amount, description, date)
  - Monthly budget with a colorful progress bar
  - Search, filter, sort and download (CSV)
  - Daily table + 7 interactive colorful charts
  - Sample data button for quick demos
"""

import json
import os
import uuid
from datetime import date, datetime, timedelta
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# 0. SAFETY CHECK  (this app must be started with "streamlit run")
# ------------------------------------------------------------------
# If you press F5 in IDLE, Streamlit shows hundreds of warnings.
# This check stops the script early and explains what to do instead.
from streamlit.runtime.scriptrunner import get_script_run_ctx

try:
    _ctx = get_script_run_ctx(suppress_warning=True)
except TypeError:  # older Streamlit versions do not have suppress_warning
    _ctx = get_script_run_ctx()

if _ctx is None:
    print("=" * 60)
    print("This is a Streamlit web app, so it cannot run from IDLE (F5).")
    print("Open Command Prompt and run these two lines:")
    print()
    print("    cd " + os.path.dirname(os.path.abspath(__file__)))
    print("    python -m streamlit run " + os.path.basename(__file__))
    print("=" * 60)
    raise SystemExit

# ------------------------------------------------------------------
# 1. BASIC SETTINGS
# ------------------------------------------------------------------
st.set_page_config(page_title="Expense Tracker", page_icon="💸", layout="wide")

DATA_FILE = "expenses.json"      # all expenses are stored here
SETTINGS_FILE = "settings.json"  # name, mode, budget, currency are stored here
MAX_AMOUNT = 10_000_000          # biggest amount we accept
CURRENCIES = ["₹", "$", "€", "£"]
CURRENCY = "₹"                   # changed later from the sidebar

# Every category has its own color (used in tables and charts)
CATEGORY_COLORS = {
    "🍔 Food": "#FF6B6B",
    "🚌 Transport": "#FFA94D",
    "🛍️ Shopping": "#F783AC",
    "🏠 Rent": "#845EF7",
    "💡 Bills": "#F59F00",
    "🎬 Entertainment": "#CC5DE8",
    "🏥 Health": "#20C997",
    "📚 Education": "#339AF0",
    "📦 Other": "#868E96",
}
CATEGORIES = list(CATEGORY_COLORS.keys())

PAYMENT_COLORS = {
    "💵 Cash": "#40C057",
    "📱 UPI": "#4C6EF5",
    "💳 Card": "#E64980",
    "🏦 Net Banking": "#15AABF",
}
PAYMENTS = list(PAYMENT_COLORS.keys())

# Colors used for charts that do not depend on a category
RAINBOW = ["#FF6B6B", "#FFA94D", "#FAB005", "#51CF66", "#20C997", "#339AF0", "#845EF7", "#F783AC"]

# The calendar box shows dates like 01/10/2026  (Day/Month/Year)
DATE_FORMAT = "DD/MM/YYYY"


def money(amount):
    """12345.5  ->  ₹12,345.50"""
    return f"{CURRENCY}{amount:,.2f}"


def nice_date(d):
    """Short, easy date  ->  Thu, 01 Oct 2026"""
    return d.strftime("%a, %d %b %Y")


def long_date(d):
    """Full date  ->  Thursday, 01 October 2026"""
    return d.strftime("%A, %d %B %Y")


# ------------------------------------------------------------------
# 2. JSON HELPER FUNCTIONS (our tiny "database")
# ------------------------------------------------------------------
def load_json(path, default):
    """Read a JSON file. If it does not exist or is broken, return default."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path, data):
    """Write data into a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_expenses():
    return load_json(DATA_FILE, [])


def save_expenses(expenses):
    save_json(DATA_FILE, expenses)


def make_theme_file():
    """Creates .streamlit/config.toml once, so default widget colors are purple (not red)."""
    path = os.path.join(".streamlit", "config.toml")
    if not os.path.exists(path):
        try:
            os.makedirs(".streamlit", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write('[theme]\nprimaryColor = "#7C4DFF"\n')
        except OSError:
            pass


def make_sample_data():
    """A few example expenses so you can try charts quickly."""
    today = date.today()
    # (days ago, category number, amount, payment number, description)
    rows = [
        (0, 0, 180, 0, "Lunch at canteen"),
        (0, 1, 60, 1, "Bus pass top-up"),
        (1, 7, 450, 1, "Python book"),
        (2, 2, 1299, 2, "New headphones"),
        (2, 0, 220, 1, "Dinner with friends"),
        (3, 4, 699, 3, "Mobile recharge"),
        (5, 5, 350, 1, "Movie tickets"),
        (6, 6, 250, 0, "Medicines"),
        (8, 0, 150, 0, "Snacks"),
        (10, 3, 3500, 3, "Hostel rent"),
        (13, 1, 120, 1, "Auto fare"),
        (17, 2, 799, 2, "T-shirt"),
    ]
    return [
        {
            "id": str(uuid.uuid4()),
            "date": (today - timedelta(days=days)).isoformat(),
            "category": CATEGORIES[cat],
            "amount": float(amount),
            "payment": PAYMENTS[pay],
            "description": desc,
        }
        for days, cat, amount, pay, desc in rows
    ]


make_theme_file()

# ------------------------------------------------------------------
# 3. SESSION STATE (remember things while the app is running)
# ------------------------------------------------------------------
DEFAULT_SETTINGS = {"name": "", "theme": "Light", "budget": 0.0, "currency": "₹"}

if "settings" not in st.session_state:
    st.session_state.settings = {**DEFAULT_SETTINGS, **load_json(SETTINGS_FILE, {})}
if "message" not in st.session_state:
    st.session_state.message = None  # (type, text) shown after add/edit/delete


def flash(kind, text):
    """Store a message to show after the page reloads."""
    st.session_state.message = (kind, text)


expenses = load_expenses()

# ------------------------------------------------------------------
# 4. SIDEBAR  (name, mode, currency, budget, demo tools)
# ------------------------------------------------------------------
saved = st.session_state.settings

with st.sidebar:
    st.markdown("## 🎨 Settings")
    name_input = st.text_input("👤 Your name", value=saved["name"], placeholder="e.g. Monika")
    theme = st.radio("🌗 Mode", ["Light", "Dark"], horizontal=True,
                     index=0 if saved["theme"] == "Light" else 1)
    currency = st.selectbox("💱 Currency", CURRENCIES,
                            index=CURRENCIES.index(saved["currency"]) if saved["currency"] in CURRENCIES else 0)
    budget = st.number_input(f"🎯 Monthly budget ({currency})", min_value=0.0, step=500.0,
                             format="%.2f", value=float(saved["budget"]),
                             help="Set 0 if you do not want a budget.")

    new_settings = {"name": name_input.strip(), "theme": theme,
                    "budget": float(budget), "currency": currency}
    if new_settings != saved:
        st.session_state.settings = new_settings
        save_json(SETTINGS_FILE, new_settings)

    st.markdown("---")
    with st.expander("🧪 Demo tools"):
        if st.button("➕ Add sample data"):
            save_expenses(expenses + make_sample_data())
            flash("success", "🎉 Sample expenses added!")
            st.rerun()
        sure = st.checkbox("Yes, I want to delete ALL expenses")
        if st.button("🗑️ Delete all expenses"):
            if sure:
                save_expenses([])
                flash("success", "🧹 All expenses deleted.")
                st.rerun()
            else:
                st.warning("Please tick the box first.")

user_name = st.session_state.settings["name"]
is_dark = st.session_state.settings["theme"] == "Dark"
CURRENCY = st.session_state.settings["currency"]
monthly_budget = st.session_state.settings["budget"]

# ------------------------------------------------------------------
# 5. COLORS + CSS  (rainbow theme, Light and Dark)
# ------------------------------------------------------------------
if is_dark:
    page_bg = "radial-gradient(circle at 15% 10%, #242A63 0%, #0E1024 55%)"
    card = "#1A1D3A"
    text = "#F1F3FF"
    border = "#3B3F75"
    zebra = "#212550"
    sidebar_bg = "linear-gradient(180deg, #1B1F4B, #2B1B5A)"
    accent = "#A78BFA"
    plot_template = "plotly_dark"
else:
    page_bg = "linear-gradient(135deg, #FFF1F5 0%, #EAF4FF 50%, #EFFFF4 100%)"
    card = "#FFFFFF"
    text = "#252A4A"
    border = "#D9DEFF"
    zebra = "#F6F7FF"
    sidebar_bg = "linear-gradient(180deg, #F3E8FF, #DFF3FF)"
    accent = "#7C4DFF"

RAINBOW_GRADIENT = "linear-gradient(90deg, #FF6B6B, #FFA94D, #FAB005, #51CF66, #20C997, #339AF0, #845EF7, #F783AC)"
BUTTON_GRADIENT = "linear-gradient(90deg, #7C4DFF, #339AF0, #20C997)"

st.markdown(
    f"""
    <style>
    /* ---------- page ---------- */
    .stApp {{ background: {page_bg}; background-attachment: fixed; }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    .stApp, .stApp p, .stApp label, .stApp span, .stApp li,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {text}; }}
    section[data-testid="stSidebar"] {{ background: {sidebar_bg}; }}

    /* ---------- input boxes ---------- */
    input, textarea, div[data-baseweb="select"] > div, div[data-baseweb="input"],
    [data-testid="stNumberInput"] button {{
        background-color: {card} !important; color: {text} !important;
        border-color: {border} !important;
    }}
    span[data-baseweb="tag"] {{ background-color: {accent} !important; }}
    span[data-baseweb="tag"] * {{ color: #FFFFFF !important; }}

    /* ---------- dropdown list + calendar pop-up ---------- */
    div[data-baseweb="popover"] *, div[data-baseweb="calendar"] * {{ color: {text} !important; }}
    div[data-baseweb="popover"] > div, div[data-baseweb="calendar"],
    div[data-baseweb="menu"], div[data-baseweb="popover"] ul {{
        background-color: {card} !important;
    }}
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [aria-selected="true"] * {{
        background-color: #7C4DFF !important; color: #FFFFFF !important; border-radius: 8px;
    }}

    /* ---------- forms + expanders ---------- */
    div[data-testid="stForm"] {{
        background: {card}; border: 2px solid {border}; border-radius: 18px;
        box-shadow: 0 4px 16px rgba(124, 77, 255, 0.12);
    }}
    div[data-testid="stExpander"] {{
        background: {card}; border: 1px solid {border}; border-radius: 12px;
    }}

    /* ---------- buttons (purple - blue - green gradient) ---------- */
    .stButton button, div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stDownloadButton"] button {{
        background: {BUTTON_GRADIENT} !important;
        color: #FFFFFF !important; border: none !important; border-radius: 12px;
        font-weight: 700; transition: all 0.2s;
    }}
    .stButton button *, div[data-testid="stFormSubmitButton"] button *,
    div[data-testid="stDownloadButton"] button * {{ color: #FFFFFF !important; }}
    .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover {{
        transform: translateY(-2px); box-shadow: 0 6px 16px rgba(124, 77, 255, 0.45);
    }}

    /* ---------- tabs ---------- */
    button[data-baseweb="tab"] p {{ font-size: 1rem; font-weight: 600; }}
    button[data-baseweb="tab"][aria-selected="true"] p {{ color: {accent} !important; font-weight: 800; }}
    div[data-baseweb="tab-highlight"] {{ background: {RAINBOW_GRADIENT} !important; height: 4px; }}

    /* ---------- tables (easy to read in both modes) ---------- */
    .stApp [data-testid="stTable"] table {{
        width: 100%; border-collapse: collapse; background: {card};
        border-radius: 12px; overflow: hidden;
    }}
    .stApp [data-testid="stTable"] thead th {{
        background: linear-gradient(90deg, #7C4DFF, #339AF0) !important;
        color: #FFFFFF !important; font-weight: 700;
    }}
    .stApp [data-testid="stTable"] tbody th {{ background: {card}; color: {text}; }}
    .stApp [data-testid="stTable"] td {{
        background: {card}; color: {text}; border-bottom: 1px solid {border};
    }}
    .stApp [data-testid="stTable"] tbody tr:nth-child(even) td {{ background: {zebra}; }}

    /* ---------- hero banner ---------- */
    .hero {{
        background: {RAINBOW_GRADIENT}; background-size: 300% 300%;
        animation: moveColors 10s ease infinite;
        padding: 26px 20px; border-radius: 22px; text-align: center;
        margin-bottom: 20px; box-shadow: 0 8px 26px rgba(124, 77, 255, 0.35);
    }}
    .hero-title {{
        font-size: 2.4rem; font-weight: 800; color: #FFFFFF !important;
        text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}
    .hero-sub {{ font-size: 1.05rem; color: #FFFFFF !important; margin-top: 6px; opacity: 0.95; }}
    @keyframes moveColors {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* ---------- colorful summary cards ---------- */
    .metric-card {{
        border-radius: 18px; padding: 18px 12px; text-align: center; color: #FFFFFF !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.22); transition: transform 0.2s; margin-bottom: 14px;
    }}
    .metric-card:hover {{ transform: translateY(-5px); }}
    .metric-card h4 {{ margin: 0; font-size: 1rem; color: #FFFFFF !important; opacity: .92; }}
    .metric-card h2 {{ margin: 6px 0 2px 0; font-size: 1.6rem; color: #FFFFFF !important; }}
    .metric-card small {{ color: #FFFFFF !important; opacity: .9; }}
    .c1 {{ background: linear-gradient(135deg, #FF6B6B, #F06595); }}
    .c2 {{ background: linear-gradient(135deg, #FFA94D, #F59F00); }}
    .c3 {{ background: linear-gradient(135deg, #20C997, #12B886); }}
    .c4 {{ background: linear-gradient(135deg, #339AF0, #4263EB); }}
    .c5 {{ background: linear-gradient(135deg, #845EF7, #CC5DE8); }}
    .c6 {{ background: linear-gradient(135deg, #15AABF, #20C997); }}

    /* ---------- budget box ---------- */
    .budget-box {{
        background: {card}; border: 2px solid {border}; border-radius: 18px;
        padding: 16px 18px; margin-bottom: 18px;
    }}
    .budget-top {{ display: flex; justify-content: space-between; font-size: 1.05rem; margin-bottom: 8px; }}
    .bar-bg {{ background: {zebra}; border: 1px solid {border}; height: 20px; border-radius: 12px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 12px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# 6. SMALL HELPERS FOR TABLES AND CHARTS
# ------------------------------------------------------------------
def badge_painter(colors):
    """Returns a function that gives every value its own background color."""
    def paint(column):
        return [
            f"background-color: {colors.get(value, '#868E96')}; "
            f"color: white; font-weight: bold; text-align: center;"
            for value in column
        ]
    return paint


def color_table(table, cat_col=None, pay_col=None, amount_col=None):
    """Make a table colorful: category and payment badges, bold amounts."""
    styler = table.style
    if cat_col:
        styler = styler.apply(badge_painter(CATEGORY_COLORS), subset=[cat_col])
    if pay_col:
        styler = styler.apply(badge_painter(PAYMENT_COLORS), subset=[pay_col])
    if amount_col:
        styler = styler.set_properties(subset=[amount_col], **{"font-weight": "bold", "color": "#F76707"})
    return styler


def style_fig(fig):
    """Make a chart transparent so it matches the page colors."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=text, title_font_size=18, margin=dict(t=60, b=30, l=20, r=20),
    )
    return fig


def card_html(css_class, title, value, note=""):
    """One colorful summary card."""
    return (f'<div class="metric-card {css_class}"><h4>{title}</h4>'
            f'<h2>{value}</h2><small>{note}</small></div>')


# ------------------------------------------------------------------
# 7. HERO BANNER  ->  "<Name>'s Expense Tracker"
# ------------------------------------------------------------------
today = date.today()
hour = datetime.now().hour
greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"

title = f"{escape(user_name)}'s Expense Tracker" if user_name else "Expense Tracker"
hello = f"{greeting}, {escape(user_name)}! 👋" if user_name else f"{greeting}! 👋"
st.markdown(
    f'<div class="hero"><div class="hero-title">💸 {title}</div>'
    f'<div class="hero-sub">{hello} &nbsp;•&nbsp; Today is {long_date(today)}</div></div>',
    unsafe_allow_html=True,
)

if not user_name:
    st.info("👈 Enter your name in the sidebar to personalise the title.")

# Show one-time message (success / error)
if st.session_state.message:
    kind, msg = st.session_state.message
    (st.success if kind == "success" else st.error)(msg)
    st.session_state.message = None

# ------------------------------------------------------------------
# 8. LOAD DATA + SUMMARY CARDS
# ------------------------------------------------------------------
COLUMNS = ["id", "date", "category", "amount", "payment", "description"]
df = pd.DataFrame(expenses, columns=COLUMNS)
if not df.empty:
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    df["payment"] = df["payment"].fillna(PAYMENTS[0])   # older entries have no payment
    df["description"] = df["description"].fillna("")

if df.empty:
    total = month_total = today_total = average = 0.0
    count = today_count = 0
    biggest_value, biggest_note = money(0), "no data yet"
    top_cat, top_note = "—", "no data yet"
else:
    total = df["amount"].sum()
    count = len(df)
    average = df["amount"].mean()
    in_month = (df["date"].dt.year == today.year) & (df["date"].dt.month == today.month)
    month_total = df.loc[in_month, "amount"].sum()
    is_today = df["date"].dt.date == today
    today_total = df.loc[is_today, "amount"].sum()
    today_count = int(is_today.sum())
    big = df.loc[df["amount"].idxmax()]
    biggest_value, biggest_note = money(big["amount"]), escape(str(big["description"])[:28])
    cat_totals = df.groupby("category")["amount"].sum()
    top_cat = cat_totals.idxmax()
    top_note = f"{money(cat_totals.max())} spent"

row1 = st.columns(3)
row1[0].markdown(card_html("c1", "💰 Total Spent", money(total), f"{count} expenses"), unsafe_allow_html=True)
row1[1].markdown(card_html("c2", "🗓️ This Month", money(month_total), today.strftime("%B %Y")), unsafe_allow_html=True)
row1[2].markdown(card_html("c3", "☀️ Today", money(today_total), f"{today_count} expense(s)"), unsafe_allow_html=True)
row2 = st.columns(3)
row2[0].markdown(card_html("c4", "📊 Average", money(average), "per expense"), unsafe_allow_html=True)
row2[1].markdown(card_html("c5", "🚀 Biggest Expense", biggest_value, biggest_note), unsafe_allow_html=True)
row2[2].markdown(card_html("c6", "🏆 Top Category", top_cat, top_note), unsafe_allow_html=True)

# ---------- monthly budget bar ----------
if monthly_budget > 0:
    used = month_total / monthly_budget * 100
    if used < 70:
        bar_color, note = "linear-gradient(90deg, #20C997, #51CF66)", f"✅ {money(monthly_budget - month_total)} left this month. Great job!"
    elif used < 100:
        bar_color, note = "linear-gradient(90deg, #FAB005, #FFA94D)", f"⚠️ {used:.0f}% used. Only {money(monthly_budget - month_total)} left!"
    else:
        bar_color, note = "linear-gradient(90deg, #F06595, #FF6B6B)", f"🚨 Budget crossed by {money(month_total - monthly_budget)}!"
    st.markdown(
        f'<div class="budget-box"><div class="budget-top"><b>🎯 Monthly Budget</b>'
        f'<span>{money(month_total)} of {money(monthly_budget)} ({used:.0f}%)</span></div>'
        f'<div class="bar-bg"><div class="bar-fill" style="width:{min(used, 100):.0f}%; background:{bar_color};"></div></div>'
        f'<div style="margin-top:8px;">{note}</div></div>',
        unsafe_allow_html=True,
    )
else:
    st.caption("🎯 Tip: set a monthly budget in the sidebar to see a progress bar here.")

# ------------------------------------------------------------------
# 9. TABS
# ------------------------------------------------------------------
tab_add, tab_view, tab_edit, tab_daily, tab_charts = st.tabs(
    ["➕ Add Expense", "📋 All Expenses", "✏️ Edit / Delete", "📅 Daily Table", "📈 Charts"]
)

# ---------- CREATE ----------
with tab_add:
    st.subheader("➕ Add a new expense")
    with st.form("add_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            exp_date = st.date_input(
                "📅 Date (Day / Month / Year)", value=today,
                max_value=today, format=DATE_FORMAT,
                help="Click the box to open the calendar and pick a date.",
            )
            exp_cat = st.selectbox("🏷️ Category", CATEGORIES)
            exp_pay = st.selectbox("💳 Paid using", PAYMENTS)
        with col_b:
            exp_amount = st.number_input(f"💵 Amount ({CURRENCY})", min_value=0.0, step=1.0, format="%.2f")
            exp_desc = st.text_input("📝 Description", max_chars=100, placeholder="e.g. Lunch with friends")
        submitted = st.form_submit_button("Add Expense ✅", width="stretch")

    if submitted:
        # ---- Validation ----
        if exp_amount <= 0:
            st.error("❌ Amount must be greater than 0.")
        elif exp_amount > MAX_AMOUNT:
            st.error(f"❌ Amount is too big. Please enter less than {money(MAX_AMOUNT)}.")
        elif not exp_desc.strip():
            st.error("❌ Description cannot be empty.")
        elif exp_date > today:
            st.error("❌ Date cannot be in the future.")
        else:
            expenses.append({
                "id": str(uuid.uuid4()),
                "date": exp_date.isoformat(),
                "category": exp_cat,
                "amount": round(exp_amount, 2),
                "payment": exp_pay,
                "description": exp_desc.strip(),
            })
            save_expenses(expenses)
            flash("success", f"✅ Expense added for {long_date(exp_date)}!")
            st.rerun()

    if not df.empty:
        st.markdown("#### 🕒 Recently added")
        recent = df.sort_values("date", ascending=False).head(5)[["date", "category", "payment", "amount", "description"]].copy()
        recent["date"] = recent["date"].map(nice_date)
        recent["amount"] = recent["amount"].map(money)
        recent.columns = ["Date", "Category", "Paid Using", "Amount", "Description"]
        recent.index = range(1, len(recent) + 1)
        st.table(color_table(recent, cat_col="Category", pay_col="Paid Using", amount_col="Amount"))

# ---------- READ ----------
with tab_view:
    st.subheader("📋 All expenses")
    if df.empty:
        st.info("No expenses yet. Add your first one in the ➕ tab, or use 🧪 Demo tools in the sidebar!")
    else:
        f1, f2 = st.columns([2, 1])
        search = f1.text_input("🔎 Search in description", placeholder="type a word, e.g. lunch")
        sort_choice = f2.selectbox("↕️ Sort by", ["📅 Newest first", "📅 Oldest first",
                                                   "💰 Highest amount", "💰 Lowest amount"])
        f3, f4, f5 = st.columns(3)
        chosen = f3.multiselect("🏷️ Category", CATEGORIES)
        d_from = f4.date_input("📅 From", value=df["date"].min().date(), max_value=today,
                               format=DATE_FORMAT, key="from_date")
        d_to = f5.date_input("📅 To", value=today, max_value=today,
                             format=DATE_FORMAT, key="to_date")

        if d_from > d_to:
            st.error("❌ The 'From' date must be before the 'To' date.")
        else:
            view = df.copy()
            if search.strip():
                view = view[view["description"].str.contains(search.strip(), case=False, regex=False)]
            if chosen:
                view = view[view["category"].isin(chosen)]
            view = view[(view["date"].dt.date >= d_from) & (view["date"].dt.date <= d_to)]

            sort_rules = {
                "📅 Newest first": ("date", False), "📅 Oldest first": ("date", True),
                "💰 Highest amount": ("amount", False), "💰 Lowest amount": ("amount", True),
            }
            sort_col, ascending = sort_rules[sort_choice]
            view = view.sort_values(sort_col, ascending=ascending)

            if view.empty:
                st.warning("😕 No expenses match your search or filters.")
            else:
                show = view[["date", "category", "payment", "amount", "description"]].copy()
                show["date"] = show["date"].map(nice_date)
                show["amount"] = show["amount"].map(money)
                show.columns = ["Date", "Category", "Paid Using", "Amount", "Description"]
                show.index = range(1, len(show) + 1)   # serial numbers 1, 2, 3 ...
                st.table(color_table(show, cat_col="Category", pay_col="Paid Using", amount_col="Amount"))
                st.success(f"Showing {len(view)} expense(s)  •  Total: {money(view['amount'].sum())}")

                # ---- download as CSV (opens in Excel) ----
                export = view[["date", "category", "payment", "amount", "description"]].copy()
                export["date"] = export["date"].dt.strftime("%Y-%m-%d")
                export.columns = ["Date", "Category", "Paid Using", "Amount", "Description"]
                st.download_button("⬇️ Download as CSV", export.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="my_expenses.csv", mime="text/csv")

# ---------- UPDATE + DELETE ----------
with tab_edit:
    st.subheader("✏️ Edit or 🗑️ delete an expense")
    if df.empty:
        st.info("Nothing to edit yet.")
    else:
        ordered = df.sort_values("date", ascending=False)
        labels = {
            row["id"]: f"{nice_date(row['date'])}  |  {row['category']}  |  "
                       f"{money(row['amount'])}  |  {row['description']}"
            for _, row in ordered.iterrows()
        }
        selected_id = st.selectbox("Choose an expense", list(labels.keys()),
                                   format_func=lambda i: labels[i])
        old = next(e for e in expenses if e["id"] == selected_id)
        old_cat = old["category"] if old["category"] in CATEGORIES else CATEGORIES[-1]
        old_pay = old.get("payment", PAYMENTS[0])
        old_pay = old_pay if old_pay in PAYMENTS else PAYMENTS[0]

        # the key includes the id so the form refreshes when you pick another expense
        with st.form(f"edit_form_{selected_id}"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_date = st.date_input(
                    "📅 Date (Day / Month / Year)", value=date.fromisoformat(old["date"]),
                    max_value=today, format=DATE_FORMAT,
                )
                new_cat = st.selectbox("🏷️ Category", CATEGORIES, index=CATEGORIES.index(old_cat))
                new_pay = st.selectbox("💳 Paid using", PAYMENTS, index=PAYMENTS.index(old_pay))
            with col_b:
                new_amount = st.number_input(f"💵 Amount ({CURRENCY})", min_value=0.0, step=1.0,
                                             format="%.2f", value=float(old["amount"]))
                new_desc = st.text_input("📝 Description", value=old["description"], max_chars=100)
            update_clicked = st.form_submit_button("Update Expense 💾", width="stretch")

        if update_clicked:
            if new_amount <= 0:
                st.error("❌ Amount must be greater than 0.")
            elif new_amount > MAX_AMOUNT:
                st.error(f"❌ Amount is too big. Please enter less than {money(MAX_AMOUNT)}.")
            elif not new_desc.strip():
                st.error("❌ Description cannot be empty.")
            elif new_date > today:
                st.error("❌ Date cannot be in the future.")
            else:
                old.update({
                    "date": new_date.isoformat(),
                    "category": new_cat,
                    "amount": round(new_amount, 2),
                    "payment": new_pay,
                    "description": new_desc.strip(),
                })
                save_expenses(expenses)
                flash("success", "✅ Expense updated!")
                st.rerun()

        st.markdown("---")
        confirm = st.checkbox("I am sure I want to delete this expense")
        if st.button("🗑️ Delete Expense"):
            if confirm:
                expenses = [e for e in expenses if e["id"] != selected_id]
                save_expenses(expenses)
                flash("success", "🗑️ Expense deleted.")
                st.rerun()
            else:
                st.error("Please tick the confirmation box first.")

# ---------- DAILY TABLE ----------
with tab_daily:
    st.subheader("📅 Daily expenses")
    if df.empty:
        st.info("No data yet.")
    else:
        # one row per day: how many expenses, total, most used category
        daily = (
            df.groupby(df["date"].dt.date)
            .agg(Expenses=("amount", "count"),
                 Total=("amount", "sum"),
                 TopCategory=("category", lambda s: s.value_counts().idxmax()))
            .reset_index()
            .sort_values("date", ascending=False)
        )
        daily["date"] = daily["date"].map(nice_date)
        daily["Total"] = daily["Total"].map(money)
        daily.columns = ["Date", "No. of Expenses", "Total Spent", "Most Used Category"]
        daily.index = range(1, len(daily) + 1)
        st.table(color_table(daily, cat_col="Most Used Category", amount_col="Total Spent"))

        st.markdown("#### 🔍 See details of each day")
        newest_first = df.sort_values("date", ascending=False).copy()
        newest_first["day"] = newest_first["date"].dt.date
        for day, group in newest_first.groupby("day", sort=False):
            with st.expander(f"📆 {nice_date(day)}  —  {money(group['amount'].sum())}"):
                detail = group[["category", "payment", "description", "amount"]].copy()
                detail["amount"] = detail["amount"].map(money)
                detail.columns = ["Category", "Paid Using", "Description", "Amount"]
                detail.index = range(1, len(detail) + 1)
                st.table(color_table(detail, cat_col="Category", pay_col="Paid Using", amount_col="Amount"))

# ---------- CHARTS ----------
with tab_charts:
    st.subheader("📈 Analysis")
    if df.empty:
        st.info("Add some expenses to see charts.")
    else:
        money_label = f"Amount ({CURRENCY})"
        by_cat = df.groupby("category", as_index=False)["amount"].sum()

        # --- row 1: category charts ---
        left, right = st.columns(2)
        with left:
            fig1 = px.pie(by_cat, names="category", values="amount", hole=0.45,
                          color="category", color_discrete_map=CATEGORY_COLORS,
                          title="🍩 Expenses by Category", template=plot_template)
            st.plotly_chart(style_fig(fig1), width="stretch")
        with right:
            fig2 = px.bar(by_cat.sort_values("amount"), x="amount", y="category",
                          orientation="h", color="category", color_discrete_map=CATEGORY_COLORS,
                          labels={"amount": money_label, "category": ""},
                          title="📊 Category Totals", template=plot_template)
            fig2.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig2), width="stretch")

        # --- row 2: expenses over time ---
        by_day = df.groupby(df["date"].dt.date, as_index=False)["amount"].sum()
        fig3 = px.line(by_day, x="date", y="amount", markers=True,
                       labels={"date": "Date", "amount": money_label},
                       title="📈 Expenses Over Time", template=plot_template)
        fig3.update_traces(line_color="#7C4DFF", marker_size=10, marker_color="#FF6B6B",
                           fill="tozeroy", fillcolor="rgba(124, 77, 255, 0.18)")
        fig3.update_xaxes(tickformat="%d %b %Y")
        st.plotly_chart(style_fig(fig3), width="stretch")

        # --- row 3: monthly totals + payment methods ---
        left, right = st.columns(2)
        with left:
            by_month = df.groupby(df["date"].dt.to_period("M").dt.to_timestamp(), as_index=False)["amount"].sum()
            by_month["month"] = by_month["date"].dt.strftime("%b %Y")
            fig5 = px.bar(by_month, x="month", y="amount", color="month",
                          color_discrete_sequence=RAINBOW,
                          labels={"month": "Month", "amount": money_label},
                          title="🗓️ Monthly Spending", template=plot_template)
            fig5.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig5), width="stretch")
        with right:
            by_pay = df.groupby("payment", as_index=False)["amount"].sum()
            fig6 = px.pie(by_pay, names="payment", values="amount",
                          color="payment", color_discrete_map=PAYMENT_COLORS,
                          title="💳 Payment Methods", template=plot_template)
            st.plotly_chart(style_fig(fig6), width="stretch")

        # --- row 4: daily spending by category ---
        by_day_cat = df.groupby([df["date"].dt.date, "category"], as_index=False)["amount"].sum()
        fig4 = px.bar(by_day_cat, x="date", y="amount", color="category",
                      color_discrete_map=CATEGORY_COLORS,
                      labels={"date": "Date", "amount": money_label, "category": "Category"},
                      title="🌈 Daily Spending by Category", template=plot_template)
        fig4.update_xaxes(tickformat="%d %b %Y")
        st.plotly_chart(style_fig(fig4), width="stretch")

        # --- row 5: weekday chart + top 5 expenses ---
        left, right = st.columns(2)
        with left:
            week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            by_weekday = df.groupby(df["date"].dt.day_name())["amount"].sum().reindex(week_order, fill_value=0).reset_index()
            by_weekday.columns = ["weekday", "amount"]
            fig7 = px.bar(by_weekday, x="weekday", y="amount", color="weekday",
                          color_discrete_sequence=RAINBOW,
                          labels={"weekday": "Day", "amount": money_label},
                          title="📆 Spending by Day of Week", template=plot_template)
            fig7.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig7), width="stretch")
        with right:
            st.markdown("#### 🏅 Top 5 biggest expenses")
            top5 = df.nlargest(5, "amount")[["date", "category", "amount", "description"]].copy()
            top5["date"] = top5["date"].map(nice_date)
            top5["amount"] = top5["amount"].map(money)
            top5.columns = ["Date", "Category", "Amount", "Description"]
            top5.index = range(1, len(top5) + 1)
            st.table(color_table(top5, cat_col="Category", amount_col="Amount"))

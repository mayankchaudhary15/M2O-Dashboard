"""
Mr. Brown Bakery & Coffee - Item Performance Dashboard
Run:  streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

import insights as ins
import recommend as rec_mod

pio.templates.default = "plotly_dark"

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Mr. Brown Dashboard",
    page_icon="🥐",
    layout="wide",
)

# Put the Excel file in the same folder as this script (or change the name)
_here = Path(__file__).parent
_menus = sorted(_here.glob("Menu*.xlsx"))
_found = sorted(_here.glob("Mr*Brown*Dashboard*.xlsx")) or [f for f in sorted(_here.glob("*.xlsx")) if f not in _menus]
DEFAULT_FILE = _found[0] if _found else _here / "Mr_Brown_Dashboard.xlsx"

# --------------------------------------------------------------------------
# ITEM NAME MATCHING: spelling variants in the workbook -> the name on the menu.
# Rows that end up with the same name count as one item (impressions, orders and issues are added).
# --------------------------------------------------------------------------
# Same item, different spelling: "(pc)" suffix, typos, word order
ALIASES = {
    "Baked Samosa (pc)": "Baked Samosa",
    'Bread Wheat Pizza Base [8"': 'Bread Wheat Pizza Base (8"',
    "Burger Mexican Cheese* (pc)": "Mexican Cheese Burger*",
    "Chilli Cheese Samosa* (pc)": "Chilli Cheese Samosa*",
    "Chilly Paneer Roll (pc)": "Chilli Paneer Roll",
    "Loaded Nachos* (pc)": "Loaded Nachos*",
    "Mushroom Patty (pc)": "Mushroom Patty",
    "Paneer Patty (pc)": "Paneer Patty",
    "Peri Peri Fries* (pc)": "Peri Peri Fries*",
    "Pull-apart Garlic Bread* (pc)": "Pull-apart Garlic Bread*",
    "Spiral Paneer Roll (pc)": "Spiral Paneer Roll",
    "Veg Kebab Roll (pc)": "Veg Kebab Roll",
    "Veg Aaloo Patty (pc)": "Aloo Veg Patty",
    "Penne Arrabiata Pasta*": "Penne Arrabbiata Sauce Pasta*",
    "Og Margherita Sourdough Pizza*": "Margherita Sourdough Pizza*",
}

# Probably the same item renamed on the menu (confirmed by Dev). Applied when
# MERGE_POSSIBLE is True.
POSSIBLE = {
    "Assorted Cookies Box -1000": "Assorted Cookies Box -1050",
    "Classic Cold Coffee*": "Cold Coffee*",
    "Classic Fries*": "Classic Salted Fries*",
    "Oreo Shake* (pc)": "Vanilla Oreo Shake*",
    "Yuzu Lime Iced Tea* (pc)": "Yuzu Iced Tea*",
    "Very Berry Smoothie* (pc)": "Mixed Berry Smoothie*",
    "Strawberry Shake*": "Velvet Strawberry Shake*",
}
MERGE_POSSIBLE = True


def canonical(name):
    name = ALIASES.get(name, name)
    return POSSIBLE.get(name, name) if MERGE_POSSIBLE else name


COLOR = "#8B4513"  # bakery brown
SEQ = px.colors.sequential.YlOrBr



st.markdown(
    """
<style>
[data-testid="stMetric"]{background:#1B2433;border:1px solid #2A3550;border-radius:12px;padding:14px 16px}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] *{color:#AFC0DD !important;white-space:normal !important;overflow:visible !important;text-overflow:clip !important}
[data-testid="stMetricLabel"] p{text-transform:uppercase;font-size:.72rem;letter-spacing:.05em}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:#FFFFFF !important;white-space:normal !important;overflow:visible !important;text-overflow:clip !important}
[data-testid="stMetricValue"] div{font-size:1.7rem !important;line-height:1.2}
.hero{background:linear-gradient(120deg,#1E3A5F,#14756E);border-radius:16px;padding:26px 30px;margin-bottom:14px}
.hero h1{margin:0 0 4px 0;font-size:2rem;color:#fff}
.hero p{margin:0 0 12px 0;color:#D6E4F0}
.chip{display:inline-block;background:rgba(255,255,255,.14);border-radius:999px;padding:5px 14px;margin:0 8px 6px 0;font-size:.82rem;color:#fff}
.note{background:#1B2433;border-left:4px solid #F59E0B;border-radius:8px;padding:10px 16px;margin:10px 0 18px 0;color:#C9D3E6;font-size:.9rem}
.sec{display:flex;align-items:center;gap:12px;margin:6px 0 2px 0}
.badge{background:#3B82F6;color:#fff;border-radius:8px;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:700}
.sec h2{margin:0;font-size:1.4rem}
.sub{color:#8FA0BF;margin:0 0 14px 42px;font-size:.9rem}
.take{background:#1B2433;border:1px solid #2A3550;border-radius:12px;padding:16px 22px;margin:18px 0 6px 0}
.take h4{color:#22D3EE;margin:0 0 8px 0}
.take li{margin-bottom:6px;color:#D5DCEB}
.sumwrap{container-type:inline-size}
.sumgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;align-items:stretch;margin-bottom:14px}
@container (max-width:1000px){.sumgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@container (max-width:520px){.sumgrid{grid-template-columns:minmax(0,1fr)}}
.card4{box-sizing:border-box;min-width:0;border-radius:12px;padding:18px 20px;border:1px solid;border-top-width:4px;display:flex;flex-direction:column;justify-content:flex-start}
.card4 .ct{display:flex;align-items:center;gap:8px;margin:0 0 10px 0;font-size:1.05rem;font-weight:700;line-height:1.3;flex-wrap:wrap}
.card4 p,.card4 li{margin:0;font-size:.9rem;line-height:1.55;color:#E1E7F3 !important;overflow-wrap:anywhere}
.card4 ol{margin:0;padding-left:1.2rem}.card4 li{margin-bottom:6px}.card4 li:last-child{margin-bottom:0}
/* Keep the tab bar pinned under Streamlit's top toolbar while the page scrolls */
.stTabs [role="tablist"],.stTabs [data-baseweb="tab-list"]{position:sticky;top:3.75rem;z-index:990;background:#0F141C;padding-top:6px;box-shadow:0 6px 10px -6px rgba(0,0,0,.6)}
.stTabs [role="tab"],.stTabs [role="tab"] p{color:#AFC0DD !important}
.stTabs [role="tab"]:hover,.stTabs [role="tab"]:hover p{color:#FFFFFF !important}
.stTabs [role="tab"][aria-selected="true"],.stTabs [role="tab"][aria-selected="true"] p{color:#60A5FA !important;font-weight:600}
.stTabs [data-baseweb="tab-highlight"],.stTabs .react-aria-SelectionIndicator{background-color:#60A5FA !important}
</style>
""",
    unsafe_allow_html=True,
)


def section(num, title, sub):
    st.markdown(
        f'<div class="sec"><div class="badge">{num}</div><h2>{title}</h2></div><div class="sub">{sub}</div>',
        unsafe_allow_html=True,
    )


def takeaways(title, bullets):
    items = "".join(f"<li>{b}</li>" for b in bullets)
    st.markdown(f'<div class="take"><h4>Key takeaways - {title}</h4><ul>{items}</ul></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# DATA LOADING
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading workbook...")
def load_data(file) -> dict:
    xl = pd.ExcelFile(file)
    d = {}

    # Item funnel (drop the empty spare columns)
    funnel = xl.parse("Item Level Funnel")
    funnel = funnel.loc[:, ~funnel.columns.astype(str).str.startswith("Unnamed")]
    funnel = funnel.rename(columns={"Item_names": "item_names"})
    # Merge spelling variants of the same item (see item_names.py) and recompute the rates
    funnel["item_names"] = funnel["item_names"].map(canonical)
    funnel = funnel.groupby("item_names", as_index=False, sort=False)[["Impressions", "Cart Makes", "Total Orders"]].sum()
    funnel["I2C"] = funnel["Cart Makes"] / funnel["Impressions"] * 100
    funnel["C2O"] = (funnel["Total Orders"] / funnel["Cart Makes"].where(funnel["Cart Makes"] > 0) * 100).fillna(0)
    funnel["I2O"] = funnel["Total Orders"] / funnel["Impressions"] * 100
    d["funnel"] = funnel

    # Item performance summary (one row per item per outlet)
    perf = xl.parse("Item Performance Summary").rename(columns={"item_names": "Item_names"})
    perf["Item_names"] = perf["Item_names"].map(canonical)
    # A rating of 0 means "not rated yet", not a score of 0
    perf["Item Rating"] = perf["Item Rating"].astype(float).mask(lambda s: s == 0)
    d["perf"] = perf

    # The funnel sheet averages ratings with unrated outlets counted as 0, so use the
    # performance sheet's rating (mean of the outlets that have one) instead
    item_rating = perf.groupby("Item_names")["Item Rating"].mean()
    d["funnel"]["Item Rating"] = d["funnel"]["item_names"].map(item_rating)

    # Null searches: drop repeated header rows / blanks and merge duplicate terms
    ns = xl.parse("Null Searches", header=None)
    ns = ns.iloc[:, :4]
    ns.columns = ["restaurant", "region", "search_term", "searches"]
    ns["search_term"] = ns["search_term"].astype(str).str.strip().str.lower()
    ns = ns[~ns["search_term"].isin(["keyword", "search_term", "", "nan"])]
    ns["searches"] = pd.to_numeric(ns["searches"], errors="coerce").fillna(0)
    ns = ns.groupby(["restaurant", "region", "search_term"], as_index=False)["searches"].sum()
    d["null_search"] = ns

    # Dish recommendations (per outlet)
    d["rec"] = xl.parse("Dish_recommendations") if "Dish_recommendations" in xl.sheet_names else None

    # S2O by dish
    d["s2o"] = xl.parse("S2O for Zone")
    # Zone dishes that fit a bakery & coffee menu (Mr. Brown is all veg); biryani, dal, thali etc. are left out
    keep = (r"\b(?:cakes?|cheese ?cake|pastry|pastries|brownies?|cookies?|muffins?|waffles?|donuts?|doughnuts?|breads?|pizza|"
            r"sandwich(?:es)?|burgers?|pasta|fries|nachos|patty|patties|puffs?|samosa|wraps?|salad|coffee|tea|shakes?|"
            r"smoothies?|kunafa|baklava|tarts?|rusk|bao|ramen|rice bowl|gift hamper|bakery|desserts)\b")
    drop = r"\b(?:chicken|mutton|fish|egg|tikki|milk cake)\b"
    names = d["s2o"]["dish_name"].astype(str)
    d["s2o_menu"] = d["s2o"][names.str.contains(keep, case=False) & ~names.str.contains(drop, case=False)]

    # Cross dish ordering (CDO)
    cdo = xl.parse("CDO")
    cdo["start_date"] = pd.to_datetime(cdo["start_date"].astype(str), format="%Y%m%d", errors="coerce")
    cdo["end_date"] = pd.to_datetime(cdo["end_date"].astype(str), format="%Y%m%d", errors="coerce")
    d["cdo"] = cdo

    # Merge spelling variants ("Aloo Patties" / "Aloo Patty" / "aloo patty ") into one row
    cdo_sum = xl.parse("Summary of CDO").dropna(subset=["item_ordered"])
    key = (
        cdo_sum["item_ordered"].astype(str).str.lower()
        .str.replace(r"[^a-z0-9 ]", " ", regex=True)
        .str.replace(r"\bpatties\b", "patty", regex=True)
        .str.split().str.join(" ")
    )
    cdo_sum = (
        cdo_sum.assign(item_ordered=key.str.title())
        .groupby("item_ordered", as_index=False)["SUM of total_orders_for_item"].sum()
        .sort_values("SUM of total_orders_for_item", ascending=False)
    )
    d["cdo_sum"] = cdo_sum

    # Order-related issues (ORS)
    ors = xl.parse("Item Level ORS")
    ors["item_names"] = ors["item_names"].map(canonical)
    ors = ors.groupby("item_names", as_index=False, sort=False)[[c for c in ors.columns if c.endswith(("Issue", "Issues"))]].sum()
    ors_orders = ors["item_names"].map(funnel.set_index("item_names")["Total Orders"])
    ors["ORS %"] = (ors["Total Issues"] / ors_orders * 100).round(2)
    d["ors"] = ors

    # Rename the Excel column "item_names" -> "Item_names" in every sheet
    for k, v in d.items():
        if v is not None:
            d[k] = v.rename(columns={"item_names": "Item_names"})

    return d


# --------------------------------------------------------------------------
# SIDEBAR - FILE + FILTERS
# --------------------------------------------------------------------------
st.sidebar.title("🥐 Mr. Brown")
uploaded = st.sidebar.file_uploader("Upload Excel (optional)", type=["xlsx"])

source = uploaded if uploaded else DEFAULT_FILE
if not uploaded and not Path(DEFAULT_FILE).exists():
    st.error(
        f"Excel file not found: `{DEFAULT_FILE.name}`. "
        "Place it next to app.py or upload it from the sidebar."
    )
    st.stop()

data = load_data(source)
perf_raw, funnel, ors = data["perf"], data["funnel"], data["ors"]


def combine_outlets(p):
    """One row per item: sum volumes across outlets, average the per-item attributes."""
    return p.groupby("Item_names", as_index=False).agg(
        **{
            "Item Category": ("Item Category", "first"),
            "Total Orders": ("Total Orders", "sum"),
            "Total Item quantity": ("Total Item quantity", "sum"),
            "Total Revenue": ("Total Revenue", "sum"),
            "Cost Per Item": ("Cost Per Item", "mean"),
            "Item Rating": ("Item Rating", "mean"),
            "Salt Discount": ("Salt Discount", "max"),
            "Visibility Percent": ("Visibility Percent", "mean"),
            "Salt Flag": ("Salt Flag", "max"),
            "Has Image": ("Has Image", "max"),
            "Healthy Flag": ("Healthy Flag", "max"),
            "Has Description": ("Has Description", "max"),
        }
    )


st.sidebar.header("Filters")
ALL_OUTLETS = "All outlets (combined)"
outlet = st.sidebar.selectbox("Outlet", [ALL_OUTLETS] + sorted(perf_raw["res_name"].dropna().unique()))
perf = combine_outlets(perf_raw if outlet == ALL_OUTLETS else perf_raw[perf_raw["res_name"] == outlet])

categories = sorted(perf["Item Category"].dropna().unique())
sel_cats = st.sidebar.multiselect("Item category", categories, default=categories)

min_orders = st.sidebar.slider(
    "Minimum orders (Performance tab)",
    0,
    int(perf["Total Orders"].max()),
    0,
)
top_n = st.sidebar.slider("Top N items in charts", 5, 30, 10)

perf_f = perf[perf["Item Category"].isin(sel_cats) & (perf["Total Orders"] >= min_orders)]

# Least-ordered items from the performance sheet, which matches the Funnel and ORS sheets order for order.
# The workbook's "Least ordered item" sheet is not used: it disagrees with all three (e.g. 0 orders for items with 1).
least_f = perf_f.nsmallest(10, "Total Orders")[["Item_names", "Total Orders"]]

# --------------------------------------------------------------------------
# HEADER KPIs
# --------------------------------------------------------------------------
cdo_df = data["cdo"]
chips = [
    "Delhi NCR",
    f"{len(perf_f)} items shown",
    f"{perf_f['Item Category'].nunique()} categories",
    f"Cross-dish window: {cdo_df['start_date'].min():%d %b} - {cdo_df['end_date'].max():%d %b %Y}",
]
st.markdown(
    '<div class="hero"><h1>Mr. Brown Bakery & Coffee</h1>'
    "<p>Item Performance + Funnel + Order Issues + Search Demand</p>"
    + "".join(f'<span class="chip">{c}</span>' for c in chips)
    + "</div>",
    unsafe_allow_html=True,
)

# Funnel and ORS sheets are item-level (both outlets combined); use the items currently shown
_items = set(perf_f["Item_names"])
_fun = funnel[funnel["Item_names"].isin(_items)]
_ors = ors[ors["Item_names"].isin(_items)]


def _fmt(v, fmt):
    return "–" if pd.isna(v) else fmt.format(v)


# Items that sold in the period (Item Performance Summary) missing an image or a description,
# from the workbook's Has Image / Has Description flags
n_missing = int(((perf_f["Has Image"] == 0) | (perf_f["Has Description"] == 0)).sum())

kpis = [
    ("Items listed", f"{len(perf_f):,}"),
    ("Items missing image or description", f"{n_missing:,}"),
    ("Avg rating (rated items)", _fmt(perf_f["Item Rating"].mean(), "{:.2f}")),
    ("Avg visibility %", _fmt(perf_f["Visibility Percent"].mean(), "{:.1f}%")),
    ("Avg I2C", _fmt(_fun["I2C"].mean(), "{:.1f}%")),
    ("Avg C2O", _fmt(_fun.loc[_fun["Cart Makes"] > 0, "C2O"].mean(), "{:.1f}%")),  # C2O undefined with 0 carts
]
# 3 cards per row
for row in (kpis[:3], kpis[3:]):
    for col, (label, value) in zip(st.columns(3), row):
        col.metric(label, value)

# One row per item: menu listing + funnel numbers, the basis for menu-to-order (M2O) analysis
items = perf_f.merge(
    _fun[["Item_names", "Impressions", "Cart Makes", "Total Orders", "I2C", "C2O", "I2O"]].rename(
        columns={"Total Orders": "Orders (funnel)"}),
    on="Item_names", how="left",
).rename(columns={"Total Orders": "Orders", "Orders (funnel)": "Total Orders"})

# What customers order at other restaurants, and whether we list something matching
_menu_index = rec_mod.build_menu_index(combine_outlets(perf_raw))
cdo_tbl = data["cdo_sum"].head(40).rename(columns={"item_ordered": "Item", "SUM of total_orders_for_item": "Orders elsewhere"})
_match = cdo_tbl["Item"].map(lambda x: rec_mod.match_dish(x, _menu_index))
cdo_tbl["On our menu"] = _match.map(lambda m: m[0])
cdo_tbl["Our closest item"] = _match.map(lambda m: ", ".join(m[1][:1]))

tab_sum, tab_over, tab_funnel, tab_quality, tab_search, tab_cdo, tab_rec, tab_data = st.tabs(
    [
        "⭐ Summary",
        "📊 Overview",
        "🔻 Funnel",
        "⚠️ Order Issues (ORS)",
        "🔍 Searches & S2O",
        "🛒 Cross-Dish Orders",
        "💡 Menu Additions",
        "🗂️ Raw Data",
    ]
)

# --------------------------------------------------------------------------
# TAB 0: SUMMARY (menu-to-order focus)
# --------------------------------------------------------------------------
with tab_sum:
    section("★", "Summary", "Where menu views are lost and what to change to turn more of them into orders")
    st.subheader("Visibility % by item (lowest first)")
    st.caption("Items customers rarely see can't convert. Low visibility with a good I2O = move the item up the menu.")
    vis_tbl = items.sort_values("Visibility Percent", ascending=True)[
        ["Item_names", "Item Category", "Visibility Percent", "Impressions", "Total Orders", "I2C", "I2O"]
    ].rename(columns={"Item_names": "Item", "Item Category": "Category", "Visibility Percent": "Visibility %",
                      "Total Orders": "Orders", "I2C": "I2C %", "I2O": "I2O %"})
    st.dataframe(
        vis_tbl, width="stretch", hide_index=True, height=360,
        column_config={c: st.column_config.NumberColumn(c, format="%.1f") for c in ["Visibility %", "I2C %", "I2O %"]},
    )

    st.subheader("CDO: what the same customers order elsewhere")
    st.dataframe(cdo_tbl, width="stretch", hide_index=True, height=360)

    # Wins / Concerns / Opportunities / Actions, just above the takeaways.
    # Each card sits in its own Streamlit column so the page layout always makes room for it.
    colors = {"🎯 Wins": ("#0F2A22", "#1F6B4F", "#4ADE80"), "⚠️ Concerns": ("#2A171C", "#7A2E3A", "#F87171"),
              "💡 Opportunities": ("#122036", "#2B4C80", "#60A5FA"), "🔧 Action items": ("#2A2412", "#7A6320", "#FBBF24")}
    summ = ins.summary(items, _ors, data["null_search"], cdo_tbl)
    for col, (title, body) in zip(st.columns(4, gap="small"), summ.items()):
        bg, border, head = colors[title]
        icon, name = title.split(" ", 1)
        body_html = ("<ol>" + "".join(f"<li>{x}</li>" for x in body) + "</ol>") if isinstance(body, list) else f"<p>{body}</p>"
        col.markdown(
            f'<div class="card4" style="background:{bg};border-color:{border};border-top-color:{head}">'
            f'<div class="ct"><span>{icon}</span><span style="color:{head}">{name}</span></div>{body_html}</div>',
            unsafe_allow_html=True,
        )
    takeaways("Menu to Order", ins.m2o(items, cdo_tbl, data["null_search"]))

# --------------------------------------------------------------------------
# TAB 1: OVERVIEW
# --------------------------------------------------------------------------
with tab_over:
    section(1, "Item & Category Performance", "Where revenue and orders come from")
    c1, c2 = st.columns(2)

    top_rev = perf_f.nlargest(top_n, "Total Revenue").sort_values("Total Revenue")
    fig = px.bar(
        top_rev,
        x="Total Revenue",
        y="Item_names",
        orientation="h",
        title=f"Top {top_n} items by revenue",
        color="Total Revenue",
        color_continuous_scale=SEQ,
    )
    fig.update_layout(yaxis_title=None, coloraxis_showscale=False)
    c1.plotly_chart(fig, width="stretch")

    top_ord = perf_f.nlargest(top_n, "Total Orders").sort_values("Total Orders")
    fig = px.bar(
        top_ord,
        x="Total Orders",
        y="Item_names",
        orientation="h",
        title=f"Top {top_n} items by orders",
        color="Total Orders",
        color_continuous_scale=SEQ,
    )
    fig.update_layout(yaxis_title=None, coloraxis_showscale=False)
    c2.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)

    cat = (
        perf_f.groupby("Item Category", as_index=False)
        .agg(Revenue=("Total Revenue", "sum"), Orders=("Total Orders", "sum"), Items=("Item_names", "count"))
        .sort_values("Revenue", ascending=False)
    )
    # 40+ categories make an unreadable pie, so group everything past the top 8 into "Other"
    pie = cat.head(8)
    if len(cat) > 8:
        pie = pd.concat([pie, pd.DataFrame([{"Item Category": "Other", "Revenue": cat["Revenue"].iloc[8:].sum()}])])
    fig = px.pie(
        pie,
        names="Item Category",
        values="Revenue",
        hole=0.45,
        title="Revenue share by category",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    c3.plotly_chart(fig, width="stretch")

    fig = px.treemap(
        cat,
        path=["Item Category"],
        values="Orders",
        color="Revenue",
        color_continuous_scale=SEQ,
        title="Orders by category (colour = revenue)",
    )
    c4.plotly_chart(fig, width="stretch")

    c5, c6 = st.columns(2)
    flags = pd.DataFrame(
        {
            "Flag": ["Salt discount", "Has image", "Healthy", "Has description"],
            "Items": [
                perf_f["Salt Flag"].sum(),
                perf_f["Has Image"].sum(),
                perf_f["Healthy Flag"].sum(),
                perf_f["Has Description"].sum(),
            ],
        }
    )
    flags["% of items"] = (flags["Items"] / max(len(perf_f), 1) * 100).round(1)
    fig = px.bar(flags, x="Flag", y="% of items", text="% of items", title="Menu hygiene (% of items)")
    fig.update_traces(marker_color=COLOR, textposition="outside")
    c5.plotly_chart(fig, width="stretch")

    disc = perf_f[perf_f["Salt Flag"] == 1].nlargest(top_n, "Salt Discount").sort_values("Salt Discount")
    fig = px.bar(
        disc,
        x="Salt Discount",
        y="Item_names",
        orientation="h",
        title="Biggest salt discounts (₹ per item)",
    )
    fig.update_traces(marker_color="#C0392B")
    fig.update_layout(yaxis_title=None)
    c6.plotly_chart(fig, width="stretch")
    takeaways("Performance", ins.overview(perf_f))

# --------------------------------------------------------------------------
# TAB 2: FUNNEL
# --------------------------------------------------------------------------
with tab_funnel:
    section(2, "Conversion Funnel", "Impressions → cart makes → orders, by item")
    tot_imp = funnel["Impressions"].sum()
    tot_cart = funnel["Cart Makes"].sum()
    tot_ord = funnel["Total Orders"].sum()

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Impressions", f"{tot_imp:,}")
    f2.metric("Cart makes", f"{tot_cart:,}", f"I2C {tot_cart / tot_imp * 100:.1f}%")
    f3.metric("Orders", f"{tot_ord:,}", f"C2O {tot_ord / tot_cart * 100:.1f}%")
    f4.metric("Overall I2O", f"{tot_ord / tot_imp * 100:.2f}%")

    _, c1, _ = st.columns([1, 2, 1])
    fig = go.Figure(
        go.Funnel(
            y=["Impressions", "Cart Makes", "Orders"],
            x=[tot_imp, tot_cart, tot_ord],
            marker={"color": ["#D2B48C", "#A0522D", COLOR]},
            textinfo="value+percent initial",
        )
    )
    fig.update_layout(title="Overall funnel")
    c1.plotly_chart(fig, width="stretch")

    min_imp = 500  # items with at least this many impressions in the charts below
    ff = funnel[funnel["Impressions"] >= min_imp]

    c3, c4 = st.columns(2)
    low_i2o = ff.nlargest(top_n, "Impressions").sort_values("I2O").head(top_n)
    fig = px.bar(
        low_i2o.sort_values("I2O", ascending=False),
        x="I2O",
        y="Item_names",
        orientation="h",
        title=f"Lowest I2O among top-{top_n}-impression items",
    )
    fig.update_traces(marker_color="#C0392B")
    fig.update_layout(yaxis_title=None)
    c3.plotly_chart(fig, width="stretch")

    high_i2o = ff.nlargest(top_n, "I2O").sort_values("I2O")
    fig = px.bar(high_i2o, x="I2O", y="Item_names", orientation="h", title=f"Top {top_n} items by I2O")
    fig.update_traces(marker_color="#27AE60")
    fig.update_layout(yaxis_title=None)
    c4.plotly_chart(fig, width="stretch")

    st.subheader("Items with high impressions but poor rating")
    risky = funnel[(funnel["Impressions"] >= funnel["Impressions"].median()) & (funnel["Item Rating"] < 3.5)]
    st.dataframe(
        risky.sort_values("Impressions", ascending=False),
        width="stretch",
        hide_index=True,
    )
    takeaways("Funnel", ins.funnel(funnel))

# --------------------------------------------------------------------------
# TAB 3: ORS / ISSUES
# --------------------------------------------------------------------------
with tab_quality:
    section(3, "Order Issues (ORS)", "What goes wrong after the order is placed")
    issue_cols = [
        "Missing Item Issue",
        "Poor Packaging Issue",
        "Item not delivered Issue",
        "Poor Quality Issue",
        "Wrong Order Issue",
        "Cancellation Issues",
        "WIMO Issue",
    ]
    issue_cols = [c for c in issue_cols if c in ors.columns]
    totals = ors[issue_cols].sum().reset_index()
    totals.columns = ["Issue type", "Count"]
    totals = totals[totals["Count"] > 0]

    q1, q2, q3 = st.columns(3)
    q1.metric("Total issues", f"{int(ors['Total Issues'].sum())}")
    q2.metric("Items with issues", f"{int((ors['Total Issues'] > 0).sum())}")
    q3.metric("Overall ORS %", f"{ors['Total Issues'].sum() / funnel['Total Orders'].sum() * 100:.2f}%")

    c1, c2 = st.columns(2)
    fig = px.pie(totals, names="Issue type", values="Count", hole=0.4, title="Issue type split")
    c1.plotly_chart(fig, width="stretch")

    top_issue = ors.nlargest(top_n, "Total Issues").sort_values("Total Issues")
    fig = px.bar(
        top_issue,
        x="Total Issues",
        y="Item_names",
        orientation="h",
        title=f"Top {top_n} items by number of issues",
    )
    fig.update_traces(marker_color="#C0392B")
    fig.update_layout(yaxis_title=None)
    c2.plotly_chart(fig, width="stretch")

    st.subheader("Highest ORS % (items with at least N issues)")
    min_issues = st.slider("Minimum issues", 1, int(ors["Total Issues"].max()), 2)
    hi = ors[ors["Total Issues"] >= min_issues].nlargest(top_n, "ORS %").sort_values("ORS %")
    fig = px.bar(hi, x="ORS %", y="Item_names", orientation="h", text="ORS %")
    fig.update_layout(yaxis_title=None)
    fig.update_traces(marker_color=COLOR)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Issue breakdown by item")
    stack = ors.nlargest(top_n, "Total Issues").melt(
        id_vars="Item_names", value_vars=issue_cols, var_name="Issue", value_name="Count"
    )
    stack = stack[stack["Count"] > 0]
    fig = px.bar(stack, x="Item_names", y="Count", color="Issue", barmode="stack")
    fig.update_layout(xaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    takeaways("Order Issues", ins.ors(ors))

# --------------------------------------------------------------------------
# TAB 4: SEARCHES & S2O
# --------------------------------------------------------------------------
with tab_search:
    section(4, "Searches & S2O", "What customers look for and cannot find")
    ns = data["null_search"].sort_values("searches", ascending=False)
    s2o = data["s2o_menu"]  # only dishes that fit a bakery & coffee menu

    c1, c2 = st.columns(2)

    c1.subheader("Null searches (customers searched, no result)")
    c1.metric("Unique null search terms", f"{len(ns):,}")
    fig = px.bar(
        ns.head(top_n * 2).sort_values("searches"),
        x="searches",
        y="search_term",
        orientation="h",
        title="Most frequent null searches = menu gaps",
    )
    fig.update_traces(marker_color=COLOR)
    fig.update_layout(yaxis_title=None)
    fig.update_yaxes(dtick=1)  # label every bar
    c1.plotly_chart(fig, width="stretch")
    term = c1.text_input("Search within null terms")
    shown = ns[ns["search_term"].astype(str).str.contains(term, case=False, na=False)] if term else ns
    c1.dataframe(shown[["search_term", "searches"]], width="stretch", hide_index=True, height=250)

    c2.subheader("Search-to-order (S2O) by dish for the zone")
    c2.metric("Avg S2O", f"{s2o['S2O'].mean():.3f}")
    fig = px.bar(
        s2o.nlargest(top_n * 2, "S2O").sort_values("S2O"),
        x="S2O",
        y="dish_name",
        orientation="h",
        title="Bakery & café dishes with the highest S2O in zone",
    )
    fig.update_traces(marker_color="#27AE60")
    fig.update_layout(yaxis_title=None)
    fig.update_yaxes(dtick=1)  # label every bar
    c2.plotly_chart(fig, width="stretch")
    fig = px.histogram(s2o, x="S2O", nbins=25, title="S2O distribution")
    fig.update_traces(marker_color=COLOR)
    c2.plotly_chart(fig, width="stretch")
    takeaways("Search Demand", ins.search(data["null_search"], s2o))

# --------------------------------------------------------------------------
# TAB 5: CDO
# --------------------------------------------------------------------------
with tab_cdo:
    section(5, "Cross-Dish Orders", "What your customers order from other restaurants")
    cdo, cdo_sum, least = data["cdo"], data["cdo_sum"], least_f

    st.caption(
        "CDO = items customers ordered from *other* restaurants alongside/around Mr. Brown "
        f"({cdo['start_date'].min():%d %b %Y} → {cdo['end_date'].max():%d %b %Y})."
    )

    c1, c2 = st.columns(2)
    fig = px.bar(
        cdo_sum.nlargest(top_n * 2, "SUM of total_orders_for_item").sort_values("SUM of total_orders_for_item"),
        x="SUM of total_orders_for_item",
        y="item_ordered",
        orientation="h",
        title="Items most ordered elsewhere by our customers",
    )
    fig.update_traces(marker_color=COLOR)
    fig.update_layout(yaxis_title=None, xaxis_title="Orders")
    c1.plotly_chart(fig, width="stretch")

    # Group similar items by simple keyword to see themes
    # Same theme definitions as the takeaways, so the chart and the text agree
    th = ins._theme_totals(cdo_sum, "item_ordered", "SUM of total_orders_for_item")
    theme = pd.DataFrame([{"Theme": k, "Orders": v[0]} for k, v in th.items()]).sort_values("Orders", ascending=False)
    fig = px.bar(theme, x="Theme", y="Orders", title="Demand themes in CDO (keyword match)")
    fig.update_traces(marker_color="#A0522D")
    c2.plotly_chart(fig, width="stretch")

    st.subheader("Least ordered items on our menu")
    st.dataframe(
        least.rename(columns={"Item_names": "Item"}),
        width="stretch",
        hide_index=True,
        column_config={"Total Orders": st.column_config.NumberColumn("Total Orders", width="small")},
    )
    takeaways("Cross-Dish Demand", ins.cdo(cdo_sum, perf_f, least))

# --------------------------------------------------------------------------
# TAB 6: MENU ADDITIONS (from Dish_recommendations sheet)
# --------------------------------------------------------------------------
with tab_rec:
    section(6, "Menu Additions", "Recommended dishes vs your current menu, with a suggested action for each")
    rec = data["rec"]
    if rec is None or rec.empty:
        st.info("No `Dish_recommendations` sheet found in the workbook.")
    else:
        sug = rec_mod.suggest(rec, combine_outlets(perf_raw), data["null_search"], data["cdo_sum"])
        summ = rec_mod.dish_summary(sug)

        outlets = sorted(sug["res_id"].unique())
        sel_out = st.multiselect("Outlets (res_id)", outlets, default=outlets)
        sug_f = sug[sug["res_id"].isin(sel_out)]
        summ_f = rec_mod.dish_summary(sug_f) if len(sug_f) else summ.iloc[0:0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Recommended dishes", len(summ_f))
        m2.metric("Not on menu", int((summ_f["menu_match"] == "Not on menu").sum()))
        m3.metric("Similar on menu (add variant)", int((summ_f["menu_match"] == "Similar on menu").sum()))
        m4.metric("Already on menu", int((summ_f["menu_match"] == "On menu").sum()))

        st.subheader("Dish-level summary (all selected outlets)")
        st.dataframe(
            summ_f.drop(columns=["best_rank", "signals"]).rename(columns={"dish_name": "Dish", "outlets": "Outlets recommending",
                                   "menu_match": "Menu match", "null_searches": "Null searches",
                                   "cdo_orders": "Orders elsewhere (CDO)", "action": "Suggested menu action"}),
            width="stretch", hide_index=True,
        )

        st.subheader("Recommended dishes - suggested menu action")
        cols = ["dish_name", "Suggested menu action"]
        rec_tbl = sug_f.drop_duplicates("dish_key")[cols].rename(columns={"dish_name": "Dish"})
        st.table(rec_tbl.set_index("Dish"))  # st.table wraps long text instead of cutting it off

        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            rec_tbl.to_excel(xw, sheet_name="Dish_recommendations", index=False)
            summ_f.drop(columns=["best_rank", "signals"]).to_excel(xw, sheet_name="Dish summary", index=False)
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Download as Excel", buf.getvalue(), file_name="dish_recommendations_with_actions.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        d2.download_button("⬇️ Download as CSV", rec_tbl.to_csv(index=False).encode("utf-8"),
                           file_name="dish_recommendations_with_actions.csv", mime="text/csv")

        add = summ_f[summ_f["menu_match"] != "On menu"]
        takeaways("Menu Additions", [
            f"<b>{len(add)} of {len(summ_f)}</b> recommended dishes are not fully on your menu - "
            f"{int((summ_f['menu_match'] == 'Not on menu').sum())} are completely new.",
            "<b>Top additions (most outlets recommending):</b> "
            + ", ".join(f"<b>{r.dish_name.title()}</b> ({r.outlets} outlets)" for r in add.sort_values("outlets", ascending=False).head(4).itertuples())
            + ".",
            "<b>Already listed:</b> " + (", ".join(f"<b>{x.title()}</b>" for x in summ_f[summ_f['menu_match'] == 'On menu']['dish_name'].head(4))
                                          or "none") + " - push visibility and ratings instead of adding duplicates.",
        ])

# --------------------------------------------------------------------------
# TAB 7: RAW DATA
# --------------------------------------------------------------------------
with tab_data:
    choice = st.selectbox(
        "Dataset",
        ["Item Performance (filtered)", "Item Funnel", "Item ORS", "Null Searches", "S2O", "CDO", "CDO Summary", "Least Ordered"] + (["Dish Recommendations"] if data["rec"] is not None else []),
    )
    mapping = {
        "Item Performance (filtered)": perf_f,
        "Item Funnel": funnel,
        "Item ORS": ors,
        "Null Searches": data["null_search"],
        "S2O": data["s2o"],
        "CDO": data["cdo"],
        "CDO Summary": data["cdo_sum"],
        "Least Ordered": least_f,
        "Dish Recommendations": data["rec"],
    }
    df_show = mapping[choice]
    st.dataframe(df_show, width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download as CSV",
        df_show.to_csv(index=False).encode("utf-8"),
        file_name=f"{choice.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )


with st.expander("Glossary"):
    st.markdown(
        """
- **I2C** - Impression to Cart: cart makes / impressions
- **C2O** - Cart to Order: orders / cart makes
- **I2O** - Impression to Order: orders / impressions (the menu-to-order, M2O, rate this dashboard aims to raise)
- **S2O** - Search to Order: share of searches for a dish that end in an order
- **ORS %** - Order Rating Score issues: share of an item's orders that had an issue
- **Null search** - a search that returned no result
- **CDO** - Cross Dish Ordering: items your customers ordered from other restaurants
- **Salt discount** - discount applied on an item's price (Salt Flag = 1)
- **Visibility %** - how often the item was shown to customers
"""
    )

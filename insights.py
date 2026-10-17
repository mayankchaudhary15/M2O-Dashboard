"""Data-driven 'Key takeaways' for the Mr. Brown dashboard.
Every sentence is computed from the data, so it updates with the filters."""

import pandas as pd

# Keywords match at the start of a word, so "cake" does not catch pancake / cupcake
THEMES = {
    "Cake": ["cake", "cheesecake"], "Pizza": ["pizza"], "Burger": ["burger"], "Sandwich": ["sandwich"],
    "Puff / Patty / Samosa": ["puff", "patty", "patties", "samosa"],
    "Pastry / Cream roll": ["pastry", "pastries", "cream roll", "creamroll", "cr roll", "crroll"],
    "Donut": ["donut", "doughnut"], "Cookie": ["cookie", "biscuit"],
    "Coffee / Shake": ["coffee", "shake", "tea"], "Bread / Bun": ["bread", "bun", "pav"],
    "Pasta / Wrap": ["pasta", "wrap", "noodle", "kathi roll", "frankie"],
}


def _std(df):
    """Accept either 'item_names' or 'Item_names' from the workbook."""
    return df.rename(columns={"item_names": "Item_names"}) if hasattr(df, "rename") else df


def _names(s, n=3):
    return ", ".join(f"<b>{x}</b>" for x in list(s)[:n])


def _theme_totals(df, name_col, val_col=None):
    out = {}
    for t, kws in THEMES.items():
        m = df[name_col].astype(str).str.contains(r"\b(?:" + "|".join(kws) + ")", case=False, na=False, regex=True)
        out[t] = (df.loc[m, val_col].sum() if val_col else 0, int(m.sum()))
    return out


def overview(perf):
    perf = _std(perf)
    if perf.empty:
        return ["No items match the current filters."]
    tot = perf["Total Revenue"].sum()
    top1 = perf.nlargest(1, "Total Revenue").iloc[0]
    top5 = perf.nlargest(5, "Total Revenue")["Total Revenue"].sum() / tot * 100
    cat = perf.groupby("Item Category")["Total Revenue"].sum().sort_values(ascending=False)
    tail = (perf["Total Orders"] < 10).mean() * 100
    rated = perf["Item Rating"].dropna()  # 0 = unrated is already NaN (see app.load_data)
    hi_vis = perf[(perf["Visibility Percent"] >= 80) & (perf["Total Orders"] < perf["Total Orders"].median())]
    salt = perf[perf["Salt Flag"] == 1]
    spread = ("Revenue is well spread" if top5 < 40 else "Revenue is concentrated" if top5 >= 60
              else "Revenue is moderately concentrated")
    b = [
        f"<b>{spread}:</b> the top 5 items bring {top5:.0f}% of revenue; "
        f"<b>{top1['Item_names']}</b> leads with ₹{top1['Total Revenue']:,.0f} ({top1['Total Revenue'] / tot * 100:.1f}%).",
        f"<b>{cat.index[0]}</b> is the biggest category ({cat.iloc[0] / tot * 100:.0f}% of revenue)"
        + (f", followed by <b>{cat.index[1]}</b> ({cat.iloc[1] / tot * 100:.0f}%)." if len(cat) > 1 else "."),
        f"<b>Long tail:</b> {tail:.0f}% of listed items have fewer than 10 orders - candidates to fix, bundle or delist.",
        f"<b>Ratings:</b> {len(rated)} of {len(perf)} items have a rating"
        + (f" (avg {rated.mean():.2f}); " if len(rated) else "; ")
        + f"{perf['Item Rating'].isna().mean() * 100:.0f}% have none yet"
        + (" - low rating coverage." if perf["Item Rating"].isna().mean() > 0.3 else "."),
    ]
    if len(hi_vis):
        b.append(f"<b>Visible but not selling:</b> {len(hi_vis)} items have 80%+ visibility yet below-median orders "
                 f"(e.g. {_names(hi_vis.nlargest(3, 'Visibility Percent')['Item_names'])}) - review price, photo, description.")
    if len(salt):
        b.append(f"<b>Salt discount</b> is applied on {len(salt)} items (avg ₹{salt['Salt Discount'].mean():,.0f} off); "
                 f"{(1 - perf['Has Image'].mean()) * 100:.0f}% of items still lack an image.")
    return b


def funnel(f):
    f = _std(f)
    imp, cart, orders = f["Impressions"].sum(), f["Cart Makes"].sum(), f["Total Orders"].sum()
    top = f.nlargest(20, "Impressions")
    leak = top.nsmallest(3, "I2C")
    gems = f[(f["I2O"] >= f["I2O"].quantile(0.75)) & (f["Impressions"] < f["Impressions"].median())]
    risk = f[(f["Impressions"] >= f["Impressions"].median()) & (f["Item Rating"] < 3)]
    lost = (f["Cart Makes"] - f["Total Orders"]).sort_values(ascending=False)
    drop_i2c, drop_c2o = 1 - cart / imp, 1 - orders / cart
    stage = "impression → cart" if drop_i2c >= drop_c2o else "cart → order"
    b = [
        f"<b>Overall funnel:</b> {imp:,} impressions → {cart:,} cart makes (I2C {cart / imp * 100:.1f}%) → "
        f"{orders:,} orders (C2O {orders / cart * 100:.0f}%). The biggest drop is at <b>{stage}</b> "
        f"({max(drop_i2c, drop_c2o) * 100:.0f}% lost).",
        f"<b>Weak I2C among top-20 impression items:</b> {_names(leak['Item_names'])} "
        f"({', '.join(f'{v:.1f}%' for v in leak['I2C'])}) - lots of eyeballs, few add-to-carts.",
    ]
    if len(gems):
        b.append(f"<b>Hidden gems:</b> {_names(gems.nlargest(3, 'I2O')['Item_names'])} convert in the top quartile "
                 f"but get below-median impressions - push visibility / ads here.")
    if len(risk):
        b.append(f"<b>Rating risk:</b> {_names(risk.nlargest(3, 'Impressions')['Item_names'])} get high impressions "
                 f"but rate under 3.0 - fix quality before spending more on visibility.")
    li = f.loc[lost.index[0]]
    b.append(f"<b>Largest cart drop-off:</b> <b>{li['Item_names']}</b> - {int(lost.iloc[0])} carts did not become orders.")
    return b


def ors(o):
    o = _std(o)
    cols = ["Missing Item Issue", "Poor Packaging Issue", "Item not delivered Issue",
            "Poor Quality Issue", "Wrong Order Issue", "Cancellation Issues", "WIMO Issue"]
    cols = [c for c in cols if c in o.columns]
    t = o[cols].sum().sort_values(ascending=False)
    tot = int(o["Total Issues"].sum())
    if tot == 0:
        return ["No order issues recorded."]
    top = o.nlargest(1, "Total Issues").iloc[0]
    hi = o[o["Total Issues"] >= 3].nlargest(3, "ORS %")
    b = [
        f"<b>{tot} issues</b> across {int((o['Total Issues'] > 0).sum())} items. "
        f"<b>{t.index[0].replace(' Issue', '')}</b> ({t.iloc[0] / tot * 100:.0f}%) and "
        f"<b>{t.index[1].replace(' Issue', '')}</b> ({t.iloc[1] / tot * 100:.0f}%) make up most of them.",
        f"<b>{top['Item_names']}</b> has the most issues ({int(top['Total Issues'])}), "
        + (f"though its ORS is only {top['ORS %']:.2f}% because of high volume."
           if top["ORS %"] <= o.loc[o["Total Issues"] > 0, "ORS %"].median() else f"and an ORS of {top['ORS %']:.2f}%."),
    ]
    if len(hi):
        b.append(f"<b>High ORS % (3+ issues):</b> {_names(hi['Item_names'])} "
                 f"({', '.join(f'{v:.1f}%' for v in hi['ORS %'])}) - check packing and prep for these.")
    top2 = " and ".join(i.replace(" Issue", "").replace(" Issues", "").lower() for i in t.index[:2])
    b.append(f"<b>Where to focus:</b> {top2} issues are {(t.iloc[0] + t.iloc[1]) / tot * 100:.0f}% "
             "of the total - fixing these two covers most complaints.")
    return b


def search(ns, s2o):
    ns = ns[ns["search_term"].astype(str).str.strip() != ""]
    top = ns.sort_values("searches", ascending=False)
    th = _theme_totals(ns, "search_term", "searches")
    th = sorted(((k, v[0]) for k, v in th.items() if v[0] > 0), key=lambda x: -x[1])
    b = [f"<b>{len(ns)} unique null-search terms</b> ({int(ns['searches'].sum())} searches) - customers looked for "
         f"something and found nothing."]
    if len(top):
        b.append(f"<b>Most repeated:</b> {_names(top['search_term'], 5)}.")
    if th:
        b.append("<b>Themes in null searches:</b> " + ", ".join(f"<b>{k}</b> ({int(v)})" for k, v in th[:4])
                 + " - strongest signals for menu additions or better search keywords / tags.")
    short = ns[ns["search_term"].astype(str).str.fullmatch(r"[a-z]{3,4}")]["search_term"].head(2).tolist()
    if short:
        b.append(f"<b>Partial / misspelled searches</b> (e.g. {', '.join(repr(x) for x in short)}) show search needs "
                 "fuzzy matching - add alt names to item titles.")
    hi = s2o[s2o["S2O"] >= 0.3]
    b.append(f"<b>Zone S2O:</b> {len(hi)} dishes convert at 0.30+ (top: {_names(s2o.nlargest(3, 'S2O')['dish_name'])}) - "
             "check which of these fit a bakery menu.")
    return b


def cdo(cdo_sum, perf, least):
    perf, least = _std(perf), _std(least)
    cdo_th = _theme_totals(cdo_sum, "item_ordered", "SUM of total_orders_for_item")
    menu_th = _theme_totals(perf, "Item_names")
    rows = [(k, cdo_th[k][0], menu_th[k][1]) for k in THEMES if cdo_th[k][0] > 0]
    rows.sort(key=lambda r: -r[1])
    top = cdo_sum.nlargest(3, "SUM of total_orders_for_item")
    b = [f"<b>Customers order elsewhere:</b> {_names(top['item_ordered'])} "
         f"({', '.join(str(int(v)) for v in top['SUM of total_orders_for_item'])} orders)."]
    for k, orders, n_menu in rows[:3]:
        b.append(f"<b>{k}:</b> {int(orders)} orders on other restaurants vs {n_menu} items on your menu - "
                 + ("review depth, price and visibility." if n_menu else "a gap worth filling."))
    z = least[least["Total Orders"] == 0]
    if len(z):
        b.append(f"<b>{len(z)} items with 0 orders</b> ({_names(z['Item_names'], 3)}...) - refresh photo / price or delist.")
    return b


def _rates(items):
    imp, cart, orders = items["Impressions"].sum(), items["Cart Makes"].sum(), items["Total Orders"].sum()
    return imp, cart, orders, (cart / imp * 100 if imp else 0), (orders / cart * 100 if cart else 0), (orders / imp * 100 if imp else 0)


def _gems(items):
    """Low-visibility items that already convert above the median: more visibility = more orders."""
    seen = items[items["Impressions"] >= 50]
    return seen[(seen["Visibility Percent"] <= seen["Visibility Percent"].quantile(0.25))
                & (seen["I2O"] >= seen["I2O"].median())].sort_values("I2O", ascending=False)


def _leaks(items, i2c):
    """Most-viewed items whose view -> cart rate is below the menu average."""
    return items.nlargest(20, "Impressions").query("I2C < @i2c").sort_values("Impressions", ascending=False)


def m2o(items, cdo_tbl, ns):
    """Menu-to-order takeaways for the Summary tab. Every point is an action that turns menu views into orders."""
    if items.empty:
        return ["No items match the current filters."]
    imp, cart, orders, i2c, c2o, i2o = _rates(items)
    drop_view, drop_cart = 100 - i2c, 100 - c2o
    b = [f"<b>Menu to order (M2O) is {i2o:.1f}%:</b> of every 100 menu views, {i2o:.1f} become orders. "
         + (f"Most customers drop off <b>before adding to cart</b> ({drop_view:.0f}% of views), so the menu listing "
            "itself (photo, name, price, position) is the main lever." if drop_view >= drop_cart else
            f"Most customers drop off <b>after adding to cart</b> ({drop_cart:.0f}% of carts), so check price, "
            "add-on cost and delivery time.")]
    gems = _gems(items)
    if len(gems):
        b.append(f"<b>Raise visibility on proven converters:</b> {len(gems)} items sit in the lowest quarter for "
                 f"visibility but convert above the median, e.g. {_names(gems['Item_names'])} "
                 f"(I2O {', '.join(f'{v:.1f}%' for v in gems['I2O'].head(3))}). Move them up the menu or into a "
                 "recommended / bestseller section.")
    leaks = _leaks(items, i2c)
    if len(leaks):
        b.append(f"<b>Fix the most-viewed items that don't get added:</b> {_names(leaks['Item_names'])} get the most "
                 f"views but convert to cart below the {i2c:.1f}% average "
                 f"({', '.join(f'{v:.1f}%' for v in leaks['I2C'].head(3))}). Refresh the photo, name and price.")
    if items["Has Image"].between(0, 1).all() and (items["Has Image"] == 0).any():
        w = items[items["Has Image"] == 1]; wo = items[items["Has Image"] == 0]
        i2c_w, i2c_wo = _rates(w)[3], _rates(wo)[3]
        if i2c_w > i2c_wo:
            b.append(f"<b>Add photos:</b> items with a photo convert to cart at {i2c_w:.1f}% vs {i2c_wo:.1f}% without. "
                     f"{len(wo)} items have no photo.")
    if cdo_tbl is not None and len(cdo_tbl):
        gap = cdo_tbl[cdo_tbl["On our menu"] == "Not on menu"].head(3)
        have = cdo_tbl[cdo_tbl["On our menu"] != "Not on menu"].head(3)
        if len(gap):
            b.append(f"<b>Add what customers buy elsewhere:</b> {_names(gap['Item'])} "
                     f"({', '.join(str(int(v)) for v in gap['Orders elsewhere'])} orders at other restaurants) are not on "
                     "the menu.")
        if len(have):
            b.append(f"<b>Win back orders you already can serve:</b> customers order {_names(have['Item'])} elsewhere "
                     "although you list them. Push these in visibility, combos or offers.")
    ns = ns[ns["search_term"].astype(str).str.strip() != ""].sort_values("searches", ascending=False)
    if len(ns):
        b.append(f"<b>Turn failed searches into orders:</b> {_names(ns['search_term'], 4)} returned nothing. Add these "
                 "words to item names / tags, or add the item.")
    return b


def summary(items, o, ns, cdo_tbl):
    """Wins / Concerns / Opportunities / Actions, all framed around menu-to-order conversion."""
    imp, cart, orders, i2c, c2o, i2o = _rates(items)
    seen = items[items["Impressions"] >= 200]
    best = seen.nlargest(3, "I2O")
    gems, leaks = _gems(items), _leaks(items, i2c)
    no_img = int((items["Has Image"] == 0).sum())
    cols = [c for c in o.columns if c.endswith(("Issue", "Issues")) and c != "Total Issues"]
    issues = o[cols].sum().sort_values(ascending=False)
    top_issues = [i.replace(" Issues", "").replace(" Issue", "").lower() for i in issues.index[:2]]
    gap = cdo_tbl[cdo_tbl["On our menu"] == "Not on menu"]["Item"].head(3).tolist() if cdo_tbl is not None else []
    ns_top = ns.sort_values("searches", ascending=False)["search_term"].head(3).tolist()

    actions = []
    if len(gems):
        actions.append(f"Move {len(gems)} low-visibility, high-converting items up the menu.")
    if len(leaks):
        actions.append(f"Refresh photo, name and price for the {len(leaks)} most-viewed items with below-average I2C.")
    if no_img:
        actions.append(f"Add photos to the {no_img} items without one.")
    if gap:
        actions.append(f"Add items customers buy elsewhere ({', '.join(gap)}).")
    if ns_top:
        actions.append(f"Add search words for {', '.join(ns_top)}.")
    actions.append(f"Fix {' and '.join(top_issues)} issues so repeat customers keep converting.")
    return {
        "🎯 Wins": (
            f"M2O is {i2o:.1f}% ({orders:,} orders from {imp:,} menu views). "
            + (f"Best converters with real traffic: {_names(best['Item_names'])} "
               f"({', '.join(f'{v:.1f}%' for v in best['I2O'])} I2O). " if len(best) else "")
            + f"Once in the cart, {c2o:.0f}% of items are ordered."),
        "⚠️ Concerns": (
            f"Only {i2c:.1f}% of menu views lead to an add-to-cart, so {100 - i2c:.0f}% of views are lost at the listing. "
            + (f"{len(leaks)} of the 20 most-viewed items convert below average. " if len(leaks) else "")
            + (f"{no_img} items have no photo." if no_img else "")),
        "💡 Opportunities": (
            (f"{len(gems)} items convert well but are hard to find ({_names(gems['Item_names'], 2)}). " if len(gems) else "")
            + (f"Customers buy {', '.join(gap)} elsewhere. " if gap else "")
            + (f"Failed searches: {', '.join(ns_top)}." if ns_top else "")),
        "🔧 Action items": actions,  # list, rendered as a numbered list
    }

"""Match recommended dishes against the current menu and build a 'Suggested menu action' column."""

import re

import pandas as pd

SYN = {"choco": "chocolate", "donut": "doughnut", "cheesecake": "cheese cake", "patties": "patty"}
STOP = {"cake", "the", "and", "of", "with", "box", "pc", "pcs", "g", "gm", "eggless"}


def _words(text):
    t = re.sub(r"[^a-z0-9 ]", " ", str(text).lower())
    for a, b in SYN.items():
        t = re.sub(rf"\b{a}\b", b, t)
    out = []
    for w in t.split():
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.append(w)
    return out


def _tokens(text):
    return set(_words(text))


def _key(d):
    k = d - STOP
    return k or d


# 'X cake' / 'X puff' / 'X tea' / 'X sandwich' is usually a different product from other items with
# that word (e.g. aloo puff vs Jeera Puff 200g biscuits, bubble tea vs Tea Cake), so these need a
# flavour word in common before they count as "Similar on menu"
GENERIC_HEADS = {"cake", "puff", "tea", "sandwich"}


def build_menu_index(perf):
    perf = perf.rename(columns={"item_names": "Item_names"})  # accept either spelling
    m = perf[["Item_names", "Total Orders"]].copy()
    m["tok"] = m["Item_names"].map(_tokens)
    return m


def match_dish(dish, menu):
    """Return (status, matched_items, orders_of_matches).
    On menu         : every word of the dish appears in one menu item.
    Similar on menu : the dish type (last word, e.g. sandwich/doughnut) is sold, but not this flavour -> add a variant.
    Not on menu     : the dish type itself is not sold."""
    words = _words(dish)
    d = set(words)
    full = menu[menu["tok"].map(lambda t: d <= t)]
    if len(full):
        top = full.nlargest(2, "Total Orders")
        return "On menu", list(top["Item_names"].unique()), int(full["Total Orders"].sum())
    head = words[-1]
    cand = menu[menu["tok"].map(lambda t: head in t)]
    if not len(cand):
        return "Not on menu", [], 0
    mods = _key(d) - {head}
    cand = cand.assign(sc=cand["tok"].map(lambda t: len(mods & t)))
    if head in GENERIC_HEADS and cand["sc"].max() == 0:
        return "Not on menu", [], 0
    top = cand.sort_values(["sc", "Total Orders"], ascending=False).head(2)
    return "Similar on menu", list(top["Item_names"].unique()), int(top["Total Orders"].sum())


def _sum_matching(df, text_col, val_col, dish):
    # Use every word of the dish: dropping "cake" made "cheese cake" match cheese sandwiches / pizzas
    key = _tokens(dish)
    m = df[text_col].map(lambda s: key <= _tokens(s))
    return int(df.loc[m, val_col].sum())


def suggest(rec, perf, null_search, cdo_sum):
    """Add 'Menu match', evidence columns and the final 'Suggested menu action' column."""
    menu = build_menu_index(perf)
    ns = null_search.rename(columns={"search_term": "kw"})
    rows = {}
    for dish in rec["dish_name"].unique():
        status, items, orders = match_dish(dish, menu)
        rows[dish] = (
            status,
            ", ".join(items),
            _sum_matching(ns, "kw", "searches", dish),
            _sum_matching(cdo_sum, "item_ordered", "SUM of total_orders_for_item", dish),
            orders,
        )
    out = rec.copy()
    out["dish_key"] = out["dish_name"].map(lambda d: " ".join(_words(d)))  # "choco waffles" == "chocolate waffles"
    out["Menu match"] = out["dish_name"].map(lambda d: rows[d][0])
    out["Similar menu items"] = out["dish_name"].map(lambda d: rows[d][1])
    out["Null searches"] = out["dish_name"].map(lambda d: rows[d][2])
    out["Orders elsewhere (CDO)"] = out["dish_name"].map(lambda d: rows[d][3])

    def action(r):
        d = r["dish_name"].title()
        ev = []
        if r["Null searches"]:
            ev.append(f"{r['Null searches']} null searches")
        if r["Orders elsewhere (CDO)"]:
            ev.append(f"{r['Orders elsewhere (CDO)']} orders on other restaurants")
        ev = f" ({'; '.join(ev)})" if ev else ""
        if r["Menu match"] == "Not on menu":
            return f"ADD '{d}' to menu{ev} - not listed today"
        if r["Menu match"] == "Similar on menu":
            return f"ADD '{d}' as a new variant{ev} - closest on menu: {r['Similar menu items']}"
        return f"ALREADY LISTED ({r['Similar menu items']}){ev} - improve visibility / photo / rating"

    out["Suggested menu action"] = out.apply(action, axis=1)
    return out


def dish_summary(sug):
    g = sug.groupby("dish_key", as_index=False).agg(
        dish_name=("dish_name", "first"), outlets=("res_id", "nunique"), best_rank=("rnk", "min"),
        signals=("signal", lambda s: "/".join(sorted(set(s)))),
        menu_match=("Menu match", "first"), null_searches=("Null searches", "first"),
        cdo_orders=("Orders elsewhere (CDO)", "first"), action=("Suggested menu action", "first"),
    )
    order = {"Not on menu": 0, "Similar on menu": 1, "On menu": 2}
    g["_o"] = g["menu_match"].map(order)
    return g.sort_values(["_o", "outlets", "best_rank"], ascending=[True, False, True]).drop(columns=["_o", "dish_key"])

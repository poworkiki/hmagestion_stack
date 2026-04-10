# Marimo Gallery — Templates de reference

Source : https://github.com/marimo-team/gallery-examples

Dernier fetch : 2026-04-10

---

## Table des matieres

1. [Pattern Dashboard — Movies (KPI + filtres dates + graphiques reactifs)](#1-dashboard-movies)
2. [Pattern Dashboard — Lego (sidebar filtres + multiselect + altair interactif)](#2-dashboard-lego)
3. [Pattern Dashboard — World of Warcraft (slider reactif + pipeline Polars + cache)](#3-dashboard-world-of-warcraft)
4. [Pattern Dashboard — Portfolio Tracker (data_editor + yfinance + Polars pipes)](#4-dashboard-portfolio-tracker)
5. [Pattern SQL — SQLite + DuckDB (cellules SQL natives + sqlalchemy)](#5-sql-sqlite-duckdb)
6. [Pattern SQL — F1 Driver Career Explorer (SQL parametrise + drilldown multi-niveaux)](#6-sql-f1-driver-career-explorer)
7. [Pattern SQL — MotherDuck (SQL reactif + UI elements + recherche)](#7-sql-motherduck)
8. [Pattern SQL — Interpolation (slider vers SQL reactif)](#8-sql-interpolation)
9. [Pattern Interactif — Altair Demo (brush selection + table + histogrammes)](#9-interactif-altair-demo)
10. [Pattern Exploration — Chemical Space Explorer (scatter matplotlib + table formatee)](#10-exploration-chemical-space-explorer)

---

## 1. Dashboard Movies

**Ce que ca demontre** : Dashboard complet avec KPI statistiques (mo.stat), comparaison periode precedente (taux de variation), filtres par dates, boutons rapides par decennie, graphique scatter interactif (altair_chart) avec selection qui met a jour des stats en dessous, et bar chart par genre.

**Patterns cles** :
- `mo.stat()` avec `caption` pour afficher les taux de variation
- `mo.state()` pour gerer l'etat des dates (get/set)
- `mo.ui.date()` connecte au state
- `mo.ui.altair_chart()` avec selection qui filtre les donnees
- `mo.hstack()` pour la mise en page horizontale des KPI
- `@app.function` pour les fonctions utilitaires reutilisables
- Comparaison automatique avec la periode precedente de meme duree

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "altair==6.0.0",
#     "marimo>=0.19.11",
#     "pandas==3.0.1",
#     "vega-datasets==0.9.0",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo
    import datetime
    import time
    import altair as alt
    import pandas as pd
    import vega_datasets as data


@app.cell
def _(button_00s, button_10s, button_80s, button_90s, end_date, start_date):
    _range = mo.md(f"{start_date} - {end_date}")

    mo.hstack(
        [
            _range,
            mo.hstack(
                [
                    mo.md("Quick decade:"),
                    button_80s,
                    button_90s,
                    button_00s,
                    button_10s,
                ]
            ),
        ]
    )
    return


@app.cell
def _(set_end_date, set_start_date):
    def decade_button(decade):
        s = pd.to_datetime(f"{decade}-01-01")
        e = pd.to_datetime(f"{decade + 10}-01-01")

        def handle_click(v):
            set_start_date(s)
            set_end_date(e)
            return 1

        return mo.ui.button(
            label=f"{decade}s",
            on_click=handle_click,
        )


    button_80s = decade_button(1980)
    button_90s = decade_button(1990)
    button_00s = decade_button(2000)
    button_10s = decade_button(2010)
    return button_00s, button_10s, button_80s, button_90s


@app.cell
def _(previous_end_date, previous_start_date):
    mo.md(f"""
    > Compared to: {previous_start_date.strftime("%Y-%m-%d")} - {previous_end_date.strftime("%Y-%m-%d")}
    """)
    return


@app.cell
def _(get_end_date, get_start_date, set_end_date, set_start_date):
    start_date = mo.ui.date(
        label="Start Date",
        value=get_start_date().strftime("%Y-%m-%d"),
        on_change=lambda x: set_start_date(pd.to_datetime(x)),
    )
    end_date = mo.ui.date(
        label="End Date",
        value=get_end_date().strftime("%Y-%m-%d"),
        on_change=lambda x: set_end_date(pd.to_datetime(x)),
    )
    return end_date, start_date


@app.cell
def _(filtered_movies, previous_movies):
    mo.stop(len(filtered_movies) == 0, "")

    previous_total_movies_count = len(previous_movies)
    previous_total_movies_change_rate = (
        (len(filtered_movies) - previous_total_movies_count)
        / previous_total_movies_count
        if previous_total_movies_count > 0
        else 0
    )
    total_movies = mo.stat(
        label="Total Movies",
        bordered=True,
        caption=f"{previous_total_movies_change_rate:.0%}",
        direction="increase"
        if previous_total_movies_change_rate > 0
        else "decrease",
        value=f"{len(filtered_movies):,.0f}",
    )

    gross_current, gross_previous, gross_rate = get_average_gross(
        filtered_movies, previous_movies
    )
    gross_stat = mo.stat(
        label="Average Gross",
        bordered=True,
        caption=f"{gross_rate:.0%}",
        direction="increase" if gross_rate > 0 else "decrease",
        value=f"${gross_current:,.0f}",
    )

    budget_current, budget_previous, budget_rate = get_average_budget(
        filtered_movies, previous_movies
    )
    budget_stat = mo.stat(
        label="Average Budget",
        bordered=True,
        caption=f"{budget_rate:.0%}",
        direction="increase" if budget_rate > 0 else "decrease",
        value=f"${budget_current:,.0f}",
    )

    runtime_current, runtime_previous, runtime_rate = get_average_runtime(
        filtered_movies, previous_movies
    )
    runtime_stat = mo.stat(
        label="Average Runtime",
        bordered=True,
        caption=f"{runtime_rate:.0%}",
        direction="increase" if runtime_rate > 0 else "decrease",
        value=f"{runtime_current:,.0f} min",
    )

    rating_current, rating_previous, rating_rate = get_average_rating(
        filtered_movies, previous_movies
    )
    average_rating = mo.stat(
        label="Average Rating",
        bordered=True,
        caption=f"{rating_rate:.0%}",
        direction="increase" if rating_rate > 0 else "decrease",
        value=f"{rating_current:.1f}",
    )

    mo.hstack(
        [total_movies, gross_stat, budget_stat, runtime_stat, average_rating],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(filtered_movies):
    mo.ui.table(filtered_movies, selection=None)
    return


@app.cell
def _(filtered_movies):
    # chart of rating by budget
    _chart = (
        alt.Chart(filtered_movies)
        .mark_circle()
        .encode(
            x="Production_Budget",
            y="IMDB_Rating",
            color="Major_Genre",
            tooltip=[
                "Title",
                "Production_Budget",
                "Worldwide_Gross",
                "IMDB_Rating",
                "Major_Genre",
            ],
        )
    )
    chart = mo.ui.altair_chart(_chart)
    chart
    return (chart,)


@app.cell
def _(chart):
    mo.stop(len(chart.value) == 0, mo.callout("Select data to view stats."))

    _total_movies = mo.stat(
        label="Total Movies",
        value=f"{len(chart.value):,.0f}",
    )

    _gross_current, _, _ = get_average_gross(chart.value, chart.value)
    _gross_stat = mo.stat(
        label="Average Gross",
        value=f"${_gross_current:,.0f}",
    )

    _budget_current, _, _ = get_average_budget(chart.value, chart.value)
    _budget_stat = mo.stat(
        label="Average Budget",
        value=f"${_budget_current:,.0f}",
    )

    _runtime_current, _, _ = get_average_runtime(chart.value, chart.value)
    _runtime_stat = mo.stat(
        label="Average Runtime",
        value=f"{_runtime_current:,.0f} min",
    )

    _rating_current, _, _ = get_average_rating(chart.value, chart.value)
    _average_rating = mo.stat(
        label="Average Rating",
        value=f"{_rating_current:.1f}",
    )

    mo.hstack(
        [_total_movies, _gross_stat, _budget_stat, _runtime_stat, _average_rating],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(filtered_movies):
    # chart of ratings by genre
    # colored by decade
    _bar_chart = (
        alt.Chart(filtered_movies)
        .mark_bar()
        .encode(
            x=alt.X("Major_Genre", sort="-y"),
            y="count()",
            color=alt.Color("Release_Date", scale=alt.Scale(scheme="viridis")),
            tooltip=["Major_Genre", "count()"],
        )
    )
    bar_chart = mo.ui.altair_chart(_bar_chart)
    bar_chart
    return


@app.function
def get_average_budget(df, previous):
    current = df["US_Gross"].mean()
    previous = previous["US_Gross"].mean()
    rate = (current - previous) / previous
    return (current, previous, rate)


@app.function
def get_average_gross(df, previous):
    current = df["Worldwide_Gross"].mean()
    previous = previous["Worldwide_Gross"].mean()
    rate = (current - previous) / previous
    return (current, previous, rate)


@app.function
def get_average_runtime(df, previous):
    current = df["Running_Time_min"].mean()
    previous = previous["Running_Time_min"].mean()
    rate = (current - previous) / previous
    return (current, previous, rate)


@app.function
def get_average_rating(df, previous):
    current = df["IMDB_Rating"].mean()
    previous = previous["IMDB_Rating"].mean()
    rate = (current - previous) / previous
    return (current, previous, rate)


@app.function
def get_previous_date_range(start_date, end_date):
    delta = end_date - start_date
    return (
        (start_date - datetime.timedelta(days=delta.days)),
        (end_date - datetime.timedelta(days=delta.days)),
    )


@app.function
def format_date(date):
    return date.strftime("%Y-%m-%d")


@app.cell
def _():
    movies = data.data.movies()

    # convert to date
    movies["Release_Date"] = pd.to_datetime(movies["Release_Date"])
    return (movies,)


@app.cell
def _():
    # min = movies["Release_Date"].min()
    # max = movies["Release_Date"].max()
    min = "2010-01-01"
    max = "2021-01-01"
    get_start_date, set_start_date = mo.state(pd.to_datetime(min))
    get_end_date, set_end_date = mo.state(pd.to_datetime(max))
    return get_end_date, get_start_date, set_end_date, set_start_date


@app.cell
def _(end_date, movies, start_date):
    start = pd.to_datetime(start_date.value)
    end = pd.to_datetime(end_date.value)
    filtered_movies = movies[
        (movies["Release_Date"] >= start) & (movies["Release_Date"] <= end)
    ]
    try:
        previous_start_date, previous_end_date = get_previous_date_range(
            start, end
        )
        previous_movies = movies[
            (movies["Release_Date"] >= previous_start_date)
            & (movies["Release_Date"] <= previous_end_date)
        ]
    except:
        previous_start_date = start
        previous_end_date = end
        previous_movies = filtered_movies
    return (
        filtered_movies,
        previous_end_date,
        previous_movies,
        previous_start_date,
    )


if __name__ == "__main__":
    app.run()
```

---

## 2. Dashboard Lego

**Ce que ca demontre** : Exploration de donnees avec multiselect pour filtrer par theme, KPI dynamiques (mo.stat), range sliders pour filtrer prix/prix par piece, dropdowns pour choisir les axes X/Y, checkbox pour overlay ligne de tendance (loess), et graphique Altair interactif avec selection qui affiche les details dans un tableau.

**Patterns cles** :
- `mo.ui.multiselect()` avec `max_selections` pour limiter les choix
- `mo.ui.range_slider()` avec bornes dynamiques calculees depuis les donnees
- `mo.ui.dropdown()` pour choisir les colonnes des axes
- `mo.ui.checkbox()` pour activer/desactiver des couches graphiques
- `mo.hstack()` + `mo.vstack()` pour la mise en page settings/chart
- `mo.ui.altair_chart()` dont `.value` retourne les points selectionnes
- Polars pour le filtrage et les transformations

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair",
#     "marimo",
#     "polars",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import altair as alt
    import polars as pl


@app.cell
def _():
    df = (
        pl.read_csv("https://raw.githubusercontent.com/marimo-team/gallery-examples/refs/heads/main/notebooks/dashboard/lego/lego_sets.csv")
        .filter(pl.col("category") == "Normal")
        .filter(~pl.col("US_retailPrice").is_null())
        .filter(pl.len().over(pl.col("theme")) >= 10)
    )
    return (df,)


@app.cell(hide_code=True)
def _(multi_select):
    mo.md(f"""
    # Exploring price differences in Lego sets

    Lego is well known for producing sets across a wide range of themes and price points. It's not just movie tie-ins like Star Wars or Harry Potter that are out there, we also have more generic themes like City or Technic.

    One might wonder, are there sets that are more expensive than other ones? Does it depend on the total number of pieces in the box? Or might a license fee also apply? 

    ## Select themes

    Start by selecting the lego themes that you want to explore first. 

    {multi_select}
    """)
    return


@app.cell
def _(final):
    mo.hstack(
        [
            mo.stat(caption="Average piece price", label=_["theme"], value=_["pieceprice"], bordered=True)
            for _ in final.group_by("theme").agg(pl.mean("pieceprice")).to_dicts()
        ], gap=1, justify="start"
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    These are the average prices per piece per theme. But you may want to dive a bit deeper.
    """)
    return


@app.cell
def _():
    checkbox = mo.ui.checkbox(label="Show line chart", value=False)
    check_inflation = mo.ui.checkbox(label="Assume inflation", value=False)
    return check_inflation, checkbox


@app.cell(hide_code=True)
def _(
    check_inflation,
    checkbox,
    date_range,
    pieceprice_range,
    price_range,
    xaxis,
    yaxis,
):
    mo.hstack([
        mo.vstack([
            mo.md("**Data Settings**"), 
            date_range, 
            price_range, 
            pieceprice_range
        ]), 
        mo.vstack([
            mo.md("**Chart Settings**"), 
            xaxis, 
            yaxis, 
            checkbox, 
            check_inflation
    ])])
    return


@app.cell
def _():
    date_range = mo.ui.range_slider(1970, 2022, 1, label="Year Range", value=[2001, 2022])
    return (date_range,)


@app.cell
def _(df):
    themes = df.group_by("theme").len()["theme"].to_list()

    multi_select = mo.ui.multiselect(
        themes, label="Select Themes", value=["Duplo", "Star Wars", "City"], max_selections=5
    )
    return (multi_select,)


@app.cell
def _(date_range):
    y1, y2 = date_range.value
    return y1, y2


@app.cell
def _(df, multi_select, y1, y2):
    subset = (
        df.filter(
            pl.col("year") >= y1, pl.col("year") <= y2, pl.col("theme").is_in(multi_select.value)
        )
        .rename(dict(US_retailPrice="price"))
        .with_columns(pl.col("price").cast(pl.Float64))
        .with_columns(inflation=pl.col("price") * 1.03**(pl.col("year") - 1970))
        .with_columns(pieceprice=pl.col("price") / pl.col("pieces"))
    )
    return (subset,)


@app.cell
def _(subset):
    max_price = subset.select(pl.col("price")).max()["price"].to_list()[0]
    max_piece_price = subset.select(pl.col("pieceprice")).max()["pieceprice"].to_list()[0]

    price_range = mo.ui.range_slider(0, max_price, label="Price Range", value=[0, 150])
    pieceprice_range = mo.ui.range_slider(0, max_piece_price, label="Piece Price Range", value=[0, 2])
    return pieceprice_range, price_range


@app.cell
def _():
    xaxis = mo.ui.dropdown(
        ["year", "pieces", "price", "pieceprice"], label="X-Axis", value="pieces"
    )
    yaxis = mo.ui.dropdown(["pieces", "price", "pieceprice"], label="Y-Axis", value="price")
    return xaxis, yaxis


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    The chart below is interactive and you can make selections in it to see each set in more detail
    """)
    return


@app.cell
def _(
    check_inflation,
    checkbox,
    pieceprice_range,
    price_range,
    subset,
    xaxis,
    yaxis,
):
    alt.renderers.set_embed_options(actions=False)

    final = subset.filter(
        pl.col("price") >= price_range.value[0], pl.col("price") <= price_range.value[1], 
        pl.col("pieceprice") >= pieceprice_range.value[0], pl.col("pieceprice") <= pieceprice_range.value[1]
    )

    if check_inflation.value:
        final = final.with_columns(
            price=pl.col("price") * pl.col("inflation"), 
            pieceprice=pl.col("pieceprice") * pl.col("inflation")
        )

    chart = alt.Chart(final).mark_point().encode(
        x=alt.X(xaxis.value).scale(zero=False), y=yaxis.value, color="theme"
    )

    if checkbox.value: 
        chart = alt.Chart(final).transform_loess(xaxis.value, yaxis.value, groupby=["theme"]).mark_line().encode(
            x=alt.X(xaxis.value).scale(zero=False), 
            y=yaxis.value, 
            color="theme"
        ) + chart.mark_point(opacity=0.2)

    mochart = mo.ui.altair_chart(chart)

    mochart
    return final, mochart


@app.cell
def _(mochart):
    mochart.value.select("set_id", "name", "theme", "imageURL")
    return


if __name__ == "__main__":
    app.run()
```

---

## 3. Dashboard World of Warcraft

**Ce que ca demontre** : Pipeline de transformation de donnees Polars avec fonctions chainables (`.pipe()`), slider reactif qui controle le seuil de detection de bots, cache via `@mo.cache` pour eviter les recalculs, et comparaison avant/apres nettoyage sur un line chart.

**Patterns cles** :
- `@app.function` pour definir des etapes de pipeline reutilisables
- `.pipe()` de Polars pour chainer les transformations
- `mo.ui.slider()` connecte directement au pipeline
- `@mo.cache` pour mettre en cache les resultats de fonctions couteuses
- Separation du pipeline en partie "fixe" (cached) et partie "variable" (dependante du slider)
- `mo.vstack()` pour combiner texte narratif + widget + graphique

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.7",
#     "altair",
#     "polars",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium", auto_download=["html"])

with app.setup:
    import marimo as mo
    import urllib.request
    import altair as alt
    import polars as pl


@app.cell(hide_code=True)
def _(chart, max_session_threshold):
    mo.vstack([
        mo.md(f"""
        ## Bot detection 

        For this work we use the [world of warcraft avatar dataset](https://github.com/koaning/wow-avatar-datasets). If we remove users that have had a session length that is too long then this has an effect on the number of users that we see over time. You can set the threshold below

        {max_session_threshold}

        And the chart below will update automatically
        """), 
        chart
    ])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Code appendix
    """)
    return


@app.cell
def _():
    path, _ = urllib.request.urlretrieve(
        "https://github.com/koaning/wow-avatar-datasets/raw/refs/heads/main/wow-full.parquet", 
        "wow-full.parquet"
    )
    return (path,)


@app.cell
def _(path):
    df = pl.read_parquet(path)
    return (df,)


@app.function(hide_code=True)
def set_types(dataf):
    return (dataf.with_columns([
                pl.col("guild").is_not_null(),
                pl.col("datetime").cast(pl.Int64).alias("timestamp")
            ]))


@app.function(hide_code=True)
def clean_data(dataf):
    return (
        dataf
        .filter(
            ~pl.col("class").is_in(["482", "Death Knight", "3485", "2400"]),
            pl.col("race").is_in(["Troll", "Orc", "Undead", "Tauren", "Blood Elf"])
        )
    )


@app.function(hide_code=True)
def sessionize(dataf, threshold=20 * 60 * 1000):
    return (dataf
             .sort(["player_id", "timestamp"])
             .with_columns(
                 (pl.col("timestamp").diff().cast(pl.Int64) > threshold).fill_null(True).alias("ts_diff"),
                 (pl.col("player_id").diff() != 0).fill_null(True).alias("char_diff"),
             )
             .with_columns(
                 (pl.col("ts_diff") | pl.col("char_diff")).alias("new_session_mark")
             )
             .with_columns(
                 pl.col("new_session_mark").cum_sum().alias("session")
             )
             .drop(["char_diff", "ts_diff", "new_session_mark"]))


@app.function(hide_code=True)
def add_features(dataf):
    return (dataf
             .with_columns(
                 pl.col("player_id").count().over("session").alias("session_length"),
                 pl.col("session").n_unique().over("player_id").alias("n_sessions_per_char")
             ))


@app.function(hide_code=True)
def remove_bots(dataf, max_session_hours=24):
    n_rows = max_session_hours * 6
    return (dataf
            .filter(pl.col("session_length").max().over("player_id") < n_rows))


@app.cell
def _(df):
    cached = (
        df
        .pipe(set_types)
        .pipe(clean_data)
        .pipe(sessionize, threshold=30 * 60 * 1000)
        .pipe(add_features)
    )
    return (cached,)


@app.cell
def _():
    max_session_threshold = mo.ui.slider(2, 24, 1, value=24, label="Max session length (hours)")
    return (max_session_threshold,)


@app.cell
def _(max_session_threshold, plot_per_date):
    chart = plot_per_date(max_session_threshold.value)
    return (chart,)


@app.cell(hide_code=True)
def _(cached, df, max_session_threshold):
    @mo.cache
    def plot_per_date(threshold):
        df_out = (
            cached.pipe(remove_bots, max_session_hours=max_session_threshold.value)
        )
        agg_orig = (
            df
            .with_columns(date=pl.col("datetime").dt.date())
            .group_by("date")
            .len()
            .with_columns(set=pl.lit("original"))
        )
        agg_clean = (
            df_out
            .with_columns(date=pl.col("datetime").dt.date())
            .group_by("date")
            .len()
            .with_columns(set=pl.lit("clean"))
        )
        return (
            pl.concat([agg_orig, agg_clean])
            .plot
            .line(x="date", y="len", color="set")
        )

    return (plot_per_date,)


if __name__ == "__main__":
    app.run()
```

---

## 4. Dashboard Portfolio Tracker

**Ce que ca demontre** : Saisie de donnees interactive avec `mo.ui.data_editor`, pipeline Polars avec fonctions chainables pour le calcul de performance de portefeuille, graphique Altair avec overlay (area + ligne pointillee), et donnees telechargeables.

**Patterns cles** :
- `mo.ui.data_editor()` pour permettre a l'utilisateur de saisir/modifier des donnees
- `@app.function` pour les etapes de pipeline (clean, calculate, chart)
- `.pipe()` Polars pour chainer les transformations
- Overlay Altair : `mark_area()` + `mark_line(strokeDash=...)` combines avec `+`
- `yfinance` pour les donnees boursieres en temps reel

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==6.0.0",
#     "diskcache==5.6.3",
#     "marimo",
#     "pandas==3.0.0",
#     "polars==1.37.1",
#     "yfinance==1.1.0",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(
    width="medium",
    css_file="/usr/local/_marimo/custom.css",
    auto_download=["html"],
)

with app.setup:
    import marimo as mo
    import altair as alt
    import pandas as pd
    import polars as pl
    import yfinance as yf
    from pathlib import Path


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Portfolio tracker

    Fill in your stock portfolio below and we will figure out how the value of your investment changes over time. We go back 72 months and use the `yfinance` SDK for the stock values.
    """)
    return


@app.cell
def _():
    investments = mo.ui.data_editor(
        pd.DataFrame(
            [
                {"Date": "2021-02-01", "Ticker": "msft", "Investment": 500},
                {"Date": "2023-02-01", "Ticker": "aapl", "Investment": 800},
                {"Date": "2024-02-01", "Ticker": "aapl", "Investment": 200},
            ]
        )
    )
    investments
    return (investments,)


@app.function(hide_code=True)
def clean_data(dataf, investment_records):
    investments_df = pl.DataFrame(investment_records)
    return (
        dataf.drop(["Dividends", "Stock Splits", "Volume"])
        .join(investments_df, on=["Date", "Ticker"], how="left")
        .with_columns(pl.col("Investment").fill_null(0))
        .sort("Ticker", "Date")
    )


@app.function(hide_code=True)
def calculate_portfolio_value(dataf):
    return (
        dataf.with_columns(
            CumInvestment=pl.col("Investment").cum_sum().over("Ticker")
        )
        .filter(pl.col("CumInvestment") > 0)
        .with_columns(
            SharesBought=pl.when(pl.col("Investment") > 0)
            .then(pl.col("Investment") / pl.col("Close"))
            .otherwise(0)
        )
        .with_columns(
            TotalShares=pl.col("SharesBought").cum_sum().over("Ticker")
        )
        .with_columns(
            PortfolioValue=pl.col("TotalShares") * pl.col("Close"),
            PnL=(pl.col("TotalShares") * pl.col("Close")) - pl.col("CumInvestment"),
        )
    )


@app.function(hide_code=True)
def calculate_performance(dataf):
    return (
        dataf.group_by("Date")
        .agg(
            [
                pl.sum("CumInvestment").alias("TotalInvested"),
                pl.sum("PortfolioValue").alias("TotalValue"),
                pl.sum("PnL").alias("TotalPnL"),
            ]
        )
        .with_columns(
            Date=pl.col("Date").str.to_date(),
            ReturnPct=((pl.col("TotalValue") / pl.col("TotalInvested")) - 1) * 100,
        )
        .sort("Date")
    )


@app.function(hide_code=True)
def make_chart(dataf):
    portfolio_chart = (
        alt.Chart(dataf)
        .mark_area(line=True, opacity=0.3)
        .encode(
            x=alt.X("Date:T", title="Date"),
            y=alt.Y("TotalValue:Q", title="Value ($)"),
        )
    )
    invested_line = (
        alt.Chart(dataf)
        .mark_line(strokeDash=[5, 5], color="black", strokeWidth=2)
        .encode(x="Date:T", y="TotalInvested:Q")
    )
    return portfolio_chart + invested_line


@app.cell(hide_code=True)
def _(parent_folder, records):
    cached = (
        pl.read_csv(f"{parent_folder}/*", glob=True)
        .pipe(clean_data, investment_records=records)
        .pipe(calculate_portfolio_value)
        .pipe(calculate_performance)
    )
    return (cached,)


@app.cell
def _(cached):
    cached.pipe(make_chart)
    return


@app.cell
def _(cached):
    cached.plot.line("Date", "ReturnPct")
    return


@app.cell
def _(investments):
    records = investments.value.assign(Ticker=lambda d: d["Ticker"].str.upper()).to_dict(
        orient="records"
    )
    return (records,)


@app.cell
def _(records):
    parent_folder = Path("invest-data")
    parent_folder.mkdir(exist_ok=True)

    def download_tickers(tickers):
        for record in tickers:
            ticker = record.upper()
            if not (parent_folder / f"{ticker}.csv").exists():
                (
                    yf.Ticker("MSFT")
                    .history(period="72mo")
                    .reset_index()
                    .assign(Date=lambda d: d["Date"].dt.strftime("%Y-%m-%d"), Ticker=ticker)
                    .to_csv(f"{parent_folder}/{ticker}.csv")
                )

    out = download_tickers(set(_["Ticker"] for _ in records))
    return (parent_folder,)


@app.cell
def _(cached):
    cached
    return


if __name__ == "__main__":
    app.run()
```

---

## 5. SQL SQLite + DuckDB

**Ce que ca demontre** : Connexion a une base SQLite via DuckDB (ATTACH) et via SQLAlchemy directement. Cellules SQL natives de Marimo avec `mo.sql()`. Le resultat d'une requete SQL est automatiquement disponible comme dataframe Python.

**Patterns cles** :
- `mo.sql()` pour executer du SQL directement dans une cellule
- `ATTACH` DuckDB pour monter une base SQLite
- `sqlalchemy.create_engine()` pour une connexion directe
- `engine=engine` dans `mo.sql()` pour utiliser un backend different de DuckDB
- Les resultats SQL sont des dataframes reutilisables en Python

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "duckdb==1.4.4",
#     "marimo",
#     "polars",
#     "pyarrow",
#     "requests==2.32.5",
#     "sqlalchemy==2.0.46",
#     "sqlglot==29.0.1",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Connect to SQLite

    You can use marimo's SQL cells to read from and write to SQLite databases.

    The first step is to attach a SQLite database. We attach to a sample database in a read-only mode below.

    For advanced usage, see [duckdb's documentation](https://duckdb.org/docs/extensions/sqlite).
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo


    def download_sample_data():
        import os
        import requests

        url = "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
        filename = "Chinook_Sqlite.sqlite"
        if not os.path.exists(filename):
            print("Downloading the Chinook database ...")
            response = requests.get(url)
            with open(filename, "wb") as f:
                f.write(response.content)


    downloaded = download_sample_data()
    return downloaded, mo


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Boilerplate: detach the database so this cell works when you re-run it
        DETACH DATABASE IF EXISTS chinook;

        -- Attach the database; omit READ_ONLY if you want to write to the database.
        ATTACH 'Chinook_Sqlite.sqlite' as chinook (TYPE SQLITE, READ_ONLY);

        -- This query lists all the tables in the Chinook database
        SELECT table_name FROM INFORMATION_SCHEMA.TABLES where table_catalog == 'chinook';
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT composer, MEAN(Milliseconds) as avg_track_ms from chinook.track GROUP BY composer ORDER BY avg_track_ms DESC;
        """
    )
    return


@app.cell
def _(downloaded):
    import sqlalchemy

    downloaded

    DATABASE_URL = "sqlite:///Chinook_Sqlite.sqlite"
    engine = sqlalchemy.create_engine(DATABASE_URL)
    return (engine,)


@app.cell
def _(engine, mo, track):
    _df = mo.sql(
        f"""
        SELECT composer, AVG(Milliseconds) as avg_track_ms 
        FROM Track 
        GROUP BY composer 
        ORDER BY avg_track_ms DESC;
        """,
        engine=engine
    )
    return


if __name__ == "__main__":
    app.run()
```

---

## 6. SQL F1 Driver Career Explorer

**Ce que ca demontre** : Application complete SQL + Python avec drilldown multi-niveaux. Dropdown de pilote qui filtre les constructeurs, selection de saison sur un bar chart qui declenche un drilldown vers les stats de course detaillees, onglets (tabs), et KPI cards.

**Patterns cles** :
- `mo.sql()` avec `output=False` pour executer du SQL sans afficher le resultat
- SQL parametrise avec des variables Python interpolees dans les f-strings
- `mo.ui.dropdown.from_series()` pour creer un dropdown depuis une colonne
- `mo.ui.altair_chart()` avec `chart_selection="point"` pour le drilldown
- `mo.ui.tabs()` pour les vues alternatives
- `mo.stat()` avec `.style(min_width=...)` pour les KPI cards
- `mo.stop()` pour le controle de flux conditionnel
- Pattern drilldown : chart selection -> extraction de l'ID -> requete SQL detaillee
- CTEs SQL complexes (WITH, window functions, aggregations)

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair",
#     "duckdb",
#     "marimo[sql]",
#     "narwhals",
#     "pandas",
# ]
# ///

import marimo

__generated_with = "0.11.14-dev6"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def init():
    import marimo as mo
    return (mo,)


@app.cell
async def _(mo):
    try:
        import micropip
        await micropip.install("sqlglot")
    except Exception:
        ...

    import altair as alt
    import duckdb

    import pandas as pd
    import narwhals as pl
    import os
    import tempfile
    import urllib.request
    import zipfile

    alt.renderers.set_embed_options(actions=False)

    _data_dir = os.path.join(tempfile.mkdtemp(), "f1-data")
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/marimo-team/gallery-examples/main/notebooks/sql/f1-driver-career-explorer/archive.zip",
        os.path.join(tempfile.gettempdir(), "f1-archive.zip"),
    )
    with zipfile.ZipFile(os.path.join(tempfile.gettempdir(), "f1-archive.zip"), "r") as _zf:
        _zf.extractall(_data_dir)

    for csv in os.listdir(_data_dir):
        if csv.endswith(".csv"):
            table_name = csv.split(".")[0]
            path = os.path.join(_data_dir, csv)
            mo.sql(
                f"""
           CREATE OR REPLACE TABLE {table_name} AS
           FROM read_csv("{path}");
            """
            )
    return alt, csv, duckdb, micropip, os, path, pd, pl, table_name


@app.cell
def _(mo):
    drivers_by_id = mo.sql(
        f"""
        SELECT
            driverId,
            CONCAT(forename, ' ', surname) as driver_name
        FROM drivers
        ORDER BY forename, surname;
        """,
        output=False
    )
    return (drivers_by_id,)


@app.cell
def _(drivers_by_id, mo):
    driver_select = mo.ui.dropdown.from_series(
        drivers_by_id["driver_name"], label="Driver", value="Lewis Hamilton"
    )
    return (driver_select,)


@app.cell
def _(driver_select, drivers_by_id, pl):
    selected_driver_id = pl.from_native(drivers_by_id).filter(
        pl.col("driver_name") == driver_select.value
    )["driverId"][0]
    return (selected_driver_id,)


@app.cell
def _(mo, selected_driver_id):
    constructor_for_driver = mo.sql(
        f"""
        SELECT DISTINCT
            c.constructorId,
            c.name as constructor_name
        FROM results r
        JOIN constructors c ON r.constructorId = c.constructorId
        WHERE r.driverId = {selected_driver_id}
        ORDER BY c.name;
        """,
        output=False
    )
    return (constructor_for_driver,)


@app.cell
def _(constructor_select, driver_select, mo):
    mo.hstack(
        [
            driver_select,
            mo.hstack(
                [
                    mo.md("**::lucide:filter:: Filters:**"),
                    constructor_select,
                ]
            ).left(),
        ]
    )
    return


@app.cell
def _(constructor_for_driver, mo):
    constructor_select = mo.ui.dropdown.from_series(
        constructor_for_driver["constructor_name"],
        label="Constructor",
        value=None,
    )
    return (constructor_select,)


@app.cell
def _(constructor_for_driver, constructor_select, pl):
    if constructor_select.value:
        selected_constructor_id = pl.from_native(constructor_for_driver).filter(
            pl.col("constructor_name") == constructor_select.value
        )["constructorId"][0]
    else:
        selected_constructor_id = "NULL"
    return (selected_constructor_id,)


@app.cell
def _(mo, selected_constructor_id, selected_driver_id):
    total_points_by_season = mo.sql(
        f"""
        SELECT
            r.year,
            SUM(res.points) as total_points,
            c.name as constructor_name
        FROM races r
        JOIN results res ON r.raceId = res.raceId
        JOIN constructors c ON res.constructorId = c.constructorId
        WHERE res.driverId = {selected_driver_id}
            AND (
                {selected_constructor_id} IS NULL
                OR
                res.constructorId = {selected_constructor_id}
            )
        GROUP BY r.year, c.name
        ORDER BY r.year;
        """,
        output=False
    )
    return (total_points_by_season,)


@app.cell
def _(mo, selected_constructor_id, selected_driver_id):
    points_by_race = mo.sql(
        f"""
        SELECT
            r.year,
            res.points,
            r.raceId,
            c.name as constructor_name,
            r.name as race_name,
            r.date,
        FROM races r
        JOIN results res ON r.raceId = res.raceId
        JOIN constructors c ON res.constructorId = c.constructorId
        WHERE res.driverId = {selected_driver_id}
            AND (
                {selected_constructor_id} IS NULL
                OR
                res.constructorId = {selected_constructor_id}
            )
        ORDER BY r.date;
        """,
        output=False
    )
    return (points_by_race,)


@app.cell
def _(mo, selected_constructor_id, selected_driver_id):
    career_stats = mo.sql(
        f"""
        SELECT
            COUNT(CASE WHEN positionOrder = 1 THEN 1 END) as total_wins,
            COUNT(CASE WHEN positionOrder <= 3 THEN 1 END) as total_podiums,
            COUNT(*) as total_races,
            ROUND(SUM(points), 0) as total_points,
            COUNT(CASE WHEN grid = 1 THEN 1 END) as pole_positions,
            COUNT(CASE WHEN rank = '1' THEN 1 END) as fastest_laps
        FROM results res
        JOIN races r ON res.raceId = r.raceId
        WHERE res.driverId = {selected_driver_id}
            AND ({selected_constructor_id} IS NULL OR res.constructorId = {selected_constructor_id});
        """,
        output=False
    )
    return (career_stats,)


@app.cell(hide_code=True)
def _(career_stats, constructor_select, driver_select, mo):
    mo.stop(career_stats is None)

    _cards = [
        mo.stat(
            label=label.title().replace("_", " "),
            value=career_stats[label][0],
            bordered=True,
        )
        for label in career_stats.columns
    ]

    _title = f"### **{driver_select.value}**'s Career Statistics"
    if constructor_select.value:
        _title += f" @ _{constructor_select.value}_"

    mo.vstack(
        [
            mo.md(_title),
            mo.hstack(_cards, widths="equal", align="center"),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""## Season Overview""")
    return


@app.cell(hide_code=True)
def _(bar_season_chart, line_season_chart, mo):
    season_chart = bar_season_chart()
    mo.ui.tabs(
        {
            "::lucide:chart-column-big:: Overall": mo.vstack(
                [season_chart, mo.md("**_Select a year on the chart above!_**")]
            ),
            "::lucide:chart-spline:: Season Progression": line_season_chart(),
        }
    )
    return (season_chart,)


@app.cell(hide_code=True)
def _(alt, mo, points_by_race):
    def line_season_chart():
        _chart = (
            alt.Chart(points_by_race)
            .mark_line()
            .transform_window(
                frame=[None, 0],
                groupby=["year"],
                cumulative_points="sum(points)",
                index="rank()",
            )
            .encode(
                x=alt.X("index:N", sort=None),
                y="cumulative_points:Q",
                color="year:N",
            )
        )
        return mo.ui.altair_chart(
            _chart,
            chart_selection=False,
            legend_selection=False,
            label="Points Progression By Season",
        )
    return (line_season_chart,)


@app.cell(hide_code=True)
def _(alt, mo, points_by_race, total_points_by_season):
    def bar_season_chart():
        _chart = (
            alt.Chart(total_points_by_season)
            .mark_bar()
            .encode(x="year:O", y="total_points:Q", color="constructor_name:N")
        )
        return mo.ui.altair_chart(
            _chart,
            chart_selection="point",
            legend_selection=False,
            label="Points By Season",
        )

    def dot_season_chart():
        _chart = (
            alt.Chart(points_by_race)
            .mark_circle()
            .encode(
                x="race_name:N",
                y="year:O",
                color="constructor_name:N",
                size="points:Q",
            )
        )
        return mo.ui.altair_chart(
            _chart,
            chart_selection="point",
            legend_selection=False,
            label="Points Progression Over Seasons",
        )
    return bar_season_chart, dot_season_chart


@app.cell
def _(mo, pl, season_chart):
    mo.stop(not len(season_chart.value["year"]))
    selected_year = pl.from_native(season_chart.value)["year"][0]
    return (selected_year,)


@app.cell
def _(mo, selected_constructor_id, selected_driver_id, selected_year):
    podium_finishes = mo.sql(
        f"""
        SELECT
            COUNT(CASE WHEN positionOrder = 1 THEN 1 END) as wins,
            COUNT(CASE WHEN positionOrder = 2 THEN 1 END) as seconds,
            COUNT(CASE WHEN positionOrder = 3 THEN 1 END) as thirds
        FROM results res
        JOIN races r ON res.raceId = r.raceId
        WHERE res.driverId = {selected_driver_id}
            AND r.year = {selected_year}
            AND ({selected_constructor_id} IS NULL OR res.constructorId = {selected_constructor_id});
        """,
        output=False
    )
    return (podium_finishes,)


@app.cell
def _(mo, pie_chart, podium_chart):
    mo.hstack([podium_chart, pie_chart], widths="equal", align="center")
    return


if __name__ == "__main__":
    app.run()
```

> **Note** : Le code complet contient egalement les cellules de drilldown par course (race_stats, qualifying_vs_race_positions) qui representent ~200 lignes supplementaires de SQL avec CTEs, window functions et aggregations. Le pattern de drilldown est : selection sur chart -> extraction ID -> requete SQL detaillee -> affichage KPI + graphiques.

---

## 7. SQL MotherDuck

**Ce que ca demontre** : Connexion a une base distante MotherDuck, requetes SQL avec resultats nommes reutilisables en Python, UI elements (multiselect, dropdown, text input) qui parametrisent le SQL de facon reactive, et graphiques Altair construits a partir des resultats SQL.

**Patterns cles** :
- `duckdb.sql("ATTACH 'md:...'")` pour connecter une base distante
- Resultats SQL nommes (affectes a une variable) reutilisables dans les cellules Python
- `mo.ui.multiselect()` avec dictionnaire (label -> valeur)
- `mo.ui.dropdown.from_series()` depuis un resultat SQL
- `mo.ui.text()` pour la recherche reactive
- Interpolation de variables Python dans le SQL via f-strings
- `mo.stop()` pour gerer les resultats vides
- `mo.hstack().left()` pour aligner les filtres a gauche

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair",
#     "duckdb",
#     "polars",
#     "pyarrow",
#     "marimo",
#     "numpy==2.4.2",
#     "sqlglot==29.0.1",
#     "pandas==3.0.1",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo

    duckdb.sql(
        "ATTACH 'md:_share/sample_data/23b0d623-1361-421d-ae77-62d701d471e6' AS sample_data"
    )
    return duckdb, mo


@app.cell
def _(mo):
    most_shared_websites = mo.sql(
        f"""
        SELECT
            regexp_extract(url, 'http[s]?://([^/]+)/', 1) AS domain,
            count(*) AS count
        FROM sample_data.hn.hacker_news
        WHERE url IS NOT NULL AND regexp_extract(url, 'http[s]?://([^/]+)/', 1) != ''
        GROUP BY domain
        ORDER BY count DESC
        LIMIT 20;
        """
    )
    return (most_shared_websites,)


@app.cell
def _(most_shared_websites):
    import altair as alt

    chart = (
        alt.Chart(most_shared_websites)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Number of Shares"),
            y=alt.Y("domain:N", sort="-x", title="Domain"),
            tooltip=["domain", "count"],
        )
        .properties(
            title="Top 20 Most Shared Websites on Hacker News", width="container"
        )
    )
    chart
    return (alt,)


@app.cell
def _(MONTHS, duckdb, mo):
    month_select = mo.ui.multiselect(
        MONTHS,
        label="Month",
        value=MONTHS.keys(),
    )

    hn_types = duckdb.sql(
        """
        SELECT DISTINCT type as 'HN Type'
        FROM sample_data.hn.hacker_news
        WHERE score IS NOT NULL AND descendants IS NOT NULL
        LIMIT 10;
        """
    ).df()

    hn_type_select = mo.ui.dropdown.from_series(hn_types["HN Type"], value="story")
    return hn_type_select, month_select


@app.cell(hide_code=True)
def _(hn_type_select, mo, month_select):
    month_list = ",".join([str(month) for month in month_select.value])
    mo.hstack(
        [
            mo.md(f"## {mo.icon('lucide:filter')}"),
            month_select,
            hn_type_select,
        ],
    ).left()
    return (month_list,)


@app.cell(hide_code=True)
def _(hn_type_select, mo, month_list):
    most_monthly_voted = mo.sql(
        f"""
        WITH ranked_stories AS (
            SELECT
                title,
                'https://news.ycombinator.com/item?id=' || id AS hn_url,
                score,
                type,
                descendants,
                YEAR(timestamp) AS year,
                MONTH(timestamp) AS month,
                ROW_NUMBER()
                    OVER (PARTITION BY YEAR(timestamp), MONTH(timestamp) ORDER BY score DESC)
                AS rn
            FROM sample_data.hn.hacker_news
            WHERE
                type = '{hn_type_select.value}'
                AND
                MONTH(timestamp) in ({month_list})
                AND
                descendants IS NOT NULL
        )

        SELECT
            month,
            score,
            type,
            title,
            hn_url,
            descendants as nb_comments,
            year,
        FROM ranked_stories
        WHERE rn = 1
        ORDER BY year, month;
        """
    )
    return (most_monthly_voted,)


@app.cell
def _(mo):
    search_input = mo.ui.text(label="Search for keywords", value="duckdb")
    search_input
    return (search_input,)


@app.cell
def _(mo, search_value):
    keyword_results = mo.sql(
        f"""
        SELECT
            YEAR(timestamp) AS year,
            MONTH(timestamp) AS month,
            COUNT(*) AS keyword_mentions
        FROM sample_data.hn.hacker_news
        WHERE
            (title LIKE '%{search_value}%' OR text LIKE '%{search_value}%')
        GROUP BY year, month
        ORDER BY year ASC, month ASC;
        """
    )
    return (keyword_results,)


if __name__ == "__main__":
    app.run()
```

---

## 8. SQL Interpolation

**Ce que ca demontre** : Pattern minimal de SQL reactif. Un slider controle le nombre de lignes generees par SQL, et le resultat est immediatement trace dans un bar chart Altair. Montre la connexion directe entre un widget UI et une requete SQL.

**Patterns cles** :
- `mo.ui.slider()` dont la valeur est interpolee dans le SQL
- `mo.sql()` qui retourne un dataframe Polars (via `sql_output="polars"`)
- `.plot.bar()` de Polars pour tracer directement

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==6.0.0",
#     "polars[pyarrow]==1.27.1",
#     "marimo[sql]",
#     "duckdb",
# ]
# ///

import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium", sql_output="polars")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    return alt, mo


@app.cell
def _(mo):
    digits = mo.ui.slider(label="Digits", start=100, stop=10000, step=200)
    digits
    return (digits,)


@app.cell
def _(digits, mo):
    result = mo.sql(
        f"""
        CREATE TABLE random_data AS
        SELECT i AS id, RANDOM() AS random_value,
        FROM range({digits.value}) AS t(i);

        SELECT * FROM random_data;
        """
    )
    return (result,)


@app.cell
def _(alt, result):
    result.plot.bar(x=alt.X("random_value").bin(), y="count()")
    return


if __name__ == "__main__":
    app.run()
```

---

## 9. Interactif Altair Demo

**Ce que ca demontre** : Pattern de selection interactive en cascade. Un scatter plot avec brush selection filtre les donnees vers un tableau, et la selection dans le tableau genere des histogrammes. Montre aussi la composition de charts Altair (scatter & bars).

**Patterns cles** :
- `alt.selection_interval()` pour le brush (selection rectangulaire)
- Composition de charts avec `&` (vertical) et `+` (superposition)
- `.transform_filter(brush)` pour filtrer un chart par la selection d'un autre
- `mo.ui.altair_chart()` dont `.value` est le dataframe filtre
- `mo.ui.table()` pour afficher et re-selectionner les donnees
- `mo.stop()` pour gerer le cas "rien selectionne"
- `mo.hstack()` avec `widths="equal"` pour la mise en page cote a cote

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==6.0.0",
#     "marimo",
#     "vega-datasets==0.9.0",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="full", auto_download=["html"])

with app.setup:
    import marimo as mo
    import altair as alt
    from vega_datasets import data


@app.cell
def _():
    cars = data.cars()

    brush = alt.selection_interval()
    scatter = (
        alt.Chart(cars)
        .mark_point()
        .encode(
            x="Horsepower",
            y="Miles_per_Gallon",
            color="Origin",
        )
        .add_params(brush)
    )
    bars = (
        alt.Chart(cars)
        .mark_bar()
        .encode(y="Origin:N", color="Origin:N", x="count(Origin):Q")
        .transform_filter(brush)
    )
    chart = mo.ui.altair_chart(scatter & bars)
    chart
    return (chart,)


@app.cell
def _(chart):
    (filtered_data := mo.ui.table(chart.value))
    return (filtered_data,)


@app.cell
def _(filtered_data):
    mo.stop(not len(filtered_data.value))
    mpg_hist = mo.ui.altair_chart(
        alt.Chart(filtered_data.value)
        .mark_bar()
        .encode(alt.X("Miles_per_Gallon:Q", bin=True), y="count()")
    )
    horsepower_hist = mo.ui.altair_chart(
        alt.Chart(filtered_data.value)
        .mark_bar()
        .encode(alt.X("Horsepower:Q", bin=True), y="count()")
    )
    mo.hstack([mpg_hist, horsepower_hist], justify="space-around", widths="equal")
    return


if __name__ == "__main__":
    app.run()
```

---

## 10. Exploration Chemical Space Explorer

**Ce que ca demontre** : Application scientifique avec de nombreux parametres reglables (t-SNE, HDBSCAN), barre de progression, scatter plot matplotlib interactif avec selection lasso, tableau formate avec rendu custom (SVG de molecules), et gestion conditionnelle de l'affichage (mo.stop avec callouts d'avertissement).

**Patterns cles** :
- `mo.ui.number()` pour les parametres numeriques avec bornes
- `mo.ui.checkbox()` pour les options booleennes
- `mo.ui.matplotlib()` avec `debounce=True` pour le scatter interactif
- `chart.value.get_mask(x, y)` pour recuperer la selection lasso/box
- `mo.ui.table()` avec `format_mapping` pour le rendu custom de colonnes
- `mo.status.progress_bar()` pour les calculs longs
- `mo.stop()` avec `mo.callout()` pour les messages conditionnels
- `mo.hstack()` + `mo.vstack()` pour organiser les controles en panneaux

```python
# (Code complet disponible dans le repo marimo-team/gallery-examples)
# Voir notebooks/library/chemical-space-explorer.py
# ~350 lignes — trop long pour etre inclus integralement ici

# Pattern essentiel pour le scatter interactif avec matplotlib :
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(x_coords, y_coords, c=labels, cmap="tab20", s=20, alpha=0.8)
chart = mo.ui.matplotlib(ax, debounce=True)

# Recuperation de la selection :
selected_indices = np.where(chart.value.get_mask(x_coords, y_coords))[0]
mo.stop(len(selected_indices) == 0, mo.callout(mo.md("Selectionnez des points..."), kind="warn"))

# Tableau avec formatage custom :
mo.ui.table(
    table_data,
    format_mapping={
        "Mol": mol_to_svg,
        "AMW": lambda x: f"{x:.2f}",
    },
    page_size=5,
)
```

---

## Resume des patterns par usage

| Besoin | Pattern Marimo | Exemple |
|--------|---------------|---------|
| KPI avec variation | `mo.stat(label, value, caption, direction, bordered)` | Movies |
| Etat partage | `get, set = mo.state(valeur_initiale)` | Movies |
| Filtres dropdown | `mo.ui.dropdown()` / `mo.ui.dropdown.from_series()` | F1, Lego |
| Filtres multi-choix | `mo.ui.multiselect()` | Lego, MotherDuck |
| Filtres range | `mo.ui.range_slider(min, max, step)` | Lego |
| Recherche texte | `mo.ui.text()` | MotherDuck |
| Saisie de donnees | `mo.ui.data_editor(df)` | Portfolio |
| Graphique interactif | `mo.ui.altair_chart(chart)` / `.value` = selection | Movies, F1, Altair |
| Tableau interactif | `mo.ui.table(df)` / `.value` = lignes selectionnees | Movies, Altair |
| SQL natif | `result = mo.sql(f"SELECT ...")` | SQLite, F1, MotherDuck |
| SQL avec backend | `mo.sql(..., engine=sqlalchemy_engine)` | SQLite |
| Onglets | `mo.ui.tabs({"label": contenu})` | F1 |
| Layout horizontal | `mo.hstack([...], widths="equal", gap=1)` | Tous |
| Layout vertical | `mo.vstack([...])` | WoW, F1 |
| Cache | `@mo.cache` | WoW |
| Controle de flux | `mo.stop(condition, message_alternatif)` | Movies, Altair |
| Pipeline Polars | `.pipe(fn1).pipe(fn2).pipe(fn3)` | WoW, Portfolio |
| Fonctions reutilisables | `@app.function` | Movies, WoW, Portfolio |
| Progression | `mo.status.progress_bar()` | Chemical Space |
| Callout | `mo.callout(contenu, kind="warn/info")` | Chemical Space |

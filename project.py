"""
CSC271 Final Project - GTA Housing Prices and Municipal Socioeconomic Characteristics
Author: Jiya Marwah

This module provides functions to load, clean, and store data from two datasets:
  1. GTA property listings (Kaggle)
  2. Statistics Canada 2021 Census profiles (per municipality)

It also provides database query functions and a visualization function.
"""

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CENSUS_FILES = {
    "Brampton":      "current-actuelle_cfm_csv_brampton.csv",
    "Mississauga":   "current-actuelle_cfm_csv_mississauga.csv",
    "Toronto":       "current-actuelle_cfm_csv_toronto.csv",
    "Markham":       "current-actuelle_cfm_csv_markham.csv",
    "Vaughan":       "current-actuelle_cfm_csv_vaughan.csv",
    "Oakville":      "current-actuelle_cfm_csv_oakville.csv",
    "Richmond Hill": "current-actuelle_cfm_csv_richmond_hill.csv",
    "Burlington":    "current-actuelle_cfm_csv_burlington.csv",
}

# Housing dataset region names -> census municipality name

REGION_MAP = {
    "Brampton, ON":               "Brampton",
    "Mississauga, ON":            "Mississauga",
    "Old Toronto, Toronto, ON":   "Toronto",
    "Scarborough, Toronto, ON":   "Toronto",
    "Markham, ON":                "Markham",
    "Vaughan, ON":                "Vaughan",
    "Oakville, ON":               "Oakville",
    "Richmond Hill, ON":          "Richmond Hill",
    "Burlington, ON":             "Burlington",
}

CENSUS_COLS = [
    "Topic", "Characteristic", "Note", "Total", "Total_Flag",
    "Men", "Men_Flag", "Women", "Women_Flag",
    "Rate_Total", "Rate_Total_Flag", "Rate_Men", "Rate_Men_Flag",
    "Rate_Women", "Rate_Women_Flag", "Extra"
]

# ---------------------------------------------------------------------------
# Data loading and cleaning
# ---------------------------------------------------------------------------

def load_properties(filepath: str) -> pd.DataFrame:
    """
    Load and clean the GTA property listings dataset.

    Reads the Excel file, filters to only the 8 municipalities we have
    census data for, and adds a 'municipality' column using REGION_MAP
    for joining with the census table.

    Parameters
    ----------
    filepath : str
        Path to clean_combined_toronto_property_data.xlsx.

    Returns
    -------
    pd.DataFrame
        Cleaned properties DataFrame with columns:
        price, region, address, bedrooms, bathrooms, pricem, municipality.
    """
    df = pd.read_excel(filepath)

    # Keep only rows whose region maps to a census municipality
    df = df[df["region"].isin(REGION_MAP.keys())].copy()

    # Add municipality column for joining
    df["municipality"] = df["region"].map(REGION_MAP)

    # Drop any rows with missing price, bedrooms, or bathrooms
    df = df.dropna(subset=["price", "bedrooms", "bathrooms"])

    # Ensure correct types
    df["price"] = df["price"].astype(int)
    df["bedrooms"] = df["bedrooms"].astype(int)
    df["bathrooms"] = df["bathrooms"].astype(int)

    df = df.reset_index(drop=True)
    return df


def _extract_census_value(df: pd.DataFrame, characteristic: str) -> float:
    """
    Extract a single numeric value from a census DataFrame by characteristic name.

    Parameters
    ----------
    df : pd.DataFrame
        Census DataFrame with a 'Characteristic' column and a 'Total' column.
    characteristic : str
        Exact stripped string to match in the Characteristic column.

    Returns
    -------
    float
        The numeric value, or NaN if not found.
    """
    match = df[df["Characteristic"].str.strip() == characteristic]
    if len(match) == 0:
        return float("nan")
    return pd.to_numeric(match["Total"].values[0], errors="coerce")


def load_census(data_dir: str) -> pd.DataFrame:
    """
    Load and parse the Statistics Canada 2021 Census CSV files.

    Reads one CSV per municipality, extracts five key indicators, and
    returns a single tidy DataFrame with one row per municipality.

    Parameters
    ----------
    data_dir : str
        Directory containing the census CSV files listed in CENSUS_FILES.

    Returns
    -------
    pd.DataFrame
        Census DataFrame with columns:
        municipality, population, median_household_income,
        unemployment_rate, pct_bachelor, pct_low_income.
    """
    rows = []

    for municipality, filename in CENSUS_FILES.items():
        path = os.path.join(data_dir, filename)
        df = pd.read_csv(path, encoding="latin1", header=2)
        df.columns = CENSUS_COLS

        row = {
            "municipality": municipality,
            "population": _extract_census_value(df, "Population, 2021"),
            "median_household_income": _extract_census_value(
                df, "Median total income of household in 2020 ($)"
            ),
            "unemployment_rate": _extract_census_value(df, "Unemployment rate"),
            "pct_bachelor": pd.to_numeric(
                df[df["Characteristic"].str.strip() == "Bachelor's degree or higher"]["Total"].values[0],
                errors="coerce"
            ) if len(df[df["Characteristic"].str.strip() == "Bachelor's degree or higher"]) > 0 else float("nan"),
            "pct_low_income": _extract_census_value(
                df,
                "Prevalence of low income based on the Low-income measure, after tax (LIM-AT) (%)"
            ),
        }
        rows.append(row)

    census_df = pd.DataFrame(rows)

    # pct_bachelor is a raw count — convert to percentage of population
    census_df["pct_bachelor"] = (
        census_df["pct_bachelor"] / census_df["population"] * 100
    ).round(1)

    return census_df

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def create_database(db_path: str, properties_df: pd.DataFrame, census_df: pd.DataFrame) -> None:
    """
    Create a SQLite database and populate it with two tables.

    Tables created:
      - properties(id, price, region, address, bedrooms, bathrooms, municipality)
      - census(municipality, population, median_household_income,
               unemployment_rate, pct_bachelor, pct_low_income)

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file to create (or overwrite).
    properties_df : pd.DataFrame
        Cleaned properties DataFrame from load_properties().
    census_df : pd.DataFrame
        Census DataFrame from load_census().
    """
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE properties (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            price       INTEGER NOT NULL,
            region      TEXT NOT NULL,
            address     TEXT,
            bedrooms    INTEGER,
            bathrooms   INTEGER,
            municipality TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE census (
            municipality            TEXT PRIMARY KEY,
            population              INTEGER,
            median_household_income INTEGER,
            unemployment_rate       REAL,
            pct_bachelor            REAL,
            pct_low_income          REAL
        )
    """)

    # Insert properties
    props_to_insert = properties_df[
        ["price", "region", "address", "bedrooms", "bathrooms", "municipality"]
    ].values.tolist()
    cur.executemany(
        "INSERT INTO properties (price, region, address, bedrooms, bathrooms, municipality) VALUES (?,?,?,?,?,?)",
        props_to_insert
    )

    # Insert census
    census_to_insert = census_df[
        ["municipality", "population", "median_household_income",
         "unemployment_rate", "pct_bachelor", "pct_low_income"]
    ].values.tolist()
    cur.executemany(
        "INSERT INTO census VALUES (?,?,?,?,?,?)",
        census_to_insert
    )

    conn.commit()
    conn.close()


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return a sqlite3 connection with row_factory set to Row.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------------------------
# Query 1 — GROUP BY + aggregate: avg price and listing count per municipality
# ---------------------------------------------------------------------------

def query_avg_price_by_municipality(db_path: str) -> pd.DataFrame:
    """
    Query the average housing price and number of listings per municipality.

    Uses GROUP BY and aggregate functions (AVG, COUNT).

    Parameters
    ----------
    db_path : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        Columns: municipality, avg_price, listing_count.
        Sorted by avg_price descending.
    """
    sql = """
        SELECT
            municipality,
            ROUND(AVG(price), 0)  AS avg_price,
            COUNT(*)              AS listing_count
        FROM properties
        GROUP BY municipality
        ORDER BY avg_price DESC
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ---------------------------------------------------------------------------
# Query 2 — JOIN: housing prices with census socioeconomic data
# ---------------------------------------------------------------------------

def query_price_with_census(db_path: str) -> pd.DataFrame:
    """
    Join the properties and census tables to combine average housing prices
    with municipal socioeconomic indicators.

    Uses JOIN, GROUP BY, and aggregate functions (AVG, COUNT).

    Parameters
    ----------
    db_path : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        Columns: municipality, avg_price, listing_count,
                 median_household_income, unemployment_rate,
                 pct_bachelor, pct_low_income.
        Sorted by avg_price descending.
    """
    sql = """
        SELECT
            p.municipality,
            ROUND(AVG(p.price), 0)   AS avg_price,
            COUNT(*)                  AS listing_count,
            c.median_household_income,
            c.unemployment_rate,
            c.pct_bachelor,
            c.pct_low_income
        FROM properties p
        JOIN census c ON p.municipality = c.municipality
        GROUP BY p.municipality
        ORDER BY avg_price DESC
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ---------------------------------------------------------------------------
# Query 3 — GROUP BY bedrooms + aggregate: avg price by bedroom count
# ---------------------------------------------------------------------------

def query_avg_price_by_bedrooms(db_path: str) -> pd.DataFrame:
    """
    Query the average housing price grouped by number of bedrooms.

    Uses GROUP BY and AVG aggregate function.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        Columns: bedrooms, avg_price, listing_count.
        Sorted by bedrooms ascending.
    """
    sql = """
        SELECT
            bedrooms,
            ROUND(AVG(price), 0) AS avg_price,
            COUNT(*)             AS listing_count
        FROM properties
        WHERE bedrooms BETWEEN 1 AND 6
        GROUP BY bedrooms
        ORDER BY bedrooms ASC
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ---------------------------------------------------------------------------
# Query 4 — Parameterized: listings for a specific municipality
# ---------------------------------------------------------------------------

def query_listings_by_municipality(db_path: str, municipality: str) -> pd.DataFrame:
    """
    Retrieve all property listings for a given municipality.

    Uses a parameterized query to safely pass the municipality argument.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database.
    municipality : str
        Name of the municipality to filter by (e.g. 'Oakville').

    Returns
    -------
    pd.DataFrame
        All listing rows for that municipality, sorted by price descending.
    """
    sql = """
        SELECT
            price,
            region,
            address,
            bedrooms,
            bathrooms
        FROM properties
        WHERE municipality = ?
        ORDER BY price DESC
    """
    conn = get_connection(db_path)
    df = pd.read_sql_query(sql, conn, params=(municipality,))
    conn.close()
    return df

# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_price_vs_income(joined_df: pd.DataFrame, save_path: str = None) -> None:
    """
    Plot average housing price vs. median household income per municipality,
    with bubble size representing number of listings and colour representing
    unemployment rate.

    Parameters
    ----------
    joined_df : pd.DataFrame
        Output of query_price_with_census().
    save_path : str, optional
        If provided, saves the figure to this path instead of showing it.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("GTA Housing Prices vs. Municipal Socioeconomic Indicators (2021)",
                 fontsize=13, fontweight="bold")

    # --- Plot 1: avg price vs median household income ---
    ax1 = axes[0]
    sizes = (joined_df["listing_count"] / joined_df["listing_count"].max()) * 600 + 100
    scatter = ax1.scatter(
        joined_df["median_household_income"],
        joined_df["avg_price"],
        s=sizes,
        c=joined_df["unemployment_rate"],
        cmap="RdYlGn_r",
        alpha=0.85,
        edgecolors="grey",
        linewidths=0.5
    )
    for _, row in joined_df.iterrows():
        ax1.annotate(
            row["municipality"],
            (row["median_household_income"], row["avg_price"]),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=8
        )
    cb = fig.colorbar(scatter, ax=ax1)
    cb.set_label("Unemployment Rate (%)", fontsize=9)
    ax1.set_xlabel("Median Household Income ($)", fontsize=10)
    ax1.set_ylabel("Average Property Price ($)", fontsize=10)
    ax1.set_title("Avg Price vs. Median Household Income\n(bubble size = # listings)", fontsize=10)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
    ax1.grid(True, linestyle="--", alpha=0.4)

    # --- Plot 2: avg price vs % bachelor's degree ---
    ax2 = axes[1]
    ax2.scatter(
        joined_df["pct_bachelor"],
        joined_df["avg_price"],
        s=sizes,
        color="steelblue",
        alpha=0.8,
        edgecolors="grey",
        linewidths=0.5
    )
    for _, row in joined_df.iterrows():
        ax2.annotate(
            row["municipality"],
            (row["pct_bachelor"], row["avg_price"]),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=8
        )
    ax2.set_xlabel("Population with Bachelor's Degree or Higher (%)", fontsize=10)
    ax2.set_ylabel("Average Property Price ($)", fontsize=10)
    ax2.set_title("Avg Price vs. Education Level\n(bubble size = # listings)", fontsize=10)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    ax2.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_avg_price_by_municipality(avg_price_df: pd.DataFrame, save_path: str = None) -> None:
    """
    Bar chart of average housing price by municipality, sorted descending.

    Parameters
    ----------
    avg_price_df : pd.DataFrame
        Output of query_avg_price_by_municipality().
    save_path : str, optional
        If provided, saves the figure to this path.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    df = avg_price_df.sort_values("avg_price", ascending=True)
    bars = ax.barh(df["municipality"], df["avg_price"], color="steelblue", edgecolor="white")

    ax.set_xlabel("Average Property Price ($)", fontsize=11)
    ax.set_title("Average Housing Price by Municipality — GTA (2021)", fontsize=12, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))

    # Add value labels
    for bar, val in zip(bars, df["avg_price"]):
        ax.text(val + 10000, bar.get_y() + bar.get_height() / 2,
                f"${val/1e6:.2f}M", va="center", fontsize=8.5)

    ax.grid(axis="x", linestyle="--", alpha=0.4)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_price_by_bedrooms(bedrooms_df: pd.DataFrame, save_path: str = None) -> None:
    """
    Bar chart of average housing price by number of bedrooms.

    Parameters
    ----------
    bedrooms_df : pd.DataFrame
        Output of query_avg_price_by_bedrooms().
    save_path : str, optional
        If provided, saves the figure to this path.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(
        bedrooms_df["bedrooms"].astype(str),
        bedrooms_df["avg_price"],
        color="coral",
        edgecolor="white",
        width=0.6
    )

    ax.set_xlabel("Number of Bedrooms", fontsize=11)
    ax.set_ylabel("Average Property Price ($)", fontsize=11)
    ax.set_title("Average Housing Price by Number of Bedrooms — GTA (2021)",
                 fontsize=12, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))

    for bar, row in zip(bars, bedrooms_df.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10000,
                f"${row.avg_price/1e6:.2f}M\n(n={row.listing_count})",
                ha="center", fontsize=8.5)

    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()

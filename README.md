# GTA Housing Prices and Municipal Socioeconomic Characteristics

An exploratory data analysis project examining how housing prices vary across eight Greater Toronto Area (GTA) municipalities, and whether municipal-level socioeconomic indicators are associated with those prices.

---

## Research Questions

1. Which GTA municipalities have the highest average housing prices, and how much do they differ?
2. How does average housing price change as the number of bedrooms increases?
3. Is there an association between a municipality's median household income and its average housing price? Does education level show a similar pattern?

---

## Data Sources

**Dataset 1 - GTA Property Listings**
- Source: [Kaggle — Toronto Properties by Mangaljit Singh](https://www.kaggle.com/datasets/mangaljitsingh/torontoproperties)
- File: `clean_combined_toronto_property_data.xlsx`
- 4,136 listings across 8 GTA municipalities (filtered from 7,324 total)

**Dataset 2 - Statistics Canada 2021 Census Profiles**
- Source: [Statistics Canada Census Profile, 2021](https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/index.cfm?Lang=E)
- One CSV per municipality at the Census Subdivision level
- Municipalities: Toronto, Mississauga, Brampton, Markham, Vaughan, Oakville, Richmond Hill, Burlington

> **Note:** Raw data files are not included in this repository due to file size and licensing. Download them directly from the links above.

---

## Tools & Technologies

- **Python** - data loading, cleaning, and visualization
- **SQLite** - relational database for storing and querying joined data
- **SQL** - `GROUP BY`, `AVG`, `COUNT`, `JOIN`, and parameterized queries
- **pandas** - data manipulation and preprocessing
- **matplotlib** - charts and scatter plots

---

## Database Schema

**`properties` table** - one row per listing

| Column | Type | Description |
|---|---|---|
| id | INTEGER (PK) | Auto-incremented |
| price | INTEGER | Listing price in CAD |
| region | TEXT | Original region string |
| address | TEXT | Property address |
| bedrooms | INTEGER | Number of bedrooms |
| bathrooms | INTEGER | Number of bathrooms |
| municipality | TEXT (FK) | Standardized municipality name |

**`census` table** - one row per municipality

| Column | Type | Description |
|---|---|---|
| municipality | TEXT (PK) | Municipality name |
| population | INTEGER | 2021 population |
| median_household_income | INTEGER | Median total household income (2020) |
| unemployment_rate | REAL | Unemployment rate (%) |
| pct_bachelor | REAL | % of population with a bachelor's degree or higher |
| pct_low_income | REAL | % in low income (LIM-AT) |

---

## Key Findings

- **Municipality is the strongest price driver.** Oakville averages $2.49M compared to Toronto's $1.1M. A gap of over $1.3M for the same number of bedrooms.
- **Bedroom count has a strong positive relationship with price.** Average prices roughly quintuple from 1-bedroom (~$683K) to 5-bedroom (~$3.6M) properties.
- **Median household income is positively associated with housing prices** at the municipal level. Higher-income municipalities (Oakville, Vaughan) tend to have higher average prices.
- **Education level is a weaker predictor.** The relationship exists but is inconsistent. Brampton and Mississauga have similar average prices despite different bachelor's degree rates.

---

## How to Run

1. Clone this repo
2. Download the required datasets (links above) and place them in the project root
3. Install dependencies:
   ```bash
   pip install pandas openpyxl matplotlib
   ```
4. Run the analysis:
   ```bash
   python project.py
   ```
   Or open `project.ipynb` in Jupyter Notebook / JupyterLab.

---

## Limitations

- Data represents **listing prices**, not final sale prices
- Census data is from **2021** (income figures from 2020); listing data has no clear date stamp
- Only **8 municipalities** so trends are suggestive, not conclusive
- Missing variables: property type (condo vs. detached), square footage, lot size, proximity to transit

---

## Project Structure

```
.
├── project.py              # All functions: loading, database creation, queries, plots
├── project.ipynb           # Full analysis with narrative and visualizations
└── README.md
```

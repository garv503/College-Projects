# Shivam Garments — Billing and Store Management

A Python coursework project for a garment retail shop. Two programs: a small invoice calculator, and a menu-driven store management system backed by CSV files.

## The two programs

| File | What it does |
| --- | --- |
| `Basic Billing.py` | A short invoice calculator. Takes a garment type, sub-type and price, applies the discount for that combination, adds GST and prints a formatted invoice. |
| `G.S.M.S.py` | The full Garment Store Management System — log in, then add, remove, modify, sort and search records, generate reports and plot charts. |

## Data files

Everything is stored in CSVs beside the scripts. pandas reads them at startup and writes back after each change.

| File | Indexed by | Holds |
| --- | --- | --- |
| `Customer Details.csv` | `Cust_ID` | Name, gender, phone, email, date of birth, address, pin code |
| `Stock Details.csv` | `Stock_Id` | Garment name, vendor, quantity purchased, unit price, description |
| `Billing Details.csv` | `Bill_Id` | Bills raised |
| `Login Id.csv` | `Login_ID` | Admin login credentials |

## Requirements

Python 3, with pandas and matplotlib:

```bash
pip install pandas matplotlib
```

## Running it

```bash
python "G.S.M.S.py"
```

Run it from this folder. The scripts open the CSVs by relative filename, so starting from a different working directory fails with `FileNotFoundError`.

The standalone calculator needs no data files:

```bash
python "Basic Billing.py"
```

## Menu

After signing in: **Add**, **Remove**, **Modify**, **Sort**, **Searching**, **Reports**, **Data Visualization**, **Logout**. Add, remove and modify each apply to customers, stock or bills. Record IDs are generated automatically in sequence (`A001`, `S01`).

Discount rules used by `Basic Billing.py`:

| Type | Sub-type | Discount |
| --- | --- | --- |
| Woolen | Sweater | 12% |
| Woolen | Jacket | 8% |
| Woolen | Blazer | 10% |
| Festive | Kurta Set | 12% |
| Festive | Sherwani | 16% |
| Festive | Nehru Jacket | 8% |

GST is a flat 10% on the pre-discount price.

## Notes

- Login credentials sit in plain text in `Login Id.csv`, and the password is read as an integer. Fine for a college demo, not for anything real.
- Edits are written straight back over the CSVs, so keep a copy before experimenting.

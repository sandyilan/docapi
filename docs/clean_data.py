from pathlib import Path

import pandas as pd

folder = Path(__file__).parent
input_file = folder / "messy_records.csv"
output_file = folder / "cleaned_records.csv"
log_file = folder / "cleaning_log.txt"

df = pd.read_csv(input_file)
changes = []

# Convert dates to YYYY-MM-DD. Drop and log rows with invalid dates.
original_dates = df["date"].copy()
parsed_dates = pd.to_datetime(df["date"], format="mixed", errors="coerce")
invalid_dates = parsed_dates.isna()

for index in df.index[invalid_dates]:
    changes.append(
        f"Dropped row id={df.loc[index, 'id']}: invalid date "
        f"{original_dates.loc[index]!r}"
    )

df = df.loc[~invalid_dates].copy()
df["date"] = parsed_dates.loc[~invalid_dates].dt.strftime("%Y-%m-%d")

# Convert amounts to numbers and fill missing or invalid amounts with the median.
original_amounts = df["amount"].copy()
amounts = pd.to_numeric(df["amount"], errors="coerce")
median_amount = amounts.median()

for index in df.index[amounts.isna()]:
    changes.append(
        f"Filled amount for row id={df.loc[index, 'id']}: "
        f"{original_amounts.loc[index]!r} -> {median_amount}"
    )

df["amount"] = amounts.fillna(median_amount)

# Fill missing names.
missing_names = df["name"].isna()
for index in df.index[missing_names]:
    changes.append(f"Filled missing name for row id={df.loc[index, 'id']}")

df["name"] = df["name"].fillna("Unknown")

# Remove duplicate records, keeping the first one.
duplicates = df.duplicated(subset=["name", "amount", "date"], keep="first")
for index in df.index[duplicates]:
    changes.append(f"Removed duplicate row id={df.loc[index, 'id']}")

df = df.loc[~duplicates]

df.to_csv(output_file, index=False)
log_file.write_text("\n".join(changes) + "\n", encoding="utf-8")

print(f"Cleaned data saved to: {output_file}")
print(f"Change log saved to: {log_file}")
print(f"Rows remaining: {len(df)}")
print(f"Changes logged: {len(changes)}")
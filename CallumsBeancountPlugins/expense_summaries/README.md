# `expense_summaries`

`expense_summaries` is a Fava extension that shows yearly expense summaries by
category.

It is intended as a convenience report for reviewing ledger activity inside
Fava. It is not authoritative budgeting, tax, or financial-reporting software,
and the values shown should be checked against your ledger conventions and any
other records you rely on.

## What It Does

The extension renders two tables on a single Fava page:

1. yearly expense totals in CAD by expense category
2. average monthly expense in CAD by expense category

Both tables use years as columns and categories as rows.

## How It Works

The extension scans loaded transactions and inspects postings whose account
starts with `Expenses:`.

For each matching posting, it:

1. converts the posting to CAD using Fava's conversion helpers
2. groups the amount by calendar year
3. infers the category from the second account component under `Expenses`

The yearly totals table includes all expense postings for each year.

The average table is stricter. It only includes postings from fully completed
months, and it divides yearly totals by the number of completed months in that
year that had any expense posting.

For example, if today is April 19 and your ledger has expenses in January,
February, March, and April, the average table for the current year uses January
through March only and divides by `3`, not `4`.

## How To Enable It

Add the extension to your Fava configuration using this module path:

```beancount
CallumsBeancountPlugins.expense_summaries
```

## What To Expect

After enabling it in Fava, you should get a report page titled:

```beancount
Expenses
```

The page shows:

1. a `Yearly Expense Totals (CAD)` table
2. an `Average Expense Per Active Month (CAD)` table

Zero values in category cells render as `-` for readability.

## Assumptions

This extension assumes:

1. expense postings live under accounts that start with `Expenses:`
2. the category you want to report on is the second account component, such as
   `Food` in `Expenses:Food:Restaurants`
3. Fava can convert the posting to CAD using the ledger's price data

If a posting cannot be converted to CAD, it is omitted from the report.

## Limitations And Manual Checks

You should manually review:

1. whether the second expense account component matches the category structure
   you want
2. whether CAD conversions are available and correct for any non-CAD expenses
3. whether excluding the current partial month matches your reporting intent
4. whether yearly totals and averages agree with any budgeting workflow you use

This extension is a convenience summary only. For official reporting or any
workflow where precision requirements go beyond personal review, use the source
ledger, external records, and professional tools as needed.

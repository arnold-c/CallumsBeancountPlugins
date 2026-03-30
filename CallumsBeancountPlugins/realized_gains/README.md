# `realized_gains`

`realized_gains` is a Fava extension that summarizes gain-related postings by year and person.

It is intended as a convenience report over your ledger, not an authoritative tax calculation. Always check the results against broker statements, slips, CRA records, and any professional tools or advice you use for real tax work.

## What It Does

The extension scans the loaded ledger and aggregates amounts from:

1. postings whose account contains `PnL`
2. postings whose account ends with `:CGDividend`

It groups those amounts by calendar year and by person inferred from the account path, then renders a summary table in Fava.

## How It Works

For each transaction, the extension inspects postings and looks for the account patterns above.

When a matching posting is found, it:

1. extracts the person from the third account component
2. flips the Beancount income sign so gains display as positive amounts
3. totals the amount by year and person

The result is a compact reporting layer over your ledger rather than a formal tax engine.

## Relationship To The Other ACB Plugins

This is one of the three related ACB plugins in the repository.

1. `calculate_acb` generates convenience gain-related postings.
2. `acb_dashboard` shows historical ACB snapshots.
3. `realized_gains` summarizes gains-related amounts.

This extension is most useful when `calculate_acb` is enabled and your ledger follows the same account conventions.

## How To Enable It

Add the extension to your Fava configuration using this module path:

```beancount
CallumsBeancountPlugins.realized_gains
```

## What To Expect

After enabling it in Fava, you should get a report page titled:

```beancount
realized Gains
```

The table lists years in reverse chronological order and provides:

1. a column for each detected person
2. a per-year total column

## Assumptions

This extension assumes gain-related postings use the same account style as the rest of the ACB workflow in this repository.

In particular, it assumes:

1. PnL postings are posted to accounts containing `PnL`
2. capital-gain-dividend reclassifications end in `:CGDividend`
3. the owner can be inferred from the third account component

If your ledger uses different conventions, the report may omit or misattribute data.

## Limitations And Manual Checks

You should manually verify:

1. whether all gain postings you care about match the expected account patterns
2. whether person names are being inferred correctly from account paths
3. whether the report agrees with the records you actually use for tax work
4. whether capital-gain dividends and realized gains should really be reviewed
   together for your workflow

This report is a convenience summary only. For official tracking, CRA reconciliation, and filing, use professional tools and professional advice.

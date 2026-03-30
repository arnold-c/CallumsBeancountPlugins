# `acb_dashboard`

`acb_dashboard` is a Fava extension that shows historical year-end snapshots of
holdings and adjusted cost base.

It is intended as a convenience report for reviewing the state of your ledger.
It is not authoritative tax software, and any values shown should be checked
against broker records, CRA expectations, and whatever professional workflow you
use for actual tax tracking.

## What It Does

The dashboard reconstructs running holdings from ledger transactions and then
captures a snapshot at each year boundary.

For open positions, it displays:

1. account
2. ticker
3. shares held
4. total ACB in CAD
5. average cost per share

## How It Works

The extension walks the loaded ledger in date order.

It tracks:

1. non-CAD postings with a price as buys and sells (i.e., assumes you hold tickers as currencies - this will not handle non-CAD investments.)
2. tax-basis postings under `Assets:TaxBasis` as direct ACB adjustments

At each year change, it stores a snapshot of positions that still have positive share balances.

This means the dashboard is a report over the ledger as loaded in Fava. It does not perform official tax calculations by itself.

## Relationship To The Other ACB Plugins

This is one of the three related ACB plugins in the repository.

1. `calculate_acb` produces convenience tax-basis and gains bookkeeping.
2. `acb_dashboard` shows a year-end holdings and ACB view.
3. `realised_gains` shows a gains-oriented summary.

This dashboard is most useful when `calculate_acb` is enabled, because it uses the same account conventions and can incorporate generated `Assets:TaxBasis` postings.

## How To Enable It

Add the extension to your Fava configuration using its module path:

```beancount
CallumsBeancountPlugins.acb_dashboard
```

The exact configuration mechanism depends on how you manage Fava, but the value you need is the Python import path above.

See [`calculate_acb`](../calculate_acb/README.md#usage-example)

## What To Expect

After enabling the extension in Fava, you should get a report page titled:

```beancount
Canadian ACB
```

The page shows year-end tables in reverse chronological order. Each table contains only positions with shares still outstanding at the end of that year.

## Assumptions

This extension assumes a ledger structure compatible with the ACB workflow in this repository.

Important assumptions include:

1. asset positions are held in `Assets:...` accounts
2. tax-basis adjustments are posted under `Assets:TaxBasis:...`
3. priced non-CAD postings represent security buys or sells
4. the Beancount plugin configuration may optionally restrict processing to
   certain account prefixes

## Limitations And Manual Checks

You should manually review:

1. whether the dashboard matches your broker's year-end holdings
2. whether phantom and ROC adjustments were recorded correctly in the ledger
3. whether historical transactions are complete enough to support the numbers
4. whether your account naming matches what the extension expects

This extension is a convenience view only. For actual tax records, CRA reconciliation, or filing, use professional tools and professional advice.

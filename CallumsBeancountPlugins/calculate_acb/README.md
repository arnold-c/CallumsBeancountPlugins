# `calculate_acb`

`calculate_acb` is a Beancount plugin that adds convenience bookkeeping for Canadian adjusted cost base workflows.

It is meant to reduce manual ledger work for common buy, sell, phantom distribution, return-of-capital, and capital-gain-dividend scenarios.

It is not authoritative tax software.

Always verify its output against broker statements, fund notices, CRA records, and any professional workflow you use for real tax tracking or filing.

## What It Does

This plugin walks through your ledger in order and keeps running state for each account and ticker.

For qualifying transactions and supported `Custom` directives, it can:

1. track shares held
2. track total CAD adjusted cost base
3. reduce ACB on sale using average cost
4. add realised-gain postings on sale
5. post tax-basis adjustments for phantom distributions and ROC
6. reclassify certain dividend amounts as capital-gain dividends

## How It Works

The plugin processes entries sequentially.

### Buys and DRIPs

When it sees a posting with non-CAD units and a CAD `@` price (or a CAD cost with `@@` transactions), it treats the posting as a security purchase and increases both:

1. share count
2. total CAD ACB

### Sells

When it sees a negative security posting with a CAD `@` price (or a CAD cost with `@@` transactions), it calculates:

1. average cost per share from the running position
2. cost of the shares sold
3. gain or loss based on proceeds minus cost of sale

It then appends convenience postings for gains bookkeeping.

### `acb_adjust` custom directives

The plugin also supports `Custom` entries of type `acb_adjust` for additional bookkeeping situations.

Supported adjustment types are:

1. `phantom`
2. `roc`
3. `cg_dividend`
4. `cg_split`

These are transformed into generated transactions that post to derived account paths based on the original asset account.

## Account Conventions

This plugin relies on account naming conventions.

Given an asset account such as:

```beancount
Assets:CA:Primary:Taxable:Broker:ETF
```

the plugin derives related account paths by replacing the leading `Assets`
component.

Examples of derived paths include:

1. `Assets:TaxBasis:CA:Primary:Taxable:Broker:ETF:VEQT:Phantom`
2. `Assets:TaxBasis:CA:Primary:Taxable:Broker:ETF:VEQT:ROC`
3. `Income:CA:Primary:Taxable:Broker:ETF:PnL:Long`
4. `Income:CA:Primary:Taxable:Broker:ETF:Dividend`
5. `Income:CA:Primary:Taxable:Broker:ETF:VEQT:CGDividend`

On sales, the plugin also posts to:

```beancount
Equity:<person>:RealisedGains
```

where `<person>` is inferred from the third account component when available.

If your ledger does not follow this style, review the code and adjust it before using the plugin.

## How To Enable It

Add the plugin to your Beancount ledger:

```beancount
plugin "CallumsBeancountPlugins.calculate_acb"
```

You can optionally restrict processing to specific account prefixes by passing a comma-separated string:

```beancount
plugin "CallumsBeancountPlugins.calculate_acb" "Assets:CA:Primary:Taxable,Assets:CA:Joint:Taxable"
```

Only postings in matching accounts will be processed.

## Usage Examples

### From your brokerage

You will need to enter your trades as usual, being sure to specify the ticker as a currency.
Because Canadian taxes require average cost basis calculations, using lots (specified with `{}` directives) doesn't work very well, and the `AVERAGE` method is still a proposal in Beancount v3, so I just set my investment accounts to [`NONE`](https://beancount.github.io/docs/how_inventories_work.html#no-booking).
Specifying transactions using `@` or `@@` should work, but I use `@@` cost directives as I find it reduces rounding errors and better aligns with the numbers I get from my brokerage.

#### Standard buy and sell workflow

```beancount
2024-01-10 * "Buy VEQT"
  Assets:CA:Primary:Taxable:Broker      10 VEQT @ 35.00 CAD
  Assets:CA:Primary:Cash              -350.00 CAD

2024-06-15 * "Sell VEQT"
  Assets:CA:Primary:Taxable:Broker      -4 VEQT @@ 156.00 CAD
  Assets:CA:Primary:Cash
```

### From CDS.ca

You can find the relevant information to handle distributions from various ETFs and Mutual Funds at [CDS.ca](https://ctbsext.posttrade.cds.ca/ctbsExt/).
By selecting the option to "Display tax information for year 20XX", you will be provided a list of funds on the TSX, and after finding the relevant one to you and opening the PDF, you will get information you can use to fill out the following sections.
See [adjustedcostbasis.ca's blog](https://www.adjustedcostbase.ca/blog/phantom-distributions-and-their-effect-on-adjusted-cost-base/) for more guidance on this.

#### Return of capital

```beancount
2024-12-31 custom "acb_adjust"
  "Assets:CA:Primary:Taxable:Broker"
  "VEQT"
  "roc"
  0.08 CAD
  "per-share"
```

#### Phantom distribution

In your beancount file, add a custom directive as below, using the value(s) from the "Total Non Cash Distribution ($) Per Unit" row.
You can either enter it as `"per-share"` (the default if left blank), or `"total"`.
In `per-share` mode, the plugin will calculate the number of shares of the ticker held in the account on the date and multiple it by the per-share distribution amount.
Alternatively, you can perform these calculations by hand and just enter the total.

```beancount
2024-12-31 custom "acb_adjust"
  "Assets:CA:Primary:Taxable:Broker"
  "VEQT"
  "phantom"
  0.12 CAD
  "per-share"
```


#### Capital gain dividend reclassification

In some instances, the fund will also distribute capital gains in excess of the phantom distributions.
This is the case if you see values in the "Capital gain" row in excess of the "Total Non Cash Distribution ($) Per Unit" (phantom distributions) for a given date.
When phantom distributions do not exist for a date, this value is to be entered with a custom directive (see [below](#split-capitqal-gain-distribution), for instances when both exist for a given date and the capital gains exceed the phantom distribution).
You can either enter it as `"per-share"` (the default if left blank), or `"total"`.
In `per-share` mode, the plugin will calculate the number of shares of the ticker held in the account on the date and multiple it by the per-share distribution amount.
Alternatively, you can perform these calculations by hand and just enter the total.

```beancount
2024-12-31 custom "acb_adjust"
  "Assets:CA:Primary:Taxable:Broker"
  "VEQT"
  "cg_dividend"
  10.50 CAD
  "total"
```

#### Split capital-gain distribution

When both a capital gain and phantom distribution are present for a given record date, you need to enter two records into your ledger - one for each.
This plugin can handle this for you but calculating the amount attributable to capital gains (in excess of the phantom distribution).
You can enter this as below.
You can either enter it as `"per-share"` (the default if left blank), or `"total"`.
In `per-share` mode, the plugin will calculate the number of shares of the ticker held in the account on the date and multiple it by the per-share distribution amount.
Alternatively, you can perform these calculations by hand and just enter the total.

```beancount
2024-12-31 custom "acb_adjust"
  "Assets:CA:Primary:Taxable:Broker"
  "VEQT"
  "cg_split"
  0.30 CAD # This is the capital gain amount
  0.12 CAD # This is the non cash (phantom) distribution
  "per-share"
```

For `cg_split`, the fourth value is the total capital-gain amount and the fifth
value is the phantom portion.
The plugin increases ACB only by the phantom amount and reclassifies the remaining cash portion as a capital-gain dividend.

## What To Expect

After enabling the plugin:

1. qualifying sales may gain extra postings for convenience gains bookkeeping
2. qualifying `acb_adjust` directives will be replaced by generated
   transactions
3. tax-basis postings may appear under `Assets:TaxBasis:...`
4. income and gain postings may appear under derived `Income:...` accounts

This plugin does not attempt to be a complete tax engine. It follows a narrow, ledger-opinionated workflow.

## Related Plugins

This plugin is the bookkeeping foundation for the other ACB-related plugins in this repository.

1. `../acb_dashboard/README.md` explains the Fava dashboard for year-end ACB
   snapshots.
2. `../realised_gains/README.md` explains the Fava dashboard for gains
   summaries.

Those two Fava extensions are most useful when this plugin, or an equivalent accounting workflow, is already in place.

## Limitations And Manual Checks

You should review and validate at least the following.

1. whether your account naming matches the plugin assumptions
2. whether your broker or fund issuer reports different adjustment values
3. whether all historical purchases needed for correct average cost are present
4. whether sales, splits, transfers, or reorganizations need special handling
5. whether the derived realised gains match the records you actually rely on

For real tax tracking and compliance, use professional tools and professional advice. Treat this plugin as a convenience aid only.

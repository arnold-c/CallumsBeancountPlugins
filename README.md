# CallumsBeancountPlugins

Convenience Beancount and Fava plugins for a Canadian personal-finance workflow.

These plugins are designed to make a Beancount ledger easier to work with for common Canadian bookkeeping tasks such as adjusted cost base tracking, realized gains reporting, and TFSA contribution room estimation.

They are not authoritative tax software.

Always check the output against CRA records, broker statements, fund notices, and other source documents. For actual tax tracking, compliance, filing, or any situation where accuracy matters beyond personal convenience, use professional software and professional advice.

## Included Plugins

This repository currently contains six plugins.

1. `calculate_acb`
   A Beancount plugin that derives convenience ACB, tax-basis, and realized gain postings from qualifying investment transactions and supported custom directives.
2. `acb_dashboard`
   A Fava extension that reconstructs historical year-end ACB snapshots for currently held positions.
3. `realized_gains`
   A Fava extension that summarizes gain-related postings by year and person.
4. `tfsa_contribution_room`
     A Fava extension that estimates TFSA contribution room from ledger activity and account metadata.
5. `fhsa_contribution_room`
    A Fava extension that estimates FHSA contribution usage, cumulative
    contributions, and remaining room from ledger activity and account metadata.
6. `rrsp_contribution_room`
    A Fava extension that estimates RRSP contribution usage, cumulative
    contributions, and remaining room from ledger activity and manually
    recorded CRA room metadata.

## Related ACB Plugins

The three ACB-related plugins are intended to be used together.

1. `calculate_acb` does the bookkeeping work.
2. `acb_dashboard` provides a year-end ACB view over the resulting ledger.
3. `realized_gains` provides a gains-focused summary over the resulting ledger.

You can use the Fava extensions independently, but they are most useful when the ledger follows the same conventions as `calculate_acb` and, in practice, when that Beancount plugin is enabled.

## Installation

This package is a Python package and can be added to a Pixi-managed project as a PyPI dependency sourced from Git.

Example:

```bash
pixi add --pypi --git https://github.com/arnold-c/beancount-plugins.git CallumsBeancountPlugins
```

If you prefer SSH-style Git URLs, use the same command with your preferred Git remote URL instead.

After installation, enable the Beancount plugin in your ledger and the Fava extensions in your Fava configuration as needed.

## Usage Overview

### Beancount plugin

Enable `calculate_acb` in your ledger:

```beancount
plugin "CallumsBeancountPlugins.calculate_acb"
```

You can optionally restrict it to specific account prefixes:

```beancount
plugin "CallumsBeancountPlugins.calculate_acb" "Assets:Investments:Non-Registered"
```

### Fava extensions

Enable the Fava extensions in your Fava configuration using their import paths:

1. `CallumsBeancountPlugins.acb_dashboard`
2. `CallumsBeancountPlugins.realized_gains`
3. `CallumsBeancountPlugins.tfsa_contribution_room`
4. `CallumsBeancountPlugins.fhsa_contribution_room`
5. `CallumsBeancountPlugins.rrsp_contribution_room`

The exact Fava configuration format depends on how you launch Fava, but each extension is intended to be added by its Python module path.

## Account And Metadata Assumptions

The plugins in this repository assume a specific ledger style.

### ACB workflow assumptions

`calculate_acb` assumes account names that can be transformed mechanically.

1. Investment holdings are recorded under `Assets:...` accounts.
2. Tax-basis adjustments are posted to derived `Assets:TaxBasis:...` accounts.
3. Income-side postings are derived by replacing `Assets` with `Income`.
4. realized gain balancing entries use `Equity:<person>:realizedGains`.
5. The account path usually encodes the owner in the third path component.

If your ledger uses different conventions, you should review the plugin code before relying on it.

### TFSA workflow assumptions

`tfsa_contribution_room` expects TFSA accounts to include metadata such as:

```beancount
2024-01-01 open Assets:CA:Primary:TFSA:Cash CAD,XEQT "NONE"
  canadian_tax_type: "TFSA"
  owner: "Primary"
  start_year: "2015"
```

`owner` defaults to `Primary` if omitted. `start_year` is optional and is used
to start the room calculation earlier than the default baseline.

### FHSA workflow assumptions

`fhsa_contribution_room` expects FHSA accounts to include metadata such as:

```beancount
2024-01-01 open Assets:CA:Primary:FHSA:Cash CAD,CASH "NONE"
  canadian_tax_type: "FHSA"
  owner: "Primary"
  start_year: "2024"
  fhsa_deduction_2024: "6000"
```

`owner` defaults to `Primary` if omitted. `start_year` is optional and is used
to identify the first calendar year the FHSA was open for room calculations.
FHSA deductions are expected to be entered manually using
`fhsa_deduction_<year>` metadata keys.

### RRSP workflow assumptions

`rrsp_contribution_room` expects RRSP accounts to include metadata such as:

```beancount
2024-01-01 open Assets:CA:Primary:RRSP:Cash CAD,CASH "NONE"
  canadian_tax_type: "RRSP"
  owner: "Primary"
  rrsp_room_2024_verified: "18500"
  rrsp_deduction_2024: "12000"
  rrsp_room_2025_verified: "21200"
  rrsp_deduction_2025: "8000"
  rrsp_room_2026_estimate: "23000"
```

`owner` defaults to `Primary` if omitted. CRA room values are expected to be
entered manually using `rrsp_room_<year>_verified` or
`rrsp_room_<year>_estimate` metadata keys. RRSP deductions are expected to be
entered manually using `rrsp_deduction_<year>` metadata keys.

Direct FHSA-to-RRSP transfers that do not consume RRSP room should be marked
with `rrsp_room_exempt: "FHSA_TRANSFER"` on the transaction or RRSP posting.

## Limitations

These plugins are convenience tools, not a substitute for tax software.
It also is only designed to work with CAD denominations, with no focus on any foreign-held investments, as is relatively common for Canadian investors.

Examples of things you should still verify manually include:

1. ACB adjustments from fund notices and broker reporting.
2. Capital gains and losses reported on slips and statements.
3. Return of capital and phantom distributions.
4. TFSA contribution room as reported by CRA My Account.
5. FHSA contribution usage and limits as reported by your institution or CRA.
6. FHSA deductions claimed on your tax returns.
7. RRSP contribution room as reported by CRA My Account.
8. Any cases involving corporate actions, unusual bookkeeping, or incomplete
    historical ledger data.

## Plugin Documentation

Each plugin directory contains its own `README.md` with details on what it does, how it works, how to configure it, and what to expect.

1. `CallumsBeancountPlugins/calculate_acb/README.md`
2. `CallumsBeancountPlugins/acb_dashboard/README.md`
3. `CallumsBeancountPlugins/realized_gains/README.md`
4. `CallumsBeancountPlugins/tfsa_contribution_room/README.md`
5. `CallumsBeancountPlugins/fhsa_contribution_room/README.md`
6. `CallumsBeancountPlugins/rrsp_contribution_room/README.md`

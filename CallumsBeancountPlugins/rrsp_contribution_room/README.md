# `rrsp_contribution_room`

`rrsp_contribution_room` is a Fava extension that estimates RRSP contribution usage from your ledger history.

It is a convenience tracker only.

It is not authoritative, should not be treated as official CRA RRSP room tracking, and should always be checked against CRA My Account, broker records, and any professional tools or advice you use for real tax planning or compliance.

## What It Does

The extension finds RRSP accounts in your ledger, groups them by owner, totals qualifying CAD contributions by year, tracks cumulative contributions and deductions, and combines those totals with manually recorded CRA room figures.

It gives you a bookkeeping-oriented view of:

1. annual RRSP contributions
2. cumulative RRSP contributions
3. annual RRSP deductions
4. cumulative RRSP deductions
5. remaining undeducted contributions
6. CRA room recorded for each year
7. estimated remaining room after that year's contributions

## How It Works

The extension looks for account metadata marking an account as RRSP.

It then:

1. groups RRSP accounts by `owner`
2. skips transactions that appear to be internal-only or explicitly marked as transfers
3. skips postings marked with RRSP room exemption metadata for FHSA-to-RRSP direct transfers
4. counts only positive CAD postings directly affecting the RRSP accounts
5. never adds withdrawals back to RRSP room
6. reads CRA room values from year-specific account metadata
7. reads RRSP deductions from year-specific account metadata
8. checks that cumulative deductions never exceed cumulative contributions

The output is therefore only as good as the completeness and correctness of the ledger data and metadata.

## Required Metadata

RRSP accounts should include metadata like this:

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

Expected fields:

1. `canadian_tax_type: "RRSP"`
2. `owner`: optional, defaults to `Primary`
3. `rrsp_room_<year>_verified`: optional, CRA-verified room for that year
4. `rrsp_room_<year>_estimate`: optional, estimated room for an upcoming year
5. `rrsp_deduction_<year>`: optional, RRSP deduction claimed for that tax year

The extension starts at the earliest room year or RRSP contribution year it can find.

## Transfer Exemption Metadata

Direct FHSA-to-RRSP transfers should be marked so they are not counted as RRSP contributions.

You can place the metadata on the transaction or on the RRSP posting:

```beancount
2025-01-15 * "FHSA transfer to RRSP"
  rrsp_room_exempt: "FHSA_TRANSFER"
  Assets:CA:Primary:RRSP:Cash   5000 CAD
  Assets:CA:Primary:FHSA:Cash  -5000 CAD
```

This exemption is intended for direct qualifying transfers that do not consume RRSP contribution room.

## How To Enable It

Add the extension to your Fava configuration using this module path:

```beancount
CallumsBeancountPlugins.rrsp_contribution_room
```

## What To Expect

After enabling it in Fava, you should get a report page titled:

```text
RRSP Contribution Tracker
```

The page shows one table per owner with annual rows for:

1. CRA room entered for the year
2. whether that room is `verified` or `estimate`
3. annual RRSP contributions
4. cumulative RRSP contributions
5. annual RRSP deductions
6. cumulative RRSP deductions
7. remaining undeducted contributions
8. a validity check showing whether cumulative deductions exceed cumulative contributions
9. estimated remaining room for that year

## Important Assumptions

This extension assumes all of the following.

1. your RRSP accounts are tagged correctly with metadata
2. your ledger history is complete for the years you care about
3. transfers and internal balancing entries are represented in a way the extension can safely ignore
4. direct FHSA-to-RRSP transfers are explicitly marked with `rrsp_room_exempt: "FHSA_TRANSFER"`
5. only CAD cash movements into the RRSP should count toward contribution totals
6. CRA room metadata is entered correctly for each year you want to review
7. deduction metadata is entered correctly for each year you want to review

If any of those assumptions are false, the estimate may be wrong.

## Limitations And Manual Checks

You should manually verify at least:

1. whether CRA reports different available RRSP room
2. whether all RRSP contributions are fully represented in the ledger
3. whether FHSA-to-RRSP direct transfers were tagged correctly
4. whether all RRSP deductions claimed on your tax returns are reflected in metadata
5. whether payroll-style, employer, or institution-specific RRSP flows need special handling in your ledger
6. whether the upcoming year's `estimate` metadata still matches your own tax planning assumptions

This extension is for convenience only. For actual RRSP tracking, planning, compliance, or filing-related work, use authoritative records and professional tools or professional advice.

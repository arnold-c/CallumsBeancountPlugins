# `fhsa_contribution_room`

`fhsa_contribution_room` is a Fava extension that estimates FHSA contribution usage from your ledger history.

It is a convenience tracker only.

It is not authoritative, should not be treated as official CRA FHSA tracking, and should always be checked against CRA records, broker records, and any professional tools or advice you use for real tax planning or compliance.

## What It Does

The extension finds FHSA accounts in your ledger, groups them by owner, totals qualifying CAD contributions by year, and applies FHSA annual, carry-forward, lifetime, and 15-year eligibility rules.

It gives you a bookkeeping-oriented view of:

1. annual FHSA contributions
2. cumulative FHSA contributions
3. estimated remaining room for each year
4. estimated remaining lifetime contribution capacity

## How It Works

The extension looks for account metadata marking an account as FHSA.

It then:

1. groups FHSA accounts by `owner`
2. skips certain transactions that appear to be internal-only or explicitly
   marked as transfers
3. counts only positive CAD postings directly affecting the FHSA accounts
4. totals annual contributions
5. applies an 8,000 CAD annual room amount
6. caps carry-forward at 8,000 CAD
7. caps lifetime contributions at 40,000 CAD
8. stops generating new room after 15 calendar years from the opening year

The output is therefore only as good as the completeness and correctness of the ledger data and metadata.

## Required Metadata

FHSA accounts should include metadata like this:

```beancount
2024-01-01 open Assets:CA:Primary:FHSA:Cash CAD,CASH "NONE"
  canadian_tax_type: "FHSA"
  owner: "Primary"
  start_year: "2024"
```

Expected fields:

1. `canadian_tax_type: "FHSA"`
2. `owner`: optional, defaults to `Primary`
3. `start_year`: optional, the first calendar year the FHSA was open for that
   owner

If `start_year` is omitted, the extension falls back to the earliest FHSA contribution year it can find, or 2023 if no FHSA activity exists yet.

## How To Enable It

Add the extension to your Fava configuration using this module path:

```beancount
CallumsBeancountPlugins.fhsa_contribution_room
```

## What To Expect

After enabling it in Fava, you should get a report page titled:

```text
FHSA Contribution Tracker
```

The page shows one table per owner with annual rows for:

1. annual FHSA limit
2. opening room for the year
3. annual contributions
4. cumulative contributions
5. estimated remaining room
6. estimated remaining lifetime contribution limit
7. carry-forward into the next eligible year

## Important Assumptions

This extension assumes all of the following.

1. your FHSA accounts are tagged correctly with metadata
2. your ledger history is complete for the years you care about
3. transfers and internal balancing entries are represented in a way the
   extension can safely ignore
4. only CAD cash movements into the FHSA should count toward contribution
   totals
5. `start_year` matches the first year the FHSA was actually open if you choose
   to provide it

If any of those assumptions are false, the estimate may be wrong.

## Limitations And Manual Checks

You should manually verify at least:

1. whether CRA or your institution reports different FHSA contribution usage
2. whether all FHSA contributions are fully represented in the ledger
3. whether transfers were classified correctly
4. whether your FHSA opening year is represented correctly
5. whether withdrawals or institution-specific handling affect your own review

This extension is for convenience only. For actual FHSA tracking, planning, compliance, or filing-related work, use authoritative records and professional tools or professional advice.

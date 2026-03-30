# `tfsa_contribution_room`

`tfsa_contribution_room` is a Fava extension that estimates TFSA contribution room from your ledger history.

It is a convenience tracker only.

It is not authoritative, should not be treated as official CRA room tracking, and should always be checked against CRA My Account, broker records, and any professional tools or advice you use for real tax planning or compliance.

## What It Does

The extension finds TFSA accounts in your ledger, groups them by owner, totals qualifying CAD contributions and withdrawals by year, and applies annual TFSA limits to estimate remaining room.

It is useful for a quick bookkeeping-oriented view of how your ledger activity may have affected TFSA room over time.

## How It Works

The extension looks for account metadata marking an account as TFSA.

It then:

1. groups TFSA accounts by `owner`
2. skips certain transactions that appear to be internal-only or explicitly
   marked as transfers
3. counts only CAD postings directly affecting the TFSA accounts
4. totals annual contributions and withdrawals
5. rolls contribution room forward using annual limits and withdrawal carryover

The output is therefore only as good as the completeness and correctness of the ledger data and metadata.

## Required Metadata

TFSA accounts should include metadata like this:

```beancount
2024-01-01 open Assets:CA:Primary:TFSA:Cash CAD,XEQT "NONE"
  canadian_tax_type: "TFSA"
  owner: "Primary"
  start_year: "2015"
```

Expected fields:

1. `canadian_tax_type: "TFSA"`
2. `owner`: optional, defaults to `Primary`
3. `start_year`: optional, earliest year to start the room calculation for that
   owner

## How To Enable It

Add the extension to your Fava configuration using this module path:

```beancount
CallumsBeancountPlugins.tfsa_contribution_room
```

## What To Expect

After enabling it in Fava, you should get a report page titled:

```text
TFSA Room Tracker
```

The page shows one table per owner with annual rows for:

1. TFSA limit
2. annual contributions
3. annual withdrawals
4. estimated remaining room

## Important Assumptions

This extension assumes all of the following.

1. your TFSA accounts are tagged correctly with metadata
2. your ledger history is complete for the years you care about
3. transfers and internal balancing entries are represented in a way the
   extension can safely ignore
4. only CAD cash movements should count toward contribution or withdrawal totals

If any of those assumptions are false, the estimate may be wrong.

## Limitations And Manual Checks

You should manually verify at least:

1. whether CRA reports different available room
2. whether all TFSA contributions and withdrawals are fully represented in the
   ledger
3. whether transfers were classified correctly
4. whether non-cash events or institution-specific handling affected your room
5. whether the `start_year` metadata matches the actual start of eligibility or
   account activity you want to model

This extension is for convenience only. For actual TFSA tracking, planning, compliance, or filing-related work, use CRA records and professional tools or professional advice.

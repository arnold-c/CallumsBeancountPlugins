"""Fava extension for estimating FHSA contribution usage from ledger data.

This extension inspects FHSA-tagged accounts and transaction history to build a
year-by-year estimate of annual contributions, cumulative contributions, and
remaining FHSA room. It is a convenience tracker only and must be checked
against CRA records and professional tools before being relied upon for
compliance or filing decisions.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from beancount.core import data
from fava.ext import FavaExtensionBase


class FHSAContributionRoom(FavaExtensionBase):
    """Render FHSA contribution history and remaining room inside Fava.

    The extension expects FHSA accounts to carry metadata such as
    ``canadian_tax_type: "FHSA"`` and uses optional ``owner`` and
    ``start_year`` metadata to group and initialize calculations.
    """

    report_title = "FHSA Contribution Tracker"

    ANNUAL_LIMIT = Decimal("8000")
    MAX_CARRY_FORWARD = Decimal("8000")
    LIFETIME_LIMIT = Decimal("40000")
    FIRST_ELIGIBLE_YEAR = 2023
    MAX_ELIGIBILITY_YEARS = 15

    INTERNAL_ACCOUNTS = {
        "ZeroSumAccounts:Transfers",
        "Equity:Rounding-Errors:Imports",
    }

    def get_all_fhsa_data(self):
        """Estimate annual FHSA contributions and room for each owner.

        The calculation groups FHSA accounts by owner, totals qualifying CAD
        contributions by year, applies FHSA annual and lifetime limits, caps
        carry-forward at 8,000 CAD, and stops generating new room after 15
        calendar years from the FHSA opening year.

        Returns:
            A mapping of owner name to yearly history rows containing annual
            room, annual contributions, cumulative contributions, and estimated
            remaining room.
        """
        owners = defaultdict(list)
        owner_start_years = {}
        account_open_years = {
            entry.account: entry.date.year
            for entry in self.ledger.all_entries
            if isinstance(entry, data.Open)
        }

        for name in self.ledger.accounts:
            meta = self.ledger.accounts[name].meta
            if meta.get("canadian_tax_type") != "FHSA":
                continue

            owner = str(meta.get("owner", "Primary")).strip()
            owners[owner].append(name)

            start_year = self._coerce_start_year(meta.get("start_year"))
            if start_year is None:
                start_year = self._coerce_start_year(account_open_years.get(name))

            if start_year is not None:
                previous_year = owner_start_years.get(owner)
                if previous_year is None or start_year < previous_year:
                    owner_start_years[owner] = start_year

        results = {}

        for owner, account_names in owners.items():
            yearly_contributions = defaultdict(lambda: Decimal("0"))
            fhsa_and_internal = set(account_names) | self.INTERNAL_ACCOUNTS

            for entry in self.ledger.all_entries:
                if not isinstance(entry, data.Transaction):
                    continue

                if entry.meta.get("type") == "transfer":
                    continue

                if any(
                    posting.account.startswith(("Income:", "Expenses:"))
                    for posting in entry.postings
                ):
                    continue

                if all(posting.account in fhsa_and_internal for posting in entry.postings):
                    continue

                for posting in entry.postings:
                    if posting.account not in account_names:
                        continue

                    if posting.meta and posting.meta.get("type") == "transfer":
                        continue

                    if posting.units.currency != "CAD":
                        continue

                    if posting.units.number > 0:
                        yearly_contributions[entry.date.year] += posting.units.number

            start_year = owner_start_years.get(owner)
            if start_year is None:
                start_year = self._infer_start_year(yearly_contributions)

            results[owner] = self._build_history(start_year, yearly_contributions)

        return results

    def _build_history(self, start_year, yearly_contributions):
        """Build yearly FHSA contribution rows for a single owner."""
        current_year = date.today().year
        last_activity_year = max(yearly_contributions.keys(), default=current_year)
        final_year = max(current_year, last_activity_year)
        eligibility_end_year = start_year + self.MAX_ELIGIBILITY_YEARS - 1

        history = []
        carry_forward = Decimal("0")
        cumulative_contributions = Decimal("0")

        for year in range(start_year, final_year + 1):
            contributions = yearly_contributions[year]
            remaining_lifetime_before = self.LIFETIME_LIMIT - cumulative_contributions
            is_eligible_year = year <= eligibility_end_year

            if remaining_lifetime_before < 0:
                remaining_lifetime_before = Decimal("0")

            if is_eligible_year:
                base_room = self.ANNUAL_LIMIT + carry_forward
                opening_room = min(base_room, remaining_lifetime_before)
            else:
                opening_room = Decimal("0")

            closing_room = opening_room - contributions
            cumulative_contributions += contributions
            remaining_lifetime_after = self.LIFETIME_LIMIT - cumulative_contributions

            if remaining_lifetime_after < 0:
                remaining_lifetime_after = Decimal("0")

            if is_eligible_year and closing_room > 0 and remaining_lifetime_after > 0:
                carry_forward = min(
                    self.MAX_CARRY_FORWARD,
                    closing_room,
                    remaining_lifetime_after,
                )
            else:
                carry_forward = Decimal("0")

            history.append(
                {
                    "year": year,
                    "annual_limit": self.ANNUAL_LIMIT if is_eligible_year else Decimal("0"),
                    "opening_room": opening_room,
                    "contributions": contributions,
                    "cumulative_contributions": cumulative_contributions,
                    "remaining_room": closing_room,
                    "remaining_lifetime_limit": remaining_lifetime_after,
                    "carry_forward": carry_forward,
                    "eligible": is_eligible_year,
                }
            )

        return history

    def _coerce_start_year(self, raw_value):
        """Return a valid FHSA opening year from metadata when possible."""
        if raw_value in (None, ""):
            return None

        try:
            return max(self.FIRST_ELIGIBLE_YEAR, int(raw_value))
        except (TypeError, ValueError):
            return None

    def _infer_start_year(self, yearly_contributions):
        """Infer the FHSA opening year when metadata is absent."""
        if yearly_contributions:
            return max(self.FIRST_ELIGIBLE_YEAR, min(yearly_contributions))

        return self.FIRST_ELIGIBLE_YEAR

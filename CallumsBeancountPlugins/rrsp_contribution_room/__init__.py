"""Fava extension for estimating RRSP contribution usage from ledger data.

This extension inspects RRSP-tagged accounts and transaction history to build a
year-by-year estimate of annual contributions, cumulative contributions,
cumulative deductions, remaining undeducted contributions, and remaining RRSP
room based on manually recorded CRA figures. It is a convenience tracker only
and must be checked against CRA records and professional tools before being
relied upon for compliance or filing decisions.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from beancount.core import data
from fava.ext import FavaExtensionBase


class RRSPContributionRoom(FavaExtensionBase):
    """Render RRSP contribution history and CRA room inside Fava.

    The extension expects RRSP accounts to carry metadata such as
    ``canadian_tax_type: "RRSP"`` and uses optional ``owner`` metadata to
    group calculations.

    CRA room values are supplied manually through account metadata keys like
    ``rrsp_room_2025_verified`` and ``rrsp_room_2026_estimate``. RRSP
    deductions are supplied through keys like ``rrsp_deduction_2025``.
    """

    report_title = "RRSP Contribution Tracker"

    INTERNAL_ACCOUNTS = {
        "ZeroSumAccounts:Transfers",
        "Equity:Rounding-Errors:Imports",
    }
    ROOM_KEY_PATTERN = re.compile(r"^rrsp_room_(\d{4})_(verified|estimate|estimated)$")
    DEDUCTION_KEY_PATTERN = re.compile(r"^rrsp_deduction_(\d{4})$")
    EXEMPT_TRANSFER_VALUE = "FHSA_TRANSFER"

    def get_all_rrsp_data(self):
        """Estimate annual RRSP contributions and remaining room for each owner.

        The calculation groups RRSP accounts by owner, totals qualifying CAD
        contributions by year, tracks cumulative contributions and deductions,
        and combines those totals with manually entered CRA room amounts for
        each year.

        Returns:
            A mapping of owner name to yearly history rows containing CRA room,
            annual contributions, cumulative contributions, annual deductions,
            cumulative deductions, remaining undeducted contributions, and
            estimated remaining room.
        """
        owners = defaultdict(list)
        owner_room_data = defaultdict(dict)
        owner_deduction_data = defaultdict(dict)

        for name in self.ledger.accounts:
            meta = self.ledger.accounts[name].meta
            if meta.get("canadian_tax_type") != "RRSP":
                continue

            owner = str(meta.get("owner", "Primary")).strip()
            owners[owner].append(name)

            self._merge_room_metadata(owner_room_data[owner], meta)
            self._merge_deduction_metadata(owner_deduction_data[owner], meta)

        results = {}

        for owner, account_names in owners.items():
            yearly_contributions = defaultdict(lambda: Decimal("0"))
            rrsp_and_internal = set(account_names) | self.INTERNAL_ACCOUNTS

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

                if all(
                    posting.account in rrsp_and_internal for posting in entry.postings
                ):
                    continue

                for posting in entry.postings:
                    if posting.account not in account_names:
                        continue

                    if posting.meta and posting.meta.get("type") == "transfer":
                        continue

                    if self._is_room_exempt_transfer(entry, posting):
                        continue

                    if posting.units.currency != "CAD":
                        continue

                    if posting.units.number > 0:
                        yearly_contributions[entry.date.year] += posting.units.number

            room_data = owner_room_data[owner]
            deduction_data = owner_deduction_data[owner]
            start_year = self._infer_start_year(
                yearly_contributions,
                room_data,
                deduction_data,
            )

            results[owner] = self._build_history(
                start_year,
                yearly_contributions,
                room_data,
                deduction_data,
            )

        return results

    def _build_history(
        self,
        start_year,
        yearly_contributions,
        room_data,
        deduction_data,
    ):
        """Build yearly RRSP contribution rows for a single owner."""
        current_year = date.today().year
        last_contribution_year = max(yearly_contributions.keys(), default=current_year)
        last_room_year = max(room_data.keys(), default=current_year)
        last_deduction_year = max(deduction_data.keys(), default=current_year)
        final_year = max(
            current_year,
            last_contribution_year,
            last_room_year,
            last_deduction_year,
        )

        history = []
        cumulative_contributions = Decimal("0")
        cumulative_deductions = Decimal("0")

        for year in range(start_year, final_year + 1):
            contributions = yearly_contributions[year]
            deductions = deduction_data.get(year, Decimal("0"))
            cumulative_contributions += contributions
            cumulative_deductions += deductions

            room_row = room_data.get(year)
            cra_room = None
            room_status = "missing"
            remaining_room = None
            undeducted_contributions = cumulative_contributions - cumulative_deductions
            deductions_valid = cumulative_deductions <= cumulative_contributions

            if room_row is not None:
                cra_room = room_row["amount"]
                room_status = room_row["status"]
                remaining_room = cra_room - contributions

            history.append(
                {
                    "year": year,
                    "cra_room": cra_room,
                    "room_status": room_status,
                    "contributions": contributions,
                    "cumulative_contributions": cumulative_contributions,
                    "deductions": deductions,
                    "cumulative_deductions": cumulative_deductions,
                    "undeducted_contributions": undeducted_contributions,
                    "deductions_valid": deductions_valid,
                    "remaining_room": remaining_room,
                }
            )

        return history

    def _infer_start_year(self, yearly_contributions, room_data, deduction_data):
        """Infer the first RRSP year to display from known data."""
        candidate_years = set(yearly_contributions) | set(room_data) | set(deduction_data)
        if candidate_years:
            return min(candidate_years)

        return date.today().year

    def _merge_room_metadata(self, owner_room_data, meta):
        """Merge RRSP room metadata for one owner across multiple accounts."""
        for key, raw_value in meta.items():
            match = self.ROOM_KEY_PATTERN.match(str(key))
            if match is None:
                continue

            year = int(match.group(1))
            status = match.group(2)
            if status == "estimated":
                status = "estimate"

            amount = self._coerce_decimal(raw_value)
            if amount is None:
                continue

            existing_row = owner_room_data.get(year)
            if existing_row is None or (
                existing_row["status"] == "estimate" and status == "verified"
            ):
                owner_room_data[year] = {"amount": amount, "status": status}

    def _merge_deduction_metadata(self, owner_deduction_data, meta):
        """Merge RRSP deduction metadata for one owner across multiple accounts."""
        for key, raw_value in meta.items():
            match = self.DEDUCTION_KEY_PATTERN.match(str(key))
            if match is None:
                continue

            year = int(match.group(1))
            amount = self._coerce_decimal(raw_value)
            if amount is None:
                continue

            owner_deduction_data[year] = amount

    def _coerce_decimal(self, raw_value):
        """Return a Decimal room amount from metadata when possible."""
        if raw_value in (None, ""):
            return None

        try:
            return Decimal(str(raw_value))
        except (InvalidOperation, ValueError):
            return None

    def _is_room_exempt_transfer(self, entry, posting):
        """Return whether a posting should be excluded from RRSP contributions."""
        if self._meta_marks_room_exempt(entry.meta):
            return True

        if posting.meta and self._meta_marks_room_exempt(posting.meta):
            return True

        return False

    def _meta_marks_room_exempt(self, meta):
        """Return whether metadata marks a transfer as RRSP room exempt."""
        value = meta.get("rrsp_room_exempt")
        if value is None:
            return False

        return str(value).strip().upper() == self.EXEMPT_TRANSFER_VALUE

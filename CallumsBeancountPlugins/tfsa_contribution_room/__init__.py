from fava.ext import FavaExtensionBase
from beancount.core import data
from datetime import date
from collections import defaultdict
import decimal


class TFSAContributionRoom(FavaExtensionBase):
    report_title = "TFSA Room Tracker"

    TFSA_LIMITS = {
        2009: 5000,
        2010: 5000,
        2011: 5000,
        2012: 5000,
        2013: 5500,
        2014: 5500,
        2015: 10000,
        2016: 5500,
        2017: 5500,
        2018: 5500,
        2019: 6000,
        2020: 6000,
        2021: 6000,
        2022: 6000,
        2023: 6500,
        2024: 7000,
        2025: 7000,
        2026: 7000,
    }

    def get_all_tfsa_data(self):
        owners = defaultdict(list)
        owner_start_years = {}
        INTERNAL_ACCOUNTS = {
            "ZeroSumAccounts:Transfers",
            "Equity:Rounding-Errors:Imports",
        }

        for name in self.ledger.accounts:
            meta = self.ledger.accounts[name].meta
            if meta.get("canadian_tax_type") == "TFSA":
                owner = str(meta.get("owner", "Primary")).strip()
                owners[owner].append(name)

                meta_year = meta.get("start_year")
                if meta_year:
                    try:
                        year = int(meta_year)
                        if (
                            owner not in owner_start_years
                            or year < owner_start_years[owner]
                        ):
                            owner_start_years[owner] = year
                    except ValueError:
                        continue

        results = {}

        for owner, acc_list in owners.items():
            yearly_stats = defaultdict(lambda: {"contributions": 0, "withdrawals": 0})
            # Combine your TFSA accounts and transfer accounts into one "internal" set
            tfsa_and_internal = set(acc_list) | INTERNAL_ACCOUNTS

            for entry in self.ledger.all_entries:
                if not isinstance(entry, data.Transaction):
                    continue

                if entry.meta.get("type") == "transfer":
                    continue

                if any(
                    p.account.startswith(("Income:", "Expenses:"))
                    for p in entry.postings
                ):
                    continue

                # Skip transactions that are fully inside TFSA + known internal balancing accounts
                if all(p.account in tfsa_and_internal for p in entry.postings):
                    continue

                for posting in entry.postings:
                    if posting.account not in acc_list:
                        continue

                    if posting.meta and posting.meta.get("type") == "transfer":
                        continue

                    # Only count actual CAD cash, never securities valued via @ or cost
                    if posting.units.currency != "CAD":
                        continue

                    amount = posting.units.number
                    year = entry.date.year

                    if amount > 0:
                        yearly_stats[year]["contributions"] += amount
                    elif amount < 0:
                        yearly_stats[year]["withdrawals"] += abs(amount)

            # --- Room Calculation Logic ---
            start_year = owner_start_years.get(owner, 2009)
            current_year = date.today().year
            history = []
            running_room = 0
            carryover_withdrawals = 0

            for year in range(start_year, current_year + 1):
                limit = self.TFSA_LIMITS.get(year, 0)
                opening_room = running_room + limit + carryover_withdrawals

                contributions = yearly_stats[year]["contributions"]
                withdrawals = yearly_stats[year]["withdrawals"]
                closing_room = opening_room - contributions

                history.append(
                    {
                        "year": year,
                        "limit": limit,
                        "contributions": contributions,
                        "withdrawals": withdrawals,
                        "available": closing_room,
                    }
                )

                running_room = closing_room
                carryover_withdrawals = withdrawals

            results[owner] = history

        return results

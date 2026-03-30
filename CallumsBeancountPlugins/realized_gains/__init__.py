"""Fava extension for summarizing realized gains by year and owner.

This extension reads gain-related postings from the loaded ledger and presents
them in a compact table for review inside Fava. It is designed as a convenience
view over bookkeeping data and should not be treated as an authoritative tax
calculation.
"""

from fava.ext import FavaExtensionBase
from beancount.core.data import Transaction
from collections import defaultdict


class RealizedGains(FavaExtensionBase):
    """Render a gains summary table inside Fava.

    Add this extension to Fava to inspect yearly realized gains grouped by the
    person inferred from the account path. It is most useful when the ledger is
    also processed by ``CallumsBeancountPlugins.calculate_acb``.
    """

    report_title = "Realized Gains"

    def get_gains_data(self):
        """Aggregate gain-related postings into a table-friendly structure.

        The extension scans transactions for PnL postings and generated
        ``:CGDividend`` postings, infers the owner from the account path, and
        totals amounts by calendar year.

        Returns:
            A dictionary with ``persons`` and ``rows`` keys suitable for the
            accompanying Fava template.
        """
        # We use a nested dictionary: data[year][person] = amount
        data = defaultdict(lambda: defaultdict(float))
        persons = set()

        for entry in self.ledger.all_entries:
            if isinstance(entry, Transaction):
                year = entry.date.year

                for p in entry.postings:
                    # Target BOTH PnL accounts and the generated CGDividend accounts
                    if "PnL" in p.account or p.account.endswith(":CGDividend"):
                        # Extract the person's name from the account string
                        parts = p.account.split(":")
                        if len(parts) >= 4:
                            person = parts[2]
                            persons.add(person)

                            # Income postings in Beancount are negative for profit.
                            # We multiply by -1 so they display as positive gains on the dashboard.
                            amount = float(-p.units.number)
                            data[year][person] += amount

        # Sort the data so the newest years appear at the top
        sorted_years = sorted(data.keys(), reverse=True)
        sorted_persons = sorted(list(persons))

        results = []
        for year in sorted_years:
            row = {"year": year, "total": 0.0}
            for person in sorted_persons:
                amount = data[year][person]
                row[person] = round(amount, 2)
                row["total"] += amount
            row["total"] = round(row["total"], 2)
            results.append(row)

        return {"persons": sorted_persons, "rows": results}

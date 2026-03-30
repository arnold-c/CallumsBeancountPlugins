from fava.ext import FavaExtensionBase
from beancount.core.data import Transaction
from collections import defaultdict


class RealisedGains(FavaExtensionBase):
    report_title = "Realised Gains"

    def get_gains_data(self):
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

"""Fava extension for yearly expense summaries."""

from calendar import monthrange
from collections import defaultdict
from datetime import date

from beancount.core.data import Transaction
from fava.core.conversion import convert_position
from fava.ext import FavaExtensionBase


class Expenses(FavaExtensionBase):
    """Render yearly expense totals and averages inside Fava."""

    report_title = "Expenses"

    def get_expense_summary_data(self):
        """Aggregate expense postings into yearly totals and averages.

        The first table groups postings by calendar year and the second account
        segment under ``Expenses``. The second table divides each yearly total
        by the number of distinct months in that year that had any expense
        posting at all.
        """
        yearly_category_totals = defaultdict(lambda: defaultdict(float))
        yearly_active_months = defaultdict(set)
        yearly_completed_category_totals = defaultdict(
            lambda: defaultdict(float)
        )
        yearly_completed_months = defaultdict(set)
        categories = set()
        today = date.today()

        for entry in self.ledger.all_entries:
            if not isinstance(entry, Transaction):
                continue

            year = entry.date.year
            month_key = (entry.date.year, entry.date.month)
            month_end = date(
                entry.date.year,
                entry.date.month,
                monthrange(entry.date.year, entry.date.month)[1],
            )
            is_completed_month = month_end < today

            for posting in entry.postings:
                if not posting.account.startswith("Expenses:"):
                    continue

                converted = convert_position(
                    posting,
                    "CAD",
                    self.ledger.prices,
                    entry.date,
                )
                if converted.currency != "CAD":
                    continue

                parts = posting.account.split(":")
                category = parts[1] if len(parts) > 1 else posting.account
                amount = float(converted.number)

                categories.add(category)
                yearly_category_totals[year][category] += amount
                yearly_active_months[year].add(month_key)

                if is_completed_month:
                    yearly_completed_category_totals[year][category] += amount
                    yearly_completed_months[year].add(month_key)

        sorted_years = sorted(yearly_category_totals.keys(), reverse=True)
        sorted_categories = sorted(categories)

        total_rows = []
        average_rows = []
        months_by_year = {}
        total_by_year = {}
        average_months_by_year = {}
        average_total_by_year = {}

        for year in sorted_years:
            months_count = len(yearly_active_months[year])
            months_by_year[year] = months_count
            total_row = {"category": None}
            average_row = {"category": None}
            yearly_total = 0.0
            yearly_average_total = 0.0

            for category in sorted_categories:
                total_amount = yearly_category_totals[year][category]
                yearly_total += total_amount

            total_by_year[year] = round(yearly_total, 2)

            completed_months_count = len(yearly_completed_months[year])
            average_months_by_year[year] = completed_months_count
            for category in sorted_categories:
                total_amount = yearly_completed_category_totals[year][category]
                average_amount = (
                    total_amount / completed_months_count
                    if completed_months_count
                    else 0.0
                )
                yearly_average_total += average_amount

            average_total_by_year[year] = round(yearly_average_total, 2)

        for category in sorted_categories:
            total_row = {"category": category}
            average_row = {"category": category}

            for year in sorted_years:
                months_count = average_months_by_year[year]
                total_amount = yearly_category_totals[year][category]
                average_amount = (
                    yearly_completed_category_totals[year][category] / months_count
                    if months_count
                    else 0.0
                )

                total_row[year] = round(total_amount, 2)
                average_row[year] = round(average_amount, 2)

            total_rows.append(total_row)
            average_rows.append(average_row)

        return {
            "years": sorted_years,
            "categories": sorted_categories,
            "months_by_year": months_by_year,
            "average_months_by_year": average_months_by_year,
            "total_by_year": total_by_year,
            "average_total_by_year": average_total_by_year,
            "total_rows": total_rows,
            "average_rows": average_rows,
        }

from fava.ext import FavaExtensionBase
from beancount.core.number import ZERO
from beancount.core.data import Transaction
from collections import defaultdict


class ACBDashboard(FavaExtensionBase):
    report_title = "Canadian ACB"

    def get_acb_history(self):
        # 1. Fetch configuration from ledger
        target_prefixes = ()
        for p in self.ledger.options.get("plugin", []):
            if isinstance(p, tuple) and "calculate_acb" in p[0]:
                if p[1]:
                    target_prefixes = tuple(
                        prefix.strip() for prefix in p[1].split(",")
                    )
                break

        history = {}
        # Running totals as we walk through the ledger
        running_state = defaultdict(
            lambda: defaultdict(lambda: {"shares": ZERO, "acb_cad": ZERO})
        )

        current_year = None

        # 2. Iterate through entries
        for entry in self.ledger.all_entries:
            if not isinstance(entry, Transaction):
                continue

            entry_year = entry.date.year

            # When the year changes, check if the previous year had holdings
            if current_year is not None and entry_year > current_year:
                snap = self._snapshot_state(running_state)
                if snap:  # Only add to history if the snapshot contains data
                    history[current_year] = snap

            current_year = entry_year

            for p in entry.postings:
                # Filter for target Asset and TaxBasis accounts
                if (
                    target_prefixes
                    and not p.account.startswith(target_prefixes)
                    and "Assets:TaxBasis" not in p.account
                ):
                    continue

                # Handle Shares (Buys/Sells/DRIPs)
                if p.units.currency != "CAD" and p.price is not None:
                    acct = p.account
                    tckr = p.units.currency
                    cad_val = abs(p.units.number * p.price.number)

                    if p.units.number > ZERO:
                        running_state[acct][tckr]["shares"] += p.units.number
                        running_state[acct][tckr]["acb_cad"] += cad_val
                    elif p.units.number < ZERO:
                        curr_shares = running_state[acct][tckr]["shares"]
                        if curr_shares > ZERO:
                            avg = running_state[acct][tckr]["acb_cad"] / curr_shares
                            running_state[acct][tckr]["shares"] += p.units.number
                            running_state[acct][tckr]["acb_cad"] -= avg * abs(
                                p.units.number
                            )
                        else:
                            running_state[acct][tckr]["shares"] += p.units.number

                # Handle TaxBasis (Phantom/ROC)
                if "Assets:TaxBasis" in p.account:
                    parts = p.account.split(":")

                    # The Beancount plugin appends :{ticker}:{adj_type} to the end
                    tckr = parts[-2]

                    # Reconstruct the exact original Asset account name
                    # 1. Drop the ticker and adj_type from the end
                    tax_base_acct = ":".join(parts[:-2])
                    # 2. Revert Assets:TaxBasis back to Assets
                    acct = tax_base_acct.replace("Assets:TaxBasis", "Assets")

                    # Apply directly. (ROC is negative, Phantom is positive,
                    # so += works perfectly for both without needing to check the type)
                    if acct in running_state:
                        running_state[acct][tckr]["acb_cad"] += p.units.number

        # 3. Final snapshot for the current year
        if current_year:
            snap = self._snapshot_state(running_state)
            if snap:
                history[current_year] = snap

        return history

    def _snapshot_state(self, state):
        """Helper to return a dict of holdings only if shares > 0."""
        snapshot = {}
        for acct, tickers in state.items():
            acct_data = {}
            for tckr, data in tickers.items():
                if data["shares"] > ZERO:
                    acct_data[tckr] = {
                        "shares": data["shares"],
                        "total_acb": data["acb_cad"],
                        "avg_cost": data["acb_cad"] / data["shares"],
                    }
            if acct_data:
                snapshot[acct] = acct_data

        # Returns the dict if it has content, otherwise None
        return snapshot if snapshot else None

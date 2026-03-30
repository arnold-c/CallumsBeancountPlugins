from beangulp.exceptions import Error
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import D, ZERO
from collections import defaultdict, namedtuple

__plugins__ = ["calculate_acb"]

ACBError = namedtuple("ACBError", "source message entry")


def calculate_acb(entries, options_map, config=""):
    # 1. Parse the comma-separated string into a tuple of cleaned prefixes
    target_prefixes = tuple(p.strip() for p in config.split(",")) if config else ()

    new_entries = []
    errors = []

    # State machine: account -> ticker -> {'shares': Decimal, 'acb_cad': Decimal}
    state = defaultdict(lambda: defaultdict(lambda: {"shares": ZERO, "acb_cad": ZERO}))

    for entry in entries:
        # 1. Handle Year-End Custom Adjustments (ROC & Phantom)
        if isinstance(entry, data.Custom) and entry.type == "acb_adjust":
            account = entry.values[0].value
            account_tax = account.replace("Assets", "Assets:TaxBasis")
            account_base = account.replace("Assets", "Income")

            if target_prefixes and not account.startswith(target_prefixes):
                new_entries.append(entry)
                continue

            ticker = entry.values[1].value
            adj_type = entry.values[2].value

            # Grab current shares early since we need it for calculations
            current_shares = state[account][ticker]["shares"]

            if adj_type == "cg_split":
                if len(entry.values) < 5:
                    errors.append(
                        ACBError(
                            entry.meta,
                            "cg_split requires two amounts: Total CG, then Non-Cash Distribution (phantom)",
                            entry,
                        )
                    )
                    new_entries.append(entry)
                    continue

                input_total_cg = entry.values[3].value
                input_phantom = entry.values[4].value
                currency = input_total_cg.currency

                # Check for the per-share vs total flag (Defaults to per-share)
                calc_method = (
                    entry.values[5].value if len(entry.values) > 5 else "per-share"
                )

                # Calculate the two distinct CAD totals based on the flag
                if calc_method == "total":
                    phantom_val = round(input_phantom.number, 2)
                    cash_cg_val = round(input_total_cg.number - input_phantom.number, 2)
                elif calc_method == "per-share":
                    phantom_val = round(input_phantom.number * current_shares, 2)
                    cash_cg_val = round(
                        (input_total_cg.number - input_phantom.number) * current_shares,
                        2,
                    )
                else:
                    errors.append(
                        ACBError(
                            entry.meta,
                            f"Invalid flag '{calc_method}'. Use 'per-share' or 'total'.",
                            entry,
                        )
                    )
                    new_entries.append(entry)
                    continue

                amount_phantom = Amount(phantom_val, currency)
                amount_cash = Amount(cash_cg_val, currency)

                # Only the phantom portion increases the ACB
                state[account][ticker]["acb_cad"] += amount_phantom.number

                postings = [
                    # 1. Phantom Postings (Increases ACB, offsets PnL)
                    data.Posting(
                        f"{account_tax}:{ticker}:Phantom",
                        amount_phantom,
                        None,
                        None,
                        None,
                        None,
                    ),
                    data.Posting(
                        f"{account_base}:PnL:Long",
                        -amount_phantom,
                        None,
                        None,
                        None,
                        None,
                    ),
                    # 2. Cash CG Postings (Reclassifies standard dividend to CG, no ACB effect)
                    data.Posting(
                        f"{account_base}:Dividend", amount_cash, None, None, None, None
                    ),
                    data.Posting(
                        f"{account_base}:{ticker}:CGDividend",
                        -amount_cash,
                        None,
                        None,
                        None,
                        None,
                    ),
                ]

                narration = f"{ticker} - CG SPLIT ({calc_method.upper()} | Total: {input_total_cg.number}, Phantom: {input_phantom.number})"
            else:
                input_amount = entry.values[3].value

                # Check for the per-share vs total flag (Defaults to per-share)
                calc_method = (
                    entry.values[4].value if len(entry.values) > 4 else "per-share"
                )

                # If no shares are held at this date, skip the adjustment
                if current_shares <= ZERO:
                    errors.append(
                        ACBError(
                            entry.meta,
                            f"Invalid acb_adjust: {ticker} has {current_shares} shares in {account}",
                            entry,
                        )
                    )
                    new_entries.append(entry)
                    continue

                # Calculate the total CAD adjustment based on the flag
                if calc_method == "total":
                    total_value = round(input_amount.number, 2)
                elif calc_method == "per-share":
                    total_value = round(input_amount.number * current_shares, 2)
                else:
                    errors.append(
                        ACBError(
                            entry.meta,
                            f"Invalid flag '{calc_method}'. Use 'per-share' or 'total'.",
                            entry,
                        )
                    )
                    new_entries.append(entry)
                    continue

                amount = Amount(total_value, input_amount.currency)

                if adj_type == "phantom":
                    state[account][ticker]["acb_cad"] += amount.number
                    postings = [
                        data.Posting(
                            f"{account_tax}:{ticker}:Phantom",
                            amount,
                            None,
                            None,
                            None,
                            None,
                        ),
                        data.Posting(
                            f"{account_base}:PnL:Long",
                            -amount,
                            None,
                            None,
                            None,
                            None,
                        ),
                    ]
                elif adj_type == "roc":
                    state[account][ticker]["acb_cad"] -= amount.number
                    postings = [
                        data.Posting(
                            f"{account_tax}:{ticker}:ROC",
                            -amount,
                            None,
                            None,
                            None,
                            None,
                        ),
                        data.Posting(
                            f"{account_base}:Dividend",
                            amount,
                            None,
                            None,
                            None,
                            None,
                        ),
                    ]
                elif adj_type == "cg_dividend":
                    postings = [
                        data.Posting(
                            f"{account_base}:Dividend", amount, None, None, None, None
                        ),
                        data.Posting(
                            f"{account_base}:{ticker}:CGDividend",
                            -amount,
                            None,
                            None,
                            None,
                            None,
                        ),
                    ]
                else:
                    new_entries.append(entry)
                    continue

            # Transform the custom directive into a fully balanced transaction
            txn = data.Transaction(
                meta=entry.meta,
                date=entry.date,
                flag="*",
                payee="Generated Tax True-Up",
                narration=f"{ticker} - {adj_type.upper()} ({calc_method.upper()}: {input_amount.number if adj_type != 'cg_split' else input_phantom.number})",
                tags=set(),
                links=set(),
                postings=postings,
            )
            new_entries.append(txn)
            continue

        # 2. Handle Buys and Sells (Auto-calculating Capital Gains)
        if isinstance(entry, data.Transaction):
            new_postings = list(entry.postings)
            needs_mutation = False
            added_postings = []

            for p in entry.postings:
                if target_prefixes and not p.account.startswith(target_prefixes):
                    continue

                if p.units.currency != "CAD" and p.price is not None:
                    account = p.account
                    account_base = account.replace("Assets", "Income")
                    ticker = p.units.currency
                    shares = p.units.number

                    cad_value = abs(shares * p.price.number)

                    if shares > ZERO:  # BUY OR DRIP
                        state[account][ticker]["shares"] += shares
                        state[account][ticker]["acb_cad"] += cad_value

                    elif shares < ZERO:  # SELL
                        current_shares = state[account][ticker]["shares"]
                        current_acb = state[account][ticker]["acb_cad"]

                        if current_shares > ZERO:
                            avg_cost_per_share = current_acb / current_shares
                            cost_of_sale = avg_cost_per_share * abs(shares)
                            gain = cad_value - cost_of_sale

                            state[account][ticker]["shares"] += shares
                            state[account][ticker]["acb_cad"] -= cost_of_sale

                            gain_amount = Amount(round(gain, 2), "CAD")
                            account_parts = account.split(":")
                            person = (
                                account_parts[2]
                                if len(account_parts) > 2
                                else "Unknown"
                            )

                            added_postings.append(
                                data.Posting(
                                    f"{account_base}:PnL:Long",
                                    -gain_amount,
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                            added_postings.append(
                                data.Posting(
                                    f"Equity:{person}:RealisedGains",
                                    gain_amount,
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            )
                            needs_mutation = True

            if needs_mutation:
                new_postings.extend(added_postings)
                entry = entry._replace(postings=new_postings)

        new_entries.append(entry)

    return new_entries, errors

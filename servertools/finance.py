"""Methods for financial analysis"""
from datetime import datetime
import pandas as pd
import piecash
from kavalkilu import DateTools


class GNUCash:
    """Communicates with a gnucash file"""
    def __init__(self, fpath: str):
        self.fpath = fpath
        # Datetool for making it easier to handle dates
        self.dt = DateTools()

    def filter_transactions(self, start: datetime = None, end: datetime = None, account_name: str = None,
                            account_fullname: str = None, split_type: str = None) -> pd.DataFrame:
        """Filters all transactions falling in a certain month
        Args:
            start: start date to filter on
            end: end date to filter on
            account_name: the name of the account to filter on
            account_fullname: the full path of the account to filter on
            split_type: the type of split to filter on (e.g., expense, income, asset, etc...)
        """
        desired_columns = {
            'transaction.post_date': 'date',
            'account.fullname': 'account_fullname',
            'value': 'amount',
            'memo': 'memo',
            'transaction.description': 'desc',
            'transaction.currency.mnemonic': 'cur'
        }
        with piecash.open_book(self.fpath, open_if_lock=True, readonly=True) as mybook:
            df = mybook.splits_df()
            df = df.sort_values(['transaction.post_date', 'transaction.guid'])
            df = df[desired_columns.keys()].reset_index(drop=True).rename(columns=desired_columns)
            # Extract the split type and actual account name from the full account name
            df['type'] = df['account_fullname'].str.split(':').apply(lambda x: x[0])
            df['account'] = df['account_fullname'].str.split(':').apply(lambda x: x[-1])
            # Handle (messy) filtering
            if start is not None:
                df = df[df['date'] >= start.date()]
            if end is not None:
                df = df[df['date'] <= end.date()]
            if account_name is not None:
                df = df[df['account'].str.lower() == account_name.lower()]
            if account_fullname is not None:
                df = df[df['account_fullname'].str.lower() == account_fullname.lower()]
            if split_type is not None:
                df = df[df['type'].str.lower() == split_type.lower()]
            # Convert amounts to float
            df['amount'] = df['amount'].astype(float)

        return df.reset_index(drop=True)

    def get_budget_by_name(self, budget_name: str, budget_month: datetime) -> pd.DataFrame:
        """Fetches the budget items for the budget name for the given month"""
        budget_month = budget_month.replace(day=1)
        with piecash.open_book(self.fpath, open_if_lock=True, readonly=True) as mybook:
            accounts = mybook.accounts
            bdict = {}
            for account in accounts:
                bud_amts = account.budget_amounts
                for ba in bud_amts:
                    if ba.budget.name != budget_name:
                        continue
                    budget_start = ba.budget.recurrence.recurrence_period_start
                    budget_month = budget_start.replace(month=budget_start.month + ba.period_num)
                    item_dict = {
                        'month': budget_month,
                        'account_fullname': account.fullname,
                        'account': account.fullname.split(':')[-1],
                        'type': account.fullname.split(':')[0],
                        'amount': float(ba.amount),
                        'cur': account.commodity.mnemonic
                    }
                    bdict[ba.id] = item_dict
        df = pd.DataFrame(bdict).transpose()
        df = df[df['month'] == budget_month].sort_values('account_fullname')
        return df

    def generate_monthly_budget_v_actual(self, month: datetime, budget_name: str) -> pd.DataFrame:
        """Generates a monthly budget versus actual comparison"""
        start = month.replace(day=1)
        end = self.dt.last_day_of_month(month)
        # Get budget info
        budget = self.get_budget_by_name(budget_name, month)
        budget = budget.rename(columns={'amount': 'budget'}).drop('month', axis=1)
        # Get actual transactions
        actual = self.filter_transactions(start=start, end=end)
        # Group transactions by account
        actual = actual.groupby(['account_fullname', 'account', 'type', 'cur'], as_index=False).sum()
        actual = actual.rename(columns={'amount': 'actual'})
        # Make income positive
        actual.loc[actual['type'] == 'Income', 'actual'] = actual[actual['type'] == 'Income'] * -1
        # Merge budget w/ actual
        merged = pd.merge(actual, budget, on=['account_fullname', 'account', 'type', 'cur'], how='left')
        # Calculate differences column
        merged['diff'] = merged['actual'] - merged['budget']
        return merged

    def generate_daily_account_summary(self, start: datetime, end: datetime, account: str):
        """Generates a daily account summary for a given account"""
        # TODO This
        pass

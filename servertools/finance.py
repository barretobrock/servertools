"""Methods for financial analysis"""
import re
import requests
from datetime import datetime
from typing import Dict, List, Union, Tuple
import pandas as pd
import numpy as np
import piecash
from kavalkilu import DateTools, LogWithInflux, Keys
from .selenium import BrowserAction


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


class Stock:
    def __init__(self, stock_resp: Dict, fund_resp: Dict):
        # From basic stock info
        self.symbol = stock_resp.get('symbol')
        self.bid = stock_resp.get('bidPrice')
        self.ask = stock_resp.get('askPrice')
        self.last = stock_resp.get('lastPrice')
        self.open = stock_resp.get('openPrice')
        self.high52wk = stock_resp.get('52WkHigh')
        self.low52wk = stock_resp.get('52WkLow')
        self.volatility = stock_resp.get('volatility')
        self.pe = stock_resp.get('peRatio')
        self.div_amount = stock_resp.get('divAmount')
        self.div_yield = stock_resp.get('divYield')
        # From fundamental info
        fund_info = fund_resp.get('fundamental')
        self.pbr = fund_info.get('pbRatio')  # price to book
        self.roe = fund_info.get('returnOnEquity')
        self.roa = fund_info.get('returnOnAssets')
        self.quick = fund_info.get('quickRatio')
        self.current = fund_info.get('currentRatio')


class Ameritrade:
    """Wrapper for collecting stock info from TD Ameritrade"""
    QUOTE_URL = 'https://api.tdameritrade.com/v1/marketdata/{ticker}/quotes?'
    FUNDAMENTAL_URL = 'https://api.tdameritrade.com/v1/instruments?&symbol={ticker}&projection=fundamental'

    def __init__(self):
        self.api_key = Keys().get_key('td-ameritrade-developer').get('CONSUMER_KEY')

    def _request(self, url: str) -> Dict:
        """Process request"""
        page = requests.get(url, params={'apikey': self.api_key})
        page.raise_for_status()
        return page.json()

    def get_quote(self, ticker: str) -> Stock:
        """Retrieves stock info"""
        stock_resp = self._request(self.QUOTE_URL.format(ticker=ticker))
        fund_resp = self._request(self.FUNDAMENTAL_URL.format(ticker=ticker))
        return Stock(stock_resp.get(ticker), fund_resp.get(ticker))


class InvestmentResearch(Ameritrade):
    def __init__(self, log: LogWithInflux):
        super().__init__()
        self.log = log
        self.ba = None

    def _initialize_browser(self):
        """Initializes the Selenium browser"""
        self.ba = BrowserAction(headless=True, parent_log=self.log)

    def collect_ratios(self, tickers: Union[str, List[str]]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Handles all the processes for collecting financials and other info"""
        if self.ba is None:
            self._initialize_browser()
        if isinstance(tickers, str):
            tickers = [tickers]

        ratios_df = pd.DataFrame()
        summary_df = pd.DataFrame()
        for ticker in tickers:
            self.log.debug(f'Beginning work on {ticker}')
            # Get current stock info
            current_stock = self.get_quote(ticker)
            # Get income statements / balance sheet info for the past few quarters
            self.log.debug('Working on Income Statement')
            income_stmt = self.get_income_statement_history(ticker, is_quarterly=True)
            self.log.debug('Working on Balance Sheet')
            balance_sheet = self.get_balance_sheet_history(ticker, is_quarterly=True)
            # Combine IS and BS
            self.log.debug('Combining info into ratios')
            ratio_df = self.apply_fundamental_ratios(income_stmt, balance_sheet)
            ratio_df['ticker'] = ticker
            ratios_df = ratios_df.append(ratio_df)
            # Summarize the ratios
            sdf = pd.DataFrame({'ticker': ticker}, [0])
            for col in ratio_df.columns.tolist()[:-1]:
                x = np.arange(0, len(ratio_df))
                y = ratio_df[col]
                X = x - x.mean()
                Y = y - y.mean()
                slope = (X.dot(Y)) / (X.dot(X))
                sdf[f'{col}_M'] = slope
                sdf[f'{col}_P50'] = ratio_df[col].median()
                sdf[f'{col}_max'] = ratio_df[col].max()
            summary_df = summary_df.append(sdf)

        if self.ba is not None:
            # Close the broswer session
            self.ba.tear_down()
            self.ba = None

        return ratios_df, summary_df

    def _load_stmt_page(self, url: str, is_quarterly: bool = True):
        """Shared method for loading the IS/BS statement pages"""
        self.ba.get(url)
        self.ba.fast_wait()
        if is_quarterly:
            # Click the button to load quarterly info
            qt_btn = self.ba.get_elem(
                '//section[@data-test="qsp-financial"]/div/div/button[div/span[contains(., "Quarterly")]]')
            self.ba.scroll_to_element(qt_btn)
            qt_btn.click()
            self.ba.fast_wait()

    def _grab_tbl_headers(self) -> List[str]:
        """Returns the headers of the table"""
        hdr = self.ba.get_elem('//div[@class="D(tbhg)"]/div[contains(@class, "D(tbr)")]')
        dates = []
        for hd in hdr.find_elements_by_xpath('.//div/span'):
            if 'breakdown' not in hd.text.lower():
                dates.append(hd.text)
        return dates

    def _grab_desired_rows(self, desired_rows: List[str]) -> Dict[str, List[float]]:
        """Returns the rows that match desired_rows (lowercase enforced)"""
        rows = self.ba.get_elem('.//div[@data-test="fin-row"]', single=False)
        item_dict = {}
        for row in rows:
            # Get title row
            title = row.find_element_by_xpath('.//div/div[@title]').text
            if title.lower() in desired_rows:
                # Get the data
                raw_data = row.find_elements_by_xpath('.//div/div[@data-test="fin-col"]/span')
                processed_data = []
                for cell in raw_data:
                    if cell.text.strip() != '-':
                        value = float(''.join(re.findall(r'\d+\.?', cell.text)))
                    else:
                        value = 0
                    processed_data.append(value)
                item_dict[title] = processed_data
        return item_dict

    @staticmethod
    def _process_stmt_data(date_col: List[str], data_dict: Dict[str, List[float]]) -> pd.DataFrame:
        """Processes the statement info collected into a dataframe"""
        df = pd.DataFrame(columns=date_col)
        for k, v in data_dict.items():
            if len(v) > len(date_col):
                # Sometimes lower, hidden items are included, but horizontal order of the row is preserved.
                v = v[:len(date_col)]
            elif len(v) < len(date_col):
                # If the data we've scraped doesn't match the length of the date columns,
                # let's make a (possibly foolish) assumption that the newest (TTM) column has the blank info in it
                # and thus, we'll insert a NULL value at the beginning of this list
                v = [None] + v
            df.loc[k] = v
        # Return processed dataframe, remove TTM column if it exists, as the BS likely won't have it
        return df.drop('TTM', errors='ignore', axis=1)

    def get_income_statement_history(self, ticker: str, is_quarterly: bool = True) -> pd.DataFrame:
        """Collects income statement info"""
        if self.ba is None:
            self._initialize_browser()
        url = f'https://finance.yahoo.com/quote/{ticker}/financials?p={ticker}'
        self._load_stmt_page(url, is_quarterly)
        # Headers
        dates = self._grab_tbl_headers()
        # Set the desired rows to capture
        desired_rows = [
            'total revenue',
            'cost of revenue',
            'gross profit',
            'operating income',
            'net income common stockholders',
            'total expenses',
            'normalized ebitda',
            'basic eps'
        ]
        # Line items
        item_dict = self._grab_desired_rows(desired_rows)
        # Make the IncomeStmt dataframe
        return self._process_stmt_data(dates, item_dict)

    def get_balance_sheet_history(self, ticker: str, is_quarterly: bool = True) -> pd.DataFrame:
        """Collects income statement info"""
        url = f'https://finance.yahoo.com/quote/{ticker}/balance-sheet?p={ticker}'
        self._load_stmt_page(url, is_quarterly)
        # Headers
        dates = self._grab_tbl_headers()
        # Set the desired rows to capture
        desired_rows = [
            'total assets',
            'total liabilities net minority interest',
            'total equity gross minority interest',
            'common stock equity',
            'net tangible assets',
            'tangible book value',
            'ordinary shares number',
            'total debt'
        ]
        # Line items
        item_dict = self._grab_desired_rows(desired_rows)
        # Make the dataframe
        return self._process_stmt_data(dates, item_dict)

    @staticmethod
    def apply_fundamental_ratios(is_df: pd.DataFrame, bs_df: pd.DataFrame) -> pd.DataFrame:
        """Takes in dataframe with IS and BS info, outputs a dataframe of fundamental analysis ratios
            along with a sentiment analysis

            Ratios: https://www.wallstreetmojo.com/financial-ratios/
        """
        df = pd.concat([is_df, bs_df]).drop('TTM', errors='ignore', axis=1)
        # create mapping of financial items to an easier-to-handle style
        fin_mapping = {
            'Total Revenue': 'REV',
            'Cost of Revenue': 'COGS',
            'Gross Profit': 'GP',
            'Operating Income': 'OI',
            'Net Income Common Stockholders': 'NI',
            'Total Expenses': 'TEX',
            'Normalized EBITDA': 'EBITDA',
            'Basic EPS': 'EPS',
            'Total Assets': 'TA',
            'Total Liabilities Net Minority Interest': 'TL',
            'Total Equity Gross Minority Interest': 'TEQ',
            'Common Stock Equity': 'CSEQ',
            'Net Tangible Assets': 'NTA',
            'Total Debt': 'TD',
            'Tangible Book Value': 'BV',
            'Ordinary Shares Number': 'SH'
        }
        df = df.rename(index=fin_mapping)
        # Begin building out financial ratios
        ratios = pd.DataFrame()
        ratios['ATO'] = df.loc['REV'] / df.loc['NTA']  # Asset Turnover
        ratios['PM'] = df.loc['NI'] / df.loc['REV']  # Profit Margin
        ratios['D2EBITDA'] = df.loc['TL'] / df.loc['EBITDA']  # Debt to EBITDA
        ratios['D2E'] = df.loc['TL'] / df.loc['CSEQ']  # Debt to Equity
        ratios['ROA'] = df.loc['NI'] / df.loc['TA']  # Return on Assets
        ratios['ROE'] = df.loc['NI'] / df.loc['CSEQ']  # Return on Equity
        ratios['BVPS'] = df.loc['BV'] / df.loc['SH']  # Book Value per Share
        ratios['EPS'] = df.loc['EPS']
        # 'Flip' the rows such that the table presents in chronological order
        ratios = ratios.sort_index()
        return ratios

    def get_ratings(self, ticker: str) -> float:
        """Gets the current analyst buy rating"""
        url = f'https://finance.yahoo.com/quote/D/analysis?p={ticker}'
        self.ba.get(url)
        self.ba.fast_wait()
        rating = self.ba.get_elem('//div[@data-test="rec-rating-txt"]').text
        return float(rating)

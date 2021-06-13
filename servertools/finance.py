"""Methods for financial analysis"""
import os
import re
import requests
import tempfile
from datetime import datetime
from typing import Dict, List, Union, Tuple, Optional
import pandas as pd
import piecash
import edgar
from kavalkilu import DateTools, LogWithInflux, Keys
from .text import XPathExtractor


class GNUCash:
    """Communicates with a gnucash file"""
    def __init__(self, fpath: str):
        self.fpath = fpath
        assert os.path.exists(self.fpath), f"Invalid path: {self.fpath}"
        # Datetool for making it easier to handle dates
        self.dt = DateTools()

    def filter_transactions(self, start: datetime = None, end: datetime = None,
                            filter_accounts: Union[str, List[str]] = None, filter_accounts_fullname: str = None,
                            filter_types: List[str] = None, filter_desc: List[str] = None,
                            groupby_list: List[str] = None) -> pd.DataFrame:
        """Filters all transactions falling in a certain month
        Args:
            start: start date to filter on
            end: end date to filter on
            filter_accounts: the name(s) of the account(s) to filter on
            filter_accounts_fullname: the full path of the account to filter on
            filter_types: the type of transaction splits to filter on (e.g., Expenses, Income, Asset, etc...)
            filter_desc: filter on the descriptions of the transactions
            groupby_list: list of columns to group by (date, account, desc, cur, etc...)
        """
        if filter_accounts is not None:
            if isinstance(filter_accounts, str):
                filter_accounts = [filter_accounts]

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
        # Get the 1st account name after the account type
        df['parent_account'] = df['account_fullname'].str.split(':').apply(lambda x: x[1])
        # Handle (messy) filtering
        if start is not None:
            df = df[df['date'] >= start.date()]
        if end is not None:
            df = df[df['date'] <= end.date()]
        if filter_accounts is not None:
            df = df[df['account'].isin(filter_accounts)]
        if filter_accounts_fullname is not None:
            df = df[df['account_fullname'].isin(filter_accounts_fullname)]
        if filter_types is not None:
            df = df[df['type'].isin(filter_types)]
        if filter_desc is not None:
            df = df[df['desc'].isin(filter_desc)]
        # Convert amounts to float
        df['amount'] = df['amount'].astype(float)
        # Set final column order
        final_cols = ['date', 'account_fullname', 'type', 'account', 'desc', 'memo', 'amount', 'cur']
        df = df[final_cols].reset_index(drop=True)

        if groupby_list is not None:
            # Perform grouping before returning
            df = df.groupby(groupby_list, as_index=False).sum()

        return df

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

    def generate_monthly_budget_v_actual(self, month: datetime, budget_name: str,
                                         filter_types: List[str] = None) -> pd.DataFrame:
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
        if filter_types is not None:
            merged = merged[merged['type'].isin(filter_types)]
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


class EdgarFinStatement:
    """Methods associated with the collection and processing
    of financial statement info from EDGAR"""
    def __init__(self, url_to_extract: str, stmt_contains_txt: str):
        """
        Args:
            url_to_extract: the url from which to build an XPath tree
        """
        self.xpe = XPathExtractor(url_to_extract)
        # Xpath extract the statement section
        self.section = self.get_statement_table(self.xpe, stmt_contains_txt)

    @staticmethod
    def lowercase_translate() -> str:
        """Casts uppercase text in an element to lowercase"""
        return f"translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"

    def get_line_item(self, line_contains: str, line_after: bool = False) -> Optional[float]:
        """Returns the first numerical line item from the left matching the string provided"""
        # Generate xpath
        xpth_str = f'./tr[./td/div/font[contains({self.lowercase_translate()}, "{line_contains.lower()}")]]'
        line = self.xpe.xpath(xpth_str, obj=self.section, single=True)
        if line_after:
            line = line.getnext()
        tds = self.xpe.xpath('./td[div/font]', obj=line)
        for td in tds:
            item = self.xpe.xpath('./div/font', obj=td, single=True).text
            if item is not None:
                if re.match(r'[\d,.\s]+', item) is not None:
                    # Get only numeric
                    item = ''.join(re.findall(r'[\d.]+', item))
                    try:
                        return float(item)
                    except ValueError:
                        continue
        return None

    @staticmethod
    def get_statement_table(xpe: XPathExtractor, contains_text: str) -> '_Element':
        """Returns a table that contains statement info"""
        table_xpath = f'//*[font[re:match(text(), "{contains_text}")]]/following::div/div/table'

        return xpe.xpath_with_regex(table_xpath, single=True)


class EdgarCollector:
    """Handles the entire process of collecting SEC filing data and processing that into financial ratios"""
    base_url = 'https://www.sec.gov'

    def __init__(self, start_year: float = 2017, parent_log: LogWithInflux = None):
        self.logg = LogWithInflux(parent_log, child_name=self.__class__.__name__)
        # Set temp dir for downloading the edgar filings
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'edgar')
        # Get ticker to CIK mapping
        self.logg.debug('Downloading ticket to CIK mapping...')
        self.t2cik_df = self.get_ticker_to_cik_map()
        # Download EDGAR indexes and retrieve the filepaths associated with them
        self.logg.debug('Downloading indexes (this may take ~2 mins)...')
        self.edgar_fpaths = self._download_indexes(start_year)

    @staticmethod
    def get_ticker_to_cik_map() -> pd.DataFrame:
        """Collects the mapping of stock ticker to CIK"""
        t2cik_df = pd.read_csv('https://www.sec.gov/include/ticker.txt', sep='\t', header=None)
        t2cik_df.columns = ['tick', 'cik']
        return t2cik_df

    def _download_indexes(self, since_year: float) -> List[str]:
        """Downloads company indexes from Edgar into temporary directory"""
        # Begin download
        edgar.download_index(self.tmp_dir, since_year=since_year)
        # Retrieve the file paths downloaded
        fpaths = []
        for a, b, fnames in os.walk(self.tmp_dir):
            fpaths = [os.path.join(self.tmp_dir, f) for f in fnames]
            break
        self.logg.debug(f'Collected {len(fpaths)} files...')
        return sorted(fpaths)

    def get_data_for_stock_tickers(self, tickers: Union[str, List[str]]) -> pd.DataFrame:
        """Collects the quarterly financial ratios for a given stock ticker"""
        if isinstance(tickers, str):
            tickers = [tickers]

        stocks_df = pd.DataFrame({'tick': list(map(str.lower, tickers))})
        # Merge stocks on cik
        stocks_df = stocks_df.merge(self.t2cik_df, how='left', on='tick')

        ratio_df = pd.DataFrame()
        # Capture filing locations for each quarter for each stock
        for i, fpath in enumerate(sorted(self.edgar_fpaths)):
            self.logg.debug(f'Working on file {i + 1} of {len(self.edgar_fpaths)}')
            # Parse the quarter
            year, qtr = os.path.split(fpath)[1].split('.')[0].split('-')
            self.logg.debug(f'Parsed: {qtr}-{year}')
            df = pd.read_csv(fpath, sep='|', header=None)
            df.columns = ['cik', 'company_name', 'form', 'filing_date', 'txt_file', 'html_file']
            # Filter by CIK and on either 10-K (annual) or 10-Q (quarterly) reports
            df = df.loc[df.cik.isin(stocks_df.cik) & df.form.isin(['10-Q', '10-K'])]
            self.logg.debug(f'Matched {df.shape[0]} rows of data')
            for idx, row in df.iterrows():
                # Grab the HTML file - this is the file list
                url = f'{self.base_url}/Archives/{row["html_file"]}'
                xpe = XPathExtractor(url)
                # Grab the link to the 10-* file
                form_type = row['form']
                form_row = xpe.xpath(f'//table[@class="tableFile"]/tr[td[text()="{form_type}"]]', single=True)
                form_url = xpe.xpath('./td/a', obj=form_row, single=True).get('href')

                # Grab the 10-* file data
                complete_url = f'{self.base_url}{form_url}'

                # Work on SOps (this sets a point to look 'after')
                stmt_ops = EdgarFinStatement(complete_url, 'STATEMENTS? OF OPERATIONS')
                net_sales = stmt_ops.get_line_item('net sales')
                cogs = stmt_ops.get_line_item('cost of sales')
                op_income = stmt_ops.get_line_item('operating income')
                net_income = stmt_ops.get_line_item('net income')
                eps = stmt_ops.get_line_item('earnings per share', line_after=True)
                shares = stmt_ops.get_line_item('shares used in computing earnings', line_after=True)

                # Work on Balance Sheet
                stmt_bs = EdgarFinStatement(complete_url, 'CONSOLIDATED BALANCE SHEETS')
                current_assets = stmt_bs.get_line_item('total current assets')
                intangible_assets = stmt_bs.get_line_item('intangible assets')
                total_assets = stmt_bs.get_line_item('total assets')
                current_liabilities = stmt_bs.get_line_item('total current liabilities')
                total_liabilities = stmt_bs.get_line_item('total liabilities')
                common_stock_eq = stmt_bs.get_line_item('common stock')
                total_shareholders_equity = stmt_bs.get_line_item('total shareholders')
                net_tangible_assets = total_assets - intangible_assets - total_liabilities

                # Work on Cash Flow (SCF)
                stmt_cf = EdgarFinStatement(complete_url, 'STATEMENTS OF CASH FLOWS')
                dep_and_amort = stmt_cf.get_line_item('depreciation and amortization')
                ebitda = op_income + dep_and_amort

                # Ratios
                asset_turnover = net_sales / net_tangible_assets
                profit_margin = net_income / net_sales
                debt_to_ebitda = total_liabilities / ebitda
                debt_to_equity = total_liabilities / total_shareholders_equity
                roa = net_income / total_assets
                roe = net_income / total_shareholders_equity
                bvps = total_shareholders_equity / shares

                # Apply ratios to dataframe
                ratio_df = ratio_df.append({
                    'year': year,
                    'quarter': qtr,
                    'cik': row['cik'],
                    'source': row['form'],
                    'ato': asset_turnover,
                    'pm': profit_margin,
                    'd2ebitda': debt_to_ebitda,
                    'd2e': debt_to_equity,
                    'roa': roa,
                    'roe': roe,
                    'bvps': bvps
                }, ignore_index=True)

        # Merge the financial info back in with the stocks
        stocks_df = stocks_df.merge(ratio_df, how='left', on='cik')
        return stocks_df

import os
import unittest
from datetime import datetime
from kavalkilu import LogWithInflux
from servertools import GNUCash, InvestmentResearch


class TestGNUCash(unittest.TestCase):
    """Test suite for GNUCash"""

    @classmethod
    def setUpClass(cls) -> None:
        fpath = os.path.join(os.path.expanduser('~'), *['Dropbox', 'Finance', 'GNUCash_2020', 'GNUCash2020_SQL.gnucash'])
        cls.gcash = GNUCash(fpath)

    def setUp(self) -> None:
        self.start = datetime(2020, 12, 1)
        self.end = datetime(2020, 12, 31)

    def test_transaction_filter(self):
        """Test filtering transactions for the month provided"""
        df = self.gcash.filter_transactions(start=self.start, end=self.end)
        self.assertTrue(not df.empty)

    def test_budget_filter(self):
        """Test filtering transactions for the month provided"""
        df = self.gcash.get_budget_by_name('Q4 2020', self.start)
        self.assertTrue(not df.empty)

    def test_budget_v_actual(self):
        """Test filtering transactions for the month provided"""
        month = datetime(2020, 12, 20)
        df = self.gcash.generate_monthly_budget_v_actual(month, 'Q4 2020')
        self.assertTrue(not df.empty)


class TestInvestmentResearch(unittest.TestCase):
    """Test suite for InvestmentResearch"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = LogWithInflux('invest-test')
        cls.invest = InvestmentResearch(log=cls.log)

    def test_stock_data_collection(self):
        tickers = ['PG', 'MMM']
        ratios = self.invest.collect_ratios(tickers)


if __name__ == '__main__':
    unittest.main()

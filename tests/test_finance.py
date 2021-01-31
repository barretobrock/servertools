import os
import unittest
from datetime import datetime
from kavalkilu import LogWithInflux, Keys
from servertools import GNUCash, EdgarCollector


class TestGNUCash(unittest.TestCase):
    """Test suite for GNUCash"""

    @classmethod
    def setUpClass(cls) -> None:
        props = Keys().get_key('gnucash-report')
        cls.gcash = GNUCash(props.get('path'))

    def setUp(self) -> None:
        self.start = datetime.now().replace(day=1)
        self.end = datetime.now()

    def test_transaction_filter(self):
        """Test filtering transactions for the month provided"""
        df = self.gcash.filter_transactions(start=self.start, end=self.end)
        self.assertTrue(not df.empty)

        # Test more robust filtering
        df = self.gcash.filter_transactions(start=self.start, end=self.end, filter_types=['Expenses'],
                                            filter_desc=['Amazon.com Order'],
                                            groupby_list=['type', 'desc', 'account'])
        self.assertTrue(not df.empty)

    def test_budget_filter(self):
        """Test filtering transactions for the month provided"""
        df = self.gcash.get_budget_by_name('Q4 2020', self.start)
        self.assertTrue(not df.empty)

    def test_budget_v_actual(self):
        """Test filtering transactions for the month provided"""
        month = datetime.now()
        df = self.gcash.generate_monthly_budget_v_actual(month, 'Budget 2021',
                                                         filter_types=['Income', 'Expenses'])
        self.assertTrue(not df.empty)


class TestInvestmentResearch(unittest.TestCase):
    """Test suite for InvestmentResearch"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.log = LogWithInflux('invest-test')
        cls.ed = EdgarCollector(start_year=2017, parent_log=cls.log)

    def test_stock_data_collection(self):
        tickers = ['PG', 'MMM']
        df = self.ed.get_data_for_stock_tickers(tickers)


if __name__ == '__main__':
    unittest.main()

import os
import unittest
from datetime import datetime
from servertools import GNUCash


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


if __name__ == '__main__':
    unittest.main()

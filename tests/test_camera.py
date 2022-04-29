import unittest
from datetime import datetime as dt
from pukr import get_logger
from kavalkilu import Hosts
from servertools import Amcrest


class AmcrestTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.logg = get_logger('cam-test')


if __name__ == '__main__':
    unittest.main()

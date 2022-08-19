import unittest

from pukr import get_logger


class AmcrestTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.logg = get_logger('cam-test')


if __name__ == '__main__':
    unittest.main()

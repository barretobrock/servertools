import unittest

from servertools import (
    OpenWeather,
    OWMLocation,
    YRNOLocation,
    YrNoWeather,
)


class TestOpenWeather(unittest.TestCase):
    """Test suite for OpenWeather """

    @classmethod
    def setUpClass(cls) -> None:
        cls.owmapi = OpenWeather(OWMLocation.ATX)

    def setUp(self) -> None:
        pass

    def test_current_weather(self):
        """Test getting current weather for the location provided"""
        pass


class TestYRNOWeather(unittest.TestCase):
    """Test suite for YRNO """

    @classmethod
    def setUpClass(cls) -> None:
        cls.yrno = YrNoWeather(YRNOLocation.ATX)

    def setUp(self) -> None:
        pass

    def test_current_weather(self):
        """Test getting current weather for the location provided"""
        pass


if __name__ == '__main__':
    unittest.main()

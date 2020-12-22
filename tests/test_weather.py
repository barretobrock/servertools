import unittest
from servertools import OWMLocation, OpenWeather, YRNOLocation, YrNoWeather


class TestOpenWeather(unittest.TestCase):
    """Test suite for OpenWeather """

    @classmethod
    def setUpClass(cls) -> None:
        cls.owmapi = OpenWeather(OWMLocation.ATX)

    def setUp(self) -> None:
        pass

    def test_current_weather(self):
        """Test getting current weather for the location provided"""
        result = self.owmapi.current_weather()
        self.assertTrue(not result.empty)

    def test_daily_report(self):
        df = self.owmapi.daily_summary()
        self.assertTrue(not df.empty)

    def test_hourly_report(self):
        df = self.owmapi.hourly_forecast()
        self.assertTrue(not df.empty)

    def test_3h_report(self):
        df = self.owmapi.three_hour_forecast()
        self.assertTrue(not df.empty)


class TestYRNOWeather(unittest.TestCase):
    """Test suite for YRNO """

    @classmethod
    def setUpClass(cls) -> None:
        cls.yrno = YrNoWeather(YRNOLocation.ATX)

    def setUp(self) -> None:
        pass

    def test_current_weather(self):
        """Test getting current weather for the location provided"""
        result = self.yrno.current_summary()
        self.assertTrue(not result.empty)

    def test_daily_report(self):
        df = self.yrno.daily_summary()
        self.assertTrue(not df.empty)

    def test_hourly_report(self):
        df = self.yrno.hourly_summary()
        self.assertTrue(not df.empty)


if __name__ == '__main__':
    unittest.main()

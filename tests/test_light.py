import unittest

from servertools import (
    HueBulb,
    HueSensor,
)
from tests.common import make_patcher


class TestHueBulb(unittest.TestCase):
    """Test suite for Hue Bulb """

    def setUp(self) -> None:
        self.mock_hue_bridge = make_patcher(self, 'servertools.light.HueBridge')

    def test_color_light(self):
        """Test standard procedures associated with a color-capable light"""
        self.mock_hue_bridge.return_value.get_light.return_value = 'color bulb'
        light = HueBulb('floor-lamp')
        self.assertTrue(light.is_color_bulb)
        # Turning off/on
        light.turn_on()
        # self.assertTrue(light.on)
        light.turn_off()

    def test_white_light(self):
        """Test procedures associated with a standard white cool/warm light"""
        light2 = HueBulb('kontor-lamp')
        light2.turn_on()
        # Make sure color calls fail gracefully
        light2.set_color(light2.DEEP_BLUE)
        light2.turn_off()
        light2.toggle()
        light2.toggle()

    def test_sensor(self):
        sensor = HueSensor('garage-sensor')
        sensor.turn_on()
        sensor.turn_off()
        sensor.toggle()


class TestHueSensor(unittest.TestCase):
    """Test suite for the HueSensor class"""
    def setUp(self) -> None:
        self.mock_hue_bridge = make_patcher(self, 'servertools.light.HueBridge')

    def test_motion_sensor(self):
        """Test standard procedures associated with a color-capable light"""
        sensor = HueSensor('garage-sensor')
        sensor.turn_on()
        sensor.turn_off()
        sensor.toggle()


if __name__ == '__main__':
    unittest.main()

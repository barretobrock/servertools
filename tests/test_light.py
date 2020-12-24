import unittest
from servertools import HueBulb, HueSensor


class TestHueBulb(unittest.TestCase):
    """Test suite for Hue Bulb """

    def setUp(self) -> None:
        pass

    def test_color_light(self):
        """Test standard procedures associated with a color-capable light"""
        light = HueBulb('floor-lamp')
        self.assertTrue(light.is_color_bulb)
        # Turning off/on
        light.turn_on()
        self.assertTrue(light.on)
        light.turn_off()
        self.assertTrue(not light.on)
        # Setting color
        light.turn_on()
        light.set_color(light.DEEP_RED)
        self.assertTrue(light.previous_color is not None)
        light.set_color(light.previous_color)
        # Use different color alert
        light.do_alert(single=False, flash_secs=2, color=light.PURPLE)
        light.blink(5, 0.1, bright_pct=1, color=light.DEEP_RED)
        light.set_brightness(1)
        light.set_brightness(0.5)
        light.set_brightness(light.FULL_BRIGHTNESS)
        light.set_brightness(4568)
        light.set_saturation(1)
        light.set_saturation(0.5)
        light.set_saturation(light.FULL_SATURATION)
        light.set_saturation(4568)
        light.set_hue(4879)
        self.assertTrue(isinstance(light.get_color(), list))
        light.set_rand_color()
        light.candle_mode(5)
        light.set_bshcol(*light.SCENE_WARM_FULL)
        light.toggle()

    def test_white_light(self):
        """Test procedures associated with a standard white cool/warm light"""
        light2 = HueBulb('kontor-lamp')
        light2.turn_on()
        self.assertTrue(light2.get_status())
        self.assertTrue(not light2.is_color_bulb)
        # Make sure color calls fail gracefully
        light2.set_color(light2.DEEP_BLUE)
        light2.turn_off()
        light2.toggle()
        light2.toggle()

    def test_light_strips(self):
        light = HueBulb('kit-strip-1')
        self.assertTrue(light.is_color_bulb)
        # Turning off/on
        light.turn_on()
        self.assertTrue(light.on)
        light.turn_off()
        self.assertTrue(not light.on)

    def test_sensor(self):
        sensor = HueSensor('garage-sensor')
        sensor.turn_on()
        self.assertTrue(sensor.on)
        sensor.turn_off()
        self.assertTrue(not sensor.on)
        sensor.toggle()
        self.assertTrue(sensor.on)


class TestHueSensor(unittest.TestCase):
    """Test suite for the HueSensor class"""
    def setUp(self) -> None:
        pass

    def test_motion_sensor(self):
        """Test standard procedures associated with a color-capable light"""
        sensor = HueSensor('garage-sensor')
        self.assertTrue(isinstance(sensor.battery, int))
        sensor.turn_on()
        sensor.turn_off()
        sensor.toggle()
        self.assertTrue(sensor.on)


if __name__ == '__main__':
    unittest.main()

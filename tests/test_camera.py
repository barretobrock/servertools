import unittest
import datetime
from kavalkilu import Hosts
from servertools import Amcrest


class AmcrestTest(unittest.TestCase):
    def setUp(self) -> None:
        cam_ip = Hosts().get_ip_from_host('ac-v2lis')
        self.assertTrue(cam_ip != '')
        self.cam = Amcrest(cam_ip)
        self.start_dt = datetime.datetime.today().replace(hour=0)
        self.end_dt = datetime.datetime.today().replace(hour=6)

    def test_logs(self):
        logs = self.cam.get_motion_log(self.start_dt, self.end_dt)
        self.assertTrue(len(logs) > 0)

# events = [{'end': datetime.datetime(2020, 9, 25, 2, 58, 1), 'start': datetime.datetime(2020, 9, 25, 2, 57, 58)}, {'end': datetime.datetime(2020, 9, 25, 2, 57, 43), 'start': datetime.datetime(2020, 9, 25, 2, 57, 40)}, {'end': datetime.datetime(2020, 9, 25, 0, 59, 52), 'start': datetime.datetime(2020, 9, 25, 0, 59, 29)}, {'end': datetime.datetime(2020, 9, 25, 0, 59, 19), 'start': datetime.datetime(2020, 9, 25, 0, 59, 9)}]

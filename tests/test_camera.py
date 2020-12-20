import unittest
from datetime import datetime as dt
from kavalkilu import Hosts, LogWithInflux
from servertools import Amcrest


class AmcrestTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.logg = LogWithInflux('cam-test', log_to_file=False)
        cam_ip = Hosts().get_ip_from_host('ac-garaaz')
        cls.cam = Amcrest(cam_ip, parent_log=cls.logg)

    def setUp(self) -> None:
        self.start_dt = dt.today().replace(hour=12, minute=0)
        self.end_dt = dt.today().replace(hour=13, minute=0)

    def test_logs(self):
        logs = self.cam.get_motion_log(self.start_dt, self.end_dt)
        self.assertTrue(len(logs) > 0)


if __name__ == '__main__':
    unittest.main()

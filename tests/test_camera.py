import os
import unittest
import datetime
import tempfile
from kavalkilu import Hosts
from servertools import Amcrest, SlackComm


class AmcrestTest(unittest.TestCase):

    def setUp(self) -> None:
        self.sc = SlackComm()
        cam_ip = Hosts().get_ip_from_host('ac-v2lis')
        self.assertTrue(cam_ip != '')
        self.cam = Amcrest(cam_ip)
        self.temp_dir = tempfile.gettempdir()
        self.MIN_AREA = 500
        # Filepath for saving the cropped movie file before plugging in to opencv (in)
        #   and for saving the mp4 with just motion detection areas from opencv (out)
        self.temp_inmp4_fpath = os.path.join(self.temp_dir, 'tempin.mp4')
        self.temp_outmp4_fpath = os.path.join(self.temp_dir, 'tempout.mp4')
        self.start_dt = datetime.datetime.today().replace(hour=12, minute=0)
        self.end_dt = datetime.datetime.today().replace(hour=13, minute=0)

    def test_logs(self):
        logs = self.cam.get_motion_log(self.start_dt, self.end_dt)
        self.assertTrue(len(logs) > 0)


if __name__ == '__main__':
    unittest.main()

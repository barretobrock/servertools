import unittest


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()


import os
import re
from datetime import datetime as dt
from servertools.camera import Amcrest

ac = Amcrest('192.168.1.24')

ac.is_armed
ac.camera

def extract_timestamp(fpath: str) -> str:
    """Extracts a timestamp from the filepath"""
    final = []
    regex = [
        r'(?<=\/sd\/)\d{4}(-\d{2}){2}',
        r'(?<=\/dav\/\d{2}\/)\d{2}(\.\d{2}){2}-\d{2}(\.\d{2}){2}'
    ]
    for rgx in regex:
        match = re.search(rgx, fpath)
        if match is not None:
            final.append(match.group())

    return '_'.join(final).replace('.', ':')

fmt = '%Y-%m-%d %H:%M:%S'
start = dt.strptime('2020-09-23 19:00:00', fmt)
end = dt.strptime('2020-09-24 02:00:00', fmt)

"""
Process:
     - Use log_find to get timestamps of motion detection periods
     - Process those timestamps into datetime tuples
     - For each datetime tuple, find the filepath(s) associated with them
     - Download the necessary files
     - (Maybe) find a way to trim a specific mp4 file by x seconds
        - https://stackoverflow.com/questions/37317140/cutting-out-a-portion-of-video-python
     - Convert the mp4 files into gifs
        - need to play around with the fps (maybe 2/3 fps)
"""

files = []
for text in ac.camera.find_files(start, end):
    for line in text.split('\r\n'):
        key, value = list(line.split('=', 1) + [None])[:2]
        if key.endswith('.FilePath'):
            if value.endswith('.mp4'):
                print(f'Found file {value}')
                files.append(value)

# Download the files
temp_dir = os.path.join(os.path.expanduser('~'), *['Downloads', 'tmp'])
for file in files:
    if file.endswith('.mp4'):
        # We want just the video files
        # Generate filename
        new_filename = f'{extract_timestamp(file)}.mp4'
        fpath = os.path.join(temp_dir, new_filename)
        # Download
        with open(fpath, 'wb') as f:
            f.write(ac.camera.download_file(file))

# Test mp4 -> gif conversion
from moviepy.editor import VideoFileClip, CompositeVideoClip
import sys

outpath = f'{os.path.splitext(fpath)[0]}.gif'

# Clip from 30s to 3'30s
clip = (VideoFileClip(fpath).subclip((0, 30.00), (3, 30)).resize(0.25).speedx(10))
# Write to gif
clip.write_gif(outpath, fps=2, fuzz=10)




"""For joining timelapse shots"""
import os
from moviepy.editor import ImageSequenceClip
from kavalkilu import Path, LogWithInflux
from servertools import SlackComm


log = LogWithInflux('timelapse_combi')
p = Path()
tl_dir = p.easy_joiner(p.data_dir, 'timelapse')
fnames = {}
for dirpath, _, filenames in os.walk(tl_dir):
    dirname = os.path.basename(dirpath)
    if dirname != 'timelapse':
        fnames[os.path.basename(dirpath)] = filenames

files = []
# Begin combining shots
for k, v in fnames.items():
    full_paths = sorted([os.path.join(tl_dir, *[k, x]) for x in v])
    clip = ImageSequenceClip(full_paths, fps=30)
    fpath = os.path.join(tl_dir, f'concat_{k}.mp4')
    clip.write_videofile(fpath)
    files.append(fpath)

scom = SlackComm(parent_log=log)
for file in files:
    scom.st.upload_file('kaamerad', file, os.path.basename(file))


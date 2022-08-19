"""For joining timelapse shots"""
import os

from kavalkilu import (
    LogWithInflux,
    Path,
)
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
)

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
    if not any([k.startswith(x) for x in ['ac-', 're-']]):
        continue
    log.debug(f'Working on {k}. {len(v)} files.')
    full_paths = sorted([os.path.join(tl_dir, *[k, x]) for x in v])
    clips = []
    for fpath in full_paths:
        try:
            clips.append(ImageClip(fpath).set_duration(1))
        except ValueError:
            log.debug(f'Error with this path: {fpath}')
            continue
    clip = concatenate_videoclips(clips)
    clip = clip.set_fps(30).speedx(30)
    fpath = os.path.join(tl_dir, f'concat_{k}.mp4')
    clip.write_videofile(fpath, fps=30)
    files.append(fpath)

scom = SlackComm(parent_log=log)
for file in files:
    scom.st.upload_file('kaamerad', file, os.path.basename(file))

# Remove files that were concatenated
for k, v in fnames.items():
    for x in v:
        fpath = p.easy_joiner(tl_dir, [k, x])
        os.remove(fpath)

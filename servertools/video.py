import re
import os
import tempfile
from datetime import datetime as dt
from typing import Optional, List, Dict, Tuple, Union
import numpy as np
import cv2
import imutils
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageSequenceClip, CompositeAudioClip


class VidTools:
    """Class for general video editing"""
    temp_dir = tempfile.gettempdir()
    fps = 20
    resize_perc = 0.5
    speed_x = 6

    def __init__(self, vid_w: int = 640, vid_h: int = 360, fps: int = None, resize_perc: float = None,
                 speed_x: int = None):
        if fps is not None:
            self.fps = fps
        if resize_perc is not None:
            self.resize_perc = resize_perc
        if speed_x is not None:
            self.speed_x = speed_x
        self.vid_w = vid_w
        self.vid_h = vid_h

    @staticmethod
    def _get_trim_range_from_filename(fpath: str, start: dt, end: dt) -> Tuple[int, int]:
        """Looks at the filename, returns a start and end time to trim the clip with
            based on the required start and end dates
        """
        # 1. get seconds from clip start to motion start
        # 2. get seconds from clip end to motion end
        # 3. add as subclip((secs_from_start: float), (secs_from_end: float))
        clip_ymd = re.search(r'\d{4}-\d{2}-\d{2}', fpath).group()
        clip_st, clip_end = [dt.strptime(f'{clip_ymd} {x[0]}', '%Y-%m-%d %H:%M:%S')
                             for x in re.findall(r'((\d+:){2}\d{2})', fpath)]
        # Determine if we need to crop the clip at all
        secs_from_start = (start - clip_st).seconds if start > clip_st else 0
        secs_from_end = -1 * (clip_end - end).seconds if clip_end > end else None
        return secs_from_start, secs_from_end

    def make_clip_from_filenames(self, start_dt: dt, end_dt: dt, file_list: List[str],
                                 trim_files: bool = True, prefix: str = 'motion') -> str:
        """Takes in a list of file paths, determines the cropping necessary
        based on the timerange in the path and downloads the video clip to a temp filepath"""
        clips = []
        for dl_file in file_list:
            clip = VideoFileClip(dl_file)
            if trim_files:
                trim_st, trim_end = self._get_trim_range_from_filename(dl_file, start_dt, end_dt)
                clip = clip.subclip(trim_st, trim_end)
            clip = (clip.resize(self.resize_perc).speedx(self.speed_x))
            # Append to our clips
            clips.append(clip)
        final = concatenate_videoclips(clips, method='compose')
        fpath = os.path.join(self.temp_dir, f'{prefix}_{start_dt:%T}_to_{end_dt:%T}.mp4')
        final.write_videofile(fpath)
        return fpath

    def concat_files(self, filepath_list: List[str]) -> str:
        """Concatenates a list of mp4 filepaths into one & saves it"""
        clips = []
        for filepath in filepath_list:
            clip = VideoFileClip(filepath)
            clips.append(clip)
        final = concatenate_videoclips(clips, method='compose')
        final_fpath = os.path.join(self.temp_dir, 'motion_concatenated_file.mp4')
        final.write_videofile(final_fpath)
        return final_fpath

    def draw_on_motion(self, fpath: str, min_area: int = 500, min_frames: int = 10,
                       threshold: int = 25) -> Tuple[bool, Optional[str]]:
        """Draws rectangles around motion items and re-saves the file
            If True is returned, the file has some motion highlighted in it, otherwise it doesn't have any

        Args:
            fpath: the path to the mp4 file
            min_area: the minimum contour area (pixels)
            min_frames: the threshold of frames the final file must have. Fewer than this will return False
            threshold: min threshold (out of 255). used when calculating img differences

        NB! threshold probably shouldn't exceed 254
        """
        # Read in file
        vs = cv2.VideoCapture(fpath)
        # Read in the clip as a video, extract audio
        clip = VideoFileClip(fpath)
        audio = CompositeAudioClip([clip.audio])
        vs.set(3, self.vid_w)
        vs.set(4, self.vid_h)
        fframe = None
        nth_frame = 0
        frames = []
        prev_contours = []
        while True:
            # Grab the current frame
            ret, frame = vs.read()
            if frame is None:
                # If frame could not be grabbed, we've likely reached the end of the file
                break
            # Resize the frame, convert to grayscale, blur it
            try:
                frame = imutils.resize(frame, width=self.vid_w)
                gray = self._grayscale_frame(frame)
            except AttributeError:
                continue

            # If the first frame is None, initialize it
            if fframe is None:
                fframe = gray
                continue
            rects, contours, cframe = self._detect_contours(
                fframe, frame, min_area, threshold, unique_only=False
            )
            # if rects > 0:
            #     frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if nth_frame % 100 == 0:
                print(f'Frame {nth_frame} reached.')
            nth_frame += 1

        vs.release()
        if len(frames) > min_frames:
            # Rewrite the output file with moviepy
            #   Otherwise Slack won't be able to play the mp4 due to h264 codec issues
            return True, self.write_frames(frames, fpath, audio=audio)
        return False, None

    def write_frames(self, frames: List[np.ndarray], filepath: str, audio: CompositeAudioClip) -> str:
        """Writes the frames to a given .mp4 filepath (h264 codec)"""
        vclip = ImageSequenceClip(frames, fps=self.fps)
        audio.set_duration(vclip.duration)
        vclip.audio = audio
        vclip.write_videofile(filepath, codec='libx264', fps=self.fps)
        return filepath

    @staticmethod
    def _grayscale_frame(frame: np.ndarray, blur_lvl: int = 21) -> np.ndarray:
        """Converts a frame to grayscale"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (blur_lvl, blur_lvl), 0)
        return gray

    def _detect_contours(self, first_frame: np.ndarray, cur_frame: np.ndarray,
                         min_area: int = 500, threshold: int = 25, contour_lim: int = 10,
                         prev_contours: List[np.ndarray] = None, unique_only: bool = False) -> \
            Tuple[int, List[np.ndarray], np.ndarray]:
        """Methodology used to detect contours in image differences

        Args:
            first_frame: the frame to use as base comparison
            cur_frame: the frame to compare for changes
            min_area: the minimum (pixel?) area of changes to be flagged as a significant change
            threshold: seems like the gradient of the change (in grayscale?) to identify changes?
            contour_lim: integer-wise means of detecting changes in contours (larger => more different)
            prev_contours: List of previous contours (used for detecting unique contours
            unique_only: if True, will perform unique contour analysis
        """
        # Compute absolute difference between current frame and first frame
        gray = self._grayscale_frame(cur_frame)
        fdelta = cv2.absdiff(first_frame, gray)
        thresh = cv2.threshold(fdelta, threshold, 255, cv2.THRESH_BINARY)[1]
        # Dilate the thresholded image to fill in holes, then find contours
        #   on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        # Capture unique contours
        unique_cnts = prev_contours.copy() if prev_contours is not None else []

        # Loop over contours
        rects = 0
        for cnt in cnts:
            # Ignore contour if it's too small
            if cv2.contourArea(cnt) < min_area:
                continue
            if unique_only:
                # Check for unique contours
                if any([cv2.matchShapes(cnt, ucnt, 1, 0.0) > contour_lim for ucnt in unique_cnts]):
                    # Unique contour - add to group
                    # Otherwise compute the bounding box for the contour & draw it on the frame
                    (x, y, w, h) = cv2.boundingRect(cnt)
                    cv2.rectangle(cur_frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                    unique_cnts.append(cnt)
                    rects += 1
            else:
                # Just pick up any contours
                (x, y, w, h) = cv2.boundingRect(cnt)
                cv2.rectangle(cur_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                rects += 1

        return rects, unique_cnts, cv2.cvtColor(cur_frame, cv2.COLOR_BGR2RGB)

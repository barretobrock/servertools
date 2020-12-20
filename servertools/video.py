import re
import os
import tempfile
from datetime import datetime as dt
from typing import Optional, List, Dict, Tuple, Union
import numpy as np
import cv2
import imutils
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageSequenceClip, CompositeAudioClip, VideoClip


class VidTools:
    """Class for general video editing"""
    temp_dir = tempfile.gettempdir()
    FPS = 20
    RESIZE_PCT = 0.5
    SPEEDX = 6

    def __init__(self, vid_w: float = 640, vid_h: float = 360, fps: float = FPS, resize_perc: float = RESIZE_PCT,
                 speed_x: float = SPEEDX):
        self.fps = fps
        self.resize_perc = resize_perc
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

    def draw_on_motion(self, fpath: str, min_area: int = 500, min_frames: int = 10, threshold: int = 25,
                       ref_frame_turnover: float = 20, buffer_s: float = 1) -> \
            Tuple[bool, Optional[str], Optional[float]]:
        """Draws rectangles around motion items and re-saves the file
            If True is returned, the file has some motion highlighted in it, otherwise it doesn't have any

        Args:
            fpath: the path to the mp4 file
            min_area: the minimum contour area (pixels)
            min_frames: the threshold of frames the final file must have. Fewer than this will return False
            threshold: min threshold (out of 255). used when calculating img differences
            ref_frame_turnover: the number of consecutive frames to use a single reference frame on
                before resetting the reference
            buffer_s: the seconds of buffer to include in video output before and after motion events

        NB! threshold probably shouldn't exceed 254
        """
        clip = VideoFileClip(fpath)
        frames = [x for x in clip.iter_frames()]
        total_frames = len(frames)
        # Set the reference frame
        ref_frame = clip.get_frame(0)
        keep_frames = []    # For determining which frames have motion
        for i, frame in enumerate(frames):
            rects, contours, drawn_frame = self._detect_contours(
                ref_frame, frame, min_area, threshold, unique_only=False)
            if rects > 0:
                # We've drawn some rectangles on this
                keep_frames.append(i)
                # Replace frame with drawn
                frames[i] = drawn_frame
            if i % ref_frame_turnover == 0:
                print(f'Frame {i} reached.')
                if i > 0:
                    # Reset the reference frame
                    ref_frame = frame

        # Now loop through the frames we've marked and process them into clips
        # Determine the amount of buffer frames from the seconds of buffer
        buffer_frame = int(round(clip.fps * buffer_s, 0))
        # Begin calculating the sequences
        sequences = []  # For holding lists of sequences
        sequence_frames = [keep_frames[0]]
        for f in keep_frames[1:]:
            last_seq = sequence_frames[-1]
            if f == last_seq + 1:
                sequence_frames.append(f)
            elif f < last_seq + buffer_frame:
                # Though our sequence isn't consecutive, it falls inside of the buffer. Add it
                sequence_frames.append(f)
            else:
                # Frame is definitely outside the buffer. Make a new sequence
                sequences.append((sequence_frames[0], sequence_frames[-1]))
                sequence_frames = [f]
        if len(sequence_frames) > 0:
            sequences.append((sequence_frames[0], sequence_frames[-1]))

        processed_clips = []
        for start, end in sequences:
            if end - start >= min_frames:
                processed_clips.append(
                    self.develop_drawn_clip(org_clip=clip, sq_frames=[start, end], all_frames=frames,
                                            buffer_s=buffer_s)
                )

        if len(processed_clips) > 0:
            final_clip = concatenate_videoclips(processed_clips)
            final_clip.write_videofile(fpath)
            return True, fpath, final_clip.duration
        return False, None, None

    @staticmethod
    def develop_drawn_clip(org_clip: VideoFileClip, sq_frames: List[float], all_frames: List[np.ndarray],
                           buffer_s: float = 1) -> VideoClip:
        """Calculates subclip start and end time, creates a subclip to reference.
        Combines the drawn frames (with buffer) before transforming into a video clip
        Adds original clip's audio to the video containing drawn frames.

        Args:
            org_clip: the original clip to leverage audio, duration data from
            sq_frames: the sequence of frames that have motion annotations draw in them
            all_frames: the full list of frames that we'll be slicing
            buffer_s: the seconds of buffer to add before and after the motion area
        """
        duration = org_clip.duration
        tot_frames = len(all_frames)
        # Calculate number of frames to buffer before and after motion areas
        buffer_fr = int(org_clip.fps / buffer_s)

        # Calculate the start and end frames with the buffers
        st_with_buffer = sq_frames[0] - buffer_fr
        end_with_buffer = sq_frames[-1] + buffer_fr
        start_frame_pos = st_with_buffer if st_with_buffer > 0 else 0
        end_frame_pos = end_with_buffer if end_with_buffer < tot_frames else tot_frames - 1

        # Calculate the start and end times for the start and end frames
        start_t = ((start_frame_pos / tot_frames) * duration)
        end_t = ((end_frame_pos / tot_frames) * duration)

        # Cut the original clip to fit the buffer
        cut_clip = org_clip.subclip(start_t, end_t)

        # Generate the sequence of drawn clips
        drawn_clip = ImageSequenceClip(all_frames[start_frame_pos:end_frame_pos], fps=org_clip.fps)
        if drawn_clip.duration != cut_clip.duration:
            # Cut the tail off the drawn clip to match the cut_clip.
            drawn_clip = drawn_clip.subclip(0, end_t - start_t)
        # Make the drawn clip a VideoClip by concatenating it with only itself. Add original clip's audio
        drawn_clip = concatenate_videoclips([drawn_clip])
        drawn_clip.audio = cut_clip.audio
        return drawn_clip

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

    def _detect_contours(self, reference_frame: np.ndarray, cur_frame: np.ndarray,
                         min_area: int = 500, threshold: int = 25, contour_lim: int = 10,
                         prev_contours: List[np.ndarray] = None, unique_only: bool = False,
                         color_correct_frame: bool = False) -> Tuple[int, List[np.ndarray], np.ndarray]:
        """Methodology used to detect contours in image differences

        Args:
            reference_frame: the frame to use as base comparison
            cur_frame: the frame to compare for changes
            min_area: the minimum (pixel?) area of changes to be flagged as a significant change
            threshold: seems like the gradient of the change (in grayscale?) to identify changes?
            contour_lim: integer-wise means of detecting changes in contours (larger => more different)
            prev_contours: List of previous contours (used for detecting unique contours
            unique_only: if True, will perform unique contour analysis
            color_correct_frame: if True, will try to apply a color correction to the frame before return
        """
        # Compute absolute difference between current frame and first frame
        ref_gray = self._grayscale_frame(reference_frame)
        gray = self._grayscale_frame(cur_frame)
        fdelta = cv2.absdiff(ref_gray, gray)
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
                cv2.rectangle(cur_frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                rects += 1
        if color_correct_frame:
            cur_frame = cv2.cvtColor(cur_frame, cv2.COLOR_BGR2RGB)
        return rects, unique_cnts, cur_frame

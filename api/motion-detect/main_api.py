#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime as dt, timedelta
import tempfile
from flask import Flask, make_response
from moviepy.editor import VideoFileClip
from kavalkilu import Hosts, LogWithInflux
from servertools import SlackComm, VidTools, Reolink


logg = LogWithInflux('motion_alerts', log_level_str='DEBUG')
sc = SlackComm(parent_log=logg)
vt = VidTools(fps=10, resize_perc=0.5, speed_x=5)
app = Flask(__name__)

DURATION_S = 10
CAMERA = None


@app.route('/')
def main_page():
    return 'Main page!'


@app.route('/motion/<camera>', methods=['GET'])
def detect_motion(camera: str):
    """Handle motion detection prodecures"""
    CAMERA = camera
    raw_cam_path = os.path.join(tempfile.gettempdir(), f'{camera}-motion-raw.mp4')
    processed_cam_path = os.path.join(tempfile.gettempdir(), f'{camera}-motion-proc.mp4')
    response = make_response('', 200)

    @response.call_on_close
    def process_event():
        # Load camera live stream, for {duration}
        cam_ip = Hosts().get_ip_from_host(camera)
        cam = Reolink(cam_ip, parent_log=logg)

        stream = cam.open_video_stream()
        # Determine the length of time we're capturing the camera's feed
        start_dt = dt.now()
        end_dt = (start_dt + timedelta(seconds=DURATION_S))
        frames = []
        logg.debug('Recording frames...')
        for frame in stream:
            # Store image for later
            frames.append(frame)
            # Determine if we've exceeded the duration limit
            if dt.now() > end_dt:
                logg.debug('Time limit reached. Exiting loop.')
                break
        # Draw motion squares on frames
        logg.debug('Drawing motion on frames...')
        is_motion_detected, fpath, duration = vt.draw_on_motion(
            fpath=raw_cam_path, frames=frames, min_area=1000, min_frames=5, threshold=25, ref_frame_turnover=20,
            buffer_s=1, motion_frames_only=False)
        logg.debug(f'Received processed clip at path: {fpath}')
        # Send clip to slack
        logg.debug('Adjusting clip for quality and speed...')
        clip = VideoFileClip(raw_cam_path)
        clip = (clip.resize(0.50).speedx(5))
        clip.write_videofile(processed_cam_path)
        logg.debug('Uploading clip to slack...')
        sc.st.upload_file(sc.kaamerate_kanal, processed_cam_path, filename=f'{CAMERA} events',
                          txt='Motion detected!')
        logg.debug('Process complete!')

    return response


@app.errorhandler(500)
def handle_errors(error):
    return 'Not found!'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5005')

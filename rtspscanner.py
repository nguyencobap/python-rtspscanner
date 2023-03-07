#!/usr/bin/env python
from os import getenv, path, system
import subprocess
import requests
import json
from PIL import Image
from portscan import PortScan


class RTSPScanner:
    def __init__(self, verbose=False, wspace="-"):
        # GET ENVIRONMENT VARIABLES
        self.ports = getenv("RTSP_SCAN_PORTS", "554,8554")
        self.timeout = getenv("FFMPEG_TIMEOUT", 10)
        self.retries = getenv("FFMPEG_RETRIES", 2)
        self.verbose = True if verbose or str(getenv("RTSP_VERBOSE", "false")).lower() == "true" else False
        self.whitespace = getenv("RTSP_WHITESPACE") if getenv("RTSP_WHITESPACE") else wspace
        self.creds = self.split_csv(getenv("RTSP_CREDS", "none"))
        self.paths = "/Streaming/Channels/101," \
                     "/Streaming/Channels/201," \
                     "/Streaming/Channels/301," \
                     "/Streaming/Channels/401," \
                     "/Streaming/Channels/501," \
                     "/Streaming/Channels/601," \
                     "/Streaming/Channels/701," \
                     "/Streaming/Channels/801," \
                     "/Streaming/Channels/901," \
                     "/Streaming/Channels/1001," \
                     "/Streaming/Channels/1101," \
                     "/Streaming/Channels/1201," \
                     "/Streaming/Channels/1301," \
                     "/Streaming/Channels/1401," \
                     "/Streaming/Channels/1501," \
                     "/Streaming/Channels/1601," \
                     "/Streaming/Channels/1701," \
                     "/Streaming/Channels/1801," \
                     "/Streaming/Channels/1901," \
                     "/Streaming/Channels/2001," \
                     "/," \
                     "/live," \
                     "/live2," \
                     "/h264.sdp," \
                     "/stream1," \
                     "/profile2/media.smp," \
                     "/defaultPrimary?streamType=u," \
                     "/axis-media/media.amp," \
                     "/media/video1," \
                     "/video1+audio1," \
                     "/MediaInput/h264," \
                     "/MediaInput/h264/stream_1," \
                     "/Streaming/Channels/101/," \
                     "/video.h264," \
                     "/ch1/main/av_stream," \
                     "/cam/realmonitor?channel-1&subtype=1," \
                     "/profile1," \
                     "/cam/realmonitor?channel-1&subtype=0&unicast=true&proto=Onvif," \
                     "/ch01/0," \
                     "/channel1," \
                     "/streaming/channels/0," \
                     "/VideoInput/1/h264/1," \
                     "/h264," \
                     "/live.sdp," \
                     "mobotix.h264," \
                     ""
        self.address = getenv("RTSP_ADDRESS", "192.168.2.0/24")
        self.cameras = []
        self.flaky = []
        self.scanResults = None

    def run(self):
        self.scanner()
        for c in range(0, len(self.cameras)):
            self.cameras[c][0] = self.cameras[c][0].replace('.', self.whitespace)
        return self.cameras

    def resize_img(self, img, output, height=180, ratio=1.777777778, fmt="webp"):
        if path.exists(img):
            # Resizes an image from the filesystem
            if path.exists(img):
                Image.open(img).resize((int(height * ratio), height)).save(output, fmt, quality=100, optimize=True)
                return "OK"
            else:
                return "resize_img(): Image Path Does Not Exist"

    def split_csv(self, csv):
        values = []
        for value in csv.split(','):
            values.append(value)
        return values

    def scanner(self):
        portscan = PortScan(self.address, self.ports, stdout=False)
        results = portscan.run()
        with portscan.q.mutex:
            unfinished = portscan.q.unfinished_tasks - len(portscan.q.queue)
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                portscan.q.unfinished_tasks = unfinished
                portscan.q.queue.clear()
                portscan.q.not_full.notify_all()
        if self.verbose:
            print(f"results = {results}")
        for result in results:
            if result:
                for path in self.paths.split(','):
                    for cred in self.creds.split(','):
                        transport = f"rtsp://{cred}@" if cred != "none" else "rtsp://"
                        rtsp = f'{transport}{result["ip"]}:{result["port"]}{path}'
                        status = f"Checking {rtsp}... "
                        if self.verbose:
                            print(status)
                        snapshot = f"/tmp/test.png"
                        thumbnail = f"/tmp/test.webp"
                        command = ['ffmpeg', '-y', '-frames', '1', snapshot, '-rtsp_transport', 'tcp', '-i', rtsp]
                        timedout = False
                        for x in range(0, self.retries):
                            try:
                                cmd = subprocess.run(command, stderr=subprocess.DEVNULL, timeout=self.timeout)
                                break
                            except subprocess.TimeoutExpired as e:
                                if self.verbose:
                                    label = f"Retry # {x}" if x > 0 else "1st Attempt"
                                    print(f"{label}: {e}")
                                timedout = True
                        if self.verbose:
                            print(f"Return Code: {cmd.returncode}")
                        if 'timedout' in locals():
                            if timedout:
                                self.flaky.append([str(result['ip']), rtsp])
                        if 'cmd' in locals() and cmd.returncode == 0:
                            self.cameras.append([str(result['ip']), rtsp])
                            status = "RTSP "
                            # resize_img(self,img,output,height=180,ratio=1.777777778,fmt="webp"):
                            resize = self.resize_img(snapshot, thumbnail)
                            if resize == "OK":
                                status += "VALID IMAGE"
                            else:
                                status += "NO IMAGE"
                        if self.verbose:
                            print(f"status {status}")
        self.scanResults = {"cameras": self.cameras, "flaky": self.flaky, "portscan": results}
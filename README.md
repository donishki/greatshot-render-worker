worker for creating renders for https://github.com/mittermichal/greatshot-web


# Hosting worker

If you want to host render worker for https://greatshot.xyz, I have to give you credentials for redis server and upload http auth.
 - have W:ET 2.60b with etpro mod and usual competitive maps in etmain
- install python 3.5 or greater
- install git
- `git clone https://github.com/mittermichal/greatshot-render-worker`
- `cd greatshot-render-worker`
- `pip install -r requirements.txt`
- download ffmpeg: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z
- `cp tasks_config.sample.py tasks_config.py`
- edit tasks_config.py:
  - ETPATH = \<location ET.exe is\>
  - REDIS = \<redis credentials\>
  - http upload auth:
      - RENDER_UPLOAD_AUTH_NAME = ...
      - RENDER_UPLOAD_AUTH_PW = ...
  - DRAMATIQ_NS = 'prod'
  - FFMPEG = \<path to ffmpeg.exe with binary name included\>
- copy profiles directory to etpro - contains render-worker profile with config
- copy `etmain/preinit-wav.cfg` into etmain
- run worker: `dramatiq -t 1 -p 1 tasks render_heartbeat -Q render` or `run_worker.bat`

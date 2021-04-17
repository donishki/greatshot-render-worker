worker for creating renders for https://github.com/mittermichal/greatshot-web


# Hosting worker on Windows

If you want to host render worker for https://greatshot.xyz, I have to give you credentials for redis server and upload http auth.
 - have W:ET 2.60b with etpro mod and usual competitive maps in etmain. At the moment it's not possible to run it headless on some server.
- install python 3.5 or greater, make sure installer adds python to system PATH https://stackoverflow.com/questions/34900042/why-would-i-add-python-to-path

- download ffmpeg: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z
- extract the ffmpeg archive anywhere

- install git
- open command line
- `git clone https://github.com/mittermichal/greatshot-render-worker`
- `cd greatshot-render-worker`
- optionally create virtual enviroment
- `pip install -r requirements.txt`

- create copy of tasks_config.sample.py and name it tasks_config.py: `cp tasks_config.sample.py tasks_config.py`
- edit tasks_config.py:
  - ETPATH = \<location ET.exe is\>
  - REDIS = \<redis credentials\>
  - http upload auth, contact me to get it and also REDIS:
      - RENDER_UPLOAD_AUTH_NAME = ...
      - RENDER_UPLOAD_AUTH_PW = ...
  - DRAMATIQ_NS = 'prod'
  - FFMPEG = \<path to ffmpeg.exe with binary name included\>
- copy `ET\etpro\profiles` directory to etpro - contains render-worker profile with config

- test screenshot capture by running: `python test_capture_progress.py`

- run worker: `dramatiq -t 1 -p 1 tasks render_heartbeat -Q render` or run `run_worker.bat` or `run_worker_venv.bat` if you use venv 
- pressing CTRL + C once should gracefully finish tasks, pressing it more times will kill it completely
- you can create shortcut to run_worker.bat for easy access

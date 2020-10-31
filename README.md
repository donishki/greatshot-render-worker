worker for creating renders for https://github.com/mittermichal/greatshot-web

# Hosting worker

If you want to host render worker for https://greatshot.xyz, I have to give you credentials for redis server and upload http auth.
Have W:ET installation with etpro mod.
- install python 3
- `git clone https://github.com/mittermichal/greatshot-render-worker`
- `cd greatshot-render-worker`
- `pip install -r requirements.txt`
- `cp tasks_config.sample.py tasks_config.py`
- edit tasks_config.py:
  - ETPATH = \<location where et.exe is\>
  - REDIS = \<redis credentials\>
  - http upload auth:
      - RENDER_UPLOAD_AUTH_NAME = ...
      - RENDER_UPLOAD_AUTH_PW = ...
  - DRAMATIQ_NS = 'prod'
- copy profiles directory to etpro - contains render-workder profile with config
- run worker: `dramatiq -t 1 -p 1 tasks render_heartbeat -Q render`

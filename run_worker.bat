cmd /k "cd /d venv\Scripts & activate & cd /d ..\.."
cmd /k "dramatiq -t 1 -p 1 tasks render_heartbeat -Q render"

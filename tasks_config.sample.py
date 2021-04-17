ETPATH = r"C:\Program Files (x86)\Wolfenstein - Enemy Territory"
FFMPEG = r"ffmpeg"  # another example: r"C:\bin\ffmpeg-4.3.2-2021-02-27-essentials_build\bin\ffmpeg.exe"

# contact me to get these if you plan to host the worker for greatshot.xyz
REDIS = 'redis://:localhost' 
RENDER_UPLOAD_AUTH_NAME = 'name'  
RENDER_UPLOAD_AUTH_PW = 'pw'


# usually no need to change these:
DRAMATIQ_NS = 'prod'  # change if testing
ET_HOMEPATH = ETPATH  # fs_homepath usually different on linux
ET_EXECUTABLE = 'ET.exe'  # on linux probably `et.sh` - sound fix script

import os
import re
import subprocess
from urllib.parse import urlparse
import dramatiq
from dramatiq.brokers.redis import RedisBroker
import tasks_config
import requests
import glob
import sentry_sdk
import sentry_dramatiq
from time import sleep
from threading import Thread

if __name__ == "__main__":
    if hasattr(tasks_config, 'SENTRY_DSN'):
        sentry_sdk.init(
            tasks_config.SENTRY_DSN,
            integrations=[sentry_dramatiq.DramatiqIntegration()],
        )


redis_broker = RedisBroker(url=tasks_config.REDIS, middleware=[], namespace=tasks_config.DRAMATIQ_NS)
dramatiq.set_broker(redis_broker)


RECORD_WAV_CFG = """
timescale 1
com_maxfps 125
timescale 1
echo "^1oooooooooooooooooo ^5WAV_RECORD ^1ooooooooooooooooooooooooooo"
//exec cameras\\runs\\1stPos
wav_record synctest
set nextdemo quit
"""

PREINIT_WAV_CFG = """
cl_avidemo 0
demo {}
timescale 1
wait 38
echo "^2preinit-wav.cfg"
timescale 1
exec init-wav
"""


def get_worker_last_beat():
    return int(redis_broker.client.get('worker_last_beat').decode('utf-8'))


def set_render_status(url_parsed, render_id, status_msg, progress=0):
    # print('render #{}: status: {} progress: {}'.format(render_id, status_msg, progress))
    requests.post(
        url_parsed.scheme + '://' + url_parsed.netloc + '/renders/'+str(render_id),
        json={'status_msg': status_msg, 'progress': progress},
        auth=(tasks_config.RENDER_UPLOAD_AUTH_NAME, tasks_config.RENDER_UPLOAD_AUTH_PW)
    )


def follow(file, p: subprocess.Popen):
    # file.seek(0, 2)
    while True and p.poll() is None:
        line = file.readline()
        if not line:
            sleep(0.1)
            continue
        yield line


def progress_capture(p: subprocess.Popen, callback, error):
    while True and p.poll() is None:
        try:
            logfile = open(os.path.join(tasks_config.ETPATH, 'etpro', 'etconsole.log'), "r")
        except FileNotFoundError:
            sleep(0.1)
        else:
            callback(None, False, "Starting game and loading demo")
            loglines = follow(logfile, p)
            sound = False
            for line in loglines:
                find = re.findall(
                    r'I will execute progress-(\d+) at (\d+), have a good flight o/',
                    line
                )
                if len(find) > 0:
                    try:
                        callback(int(find[0][1]), sound)
                    except IndexError:
                        pass
                elif re.search(r'execing preinit-wav', line) is not None:
                    callback(None, sound, "Reloading demo for sound capture")
                    sound = True
                elif re.search(r'^ERROR: ', line) is not None:
                    error[0] = line
                    p.kill()
                    loglines.close()
            loglines.close()
            break


def capture(start, end, exec_at_time_callback=None, etl=False, fps=50, demo_name='demo-render'):
    # http://stackoverflow.com/questions/5069224/handling-subprocess-crash-in-windows
    if etl:
        open(tasks_config.ETPATH + 'etmain\\init-tga.cfg', 'w').write(
            'exec_at_time ' + str(int(end) - 500) + ' stopvideo')
        p = subprocess.Popen(['render-etl.bat', tasks_config.ETPATH])
    else:
        delete_screenshots('etpro')
        try:
            os.remove(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'etconsole.log'))
        except FileNotFoundError:
            print("info: 'etconsole.log' not found")
        for i, time in enumerate(range(int(start), int(end), 1000)):
            with open(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'progress-'+str(i)+'.cfg'), 'w') as file:
                file.write('exec_at_time ' + str(time+1000) + ' progress-' + str(i+1))
        with open(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'record-tga.cfg'), 'w') as file:
            file.write('cl_avidemo '+str(fps)+'\n'+'exec_at_time '+str(int(start)+1000)+' progress-1')
        with open(os.path.join(tasks_config.ET_HOMEPATH, 'etmain', 'init-tga.cfg'), 'w') as file:
            file.write('exec_at_time '+str(start)+' record-tga')
        with open(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'record-wav.cfg'), 'w') as file:
            file.write(RECORD_WAV_CFG+'\n'+'exec_at_time '+str(int(start)+1000)+' progress-1')
        with open(os.path.join(tasks_config.ET_HOMEPATH, 'etmain', 'init-wav.cfg'), 'w') as file:
            file.write('exec_at_time '+str(start)+' record-wav')
        with open(os.path.join(tasks_config.ET_HOMEPATH, 'etmain', 'preinit-wav.cfg'), 'w') as file:
            file.write(PREINIT_WAV_CFG.format(demo_name))
        p = subprocess.Popen([os.path.join(tasks_config.ETPATH, tasks_config.ET_EXECUTABLE),
                              '+set', 'cl_profile', 'render-worker',
                              '+set', 'com_ignorecrash', '1',
                              '+viewlog', '1', '+logfile', '2',
                              '+set', 'fs_game', 'etpro', '+set com_maxfps 125',
                              '+timescale', '0', '+demo', demo_name,
                              '+timescale', '0', '+wait', '20',
                              '+timescale', '1', '+exec', 'init-tga',
                              '+condump', 'init-tga.log', '+timescale', '1',
                              '+set', 'nextdemo', 'exec preinit-wav'
                              ], cwd=tasks_config.ETPATH)
    try:
        error = [None]
        if exec_at_time_callback is not None:
            Thread(target=progress_capture, args=(p, exec_at_time_callback, error)).start()
        p.communicate(timeout=120)
        if error[0] is not None:
            raise GameErrorException(error[0])

    except subprocess.TimeoutExpired as e:
        p.kill()
        raise e


def delete_screenshots(mod='etpro'):
    for file in glob.glob(os.path.join(tasks_config.ET_HOMEPATH, mod, 'screenshots/*.tga')):
        os.remove(file)


def ffmpeg_args(name, country, crf, fps=50):
    args = [tasks_config.FFMPEG, '-hide_banner', '-loglevel', 'warning', '-y', '-thread_queue_size', '1024',
            '-progress', 'pipe:1',
            '-framerate', str(fps), '-i', os.path.join(tasks_config.ET_HOMEPATH, 'etpro/screenshots/shot%04d.tga')]
    if name != "" and country != "None":
        args += [
            '-filter_complex',
            "[0] [1] overlay=25:150 [b]; [b] drawtext=fontfile=courbd.ttf:text='" +
            name + "': fontcolor=white: fontsize=50: x=100: y=150+45.0-text_h-5",
        ]
        args += ['-i', '4x3/' + country + '.png']
    args += [
        '-i',
        os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'wav', 'synctest.wav'),
        '-shortest', '-crf', str(crf),
        '-pix_fmt', 'yuv420p', 'render.mp4'
    ]
    return args


@dramatiq.actor(queue_name='render')
def render(render_id, demo_url, start, end, name="", country=None, crf='23', etl=False):
    print(locals())
    url_parsed = urlparse(demo_url)

    # test_progress(url_parsed, render_id)
    # return

    # download is finished too fast to set status
    demo_name = 'demo-render'
    set_render_status(url_parsed, render_id, 'downloading demo...', 5)
    demo_file_path = os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'demos', demo_name + '.dm_84')
    try:
        os.mkdir(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'demos'))
    except FileExistsError:
        pass

    r = requests.get(demo_url)
    if r.status_code == 200:
        open(demo_file_path, 'wb').\
            write(r.content)
    else:
        RenderException('error downloading cut demo')

    if os.stat(demo_file_path).st_size == 0:
        set_render_status(url_parsed, render_id, 'error: cut demo was empty', 100)
        raise RenderException('cut demo was empty')

    set_render_status(url_parsed, render_id, 'capturing screenshots and sound...', 0)

    def exec_at_time_callback(time, sound, status=None):
        if time is not None:
            time -= 1000
            if sound:
                capturing = 'sound'
            else:
                capturing = 'screenshots'
            percent = int(100*(time - int(start)) / (int(end) - int(start)))
            # print('capturing {} {}% {}'.format(capturing, int(percent), time))
            set_render_status(url_parsed, render_id,
                              'capturing {}'.format(capturing),
                              int(percent))
        elif status is not None:
            set_render_status(url_parsed, render_id, status, 0)

    try:
        capture(start, end, exec_at_time_callback, etl)
    except subprocess.TimeoutExpired:
        # this prob wont work as intended
        set_render_status(url_parsed, render_id, 'error: game capture took too long', 100)
        raise RenderException('game capture took too long')
    except GameErrorException as e:
        set_render_status(url_parsed, render_id, str(e), 100)
        raise e

    set_render_status(url_parsed, render_id, 'encoding video...', 0)
    if etl:
        args = ['ffmpeg', '-y', '-framerate', '60',
                '-i', 'C:\\Users\\admin\\Documents\\ETLegacy\\uvMovieMod\\videos\\render.avi',
                '-shortest', 'render.mp4']
    else:
        args = ffmpeg_args(name, country, crf)

    frame_count = len(glob.glob(os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'screenshots', 'shot[0-9]*.tga')))

    if frame_count == 0:
        raise RenderException("no screenshots captured")

    def frame_processed_callback(frame):
        set_render_status(url_parsed, render_id,
                          'encoding video {}/{} frame'.format(frame, frame_count),
                          int(frame/frame_count*100))

    if ffmpeg(args, frame_processed_callback):
        set_render_status(url_parsed, render_id, 'error: failed to encode video', 100)
        raise RenderException("failed to encode video")
    set_render_status(url_parsed, render_id, 'uploading video', 0)
    filename = str(render_id) + '.mp4'
    # print(filename)
    # netloc = url_parsed.netloc.replace('localhost','127.0.0.1')
    # print('upload url: ' + url_parsed.scheme + '://' + url_parsed.netloc + '/upload')
    r = requests.put(
        url_parsed.scheme + '://' + url_parsed.netloc + '/renders',
        auth=(tasks_config.RENDER_UPLOAD_AUTH_NAME, tasks_config.RENDER_UPLOAD_AUTH_PW),
        files={filename: open(os.path.join(tasks_config.ET_HOMEPATH, 'render.mp4'), 'rb')})
    # print('upload r code:' + str(r.status_code))
    if r.status_code == 200:
        set_render_status(url_parsed, render_id, 'finished', 100)
        print('finished')
    else:
        set_render_status(url_parsed, render_id, 'upload error', 100)
        raise RenderException('Upload error: ' + str(r.status_code) + r.content.decode('utf-8'))


def ffmpeg(args, frame_processed_callback=None):
    p = subprocess.Popen(args, cwd=tasks_config.ET_HOMEPATH, stdout=subprocess.PIPE, universal_newlines=True)
    if frame_processed_callback is not None:
        for stdout_line in iter(p.stdout.readline, ""):
            find = re.findall(r'frame=(\d+)', stdout_line)
            if len(find):
                frame_processed_callback(int(find[0]))
    p.stdout.close()
    return p.wait(timeout=30)


def test_progress(url_parsed, render_id):
    for i in range(0, 100, 20):
        set_render_status(url_parsed, render_id, 'p ' + str(i), i)
        sleep(2)
    set_render_status(url_parsed, render_id, 'finished', 100)


def test_capture_progress(start, end, fps=None, demo_name=None):
    def exec_at_time_callback(time, sound, status=None):
        if time is not None:
            time -= 1000
            if sound:
                capturing = 'sound'
            else:
                capturing = 'screenshots'
            percent = int(100*(time - int(start)) / (int(end) - int(start)))
            print('capturing {} {}% {}'.format(capturing, int(percent), time))
        elif status is not None:
            print(status)

    capture(start, end, exec_at_time_callback, fps=fps, demo_name=demo_name)


class RenderException(Exception):
    pass


class GameErrorException(Exception):
    pass

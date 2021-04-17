import tasks
import tasks_config
import os
from shutil import copyfile

demo_file_name = 'capture-test-demo.dm_84'
demos_folder = os.path.join(tasks_config.ET_HOMEPATH, 'etpro', 'demos')

if not os.path.isfile(os.path.join(demos_folder, demo_file_name)):
    copyfile(os.path.join('ET', 'etpro', 'demos', demo_file_name), os.path.join(demos_folder, demo_file_name))

# https://greatshot.xyz/renders/1403
tasks.test_capture_progress(179568100, 179580100, demo_name=demo_file_name)

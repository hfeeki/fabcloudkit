from __future__ import absolute_import

from collections import defaultdict
from itertools import chain, imap, repeat
from os import walk
from os.path import join
from setuptools import setup, find_packages
import re


def all_files_under(**kwargs):
    result = defaultdict(list)
    for package, start_paths in kwargs.iteritems():
        if isinstance(start_paths, basestring):
            start_paths = [start_paths]
        for start_path in start_paths:
            top = join(package, start_path)
            prefix = re.compile('^' + re.escape(top))
            result[package].extend(chain.from_iterable(imap(join, repeat(prefix.sub(start_path, dirpath)), filenames)
                for dirpath, _, filenames in walk(top)))
    return result


setup(
    name='fabcloudkit',
    version='0.1',
    description='An AWS provisioning, build, and deployment library built on Fabric and Boto.',
    zip_safe=False,

    # only focusing on dependencies.
    packages=find_packages(),
#    package_data=all_files_under(app=['static', 'templates']),

    install_requires=[
        'boto',
        'fabric',
        'pyaml'
    ],

    entry_points = {
        'console_scripts': [
            # runs unit tests in the correct virtualenv.
            #'unittest=unittest:main',

            # create the user database.
            #'dj_create_user_db=persist.user_store:db_tool',

            # create the song-queue/playlist database.
            #'dj_create_song_queue=persist.song_queue:db_tool'
        ]
    }
)
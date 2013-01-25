from __future__ import absolute_import

# standard
import json
import posixpath as path
from StringIO import StringIO

# pypi
from fabric.context_managers import cd, prefix
from fabric.decorators import task
from fabric.operations import get, run

# package
from fabcloudkit import cfg, ctx
from fabcloudkit.tool import git
from fabcloudkit.tool.virtualenv import activate_prefix
from .internal import *
from .util import *


__all__ = ['increment_name']


def build_repo(build_env_dir, repo):
    full_repo_dir = ctx().repo_path(repo.dir)
    dist_dir = path.join(full_repo_dir, 'dist')

    # with the build virtualenv activated, and within the repo directory.
    with prefix(activate_prefix(build_env_dir)), cd(full_repo_dir):
        start_msg('Running "python setup.py install" for repo "{0}"'.format(repo.dir))

        # first create a source distribution using setup.py in this repo.
        result = run('python setup.py sdist --formats=gztar')
        if result.failed:
            raise HaltError('"python setup.py sdist" failed in repo: "{0}"'.format(repo.dir))

        # now use pip to install. couple of things to note:
        # a) pip does a "flat" (not versioned) install, no eggs, and consistent package directory names.
        # b) we're still allowing pip to grab packages from pypi; this should be fixed in a later version
        #    where packages can (optionally) be picked up only from a local directory.
        result = run('pip install --find-links=file://{dist_dir} {repo.package_name}'.format(**locals()))
        if result.failed:
            raise HaltError('"pip install" failed in repo: "{0}"'.format(repo.dir))
        succeed_msg('Build successful.')


class BuildInfo(object):
    BUILD_INFO_FILE = 'build_info.txt'

    @classmethod
    def get_last_good(cls, context_name=None):
        return BuildInfo(context_name).load().last

    @classmethod
    def set_last_good(cls, build_name):
        BuildInfo().load().update(build_name)

    @classmethod
    def next(cls, ref_repo_name):
        commit = git.head_commit(ref_repo_name)
        return BuildInfo().load().next_name(commit)

    @property
    def last(self):
        return self._dct['last']

    @last.setter
    def last(self, build_name):
        self._dct['last'] = build_name

    @property
    def active(self):
        return self._dct['active']

    @active.setter
    def active(self, build_name):
        self._dct['active'] = build_name

    @property
    def active_port(self):
        return self._dct['active_port']

    @active_port.setter
    def active_port(self, port):
        self._dct['active_port'] = int(port)

    @property
    def number(self):
        return self._dct['number']

    def __init__(self, context_name=None):
        self._context_name = ctx().name if not context_name else context_name
        self._dct = None

    def __repr__(self):
        return 'context-name: "{0}"; {1}'.format(self._context_name, self._dct.__repr__())

    def load(self):
        if not self._info_exists():
            self._dct = self._default()
        else:
            stream = StringIO()
            result = get(self._file_path(), stream)
            if result.failed:
                raise HaltError('Unable to retrieve build info file: {0}'.format(self._file_path()))
            self._dct = json.loads(stream.getvalue())
        return self

    def save(self):
        # print it purdy to make things easier on someone looking at the file contents.
        put_string(
            json.dumps(self._dct, sort_keys=True, indent=4, separators=(',', ': ')),
            self._file_path(), use_sudo=True)
        return self

    def next_name(self, commit):
        n = self.number + 1
        name = self._build_name(n, commit)
        self._dct['number'] = n
        self.save()
        return name

    def update(self, build_name):
        self.last = build_name
        self.save()
        return self

    def _info_exists(self):
        result = run('test -f {0}'.format(self._file_path()), quiet=True)
        return result.succeeded

    def _file_path(self):
        return ctx().repo_path(self.BUILD_INFO_FILE)

    def _default(self):
        # number: the mostly recently used build number (build may have failed).
        # last: name of the last known good build.
        # active: name of the active build.
        # active_port: number of the port the active build is running on.
        return dict(number=0, last=None, active=None, active_port=0)

    def _build_name(self, number, commit):
        return '{self._context_name}_{number:0>5}_{commit}'.format(**locals())

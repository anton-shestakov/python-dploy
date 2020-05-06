import os
import fabtools

from fabtools import require
from fabtools.python import virtualenv as _virtualenv
from fabric.contrib import files
from fabric.api import task, env, execute, cd
from fabric.colors import cyan
from dploy.context import ctx, get_project_dir


def _install_requirements(
        filename, upgrade=False, download_cache=None, allow_external=None,
        allow_unverified=None, quiet=False, pip_cmd='pip', use_sudo=False,
        user=None, exists_action=None, upgrade_strategy='only-if-needed'):
    """
    Install Python packages from a pip `requirements file`_.

    ::

        import fabtools

        fabtools.python.install_requirements('project/requirements.txt')

    .. _requirements file: http://www.pip-installer.org/en/latest/requirements.html
    """
    if allow_external is None:
        allow_external = []

    if allow_unverified is None:
        allow_unverified = []

    options = []
    if upgrade:
        options.append('--upgrade')
    if download_cache:
        options.append('--download-cache="%s"' % download_cache)
    for package in allow_external:
        options.append('--allow-external="%s"' % package)
    for package in allow_unverified:
        options.append('--allow-unverified="%s"' % package)
    if quiet:
        options.append('--quiet')
    if exists_action:
        options.append('--exists-action=%s' % exists_action)

    options.append('--upgrade-strategy=%s' % upgrade_strategy)
    options = ' '.join(options)

    command = '%(pip_cmd)s install %(options)s -r %(filename)s' % locals()

    if use_sudo:
        sudo(command, user=user, pty=False)
    else:
        run(command, pty=False)


@task
def install_requirements(upgrade=False, upgrade_strategy='only-if-needed'):
    """
    Installs pip requirements
    """
    project_dir = get_project_dir()
    requirements_pip = os.path.join(project_dir, 'requirements.pip')
    # it is necessary to cd into project dir to support relative
    # paths inside requirements correctly
    with cd(project_dir):
        if files.exists(requirements_pip, use_sudo=True):
            print(cyan("Installing requirements.pip on {}".format(env.stage)))
            with _virtualenv(env.venv_path):
                _install_requirements(
                    requirements_pip, upgrade=upgrade, use_sudo=True,
                    upgrade_strategy=upgrade_strategy)

        requirements_txt = os.path.join(project_dir, 'requirements.txt')
        if files.exists(requirements_txt, use_sudo=True):
            print(cyan("Installing requirements.txt on {}".format(env.stage)))
            with _virtualenv(env.venv_path):
                _install_requirements(
                    requirements_txt, upgrade=upgrade, use_sudo=True,
                    upgrade_strategy=upgrade_strategy)

        extra_requirements = ctx('virtualenv.extra_requirements',
                                 default=False)
        if extra_requirements and isinstance(extra_requirements, list):
            for req in extra_requirements:
                print(cyan("Installing {} on {}".format(req, env.stage)))
                with _virtualenv(env.venv_path):
                    if req.startswith('./'):
                        req = os.path.join(project_dir, req[:2])
                    fabtools.python.install(req, use_sudo=True)


@task
def setup(upgrade=False, upgrade_strategy='only-if-needed'):
    """
    Setup virtualenv on the remote location
    """
    venv_root = ctx('virtualenv.dirs.root')
    venv_name = ctx('virtualenv.name')
    venv_path = os.path.join(venv_root, venv_name)
    py = 'python{}'.format(ctx('python.version'))
    env.venv_path = venv_path

    if not fabtools.deb.is_installed('python-virtualenv'):
        fabtools.deb.install('python-virtualenv')
    # Experimental
    require.python.virtualenv(
        venv_path, python_cmd=py, use_sudo=True, venv_python=py)
    with _virtualenv(venv_path):
        require.python.pip()
        require.python.setuptools()
    execute(install_requirements, upgrade=upgrade, upgrade_strategy=upgrade_strategy)
    # /Experimental

    # lib_root = os.path.join(venv_root, venv_name, 'lib')
    # if not files.exists(lib_root, use_sudo=True):
    #     print(cyan("Setuping virtualenv on {}".format(env.stage)))
    #     with cd(venv_root):
    #         sudo('virtualenv --python=python{version} {name}'.format(
    #             version=ctx('python.version'),
    #             name=ctx('virtualenv.name')))
    # pip('install -U setuptools pip')  # Just avoiding some headaches..

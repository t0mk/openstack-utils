import os
import logging
import subprocess
import novaclient.v1_1

KEYPAIR = 'tkarasek_key'

_USERNAME = os.environ['OS_USERNAME']
_PASSWORD = os.environ['OS_PASSWORD']
_TENANT = os.environ['OS_TENANT_NAME']
_AUTH_URL = os.environ['OS_AUTH_URL']


logger = logging.getLogger('os_utils')
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class NovaWrapperError(Exception):
    pass


class NovaProxy(object):
    _client = None
    def __new__(cls, *args, **kwargs):
        if not cls._client:
            cls._client = novaclient.v1_1.client.Client(
                username=_USERNAME, api_key=_PASSWORD,
                auth_url=_AUTH_URL, project_id=_TENANT)
        return cls._client


def callCheck(command, env=None, stdin=None):
    logger.info("about to run \"%s\"" % command)
    if subprocess.call(command.split(), env=env, stdin=stdin):
        raise Exception("%s failed." % command)


import os
import logging
import subprocess
import uuid

import novaclient.v1_1
import glanceclient
import keystoneclient.v2_0
import neutronclient.neutron.client

# set the following variables to what you like

# name of openstack keypair
KEYPAIR = 'tkarasek_key'

# prefix for random names of Virtual machines run with fastnovaboot
BASE_NAME = 'tomktest'

# prefix for random names of Virtual Machines run with ansiblespawn
BASE_NAME_SPAWNTEST = 'spawntest'

# UUID of default image
BASE_IMAGE = 'db93d1ac-308e-43c5-acaa-666553b606a7'

# default flavor
BASE_FLAVOR = 'm1.tiny'

# default list of security groups for instances
BASE_SECGROUPS = 'default'

# path to file with private key for your openstack keypair
PRIVKEY_FILE = os.path.expanduser("~/keys/tkarasek_key.pem")

# openstack variables
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

reuse_proxies = True

class NovaWrapperError(Exception):
    pass

class AnsibleWrapperError(Exception):
    pass

class KeystoneProxy(object):
    _client = None
    def __new__(cls, *args, **kwargs):
        if not cls._client or not reuse_proxies:
            cls._client = keystoneclient.v2_0.client.Client(
            username=_USERNAME, password=_PASSWORD,
            tenant_name=_TENANT, auth_url=_AUTH_URL
        )
        return cls._client


class NovaProxy(object):
    _client = None
    def __new__(cls, *args, **kwargs):
        if not cls._client or not reuse_proxies:
            # nova client cant be create from Keystone catalog URL ...
            cls._client = novaclient.v1_1.client.Client(
                username=_USERNAME, api_key=_PASSWORD,
                auth_url=_AUTH_URL, project_id=_TENANT)
        return cls._client


class GlanceProxy(object):
    _client = None
    def __new__(cls, *args, **kwargs):
        if not cls._client or not reuse_proxies:
            # Glance client can be created from Keystone catalog URL
            endpoints  = KeystoneProxy().service_catalog.get_endpoints()
            url = endpoints["image"][0]["publicURL"]
            cls._client = glanceclient.Client('1', url,
                token=KeystoneProxy().auth_token)
        return cls._client


class NeutronProxy(object):
    _client = None
    def __new__(cls, *args, **kwargs):
        if not cls._client or not reuse_proxies:
            endpoints  = KeystoneProxy().service_catalog.get_endpoints()
            url = endpoints["network"][0]["publicURL"]
            cls._client = neutronclient.neutron.client.Client(
                '2.0', endpoint_url=url, token=KeystoneProxy().auth_token)
        return cls._client


def callCheck(command, env=None, stdin=None):
    logger.info("about to run \"%s\"" % command)
    if subprocess.call(command.split(), env=env, stdin=stdin):
        raise Exception("%s failed." % command)


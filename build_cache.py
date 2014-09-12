#!/usr/bin/env python

# This script will build a simple cache for openstack resources for given
# tenants. If you want to run it from cron, you should first read your
# OpenStack credentials to environment variables.

# put this in yout crontab to run each 5 minutes as
*/5 * * * * . /home/tomk/os/openrc.sh && /home/tomk/bin/openstack-utils/build_cache.py

import util
import errno
import os

CACHE_DIR = '/tmp/os_cache'
INSTANCES_CACHE_FILE = CACHE_DIR + '/instances_%s'
SECGROUPS_CACHE_FILE = CACHE_DIR + '/secgroups_%s'
IMAGES_CACHE_FILE = CACHE_DIR + '/images_%s'


def getAddrs(vm):
    addrs = getattr(vm, 'addresses')
    fixed = [ x['addr'] for x
                in addrs.itervalues().next()
                if x['OS-EXT-IPS:type'] == 'fixed'
              ]
    floating  = [ x['addr'] for x
                in addrs.itervalues().next()
                if x['OS-EXT-IPS:type'] == 'floating'
              ]
    return {'fixed': fixed, 'floating': floating}

def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

mkdirp(CACHE_DIR)

TENANTS = ['provisiontest', 'digile']

util.reuse_proxies = False

for t in TENANTS:
    util._TENANT = t
    _nova_prox = util.NovaProxy()
    with open(INSTANCES_CACHE_FILE % t, 'w') as f:
        for s in _nova_prox.servers.list():
            f.write("%s %s %s\n" % (s.id, s.name, getAddrs(s)))
    with open(SECGROUPS_CACHE_FILE % t, 'w') as f:
        for g in _nova_prox.security_groups.list():
            f.write("%s %s\n" % (g.name, g.description.replace(' ','_')))
    _glance_prox = util.GlanceProxy()
    with open(IMAGES_CACHE_FILE % t, 'w') as f:
        for i in _glance_prox.images.list():
            f.write("%s %s\n" % (i.id, i.name.replace(' ','_')))



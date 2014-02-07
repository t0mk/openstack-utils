#!/usr/bin/env python

"""
Wrapper of nova API boot call that assigns a floating ip to an instance.
It spares you from assigning a floating IP to the new instance after
"nova boot".

See the util.py first, and set the BASE_* variables to what you like

The script takes credentials, tenant name and Keystone URL from the usual
environment variables (OS_{AUTH_URL,TENANT_ID,TENANT_NAME,USERNAME,PASSWORD})

See
$ fastnovaboot --help
"""

import uuid
import time
import pprint
import argparse
import json
import sys

import util

i = util.logger.info
d = util.logger.debug

_nova = util.NovaProxy
_glance = util.GlanceProxy

def get_free_floating_ips():
    return [ ip for ip in _nova().floating_ips.list()
             if ip.instance_id is None ]


def dig_a_floating_ip():
    free_ips = get_free_floating_ips()
    if len(free_ips) == 0:
        i("There are no free allocated floating IPs. The script will attempt "
          "to get one from the first available pool.")
        pool_name = _nova().floating_ip_pools.list()[0].name
        i("Found pool %s, will try to allocate one floating IP from it"
          % pool_name)
        try:
            _nova().floating_ips.create(pool=pool_name)
        except Exception as e:
            # TODO: check what exception this throws
            util.logger.error("Most likely no more IPs in the pool %s"
                               % pool_name)
            raise e
        free_ips = get_free_floating_ips()
        i("A floating IP was allocated from the pool and will be assigned to"
          "the new instance.")
    return free_ips[0]


def find_server_with_id(server_id):
    found = [ s for s in _nova().servers.list() if s.id == server_id ]
    if not found:
        raise util.NovaWrapperError("No server with id %s" % server_id)
    return found[0]


def server_has_a_fixed_ip(server_id):
    server = find_server_with_id(server_id)
    attached_nets = server.networks
    if not attached_nets:
        return False
    for net in attached_nets.values():
        if len(net) > 0:
            i("Server %s has fixed IP %s" % (server_id, net))
            return True
    return False

def find_resource_id_by_name(name, resource_list):
    try:
        uuid.UUID(name)
        # name is uuid
        return name
    except ValueError:
        matching = [r.id for r in resource_list() if name in r.name]
        if len(matching) == 0:
            msg = ("Could not find any resource matching name '%s'. "
                   "If this is an image, check that it's public or shared "
                   "with the current tenant (it's listed in $ glance index)"
                   % name)
            raise util.NovaWrapperError(msg)
        if len(matching) > 1:
            raise util.NovaWrapperError(
                "Found too many resources matching name '%s': %s" %
                (name, matching))
        return matching[0]

def get_args(args_list):
    _name = util.BASE_NAME + '-' + uuid.uuid4().hex[:4]

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='smarter nova boot')

    help_userdata = "File with userdata for cloudinit"
    help_test = "Avoid all calls changing states in OpenStack"
    help_meta = ("JSON dict with additional meta-data. Up to 5 items. Keys "
                 "and values must be only strings - no numbers or lists."
                 "Enclose the whole argument to single quotes and string "
                 "literals in it to double quotes. I.e. OK: '{\"a\": \"5\"}', "
                 "NOT OK: \"{'a': '5'}\" ")
    help_name = ("name for the new server. Default is "
                 "%s-<4 random hex chars>." % util.BASE_NAME)
    help_image = ("name or id of image to boot.")
    help_flavor = ("name of flavor ($ nova flavor-list')")
    help_secgroups = ("Space-separated list of security groups which in which "
                      "the instance should be.")
    help_groups = ("Space-separated list of host groups that you want the "
                   "host to belong. This is completely up to the user, and it "
                   "not checked for validity. ")

    parser.add_argument('-n', '--name', help=help_name, default=_name)
    parser.add_argument('-i', '--image', help=help_image,
                        default=util.BASE_IMAGE)
    parser.add_argument('-f', '--flavor', help=help_flavor,
                        default=util.BASE_FLAVOR)

    parser.add_argument('-u', '--userdata', type=argparse.FileType('r'),
                        help=help_userdata)

    parser.add_argument('-t', '--test', default=False, action="store_true",
                        help=help_test)
    parser.add_argument('-s', '--secgroups', nargs='+', help=help_secgroups,
                        default=util.BASE_SECGROUPS)
    parser.add_argument('-m', '--meta', help=help_meta)
    parser.add_argument('-g', '--groups', help=help_groups, nargs='+')

    return parser.parse_args(sys.argv[1:])


def main(args_list):
    args = get_args(args_list)

    _image  = find_resource_id_by_name(args.image, _glance().images.list)
    _flavor = find_resource_id_by_name(args.flavor, _nova().flavors.list)

    if args.test:
        print "args are"
        print args

    params = {'name': args.name, 'image': _image, 'flavor': _flavor,
              'key_name': util.KEYPAIR, 'userdata': args.userdata,
              'security_groups': args.secgroups}

    if args.meta:
        _meta_dict = json.loads(args.meta)
        if type(_meta_dict) != dict:
            raise NovaWrapperError("the --meta parameter must be a json dict")
        if len(_meta_dict) > 5:
            raise NovaWrapperError("the meta dict can't have more than 5 items")
        params['meta'] = _meta_dict

    if args.groups:
        if 'meta' not in params:
            params['meta'] = {}
        params['meta'][u'groups'] = ",".join(args.groups)
        if len(params['meta']) > 5:
            raise NovaWrapperError("the meta dict can't have more than 5 "
                                   "items, including the group item")

    i("Launching new server with parameters:\n%s" % pprint.pformat(params))

    if args.test:
        util.GlanceProxy()
        i("This is a test run, _NOT_ booting the instance.")
    else:
        new_server = _nova().servers.create(**params)
        i("Created new server with id " + new_server.id)

        i("About to assign a floating IP. For that, we need to wait till "
          "the vm will show a fixed IP address..")

        server_id = new_server.id

        while not server_has_a_fixed_ip(server_id):
            status = _nova().servers.get(server_id).status
            if status == 'ERROR':
                raise util.NovaWrapperError('Server got to ERROR status.')
            if status != 'BUILD':
                i("Server in weird status: %s" % status)
            time.sleep(1)


        free_ip = dig_a_floating_ip()

        i("Assigning floating IP %s to the new server" % free_ip)

        new_server.add_floating_ip(free_ip)

        util.callCheck("nova show " + new_server.id)
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


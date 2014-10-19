#!/usr/bin/env python

"""
Wrapper of nova API boot call that boots an instance and assigns a floating ip
to it.

It also checks the status of the machine shortly after creation.

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
import socket
import sys
import os

import util


def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


i = util.logger.info
d = util.logger.debug


_nova = util.NovaProxy
_glance = util.GlanceProxy
_neutron = util.NeutronProxy


def get_free_floating_ips():
    return [ ip for ip in _nova().floating_ips.list()
             if ip.instance_id is None ]

def get_free_floating_ip(ip):
    for ii in get_free_floating_ips():
        if ii.ip == ip:
            return ii
    raise util.NovaWrapperError("No free floating ip %s found" % ip)


def allocate_floating_ip():
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

def dig_a_floating_ip():
    free_ips = get_free_floating_ips()
    if len(free_ips) == 0:
        i("There are no free allocated floating IPs. The script will attempt "
          "to get one from the first available pool.")
        allocate_floating_ip()
        free_ips = get_free_floating_ips()
        i("A floating IP was allocated from the pool")
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


def add_security_groups(server_id, secgroup_ids):
    i("about to get list of ports of the new server (neutron call)")
    port_list = _neutron().list_ports(device_id=server_id)
    port_list = port_list['ports']
    for port in port_list:
        i("about to add security groups %s to the new server" % secgroup_ids)
        _neutron().update_port(port['id'], body={'port': {'security_groups':secgroup_ids}})


def find_resource_id_by_name(name, resource_list, use_getitem=False,
                             subitem=None):
    try:
        uuid.UUID(name)
        # name is uuid
        return name
    except ValueError:
        if subitem:
            resource_list = resource_list[subitem]
        if use_getitem:
            matching = [r['id'] for r in resource_list if name == r['name']]
        else:
            matching = [r.id for r in resource_list if name == r.name]
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
        prog='fastnovaboot',
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
    help_image = ("name or id of image to boot. If you pass non-uuid string, "
                  "it will be substring-matched to names of existing images." )
    help_flavor = ("name of flavor ($ nova flavor-list'). If you pass "
                   "non-uuid string, it will be substring matched to names "
                   "of existing flavors.")
    help_secgroups = ("comma-separated list of security groups which in which "
                      "the instance should be.")
    help_floatingip = ("Floating IP or FQDN of a floating IP to assign after "
                       "server boot. Not mandatory - if you don't supply, the "
                       "script will try to find a free floating ip.")

    parser.add_argument('-n', '--name', help=help_name, default=_name)
    parser.add_argument('-i', '--image', help=help_image,
                        default=util.BASE_IMAGE)
    parser.add_argument('-f', '--flavor', help=help_flavor,
                        default=util.BASE_FLAVOR)
    parser.add_argument('-l', '--floatingip', help=help_floatingip)
    parser.add_argument('-u', '--userdata', type=argparse.FileType('r'),
                        help=help_userdata)

    parser.add_argument('-t', '--test', default=False, action="store_true",
                        help=help_test)
    parser.add_argument('-s', '--secgroups', help=help_secgroups,
                        required=True)
    parser.add_argument('-m', '--meta', help=help_meta)

    return parser.parse_args(args_list)


def main(args_list):
    args = get_args(args_list)

    _image  = find_resource_id_by_name(args.image, _glance().images.list())
    _flavor = find_resource_id_by_name(args.flavor, _nova().flavors.list())

    if args.test:
        print "args are"
        print args

    params = {'name': args.name, 'image': _image, 'flavor': _flavor,
              'key_name': util.KEYPAIR, 'userdata': args.userdata}

    if args.meta:
        _meta_dict = json.loads(args.meta)
        if type(_meta_dict) != dict:
            raise util.NovaWrapperError("the --meta parameter must be a json"
                                       " dict")
        if len(_meta_dict) > 5:
            raise util.NovaWrapperError("the meta dict can't have more than 5"
                                       " items")
        params['meta'] = _meta_dict

    if args.floatingip:
        if not is_valid_ipv4_address(args.floatingip):
            try:
                orig_name = args.floatingip
                args.floatingip = socket.gethostbyname(args.floatingip)
                i("FQDN %s has IP address %s" % (orig_name, args.floatingip))
            except socket.gaierror:
                raise util.NovaWrapperError("name %s does not DNS translate" %
                                       args.floatingip)
        i("Checking if ip %s is available" % args.floatingip)
        while args.floatingip not in [ii.ip for ii in get_free_floating_ips()]:
            i("ip not available, trying to allocate another from the pool")
            allocate_floating_ip()

    i("Launching new server with parameters:\n%s" % pprint.pformat(params))

    if args.test:
        util.GlanceProxy()
        i("This is a test run, _NOT_ booting the instance.")
        return (None, None)
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

        if args.floatingip:
            assigned_ip = get_free_floating_ip(args.floatingip)
        else:
            assigned_ip = dig_a_floating_ip()

        i("Assigning floating IP %s to the new server" % assigned_ip)

        new_server.add_floating_ip(assigned_ip)

        secgroup_ids = []
        all_sgs = _neutron().list_security_groups(
            tenant_id=os.environ['OS_TENANT_ID'])
        for sg in args.secgroups.split(','):
            sgid  = find_resource_id_by_name(sg, all_sgs,
                       use_getitem=True, subitem='security_groups')
            secgroup_ids.append(sgid)

        add_security_groups(new_server.id, secgroup_ids)


        util.callCheck("nova show " + new_server.id)
        return (new_server.image['id'], assigned_ip.ip)


if __name__ == '__main__':
    main(sys.argv[1:])


#!/usr/bin/python

# Script which opens sh connection to a openstack instance with
# name containing $1.
# It will try to find the instance and then a corresponding floating IP.
#
# For example if you have instance called "tomktest_f978", then
# $ novassh f978
# will open ssh connection to the instance. It will match first
# instance matching the name (first in nova list, so probably the
# latest created one),
#
# In order for the script to work, the key must be ok, network must
# be working. The script will attempt to ssh as root. If it detects
# Ubuntu image, it will ssh as "ubuntu".

import argparse

import util
import uuid
import sys

i = util.logger.info


def get_floating_ip_of_instance(instance_id):
    ips = [ip for ip in util.NovaProxy().floating_ips.list()
           if ip.instance_id == instance_id]
    if not ips:
        raise util.NovaWrapperError("Instance %s does not have a floating IP"
                                    % instance_id)
    return ips[0]


def check_port_open(vm, port):
    secgroup_names = [sg['name'] for sg in vm.security_groups]

    secgroups = [sg for sg in util.NovaProxy().security_groups.list()
                 if sg.name in secgroup_names]
    relevant_rules = sum([sg.rules for sg in secgroups], [])
    for rule in relevant_rules:
        if rule['from_port'] and rule['to_port']:
            if rule['from_port'] <= port <= rule['to_port']:
                return True
    return False


def get_matching_vms(name):
    try:
        uuid.UUID(name)
        # name is UUID
        return [ m for m in util.NovaProxy().servers.list() if name in m.id ]
    except ValueError:
        return [ m for m in util.NovaProxy().servers.list() if name in m.name ]


def get_ssh_user(image_id):
    ssh_user = 'root'

    image_name = util.NovaProxy().images.get(image_id).name

    if 'ubuntu' in image_name.lower():
        ssh_user = 'ubuntu'
    if 'centos' in  image_name.lower():
        ssh_user = 'cloud-user'
    if 'debian' in  image_name.lower():
        ssh_user = 'debian'
    return ssh_user


def test_ssh_connection(ssh_user, ip):
    try:
        ssh_cmd = ("ssh -q -o ConnectTimeout=3 -i %s %s@%s exit" %
                  (util.PRIVKEY_FILE, ssh_user, ip))
        util.callCheck(ssh_cmd)
        i("Sucessfully connected to %s" % ip)
        return 0
    except:
        i("Failed when attempting to open ssh connection as %s" %
          ssh_cmd)
        return -1


def ask():
    l = util.NovaProxy().servers.list()
    i = 1
    print "Current tenant is \"%s\". There are following VMs:" % util._TENANT
    for s in l:
        addresses = [a['addr'] for a in s.addresses.values()[0]]
        print "%d: %s, %s" % (i, s, addresses)
        i += 1

    ch = raw_input("Select VM to SSH to (give one number): ")

    num = int(ch)
    return l[num-1]


def get_args(args_list):
    parser = argparse.ArgumentParser(
        description='smart ssh to a nova instance')

    help_nosshcheck = ('Dont check if machine has port 22 open in some '
                       'security group.')

    help_test = ('Just check if the ssh connection can be open, and quit.')

    parser.add_argument('instance_name', nargs='?',
                        help='name of instance to ssh to')

    parser.add_argument('-u','--user', help='user for ssh')
    parser.add_argument('-n', '--nosshcheck', help=help_nosshcheck,
                        action='store_true')
    parser.add_argument('-t', '--test', help=help_test, action='store_true')

    return parser.parse_args(args_list)


def main(args_list):
    args = get_args(args_list)
    vm = None

    if not args.instance_name:
        vm = ask()
    else:
        matching_vms = get_matching_vms(args.instance_name)
        if not matching_vms:
            raise util.NovaWrapperError("no vm matches name %s"
                                        % args.instance_name)
        vm = matching_vms[0]


    i("Will attempt to ssh to instance %s" % vm)

    if not args.user:
        ssh_user = get_ssh_user(vm.image['id'])
    else:
        ssh_user = args.user

    fip = get_floating_ip_of_instance(vm.id)

    if not args.nosshcheck:
        if not check_port_open(vm, 22):
            raise util.NovaWrapperError("Port 22 is not open in any security "
                                        "group in the machine.")
    if args.test:
        return test_ssh_connection(ssh_user, fip.ip)
    else:
        ssh_cmd = "ssh -X -i %s %s@%s" % (util.PRIVKEY_FILE, ssh_user, fip.ip)
        util.callCheck(ssh_cmd)

    return 0


if __name__ == "__main__":

    sys.exit(main(sys.argv[1:]))



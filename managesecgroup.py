#!/usr/bin/python

# script for populating security group from command line in easy way
#
# Examples:
#
# open ports 80 443 and 22 for CIDRs 212.68.9.98/32 193.166.24.0/23 in security
# group "default":
# $ managesecgroup -n default -p 80 443 22 -i 212.68.9.98/32 193.166.24.0/23
#
# create security group called "testenv" and populate with rules opening
# 80,443 and 22 to 212.68.9.98/32 193.166.24.0/23
# $ managesecgroup -n testenv -c -p 80 443 22 \
#                  -i 212.68.9.98/32 193.166.24.0/23

import argparse
import sys
import socket

import util

i = util.logger.info

CIDR_ALIASES = {'digile': '83.150.108.249/32', 'forge': '193.166.24.0/23' }

desc = ('Create of modify security group')

def check_CIDR(cidr):
    i("Checking if '%s' is a proper CIDR address" % cidr)
    ip, maskbitcount = cidr.split('/')
    maskbitcount = int(maskbitcount)
    if not (0 <= maskbitcount <= 32):
        raise Exception("the number after slash must be 0-32")
    socket.inet_aton(ip)


def get_args(args_list):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=desc)

    help_create = 'create the security group first'

    parser.add_argument('-c', '--create', help=help_create, default=False,
                        action='store_true')

    parser.add_argument('-n', '--name', help='name of the sec group',
                        default='default', required=True)

    parser.add_argument('-p', '--ports', help='space separated list of ports',
                        nargs='+', default=['443', '80', '22'])

    parser.add_argument('-i', '--cidrs', help='space separated list of CIDRs',
                        nargs='+', required=True)

    parser.add_argument('-t', '--test', help='test run, dont change anything',
                        action='store_true')

    return parser.parse_args(args_list)


def main(args_list):
    args = get_args(args_list)
    _nova = util.NovaProxy

    sec_group = None

    if not args.test:
        if args.create:
            sec_group = _nova().security_groups.create(args.name, args.name)
        else:
            sec_group = _nova().security_groups.find(name=args.name)

    for port in args.ports:
        for cidr in args.cidrs:
            true_cidr = CIDR_ALIASES.get(cidr, cidr)
            check_CIDR(true_cidr)
            i("adding rule: port %s, cidr %s " % (port, cidr))
            if not args.test:
                _nova().security_group_rules.create(sec_group.id,
                    ip_protocol='tcp', from_port=port, to_port=port,
                    # if cidr is alias, try to get it from the alias dict,
                    # if it's not an alias, use it as CIDR:
                    cidr=true_cidr)
            else:
                i('This is just a test, the rule is not added')


if __name__ == '__main__':
    main(sys.argv[1:])


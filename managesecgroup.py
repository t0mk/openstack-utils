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
import util


CIDR_ALIASES = {'digile': '212.68.9.98/32', 'forge': '193.166.24.0/23' }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='smart security group handling')

    help_create = 'create the security group first'

    parser.add_argument('-c', '--create', help=help_create, default=False,
                        action='store_true')

    parser.add_argument('-n', '--name', help='name of the sec group',
                        default='default', required=True)

    parser.add_argument('-p', '--ports', help='space separated list of ports',
                        nargs='+', default=['443', '80', '22'])

    parser.add_argument('-i', '--cidrs', help='space separated list of CIDRs',
                        nargs='+', required=True)

    args = parser.parse_args()

    _nova = util.NovaProxy

    sec_group = None

    if args.create:
        sec_group = _nova().security_groups.create(args.name, args.name)
    else:
        sec_group = _nova().security_groups.find(name=args.name)

    for port in args.ports:
        for cidr in args.cidrs:
            _nova().security_group_rules.create(sec_group.id,
                ip_protocol='tcp', from_port=port, to_port=port,
                cidr=CIDR_ALIASES.get(cidr, cidr))


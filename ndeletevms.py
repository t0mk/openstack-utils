#!/usr/bin/env python

# script that deletes all vms in current tenant
# if an argument is passed, only vms with mathcing names are deleted

import argparse
import sys

import util

desc = 'Script deleting Openstack VMs matching given substring'

def main(args_list):
    args = get_args(args_list)

    matching = [ s for s in util.NovaProxy().servers.list()
                 if args.substring in s.name ]

    for s in matching:
        util.logger.info("Removing server %s" % s)
        if not args.test:
            util.NovaProxy().servers.delete(s.id)


def get_args(args_list):
    parser = argparse.ArgumentParser(
       formatter_class=argparse.ArgumentDefaultsHelpFormatter,
       description=desc)
    help_test = 'Dont delete, just say which servers match'
    help_substring = 'Substring to match the server names'
    parser.add_argument('-t', '--test', help=help_test, action='store_true')
    parser.add_argument('-s', '--substring', help=help_test,
                        required=True)
    return parser.parse_args(args_list)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))


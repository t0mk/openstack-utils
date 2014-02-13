#!/usr/bin/env python

import sys
import time
import uuid
import os.path

import util
import nssh
import fastnovaboot
import argparse

i = util.logger.info
interval = 3

desc = ('Spawn a VM and run an Ansible playbook on it. The playbook comes '
        'in -p argument. the rest of the arguments are passed to '
        'fastnovaboot.')

def main(args_list):
    args, unparsed_args_list = get_args(args_list)

    if not os.path.isfile(args.playbook):
        raise util.NovaWrapperError("Given playbook doesn't exist")

    util.callCheck("ansible-playbook --syntax-check %s" % args.playbook)

    if not unparsed_args_list:
        unparsed_args_list = []

    name = 'spawntest-' + uuid.uuid4().hex[:4]
    if args.name:
        name = args.name

    unparsed_args_list += ['-n',name]


    if args.test:
        # this will cause nova boot to do only a test run
        unparsed_args_list += ['-t']

    i("About to run fastnovaboot with args: %s" % unparsed_args_list)
    _, ip = fastnovaboot.main(unparsed_args_list)

    if not args.test:
        while nssh.main(['-t', name]) != 0:
            i("The %s VM is not ready yet. Sleeping for %d seconds" %
              (name, interval))
            time.sleep(interval)
    else:
        i('A test run, _NOT_ spawning the VM')

    ansible_cmd = "ansible-playbook %s -e h=%s" % (args.playbook, ip)
    i("VM ready. About to execute %s" % ansible_cmd)

    if not args.test:
        util.callCheck(ansible_cmd)
    else:
        i('A test run, _NOT_ running ansible-playbook')


def get_args(args_list):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='ansiblespawn',
        description=desc)

    help_playbook = 'ansible playbook with - hosts: "{{ h }}"'
    help_test = 'test - dont spawn and dont run ansible'
    help_name = 'name for the spawned instance, not mandatory'

    parser.add_argument('-p', '--playbook', help=help_playbook, required=True)
    parser.add_argument('-t', '--test', help=help_test, action='store_true')
    parser.add_argument('-n', '--name', help=help_name, required=False)

    # returns tupe (args with populated namespace, remaining unparsed opts)
    return parser.parse_known_args(args_list)


if __name__ == '__main__':
    main(sys.argv[1:])


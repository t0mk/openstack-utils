#!/usr/bin/env python

import sys
import yaml
import os.path

import util
import shutil
import argparse
import tempfile
import atexit

i = util.logger.info
interval = 3

desc = ('Apply a role to a host from ansible inventory')

def remove_tmp_dir(d):
    i("removing %s" % d)
    shutil.rmtree(d)

def main(args_list):
    args, unparsed_args_list = get_args(args_list)

    tmp_dir = tempfile.mkdtemp()
    i("created temporary dir %s" % tmp_dir)
    if not args.debug:
        atexit.register(remove_tmp_dir, tmp_dir)
    cwd = os.getcwd()
    os.chdir(tmp_dir)
    os.mkdir(os.path.join(tmp_dir, 'roles'))
    role_dir = os.path.join(cwd, args.role)

    if os.path.isdir(role_dir):
        role_name = os.path.basename(role_dir)
        dest_dir = os.path.join(tmp_dir, 'roles', role_name)
        shutil.copytree(role_dir, dest_dir)
        i("copied role %s" % args.role)

    elif args.role.endswith('.git'):
        role_name = args.role.split('/')[-1].split('.')[0]
        os.chdir(os.path.join(tmp_dir, 'roles'))
        util.callCheck("git clone %s" % args.role)
        i("cloned role %s" % args.role)
        os.chdir(tmp_dir)
    else:
        raise util.AnsibleWrapperError("Given role doesn't exist")

    # cur dir is tmp_dir
    # desired role is in role_name
    # desired host is in args.host

    playbook = [{
      'hosts': args.host,
      'roles': [
         {'role': role_name}
      ]
    }]

    with open ('i.yml', 'w') as playbook_file:
        playbook_file.write(yaml.dump(playbook))

    util.callCheck("cat i.yml")

    util.callCheck("ansible-playbook --syntax-check i.yml")

    if not args.test:
        ansible_cmd = "ansible-playbook -v -s i.yml"
        util.callCheck(ansible_cmd)
    else:
        i('A test run, _NOT_ running ansible-playbook')


def get_args(args_list):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='ansible-apply-role-to-host',
        description=desc)

    help_role = ("ansible role. Must be a direcoty with the role, or url of "
                "remote git repo.")
    help_test = 'test - dont run ansible-playbook'
    help_host = 'host alias present in ansible inventory'
    help_debug = 'dont remove temporary dir'

    parser.add_argument('host', help=help_host)
    parser.add_argument('-r', '--role', help=help_role, required=True)
    parser.add_argument('-t', '--test', help=help_test, action='store_true')
    parser.add_argument('-d', '--debug', help=help_debug, action='store_true')

    # returns tupe (args with populated namespace, remaining unparsed opts)
    return parser.parse_known_args(args_list)


if __name__ == '__main__':
    main(sys.argv[1:])


<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](http://doctoc.herokuapp.com/)*

- [openstack-utils](#openstack-utils)
  - [Installation](#installation)
  - [Tools description](#tools-description)
    - [fastnovaboot](#fastnovaboot)
    - [ansible-spawn](#ansible-spawn)
    - [managesecgroup](#managesecgroup)
    - [ndeletevms](#ndeletevms)
    - [nssh](#nssh)
    - [tenant-switch](#tenant-switch)
    - [build\_cache.py](#build\_cachepy)
  - [Usage](#usage)
    - [Basic workflow](#basic-workflow)
    - [Workflow with ansible](#workflow-with-ansible)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# openstack-utils

utilities that help me to cope with the OpenStack

## Installation

```
cd ~/bin
git clone https://github.com/t0mk/openstack-utils
echo 'PATH=${PATH}:~/bin/openstack-utils' >> ~/.zshrc
# echo 'PATH=${PATH}:~/bin/openstack-utils' >> ~/.bashrc
```
## Tools description

Each of the tool will print info on the --help switch.

### fastnovaboot
More convenient spawning. You can specify image, flavor, floatingip, security groups.

### ansible-spawn
Boot VM and run ansible playbook on it. It run fastnovaboot and can take parameters of fastnovaboot too.

### managesecgroup
Creates and edits security groups easier.

### ndeletevms
Delete vms mathcing a substring.

### nssh
Ssh to a machine based on a substring of it's nova name. If name of the vm is `appserver-2f3d`, you can ssh there as `$ nssh 2f3d`.

### tenant-switch
Source this script in your .zshrc (.bashrc) and change the current tenant name (OS_TENANT_ID) just on `$ t [Enter]`.

### build\_cache.py
Creates cache of resources lists in local filesystem. This can be used for example in auto-completion with https://github.com/t0mk/oh-my-zsh-openstack

## Usage

A few examples follow.

### Basic workflow

```
$ fastnovaboot -i "CentOS_6.4" -f m1.tiny -n instance-test81 -s testsecgroup
[...]
INFO:os_utils: Created new server with id 918453ec-e383-4326-be62-c523db06cabd
INFO:os_utils: About to assign a floating IP. For that, we need to wait till the vm will show a fixed IP address..
INFO:os_utils: Server 918453ec-e383-4326-be62-c523db06cabd has fixed IP [u'192.168.3.4']
INFO:os_utils: Assigning floating IP <FloatingIP fixed_ip=None, id=81676b9e-bfcd-456c-bb9c-e95b5a0e81aa, instance_id=None, ip=182.166.24.117, pool=public> to the new server
[...]

$ managesecgroup -n testsecgroup -p 22 80 443 -i 1.1.1.1/32 192.168.1.0/24

$ nssh test81
[...]

$ ndeletevm test81
```

You can also do `$ nssh` without parameters. It will list instances in current tenant and offer you to choose to which to SSH.

### Workflow with ansible

Using _ansiblespawn_:

with an example playbook showissue.yml:
```yaml
- hosts: "{{ h }}"
  tasks:
    - shell: cat /etc/issue
```
then spawn an instance and run playbook on it as

```
$ ansiblespawn -i db93d1ac-308e-43c5-acaa-666553b606a7 -p showissue.yml
```

if you don't specify image, you will be shown image list and you can choose interactively

```
[...]
INFO:os_utils: About to run fastnovaboot with args: ['-n', 'spawntest-4540']:
INFO:os_utils: Launching new server with parameters:
{'flavor': u'9cfdfdfe-36e4-4458-b17a-e864df8baee6',
 'image': 'db93d1ac-308e-43c5-acaa-666553b606a7',
 'key_name': 'tkarasek_key',
 'name': 'spawntest-4540',
 'security_groups': ['default'],
 'userdata': None}
INFO:os_utils: Created new server with id b438b904-abff-4b35-8015-3b241062a072
INFO:os_utils: About to assign a floating IP. For that, we need to wait till the vm will show a fixed IP address..
INFO:os_utils: Server b438b904-abff-4b35-8015-3b241062a072 has fixed IP [u'192.168.3.5']
INFO:os_utils: Assigning floating IP <FloatingIP fixed_ip=None, id=cd8f9b0e-3060-46cd-a67d-dbae12530aa2, instance_id=None, ip=193.166.24.142, pool=public> to the new server
[...]
INFO:os_utils: The spawntest-97e6 VM is not ready yet. Sleeping for 3 seconds
INFO:os_utils: Will attempt to ssh to instance <Server: spawntest-97e6>
INFO:os_utils: about to run "ssh -q -o ConnectTimeout=3 -i /home/tomk/keys/tkarasek_key.pem root@193.166.24.144 exit"
INFO:os_utils: Sucessfully connected to 193.166.24.144
INFO:os_utils: VM ready. About to execute ansible-playbook i.yml -e h=193.166.24.144
INFO:os_utils: about to run "ansible-playbook i.yml -e h=193.166.24.144"

PLAY [193.166.24.144] *********************************************************

GATHERING FACTS ***************************************************************
ok: [193.166.24.144]

TASK: [shell cat /etc/issue] **************************************************
changed: [193.166.24.144]

PLAY RECAP ********************************************************************
193.166.24.144             : ok=2    changed=1    unreachable=0    failed=0
[...]

$ ndeletemvs 4540
```

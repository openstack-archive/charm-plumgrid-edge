# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# This file contains functions used by the hooks to deploy PLUMgrid Director.

from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from copy import deepcopy
from charmhelpers.core.hookenv import (
    log,
    config,
    unit_get,
)
from charmhelpers.contrib.network.ip import (
    get_iface_from_addr,
    get_bridges,
    get_bridge_nics,
    is_ip,
    is_address_in_network,
    get_iface_addr
)
from charmhelpers.fetch import (
    apt_cache
)
from charmhelpers.contrib.openstack import templating
from charmhelpers.core.host import set_nic_mtu
from collections import OrderedDict
from charmhelpers.contrib.storage.linux.ceph import modprobe
from charmhelpers.contrib.openstack.utils import (
    os_release,
)
from charmhelpers.core.host import (
    service_start,
    service_stop,
    service_available,
)
from socket import gethostname as get_unit_hostname
import pg_dir_context
import subprocess
import time
import os
import json

LXC_CONF = '/etc/libvirt/lxc.conf'
TEMPLATES = 'templates/'
PG_LXC_DATA_PATH = '/var/lib/libvirt/filesystems/plumgrid-data'
PG_LXC_PATH = '/var/lib/libvirt/filesystems/plumgrid'

PG_CONF = '%s/conf/pg/plumgrid.conf' % PG_LXC_DATA_PATH
PG_KA_CONF = '%s/conf/etc/keepalived.conf' % PG_LXC_DATA_PATH
PG_DEF_CONF = '%s/conf/pg/nginx.conf' % PG_LXC_DATA_PATH
PG_HN_CONF = '%s/conf/etc/hostname' % PG_LXC_DATA_PATH
PG_HS_CONF = '%s/conf/etc/hosts' % PG_LXC_DATA_PATH
PG_IFCS_CONF = '%s/conf/pg/ifcs.conf' % PG_LXC_DATA_PATH
AUTH_KEY_PATH = '%s/root/.ssh/authorized_keys' % PG_LXC_DATA_PATH
TEMP_LICENSE_FILE = '/tmp/license'


BASE_RESOURCE_MAP = OrderedDict([
    (PG_KA_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_DEF_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_HN_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_HS_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_IFCS_CONF, {
        'services': [],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
])


def determine_packages():
    '''
    Returns list of packages required by PLUMgrid director as specified
    in the neutron_plugins dictionary in charmhelpers.
    '''
    pkgs = []
    tag = 'latest'
    for pkg in neutron_plugin_attribute('plumgrid', 'packages', 'neutron'):
        if 'plumgrid' in pkg:
            tag = config('plumgrid-build')
        elif pkg == 'iovisor-dkms':
            tag = config('iovisor-build')

        if tag == 'latest':
            pkgs.append(pkg)
        else:
            if tag in [i.ver_str for i in apt_cache()[pkg].version_list]:
                pkgs.append('%s=%s' % (pkg, tag))
            else:
                error_msg = \
                    "Build version '%s' for package '%s' not available" \
                    % (tag, pkg)
                raise ValueError(error_msg)
    return pkgs


def register_configs(release=None):
    '''
    Returns an object of the Openstack Tempating Class which contains the
    the context required for all templates of this charm.
    '''
    release = release or os_release('neutron-common', base='kilo')
    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def resource_map():
    '''
    Dynamically generate a map of resources that will be managed for a single
    hook execution.
    '''
    resource_map = deepcopy(BASE_RESOURCE_MAP)
    return resource_map


def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return {cfg: rscs['services'] for cfg, rscs in resource_map().iteritems()}


def restart_pg():
    '''
    Stops and Starts PLUMgrid service after flushing iptables.
    '''
    if not service_available('plumgrid'):
        if service_available('libvirt-bin'):
            if not service_start('libvirt-bin'):
                raise ValueError("libvirt-bin service couldn't be started")
            else:
                time.sleep(5)
        else:
            log("libvirt-bin not installed")
            return 0
    service_stop('plumgrid')
    time.sleep(2)
    _exec_cmd(cmd=['iptables', '-F'])
    service_start('plumgrid')
    time.sleep(5)


def stop_pg():
    '''
    Stops PLUMgrid service.
    '''
    service_stop('plumgrid')
    time.sleep(2)


def load_iovisor():
    '''
    Loads iovisor kernel module.
    '''
    modprobe('iovisor')


def remove_iovisor():
    '''
    Removes iovisor kernel module.
    '''
    _exec_cmd(cmd=['rmmod', 'iovisor'],
              error_msg='Error Loading IOVisor Kernel Module')
    time.sleep(1)


def interface_exists(interface):
    '''
    Checks if interface exists on node.
    '''
    try:
        subprocess.check_call(['ip', 'link', 'show', interface],
                              stdout=open(os.devnull, 'w'),
                              stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return False
    return True


def get_mgmt_interface():
    '''
    Returns the managment interface.
    '''
    mgmt_interface = config('mgmt-interface')
    if interface_exists(mgmt_interface):
        return mgmt_interface
    else:
        log('Provided managment interface %s does not exist'
            % mgmt_interface)
        return get_iface_from_addr(unit_get('private-address'))


def fabric_interface_changed():
    '''
    Returns true if interface for node changed.
    '''
    fabric_interface = get_fabric_interface()
    try:
        with open(PG_IFCS_CONF, 'r') as ifcs:
            for line in ifcs:
                if 'fabric_core' in line:
                    if line.split()[0] == fabric_interface:
                        return False
    except IOError:
        return True
    return True


def get_fabric_interface():
    '''
    Returns the fabric interface.
    '''
    fabric_interfaces = config('fabric-interfaces')
    if fabric_interfaces == 'MANAGEMENT':
        return get_mgmt_interface()
    else:
        try:
            all_fabric_interfaces = json.loads(fabric_interfaces)
        except ValueError:
            raise ValueError('Invalid json provided for fabric interfaces')
        hostname = get_unit_hostname()
        if hostname in all_fabric_interfaces:
            node_fabric_interface = all_fabric_interfaces[hostname]
        elif 'DEFAULT' in all_fabric_interfaces:
            node_fabric_interface = all_fabric_interfaces['DEFAULT']
        else:
            raise ValueError('No fabric interface provided for node')
        if interface_exists(node_fabric_interface):
            if is_address_in_network(config('os-data-network'),
                                     get_iface_addr(node_fabric_interface)[0]):
                return node_fabric_interface
            else:
                raise ValueError('Fabric interface not in fabric network')
        else:
            log('Provided fabric interface %s does not exist'
                % node_fabric_interface)
            raise ValueError('Provided fabric interface does not exist')
        return node_fabric_interface


def ensure_mtu():
    '''
    Ensures required MTU of the underlying networking of the node.
    '''
    interface_mtu = config('network-device-mtu')
    fabric_interface = get_fabric_interface()
    if fabric_interface in get_bridges():
        attached_interfaces = get_bridge_nics(fabric_interface)
        for interface in attached_interfaces:
            set_nic_mtu(interface, interface_mtu)
    set_nic_mtu(fabric_interface, interface_mtu)


def _exec_cmd(cmd=None, error_msg='Command exited with ERRORs', fatal=False):
    '''
    Function to execute any bash command on the node.
    '''
    if cmd is None:
        log("No command specified")
    else:
        if fatal:
            subprocess.check_call(cmd)
        else:
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError:
                log(error_msg)


def add_lcm_key():
    '''
    Adds public key of PLUMgrid-lcm to authorized keys of PLUMgrid Director.
    '''
    key = config('lcm-ssh-key')
    if key == 'null':
        log('lcm key not specified')
        return 0
    file_write_type = 'w+'
    if os.path.isfile(AUTH_KEY_PATH):
        file_write_type = 'a'
        try:
            fr = open(AUTH_KEY_PATH, 'r')
        except IOError:
            log('plumgrid-lxc not installed yet')
            return 0
        for line in fr:
            if key in line:
                log('key already added')
                return 0
    try:
        fa = open(AUTH_KEY_PATH, file_write_type)
    except IOError:
        log('Error opening file to append')
        return 0
    fa.write(key)
    fa.write('\n')
    fa.close()
    return 1


def post_pg_license():
    '''
    Posts PLUMgrid License if it hasnt been posted already.
    '''
    key = config('plumgrid-license-key')
    if key is None:
        log('PLUMgrid License Key not specified')
        return 0
    PG_VIP = config('plumgrid-virtual-ip')
    if not is_ip(PG_VIP):
        raise ValueError('Invalid IP Provided')
    LICENSE_POST_PATH = 'https://%s/0/tenant_manager/license_key' % PG_VIP
    LICENSE_GET_PATH = 'https://%s/0/tenant_manager/licenses' % PG_VIP
    PG_CURL = '%s/opt/pg/scripts/pg_curl.sh' % PG_LXC_PATH
    license = {"key1": {"license": key}}
    licence_post_cmd = [
        PG_CURL,
        '-u',
        'plumgrid:plumgrid',
        LICENSE_POST_PATH,
        '-d',
        json.dumps(license)
        ]
    licence_get_cmd = [PG_CURL, '-u', 'plumgrid:plumgrid', LICENSE_GET_PATH]
    try:
        old_license = subprocess.check_output(licence_get_cmd)
    except subprocess.CalledProcessError:
        log('No response from specified virtual IP')
        return 0
    _exec_cmd(cmd=licence_post_cmd,
              error_msg='Unable to post License', fatal=False)
    new_license = subprocess.check_output(licence_get_cmd)
    if old_license == new_license:
        log('No change in PLUMgrid License')
        return 0
    return 1

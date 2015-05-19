from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from copy import deepcopy
from charmhelpers.core.hookenv import log
from charmhelpers.contrib.openstack import templating
from collections import OrderedDict
from charmhelpers.contrib.openstack.utils import (
    os_release,
)
import pg_dir_context
import subprocess
import time

#Dont need these right now
NOVA_CONF_DIR = "/etc/nova"
NEUTRON_CONF_DIR = "/etc/neutron"
NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR
NEUTRON_DEFAULT = '/etc/default/neutron-server'

#Puppet Files
P_PGKA_CONF = '/opt/pg/etc/puppet/modules/sal/templates/keepalived.conf.erb'
P_PG_CONF = '/opt/pg/etc/puppet/modules/plumgrid/templates/plumgrid.conf.erb'
P_PGDEF_CONF = '/opt/pg/etc/puppet/modules/sal/templates/default.conf.erb'

#Plumgrid Files
PGKA_CONF = '/var/lib/libvirt/filesystems/plumgrid/etc/keepalived/keepalived.conf'
PG_CONF = '/var/lib/libvirt/filesystems/plumgrid/opt/pg/etc/plumgrid.conf'
PGDEF_CONF = '/var/lib/libvirt/filesystems/plumgrid/opt/pg/sal/nginx/conf.d/default.conf'
PGHN_CONF = '/var/lib/libvirt/filesystems/plumgrid-data/conf/etc/hostname'
PGHS_CONF = '/var/lib/libvirt/filesystems/plumgrid-data/conf/etc/hosts'
PGIFCS_CONF = '/var/lib/libvirt/filesystems/plumgrid-data/conf/pg/ifcs.conf'
IFCTL_CONF = '/var/run/plumgrid/lxc/ifc_list_gateway'
IFCTL_P_CONF = '/var/lib/libvirt/filesystems/plumgrid/var/run/plumgrid/lxc/ifc_list_gateway'

BASE_RESOURCE_MAP = OrderedDict([
    (PGKA_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PG_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PGDEF_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PGHN_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PGHS_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
    (PGIFCS_CONF, {
        'services': [],
        'contexts': [pg_dir_context.PGDirContext()],
    }),
])
TEMPLATES = 'templates/'


def determine_packages():
    return neutron_plugin_attribute('plumgrid', 'packages', 'neutron')


def register_configs(release=None):
    release = release or os_release('neutron-common', base='icehouse')
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
    return {k: v['services'] for k, v in resource_map().iteritems()}


def ensure_files():
    _exec_cmd(cmd=['cp', '--remove-destination', '-f', P_PGKA_CONF, PGKA_CONF])
    _exec_cmd(cmd=['cp', '--remove-destination', '-f', P_PG_CONF, PG_CONF])
    _exec_cmd(cmd=['cp', '--remove-destination', '-f', P_PGDEF_CONF, PGDEF_CONF])
    _exec_cmd(cmd=['touch', PGIFCS_CONF])
    _exec_cmd(cmd=['mkdir', '/etc/nova'])
    _exec_cmd(cmd=['touch', 'neutron_plugin.conf'])


def restart_pg():
    _exec_cmd(cmd=['virsh', '-c', 'lxc:', 'destroy', 'plumgrid'], error_msg='ERROR Destroying PLUMgrid')
    _exec_cmd(cmd=['rm', IFCTL_CONF, IFCTL_P_CONF], error_msg='ERROR Removing ifc_ctl_gateway file')
    _exec_cmd(cmd=['iptables', '-F'])
    _exec_cmd(cmd=['virsh', '-c', 'lxc:', 'start', 'plumgrid'], error_msg='ERROR Starting PLUMgrid')
    time.sleep(5)
    _exec_cmd(cmd=['service', 'plumgrid', 'start'], error_msg='ERROR starting PLUMgrid service')
    time.sleep(5)


def stop_pg():
    _exec_cmd(cmd=['virsh', '-c', 'lxc:', 'destroy', 'plumgrid'], error_msg='ERROR Destroying PLUMgrid')
    time.sleep(2)
    _exec_cmd(cmd=['rm', IFCTL_CONF, IFCTL_P_CONF], error_msg='ERROR Removing ifc_ctl_gateway file')


def _exec_cmd(cmd=None, error_msg='Command exited with ERRORs'):
    if cmd is None:
        log("NO command")
    else:
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError, e:
            log(error_msg)

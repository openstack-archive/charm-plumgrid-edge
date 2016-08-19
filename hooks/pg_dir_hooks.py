#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

import sys
import time
from charmhelpers.core.host import service_running
from charmhelpers.contrib.network.ip import is_ip
from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    config,
    relation_set,
    relation_ids,
    status_set,
    is_leader
)

from charmhelpers.fetch import (
    apt_install,
    configure_sources,
)

from pg_dir_utils import (
    register_configs,
    restart_pg,
    restart_map,
    stop_pg,
    determine_packages,
    load_iovisor,
    remove_iovisor,
    ensure_mtu,
    add_lcm_key,
    post_pg_license,
    fabric_interface_changed,
    load_iptables,
    restart_on_change,
    director_cluster_ready,
    configure_pg_sources,
    configure_analyst_opsvm,
    sapi_post_ips,
    sapi_post_license,
    sapi_post_zone_info
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    status_set('maintenance', 'Executing pre-install')
    load_iptables()
    configure_sources(update=True)
    status_set('maintenance', 'Installing apt packages')
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    load_iovisor()
    ensure_mtu()
    CONFIGS.write_all()


@hooks.hook('director-relation-joined')
@hooks.hook('director-relation-changed')
@restart_on_change(restart_map())
def dir_joined():
    '''
    This hook is run when a unit of director is added.
    '''
    if director_cluster_ready():
        ensure_mtu()
        CONFIGS.write_all()


@hooks.hook('plumgrid-relation-joined',
            'plumgrid-relation-changed',
            'plumgrid-relation-departed')
def plumgrid_joined(relation_id=None):
    '''
    This hook is run when relation with edge or gateway is created.
    '''
    opsvm_ip = config('opsvm-ip')
    if not is_ip(opsvm_ip):
        raise ValueError('Invalid OPSVM IP specified!')
    else:
        relation_set(relation_id=relation_id, opsvm_ip=opsvm_ip)
    if is_leader():
        sapi_post_ips()


@hooks.hook('plumgrid-configs-relation-joined')
def plumgrid_configs_joined(relation_id=None):
    '''
    This hook is run when relation with neutron-api-plumgrid is created.
    '''
    relation_settings = {
        'plumgrid_virtual_ip': config('plumgrid-virtual-ip'),
        'plumgrid_username': config('plumgrid-username'),
        'plumgrid_password': config('plumgrid-password'),
    }
    if is_leader():
        relation_set(relation_id=relation_id,
                     relation_settings=relation_settings)


@hooks.hook('config-changed')
def config_changed():
    '''
    This hook is run when a config parameter is changed.
    It also runs on node reboot.
    '''
    charm_config = config()
    if charm_config.changed('lcm-ssh-key'):
        if add_lcm_key():
            log("PLUMgrid LCM Key added")
    if charm_config.changed('plumgrid-license-key'):
        if is_leader() and post_pg_license():
            log("PLUMgrid License Posted")
        # Post PG license to Sol-API
        sapi_post_license()
    if charm_config.changed('fabric-interfaces'):
        if not fabric_interface_changed():
            log("Fabric interface already set")
        else:
            stop_pg()
    if charm_config.changed('plumgrid-virtual-ip'):
        CONFIGS.write_all()
        for rid in relation_ids('plumgrid'):
            plumgrid_joined(rid)
        stop_pg()
        for rid in relation_ids('plumgrid-configs'):
            plumgrid_configs_joined(rid)
    if (charm_config.changed('plumgrid-username') or
            charm_config.changed('plumgrid-password')):
        for rid in relation_ids('plumgrid-configs'):
            plumgrid_configs_joined(rid)
    if (charm_config.changed('install_sources') or
        charm_config.changed('plumgrid-build') or
        charm_config.changed('install_keys') or
            charm_config.changed('iovisor-build')):
        status_set('maintenance', 'Upgrading apt packages')
        stop_pg()
        if charm_config.changed('install_sources'):
            configure_pg_sources()
        configure_sources(update=True)
        pkgs = determine_packages()
        for pkg in pkgs:
            apt_install(pkg, options=['--force-yes'], fatal=True)
            remove_iovisor()
            load_iovisor()
    if charm_config.changed('opsvm-ip'):
        for rid in relation_ids('plumgrid'):
            plumgrid_joined(rid)
        stop_pg()
    if (charm_config.changed('sapi-port') or
        charm_config.changed('lcm-ip') or
            charm_config.changed('sapi-zone')):
        if is_leader():
            if is_ip(config('lcm-ip')):
                sapi_post_zone_info()
            else:
                raise ValueError('Invalid LCM IP specified!')
        for rid in relation_ids('plumgrid'):
            plumgrid_joined(rid)
    ensure_mtu()
    CONFIGS.write_all()
    if not service_running('plumgrid'):
        restart_pg()


@hooks.hook('start')
def start():
    '''
    This hook is run when the charm is started.
    '''
    configure_analyst_opsvm()
    if config('plumgrid-license-key') is not None:
        count = 0
        while (count < 10):
            if post_pg_license():
                break
            count += 1
            time.sleep(15)
        if count == 10:
            raise ValueError("Error occurred while posting plumgrid license"
                             "key. Please check plumgrid services.")


@hooks.hook('upgrade-charm')
@restart_on_change(restart_map())
def upgrade_charm():
    '''
    This hook is run when the charm is upgraded
    '''
    ensure_mtu()
    CONFIGS.write_all()


@hooks.hook('stop')
def stop():
    '''
    This hook is run when the charm is destroyed.
    '''
    stop_pg()


@hooks.hook('update-status')
def update_status():
    if service_running('plumgrid'):
        status_set('active', 'Unit is ready')
    else:
        status_set('blocked', 'plumgrid service not running')


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()

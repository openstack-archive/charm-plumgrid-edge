#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

import sys
import time
from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    config,
)

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
    configure_sources,
)

from charmhelpers.contrib.network.ip import is_ip
from charmhelpers.core.host import service_running

from pg_dir_utils import (
    register_configs,
    restart_pg,
    stop_pg,
    determine_packages,
    load_iovisor,
    remove_iovisor,
    ensure_mtu,
    add_lcm_key,
    post_pg_license,
    fabric_interface_changed
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    configure_sources(update=True)
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    load_iovisor()
    ensure_mtu()
    CONFIGS.write_all()


@hooks.hook('director-relation-joined')
def dir_joined():
    '''
    This hook is run when a unit of director is added.
    '''
    CONFIGS.write_all()
    restart_pg()


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
        if post_pg_license():
            log("PLUMgrid License Posted")
    if charm_config.changed('network-device-mtu'):
        ensure_mtu()
    if charm_config.changed('fabric-interfaces'):
        if not fabric_interface_changed():
            log("Fabric interface already set")
        else:
            stop_pg()
    if charm_config.changed('os-data-network'):
        if charm_config['fabric-interfaces'] == 'MANAGEMENT':
            log('Fabric running on managment network')
    if charm_config.changed('plumgrid-virtual-ip'):
        plumgrid_vip = config('plumgrid-virtual-ip')
        if is_ip(plumgrid_vip):
            stop_pg()
        else:
            raise ValueError('Invalid IP Provided')
    if (charm_config.changed('install_sources') or
        charm_config.changed('plumgrid-build') or
        charm_config.changed('install_keys') or
            charm_config.changed('iovisor-build')):
        stop_pg()
        configure_sources(update=True)
        pkgs = determine_packages()
        for pkg in pkgs:
            apt_install(pkg, options=['--force-yes'], fatal=True)
            remove_iovisor()
            load_iovisor()
    CONFIGS.write_all()
    # Starting the plumgrid service if it is stopped by
    # any of the config-parameters or node reboot
    if not service_running('plumgrid'):
        restart_pg()


@hooks.hook('start')
def start():
    '''
    This hook is run when the charm is started.
    '''
    if config('plumgrid-license-key') is not None:
        count = 0
        while (count < 10):
            if post_pg_license():
                break
            count = count + 1
            time.sleep(15)


@hooks.hook('stop')
def stop():
    '''
    This hook is run when the charm is destroyed.
    '''
    stop_pg()
    remove_iovisor()
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_purge(pkg, fatal=False)


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()

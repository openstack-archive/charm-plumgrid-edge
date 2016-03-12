#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

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
    fabric_interface_changed,
    load_iptables
)

import sys
import time

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    load_iptables()
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
    if add_lcm_key():
        log("PLUMgrid LCM Key added")
        return 1
    charm_config = config()
    if charm_config.changed('plumgrid-license-key'):
        if post_pg_license():
            log("PLUMgrid License Posted")
        return 1
    if charm_config.changed('fabric-interfaces'):
        if not fabric_interface_changed():
            log("Fabric interface already set")
            return 1
    if charm_config.changed('os-data-network'):
        if charm_config['fabric-interfaces'] == 'MANAGEMENT':
            log('Fabric running on managment network')
            return 1
    stop_pg()
    configure_sources(update=True)
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    remove_iovisor()
    load_iovisor()
    ensure_mtu()
    add_lcm_key()
    CONFIGS.write_all()
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


@hooks.hook('upgrade-charm')
def upgrade_charm():
    '''
    This hook is run when the charm is upgraded
    '''
    load_iptables()


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

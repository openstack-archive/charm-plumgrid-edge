# Overview

Once deployed this charm performs the configurations required for a PLUMgrid Director and starts the essential services on the node.

# Usage

Step by step instructions on using the charm:

    juju deploy neutron-api
    juju deploy neutron-plumgrid-plugin neutron-api
    juju deploy neutron-iovisor
    juju deploy plumgrid-director --to <Machince No of neutron-iovisor>

    juju add-relation neutron-api neutron-plumgrid-plugin
    juju add-relation neutron-plumgrid-plugin neutron-iovisor
    juju add-relation neutron-iovisor plumgrid-director

For plumgrid-director to work make the configuration in the neutron-api, neutron-plumgrid-plugin and neutron-iovisor charms as specified in the configuration section below.

# Known Limitations and Issues

This is an early access version of the PLUMgrid Director charm and it is not meant for production deployments. The charm only works with JUNO for now. This charm needs to be deployed on a node where a unit of neutron-iovisor charm exists. Also plumgrid-edge and plumgrid-gateway charms should not be deployed on the same node.

# Configuration

Example Config

    plumgrid-director:
        plumgrid-virtual-ip: "192.168.100.250"
    neutron-iovisor:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
    neutron-plumgrid-plugin:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
        enable-metadata: False
    neutron-api:
        neutron-plugin: "plumgrid"
        plumgrid-virtual-ip: "192.168.100.250"

The plumgrid-virtual-ip is the IP address of the PLUMgrid Director's Management interface and that the same IP is used to access PLUMgrid Console.
Ensure that the same ip is specified in the neutron-api charm configuration.
Using the example config provided above PLUMgrid Console can be accessed at https://192.168.100.250

# Contact Information

Bilal Baqar <bbaqar@plumgrid.com>
Bilal Ahmad <bilal@plumgrid.com>

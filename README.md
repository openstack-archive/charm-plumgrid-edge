# Overview

Once deployed this charm performs the configurations required for a PLUMgrid Director and starts the essential services on the node.

# Usage

Instructions on using the charm:

    juju deploy neutron-api
    juju deploy neutron-api-plumgrid
    juju deploy plumgrid-director

    juju add-relation neutron-api neutron-api-plumgrid

For plumgrid-director to work make the configuration in the neutron-api and neutron-api-plumgrid charms as specified in the configuration section below.

# Known Limitations and Issues

This is an early access version of the PLUMgrid Director charm and it is not meant for production deployments. The charm only supports Kilo Openstack Release.

# Configuration

Example Config

    plumgrid-director:
        plumgrid-virtual-ip: "192.168.100.250"
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
    neutron-api-plumgrid:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
        enable-metadata: True
    neutron-api:
        neutron-plugin: "plumgrid"
        plumgrid-virtual-ip: "192.168.100.250"

Provide the virtual IP you want PLUMgrid GUI to be accessible.
Make sure that it is the same IP specified in the neutron-api charm configuration for PLUMgrid.
The virtual IP passed on in the neutron-api charm has to be same as the one passed in the plumgrid-director charm.
Provide the source repo path for PLUMgrid Debs in 'install_sources' and the corresponding keys in 'install_keys'.

You can access the PG Console at https://192.168.100.250

In order to configure networking, PLUMgrid License needs to be posted.

    juju set plumgrid-director plumgrid-license-key="$LICENSE_KEY"

# Contact Information

Bilal Baqar <bbaqar@plumgrid.com>
Bilal Ahmad <bilal@plumgrid.com>

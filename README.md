# Overview

This charm provides the PLUMgrid Director configuration for a node.


# Usage

To deploy (partial deployment of linked charms only):

    juju deploy neutron-api
    juju deploy neutron-iovisor
    juju deploy plumgrid-director
    juju add-relation plumgrid-director neutron-iovisor


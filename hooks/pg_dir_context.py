# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# This file contains the class that generates context
# for PLUMgrid template files.

import re
from charmhelpers.contrib.openstack import context
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.core.hookenv import (
    config,
    unit_get,
)
from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
)
from charmhelpers.contrib.network.ip import (
    is_ip,
    get_address_in_network,
)

from socket import (
    gethostname,
    getfqdn
)


def _pg_dir_ips():
    '''
    Inspects plumgrid-director peer relation and returns the
    ips of the peer directors
    '''
    return [get_host_ip(rdata['private-address'])
            for rid in relation_ids("director")
            for rdata in
            (relation_get(rid=rid, unit=unit) for unit in related_units(rid))
            if rdata]


class PGDirContext(context.NeutronContext):

    @property
    def plugin(self):
        '''
        Over-riding function in NeutronContext Class to return 'plumgrid'
        as the neutron plugin.
        '''
        return 'plumgrid'

    @property
    def network_manager(self):
        '''
        Over-riding function in NeutronContext Class to return 'neutron'
        as the network manager.
        '''
        return 'neutron'

    def _save_flag_file(self):
        '''
        Over-riding function in NeutronContext Class.
        Function only needed for OVS.
        '''
        pass

    def pg_ctxt(self):
        '''
        Generated Config for all PLUMgrid templates inside the templates
        folder.
        '''
        pg_ctxt = super(PGDirContext, self).pg_ctxt()
        if not pg_ctxt:
            return {}

        conf = config()
        pg_dir_ips = _pg_dir_ips()
        pg_dir_ips.append(str(get_address_in_network(network=None,
                          fallback=get_host_ip(unit_get('private-address')))))
        pg_dir_ips = sorted(pg_dir_ips)
        pg_ctxt['director_ips'] = pg_dir_ips
        dir_count = len(pg_dir_ips)
        pg_ctxt['director_ips_string'] = (str(pg_dir_ips[0]) + ',' +
                                          str(pg_dir_ips[1]) + ',' +
                                          str(pg_dir_ips[2])
                                          if dir_count == 3 else
                                          str(pg_dir_ips[0]))
        PG_VIP = conf['plumgrid-virtual-ip']
        if is_ip(PG_VIP):
            pg_ctxt['virtual_ip'] = PG_VIP
        else:
            raise ValueError('Invalid PLUMgrid Virtual IP Provided')
        unit_hostname = gethostname()
        pg_ctxt['pg_hostname'] = unit_hostname
        pg_ctxt['pg_fqdn'] = getfqdn()
        from pg_dir_utils import get_mgmt_interface, get_fabric_interface
        pg_ctxt['interface'] = get_mgmt_interface()
        pg_ctxt['fabric_interface'] = get_fabric_interface()
        pg_ctxt['label'] = unit_hostname
        pg_ctxt['fabric_mode'] = 'host'
        virtual_ip_array = re.split('\.', conf['plumgrid-virtual-ip'])
        pg_ctxt['virtual_router_id'] = virtual_ip_array[3]
        pg_ctxt['opsvm_ip'] = conf['opsvm-ip']

        return pg_ctxt

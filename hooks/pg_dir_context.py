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
    pg_dir_ips = []
    for rid in relation_ids('director'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            pg_dir_ips.append(get_host_ip(rdata['private-address']))
    return pg_dir_ips


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
        pg_dir_ips_string = ''
        single_ip = True
        for ip in pg_dir_ips:
            if single_ip:
                pg_dir_ips_string = str(ip)
                single_ip = False
            else:
                pg_dir_ips_string = pg_dir_ips_string + ',' + str(ip)
        pg_ctxt['director_ips_string'] = pg_dir_ips_string
        PG_VIP = config('plumgrid-virtual-ip')
        if is_ip(PG_VIP):
            pg_ctxt['virtual_ip'] = conf['plumgrid-virtual-ip']
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

        return pg_ctxt

from charmhelpers.core.hookenv import (
    config,
    unit_get,
)
from charmhelpers.contrib.openstack import context
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.contrib.network.ip import get_address_in_network

import re
from socket import gethostname as get_unit_hostname

'''
def _neutron_api_settings():
    neutron_settings = {
        'neutron_security_groups': False,
        'l2_population': True,
        'overlay_network_type': 'gre',
    }
    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            if 'l2-population' not in rdata:
                continue
            neutron_settings = {
                'l2_population': rdata['l2-population'],
                'neutron_security_groups': rdata['neutron-security-groups'],
                'overlay_network_type': rdata['overlay-network-type'],
            }
            # Override with configuration if set to true
            if config('disable-security-groups'):
                neutron_settings['neutron_security_groups'] = False
            return neutron_settings
    return neutron_settings
'''


class PGDirContext(context.NeutronContext):
    interfaces = []

    @property
    def plugin(self):
        return 'plumgrid'

    @property
    def network_manager(self):
        return 'neutron'

    def _save_flag_file(self):
        pass

    #@property
    #def neutron_security_groups(self):
    #    neutron_api_settings = _neutron_api_settings()
    #    return neutron_api_settings['neutron_security_groups']

    def pg_ctxt(self):
        #Generated Config for all Plumgrid templates inside
        #the templates folder
        pg_ctxt = super(PGDirContext, self).pg_ctxt()
        if not pg_ctxt:
            return {}

        conf = config()
        pg_ctxt['local_ip'] = \
            get_address_in_network(network=None,
                                   fallback=get_host_ip(unit_get('private-address')))
        #neutron_api_settings = _neutron_api_settings()

        #TODO: Get this value from the neutron-api charm
        pg_ctxt['virtual_ip'] = conf['plumgrid-virtual-ip']
        pg_ctxt['pg_hostname'] = "pg-director"
        pg_ctxt['interface'] = "juju-br0"
        pg_ctxt['label'] = get_unit_hostname()
        pg_ctxt['fabric_mode'] = 'host'
        virtual_ip_array = re.split('\.', conf['plumgrid-virtual-ip'])
        pg_ctxt['virtual_router_id'] = virtual_ip_array[3]

        return pg_ctxt

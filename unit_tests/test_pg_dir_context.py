from test_utils import CharmTestCase
from mock import patch
import pg_dir_context as context
import pg_dir_utils as utils
import charmhelpers

TO_PATCH = [
    'config',
    'unit_get',
    'get_host_ip',
    'get_unit_hostname',
]


def fake_context(settings):
    def outer():
        def inner():
            return settings
        return inner
    return outer


class PGDirContextTest(CharmTestCase):

    def setUp(self):
        super(PGDirContextTest, self).setUp(context, TO_PATCH)
        self.config.side_effect = self.test_config.get
        self.test_config.set('plumgrid-virtual-ip', '192.168.100.250')

    def tearDown(self):
        super(PGDirContextTest, self).tearDown()

    @patch.object(charmhelpers.contrib.openstack.context, 'config',
                  lambda *args: None)
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_ids')
    @patch.object(charmhelpers.contrib.openstack.context, 'related_units')
    @patch.object(charmhelpers.contrib.openstack.context, 'config')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'is_clustered')
    @patch.object(charmhelpers.contrib.openstack.context, 'https')
    @patch.object(context.PGDirContext, '_save_flag_file')
    @patch.object(context.PGDirContext, '_ensure_packages')
    @patch.object(charmhelpers.contrib.openstack.context,
                  'neutron_plugin_attribute')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_private_ip')
    @patch.object(context, '_pg_dir_ips')
    @patch.object(utils, 'check_interface_type')
    def test_neutroncc_context_api_rel(self, _int_type, _pg_dir_ips,
                                       _unit_priv_ip, _npa, _ens_pkgs,
                                       _save_ff, _https, _is_clus,
                                       _unit_get, _config, _runits, _rids,
                                       _rget):
        def mock_npa(plugin, section, manager):
            if section == "driver":
                return "neutron.randomdriver"
            if section == "config":
                return "neutron.randomconfig"

        config = {'plumgrid-virtual-ip': "192.168.100.250"}

        def mock_config(key=None):
            if key:
                return config.get(key)

            return config

        self.maxDiff = None
        self.config.side_effect = mock_config
        _npa.side_effect = mock_npa
        _unit_get.return_value = '192.168.100.201'
        _unit_priv_ip.return_value = '192.168.100.201'
        self.get_unit_hostname.return_value = 'node0'
        self.get_host_ip.return_value = '192.168.100.201'
        _pg_dir_ips.return_value = ['192.168.100.202', '192.168.100.203']
        _int_type.return_value = 'juju-br0'
        napi_ctxt = context.PGDirContext()
        expect = {
            'config': 'neutron.randomconfig',
            'core_plugin': 'neutron.randomdriver',
            'local_ip': '192.168.100.201',
            'network_manager': 'neutron',
            'neutron_plugin': 'plumgrid',
            'neutron_security_groups': None,
            'neutron_url': 'https://None:9696',
            'virtual_ip': '192.168.100.250',
            'pg_hostname': 'pg-director',
            'interface': 'juju-br0',
            'label': 'node0',
            'fabric_mode': 'host',
            'virtual_router_id': '250',
            'director_ips': ['192.168.100.202', '192.168.100.203',
                             '192.168.100.201'],
            'director_ips_string':
            '192.168.100.202,192.168.100.203,192.168.100.201',
        }
        self.assertEquals(expect, napi_ctxt())

from mock import MagicMock, patch, call

from test_utils import CharmTestCase

with patch('charmhelpers.core.hookenv.config') as config:
    config.return_value = 'neutron'
    import pg_dir_utils as utils

_reg = utils.register_configs
_map = utils.restart_map

utils.register_configs = MagicMock()
utils.restart_map = MagicMock()

import pg_dir_hooks as hooks

utils.register_configs = _reg
utils.restart_map = _map

TO_PATCH = [
    'remove_iovisor',
    'apt_install',
    'CONFIGS',
    'log',
    'configure_sources',
    'stop_pg',
    'restart_pg',
    'load_iovisor',
    'ensure_mtu',
    'add_lcm_key',
    'determine_packages',
    'post_pg_license',
    'config',
    'load_iptables',
    'status_set',
    'configure_analyst_opsvm'
]
NEUTRON_CONF_DIR = "/etc/neutron"

NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR


class PGDirHooksTests(CharmTestCase):

    def setUp(self):
        super(PGDirHooksTests, self).setUp(hooks, TO_PATCH)
        self.config.side_effect = self.test_config.get
        hooks.hooks._config_save = False

    def _call_hook(self, hookname):
        hooks.hooks.execute([
            'hooks/{}'.format(hookname)])

    def test_install_hook(self):
        _pkgs = ['plumgrid-lxc', 'iovisor-dkms']
        self.determine_packages.return_value = [_pkgs]
        self._call_hook('install')
        self.configure_sources.assert_called_with(update=True)
        self.apt_install.assert_has_calls([
            call(_pkgs, fatal=True,
                 options=['--force-yes']),
        ])
        self.load_iovisor.assert_called_with()
        self.ensure_mtu.assert_called_with()

    def test_start(self):
        self._call_hook('start')
        self.test_config.set('plumgrid-license-key', None)

    def test_stop(self):
        self._call_hook('stop')
        self.stop_pg.assert_called_with()

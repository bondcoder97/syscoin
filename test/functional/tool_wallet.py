#!/usr/bin/env python3
# Copyright (c) 2018 The Syscoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test syscoin-wallet."""
import subprocess
import textwrap

from test_framework.test_framework import SyscoinTestFramework
from test_framework.util import assert_equal

class ToolWalletTest(SyscoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def syscoin_wallet_process(self, *args):
        binary = self.config["environment"]["BUILDDIR"] + '/src/syscoin-wallet' + self.config["environment"]["EXEEXT"]
        args = ['-datadir={}'.format(self.nodes[0].datadir), '-regtest'] + list(args)
        return subprocess.Popen([binary] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def assert_raises_tool_error(self, error, *args):
        p = self.syscoin_wallet_process(*args)
        stdout, stderr = p.communicate()
        assert_equal(p.poll(), 1)
        assert_equal(stdout, '')
        assert_equal(stderr.strip(), error)

    def assert_tool_output(self, output, *args):
        p = self.syscoin_wallet_process(*args)
        stdout, stderr = p.communicate()
        assert_equal(p.poll(), 0)
        assert_equal(stderr, '')
        assert_equal(stdout, output)

    def run_test(self):
        self.log.info('Testing that various invalid commands raise with specific error messages')
        self.assert_raises_tool_error('Invalid command: foo', 'foo')
        # `syscoin-wallet help` raises an error. Use `syscoin-wallet -help`.
        self.assert_raises_tool_error('Invalid command: help', 'help')
        self.assert_raises_tool_error('Error: two methods provided (info and create). Only one method should be provided.', 'info', 'create')
        self.assert_raises_tool_error('Error parsing command line arguments: Invalid parameter -foo', '-foo')
        self.assert_raises_tool_error('Error loading wallet.dat. Is wallet being used by other process?', '-wallet=wallet.dat', 'info')
        self.assert_raises_tool_error('Error: no wallet file at nonexistent.dat', '-wallet=nonexistent.dat', 'info')

        # Stop the node to close the wallet to call the info command.
        self.stop_node(0)
        self.log.info('Calling wallet tool info, testing output')
        out = textwrap.dedent('''\
            Wallet info
            ===========
            Encrypted: no
            HD (hd seed available): yes
            Keypool Size: 2
            Transactions: 0
            Address Book: 3
        ''')
        self.assert_tool_output(out, '-wallet=wallet.dat', 'info')

        # Mutate wallet to verify info command output changes accordingly.
        self.start_node(0)
        self.log.info('Generating transaction to mutate wallet')
        self.nodes[0].generate(1)
        self.stop_node(0)

        self.log.info('Calling wallet tool info after generating a transaction, testing output')
        out = textwrap.dedent('''\
            Wallet info
            ===========
            Encrypted: no
            HD (hd seed available): yes
            Keypool Size: 2
            Transactions: 1
            Address Book: 3
        ''')
        self.assert_tool_output(out, '-wallet=wallet.dat', 'info')

        self.log.info('Calling wallet tool create on an existing wallet, testing output')
        out = textwrap.dedent('''\
            Topping up keypool...
            Wallet info
            ===========
            Encrypted: no
            HD (hd seed available): yes
            Keypool Size: 2000
            Transactions: 0
            Address Book: 0
        ''')
        self.assert_tool_output(out, '-wallet=foo', 'create')

        self.log.info('Starting node with arg -wallet=foo')
        self.start_node(0, ['-wallet=foo'])

        self.log.info('Calling getwalletinfo on a different wallet ("foo"), testing output')
        out = self.nodes[0].getwalletinfo()
        self.stop_node(0)

        assert_equal(0, out['txcount'])
        assert_equal(1000, out['keypoolsize'])
        assert_equal(1000, out['keypoolsize_hd_internal'])
        assert_equal(True, 'hdseedid' in out)

if __name__ == '__main__':
    ToolWalletTest().main()

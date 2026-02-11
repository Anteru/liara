# SPDX-FileCopyrightText: 2024 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from liara import cmdline
import liara
from click.testing import CliRunner


def test_quickstart(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cmdline.cli, ['quickstart'])
        assert result.exit_code == 0

        result = runner.invoke(cmdline.cli, ['build'])
        assert result.exit_code == 0


def test_inspect_data(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cmdline.cli, ['quickstart'])
        assert result.exit_code == 0

        # Add a data file to content
        data = {
            'root': 'some data'
        }

        liara.yaml.dump_yaml(data, open('content/_data.yaml', 'w'))

        s = liara.Liara()
        s.discover_content()

        assert len(s.site.data) == 1
        assert 'root' in s.site.data[0].content

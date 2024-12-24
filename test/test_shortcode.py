from liara import cmdline
from liara.signals import register_markdown_shortcodes
import liara
from click.testing import CliRunner

_TEST_DATA = {}


def test_shortcode_with_data(tmp_path):
    global _TEST_DATA
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cmdline.cli, ['quickstart'])
        assert result.exit_code == 0

        # Add a data file to content
        data = {
            'root': 'some data'
        }

        open('content/_index.md', 'w').write("""
---
title: Hello world
---

Invoke a shortcode: <% test /%>""")

        liara.yaml.dump_yaml(data, open('content/_data.yaml', 'w'))

        register_markdown_shortcodes.connect(_register_test_shortcode)

        s = liara.Liara()
        s.build()

        assert _TEST_DATA['root'] == 'some data'


def _test_shortcode(**kwargs):
    global _TEST_DATA
    _TEST_DATA = kwargs['$data']


def _register_test_shortcode(sender, preprocessor):
    preprocessor.register('test', _test_shortcode)

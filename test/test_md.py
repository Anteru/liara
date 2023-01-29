from liara.md import ShortcodePreprocessor
import pytest


def test_shortcode_parse():
    document = r"""<% code arg1="23" arg2=52 /%>"""
    sp = ShortcodePreprocessor()

    def code(arg1, arg2, **kwargs):
        return f"*{arg1}*\n_{arg2}_"

    sp.register('code', code)

    output = list(sp.run(document.splitlines()))

    assert len(output) == 2
    assert output[0] == '*23*'
    assert output[1] == '_52_'


def test_shortcode_register_requires_kwargs():
    def h1(arg1):
        pass

    def h2(arg1, **a):
        pass

    sp = ShortcodePreprocessor()
    with pytest.raises(Exception):
        sp.register('h1', h1)

    sp.register('h2', h2)


def test_shortcode_error_handling():
    sp = ShortcodePreprocessor()

    with pytest.raises(Exception):
        _ = list(sp.run([r"""<% code foo /%>"""]))

    with pytest.raises(Exception):
        _ = list(sp.run([r"""<% /%>"""]))

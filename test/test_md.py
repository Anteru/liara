from liara.md import ShortcodePreprocessor


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

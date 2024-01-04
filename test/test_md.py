from liara.md import ShortcodePreprocessor, _ParseBuffer, _ShortcodeParser
import pytest

def _get_lines(document: str) -> list[str]:
    # document.splitlines() returns a list of string literals, so you shouldn't
    # modify it, but our pre-processor does actually replace things. This makes
    # sure everything is type safe (by "type casting" LiteralString to str in
    # the input)
    return document.splitlines()


def test_shortcode_parse():
    document = r"""<% code arg1="23" arg2=52 /%>"""
    sp = ShortcodePreprocessor()

    def code(arg1, arg2, **kwargs):
        return f"*{arg1}*\n_{arg2}_"

    sp.register('code', code)

    output = list(sp.run(_get_lines(document)))

    assert len(output) == 2
    assert output[0] == '*23*'
    assert output[1] == '_52_'


def test_shortcode_embedded_tag_end_in_string():
    document = r"""<% code arg1="/%>" /%>"""
    sp = ShortcodePreprocessor()

    def code(arg1, **kwargs):
        return arg1

    sp.register('code', code)

    output = list(sp.run(_get_lines(document)))

    assert len(output) == 1
    assert output[0] == '/%>'


def test_shortcode_two_codes_in_one_line():
    document = r"""<% code arg1="a" /%><% code arg1="b"/%>"""
    sp = ShortcodePreprocessor()

    def code(arg1, **kwargs):
        return arg1

    sp.register('code', code)

    output = list(sp.run(_get_lines(document)))

    assert len(output) == 2
    assert output[0] == 'a'
    assert output[1] == 'b'


def test_parse_buffer():
    lines = ['aaaa\n', 'bbb\n', '\n' 'c\n']
    pb = _ParseBuffer(0, lines)

    assert pb.get_current_line() == 'aaaa\n'
    assert pb.get_current_line_number() == 1

    pb.advance(2)

    assert pb.get_current_line() == 'aa\n'
    assert pb.get_current_line_number() == 1

    pb.advance_line()

    assert pb.get_current_line_number() == 2
    assert pb.get_current_line() == 'bbb\n'

    pb.consume('bb')

    assert pb.get_current_line() == 'b\n'


def test_shortcode_parser_1():
    lines = [r"""<% foo bar=baz /%> remainder"""]
    pb = _ParseBuffer(0, lines)
    sp = _ShortcodeParser(pb)

    rest, last_line, func_name, args = sp.parse()
    assert func_name == 'foo'
    assert rest == ' remainder'


def test_shortcode_parser_2():
    lines = ['<% foo bar="baz\n', 'oonga\" foo="bar" /%> remainder']
    pb = _ParseBuffer(0, lines)
    sp = _ShortcodeParser(pb)

    rest, last_line, func_name, args = sp.parse()
    assert func_name == 'foo'
    assert args['bar'] == 'baz\noonga'
    assert args['foo'] == 'bar'


def test_shortcode_parser_3():
    lines = [r"""<% foo bar=baz/%>"""]
    pb = _ParseBuffer(0, lines)
    sp = _ShortcodeParser(pb)

    rest, last_line, func_name, args = sp.parse()
    assert func_name == 'foo'
    assert args['bar'] == 'baz'


def test_shortcode_parser_4():
    lines = [r"""<% foo bar="baz"/%>"""]
    pb = _ParseBuffer(0, lines)
    sp = _ShortcodeParser(pb)

    rest, last_line, func_name, args = sp.parse()
    assert func_name == 'foo'
    assert args['bar'] == 'baz'


def test_shortcode_parser_5():
    lines = """<% figure
    arg0="foo"
    arg1="bar"
    arg2="baz"
/%>
""".splitlines()

    pb = _ParseBuffer(0, lines)
    sp = _ShortcodeParser(pb)

    rest, last_line, func_name, args = sp.parse()
    assert func_name == 'figure'
    assert args['arg0'] == 'foo'
    assert len(args) == 3


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


def test_shortcode_preprocessor_preserves_empty_lines():
    document = r"""Header
======

Body"""

    sp = ShortcodePreprocessor()
    output = '\n'.join(sp.run(_get_lines(document)))

    assert output == document

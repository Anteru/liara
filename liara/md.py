from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.preprocessors import Preprocessor
import re
import logging
from typing import (
    Any, Dict, Optional, Sequence
)


class HeadingLevelFixupProcessor(Treeprocessor):
    """This processor demotes headings by one level.

    By default, Markdown starts headings with ``<h1>``, but in general the
    title will be provided by a template. This processor replaces each heading
    with the next-lower heading, and adds a ``demoted`` class.
    """
    def run(self, root):
        return self._demote_header(root)

    def _demote_header(self, element):
        _demotions = {
            'h1': 'h2',
            'h2': 'h3',
            'h3': 'h4',
            'h4': 'h5',
            'h5': 'h6',
            'h6': 'h6',
        }

        if demotion := _demotions.get(element.tag):
            element.tag = demotion
            element.set('class', 'demoted')

        for e in element:
            self._demote_header(e)


class ShortcodeException(Exception):
    def __init__(self, error_message, line_number,
                 line_offset: Optional[int] = None):
        super().__init__(self._format_message(error_message, line_number,
                                              line_offset))
        self.__error_message = error_message
        self.__line_number = line_number

    def with_line_offset(self, offset):
        return ShortcodeException(
            self.__error_message,
            self.__line_number,
            offset
        )

    def _format_message(self, error_message, line_number, line_offset):
        if line_offset is not None:
            return f'Line {line_number + line_offset}: {error_message}'
        else:
            return error_message


class _ParseBuffer:
    def __init__(self, first_line: int, lines: Sequence[str]):
        self.__current_line = first_line
        self.__lines = lines
        self.__line_start = 0

    def get_current_line(self) -> str:
        return self.__lines[self.__current_line][self.__line_start:]

    def get_current_line_number(self) -> int:
        return self.__current_line + 1

    def advance_line(self):
        self.__current_line += 1
        self.__line_start = 0

        if self.__current_line >= len(self.__lines):
            raise ShortcodeException(
                "Unexpected end of shortcode",
                self.__current_line)

    def advance(self, offset: int):
        self.__line_start += offset

    def peek(self):
        try:
            return self.__lines[self.__current_line][self.__line_start]
        except IndexError:
            return None

    def consume(self, what: str):
        """Consume ``what`` from the input, and raise an error otherwise.

        ``what`` must not contain a newline."""
        assert '\n' not in what
        line = self.get_current_line()
        if line.startswith(what):
            self.advance(len(what))
        else:
            raise ShortcodeException(
                f'Shortcode parse error: Expected "{what}"',
                self.get_current_line_number())


class _ShortcodeParser:
    def __init__(self, buffer: _ParseBuffer):
        self.__args = dict()
        self.__function_name = None
        self.__buffer = buffer
        self.__key_re = re.compile(r'^[\w-]+')
        self.__arg_re = re.compile(r'^[\w-]+')
        self.__whitespace_re = re.compile(r'\s')

    def parse(self):
        """Parse a shortcode starting at the current position in the
        buffer.

        Returns a tuple containing: Any text following the short code in the
        last line, the next line to resume parsing from, the function name,
        and the arguments."""
        self.__consume('<%')
        self.__consume_whitespace()
        self.__function_name = self.__consume_key('function name')
        self.__consume_whitespace()

        while self.__buffer.peek() != '/':
            key = self.__consume_key('argument name')

            self.__consume_whitespace()
            self.__consume('=')
            self.__consume_whitespace()

            if self.__buffer.peek() == '"':
                value = self.__consume_string()
            else:
                value = self.__consume_arg()

            self.__args[key] = value
            self.__consume_whitespace()

        self.__consume('/%>')

        return (self.__buffer.get_current_line(),
                # This is actually the line number + 1, but that's exactly the
                # line at which parsing should continue, so this works out
                self.__buffer.get_current_line_number(),
                self.__function_name,
                self.__args,)

    def __consume(self, what):
        self.__buffer.consume(what)

    def __consume_arg(self) -> str:
        """Consume a function argument.

        Works on the current line only, may advance to the end of the line.
        """
        # args cannot span lines
        # an argument is anything that doesn't end in /%>, but we also disallow
        # whitespace and newlines. We thus search for the first whitespace
        # character or ``/%>``
        line = self.__buffer.get_current_line()
        if match := self.__arg_re.search(line):
            arg = line[:match.end()]
            self.__buffer.advance(match.end())

            return arg
        else:
            raise ShortcodeException(
                    f'Error while parsing shortcode: Could not parse argument value',
                    self.__buffer.get_current_line_number()
            )

    def __consume_whitespace(self):
        """Consume whitespace from the buffer.

        This will consume multiple lines if needed.
        """
        while True:
            line = self.__buffer.get_current_line()
            if not line:
                self.__buffer.advance_line()
                continue

            if match := self.__whitespace_re.search(line):
                if match.start() == 0:
                    self.__buffer.advance(match.end())
                else:
                    return
            else:
                return

    def __consume_string(self) -> str:
        """Consume a quoted string from the buffer.

        This will consume multiple lines if needed.
        """
        # Strings can be multi-line while inside "
        # Our strategy is as following: Find the next ", check if it was
        # escaped or not, and continue until we find one
        self.__buffer.consume('"')
        result = []
        while True:
            line = self.__buffer.get_current_line()
            next_quote = 0
            while True:
                if (quote_position := line.find('"', next_quote)) != -1:
                    if quote_position > 0 and line[quote_position-1] != '\\':
                        result.append(line[:quote_position])
                        self.__buffer.advance(quote_position)
                        self.__buffer.consume('"')
                        return ''.join(result).replace('\\"', '"')
                    else:
                        next_quote = quote_position+1
                else:
                    # No terminating quote in this line
                    result.append(line)
                    self.__buffer.advance_line()
                    break

    def __consume_key(self, what: str) -> str:
        """Consume a key from the buffer.

        Works on the current line only, may advance to the end of the line.
        """
        # keys cannot span lines, so we get the current line from the buffer
        # and match from the current position on
        line = self.__buffer.get_current_line()
        if match := self.__key_re.search(line):
            assert match.start() == 0
            key = line[:match.end()]
            self.__buffer.advance(match.end())

            return key
        else:
            raise ShortcodeException(
                    f'Error while parsing shortcode: Could not parse {what}',
                    self.__buffer.get_current_line_number()
                    )


class ShortcodePreprocessor(Preprocessor):
    """
    A Wordpress-inspired "shortcode" preprocessor which allows calling
    functions before the markup processing starts.

    Shortcodes are delimited by ``<%`` and ``/%>``. The content must start with
    the function name, followed by ``key=value`` pairs. The values are passed
    as strings, the calling function must do the type conversion.

    Values without quotation marks must consist of alphanumeric characters and
    ``-``, ``_`` only.

    .. note::
      Freestanding keys are not supported as it's ambiguous whether this should
      be a considered a plain argument (i.e. passed as a non-named argument) or
      a defaulted argument (i.e. named, but set to ``True`` or some other
      value.) For example, you can't write a shortcode like this::

        <% alert message="This is important" blink /%>

      Instead, you'll have to use something like::

        <% alert message="This is important" blink=yes /%>
    """

    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    def __init__(self, md=None, node=None):
        from .template import Page
        super().__init__(md)
        self.__functions = dict()
        self.__page = Page(node)
        self.__data = None

    def set_data(self, data: Dict[str, Any]):
        """
        Set the data context.

        .. versionadded:: 2.6.2
        """
        self.__data = data

    def register(self, name: str, function):
        """Register a new Markdown shortcode function.

        Shortcode function calls must accept all arguments as named arguments.
        Names (both function names and argument names) starting with ``$`` are
        reserved for built-in functions.

        Shortcode handlers must accept a final ``**kwargs`` argument to handle
        any context Liara may pass in. Liara context variables will be prefixed
        with ``$`` which is disallowed as an parameter name otherwise.
        """
        import inspect

        signature = inspect.signature(function)
        if not any([p.kind == p.VAR_KEYWORD
                    for p in signature.parameters.values()]):
            raise Exception(f'Cannot register function "{name}" as a '
                            'shortcode handler as the function signature '
                            'is missing a **kwargs parameter.')

        assert name and name[0] != '$'
        self.__functions[name] = function

    def run(self, lines: list[str]):
        i = 0
        line_count = len(lines)

        # We can't use for ... in range or for ... enumerate here, as we have
        # to skip lines based on the shortcode parser
        while i < line_count:
            line = lines[i]

            if (tag_start := line.find('<%')) != -1:
                # Only yield if the string is non-empty. Same logic below for
                # rest
                if start := line[:tag_start]:
                    yield start

                # Remove start from the current line
                lines[i] = line[tag_start:]

                parse_buffer = _ParseBuffer(i, lines)
                shortcode_parser = _ShortcodeParser(parse_buffer)
                rest, next_line, func_name, args = shortcode_parser.parse()

                args['$page'] = self.__page
                if self.__data:
                    args['$data'] = self.__data

                def pretty_print_args(d):
                    for k, v in d.items():
                        # Skip internal arguments as they can't be
                        # pretty-printed anyways
                        if k[0] == '$':
                            continue
                        yield f'{k}={repr(v)}'

                # Skip the text processing if logging is disabled
                if self.__log.isEnabledFor(logging.DEBUG):
                    self.__log.debug('Calling shortcode handler: "%s" with '
                                     'arguments: %s',
                                     func_name,
                                     ', '.join(pretty_print_args(args)))
                yield from self.__functions[func_name](**args).splitlines()

                # Another shortcode in the same line, so we need to resume
                # parsing there and cannot simply emit the rest
                if '<%' in rest:
                    assert next_line >= 1
                    lines[next_line-1] = rest
                    continue

                if rest:
                    yield rest

                i = next_line
            else:
                yield line
                i += 1


class LiaraMarkdownExtensions(Extension):
    """Register various markdown extensions.
    """
    def __init__(self, node=None):
        super().__init__()
        self.__node = node
        self.__shortcode_preprocessor = None

    def set_data(self, data: Dict[str, Any]):
        assert self.__shortcode_preprocessor
        self.__shortcode_preprocessor.set_data(data)

    def extendMarkdown(self, md):
        from .signals import register_markdown_shortcodes

        self.__shortcode_preprocessor = ShortcodePreprocessor(md, self.__node)

        register_markdown_shortcodes.send(
            self,
            preprocessor=self.__shortcode_preprocessor)

        md.treeprocessors.register(HeadingLevelFixupProcessor(md),
                                   'heading-level-fixup',
                                   100)
        md.preprocessors.register(self.__shortcode_preprocessor,
                                  'shortcode-preprocessor',
                                  100)
        md.registerExtension(self)

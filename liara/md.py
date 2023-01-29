from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.preprocessors import Preprocessor
from enum import Enum
import re
import logging


class HeadingLevelFixupProcessor(Treeprocessor):
    """This processor demotes headings by one level.

    By default, Markdown starts headings with ``<h1>``, but in general the
    title will be provided by a template. This processor replaces each heading
    with the next-lower heading, and adds a ``demoted`` class.
    """
    def run(self, root):
        return self._demote_header(root)

    def _demote_header(self, element):
        if element.tag == 'h1':
            element.tag = 'h2'
            element.set('class', 'demoted')
        elif element.tag == 'h2':
            element.tag = 'h3'
            element.set('class', 'demoted')
        elif element.tag == 'h3':
            element.tag = 'h4'
            element.set('class', 'demoted')
        elif element.tag == 'h4':
            element.tag = 'h5'
            element.set('class', 'demoted')
        elif element.tag == 'h5':
            element.tag = 'h6'
            element.set('class', 'demoted')
        elif element.tag == 'h6':
            element.tag = 'h6'
            element.set('class', 'demoted')

        for e in element:
            self._demote_header(e)


class ShortcodeException(Exception):
    def __init__(self, error_message, line_number):
        super().__init__(f'Line {line_number}: {error_message}')
        self.__line_number = line_number


class ShortcodePreprocessor(Preprocessor):
    """
    A Wordpress-inspired "shortcode" preprocessor which allows calling
    functions before the markup processing starts.

    Shortcodes are delimited by ``<%`` and ``/%>``. The content must start with
    the function name, followed by ``key=value`` pairs. The values are passed
    as strings, the calling function must do the type conversion.

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

    def __init__(self, line_offset: int = 1, md=None):
        super().__init__(md)
        self.__functions = dict()
        self.__tag_start = re.compile(r'<%')
        self.__tag_end = re.compile(r'/%>')
        self.__name = re.compile(r'^([\w_]+)(?:\s+)')
        self.__arg = re.compile(r'^([\w_]+)(?:\s*)=(?:\s*)')
        self.__value = re.compile(r'(\S+)(?:\s*)')
        self.__line_offset = line_offset

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

    class ParseState(Enum):
        Outside = 0
        Inside = 1

    def _parse_line(self, line: str, pending: str, state: ParseState,
                    line_number: int, shortcode_starting_line: int):
        """Return a tuple with:

        * Anything that should be output immediately
        * The content to be parsed next
        * The accumulated content inside <% /%>
        * The next parse state.
        """
        # We set the line to None here if there's a call in there and nothing
        # before/after it, so we can discern an actually empty line (which
        # must be preserved) from a generated empty line (because the shortcode
        # was cut out)
        if state == self.ParseState.Inside:
            if match := self.__tag_end.search(line):
                content = line[:match.start()]
                line = line[match.end():]
                if line == '':
                    line = None
                if shortcode_starting_line != -1:
                    line_number = shortcode_starting_line
                content = self._call_function(pending + content,
                                              line_number)
                return (content, line, None, self.ParseState.Outside,)
            else:
                # No end tag, so append the whole line to the current state
                return (None, None, pending + line, self.ParseState.Inside,)
        else:
            # Outside a statement. Check if we have a starting tag here ...
            if match := self.__tag_start.search(line):
                content = line[match.end():]
                line = line[:match.start()]
                if line == '':
                    line = None
                return (line, content, "", self.ParseState.Inside,)
            else:
                return (line, None, None, self.ParseState.Outside,)

    def _call_function(self, content: str, line_number: int):
        content = content.strip()

        function_args = dict()
        function = None

        # First token in the string is the function name, rest is arguments
        if match := self.__name.match(content):
            function = match.group(1)
            args = content[match.end():]
            while args:
                # Skip whitespace at the beginning
                args = args.lstrip()
                if arg_match := self.__arg.match(args):
                    next_character = args[arg_match.end()]
                    if next_character == '"':
                        # We're inside a string
                        string_start = arg_match.end() + 1
                        string_end = string_start + 1
                        while True:
                            if args[string_end] == '"' and \
                                    args[string_end-1] != '\\':
                                break
                            string_end += 1
                        function_args[arg_match.group(1)] = \
                            args[string_start:string_end]
                        args = args[string_end+1:]
                    else:
                        args = args[arg_match.end():]
                        if value_match := self.__value.match(args):
                            args = args[value_match.end():]
                            function_args[arg_match.group(
                                1)] = value_match.group(1)
                        else:
                            # Raise error
                            raise ShortcodeException(
                                'Invalid function argument value while trying '
                                f'to call "{function}".',
                                line_number + self.__line_offset
                            )
                else:
                    raise ShortcodeException(
                        'Error parsing argument while parsing call to '
                        f'"{function}". Arguments must have the form '
                        'key=value or key="value".',
                        line_number + self.__line_offset
                    )
        else:
            raise ShortcodeException(
                'No function name in shortcode',
                line_number + self.__line_offset
            )

        # Undo string escapes in the strings
        function_args = {k: v.replace('\\"', '"')
                         for k, v in function_args.items()}

        return self.__functions[function](**function_args)

    def run(self, lines):
        state = self.ParseState.Outside
        temp = ''
        first_inside_line = -1

        for line_number, line in enumerate(lines):
            # Must use `is not None` checks here because we want to emit
            # whitespace lines/empty lines
            while line is not None:
                output, line, temp, state = self._parse_line(
                    line, temp, state, line_number, first_inside_line)
                if state == self.ParseState.Inside and first_inside_line == -1:
                    first_inside_line = line_number
                elif state == self.ParseState.Outside:
                    first_inside_line = -1
                if output is not None:
                    # Functions can return multiple lines, and we want to
                    # preserve that so the parser can find multi-line constructs
                    if '\n' in output:
                        yield from output.splitlines()
                    else:
                        yield output

        if state == self.ParseState.Inside:
            raise ShortcodeException('Shortcode open at end of file.',
                                     first_inside_line + self.__line_offset)


class LiaraMarkdownExtensions(Extension):
    """Markdown extension for the :py:class:`HeadingLevelFixupProcessor`.
    """
    def __init__(self, line_offset: int = 1):
        super().__init__()
        self.__line_offset = line_offset

    def extendMarkdown(self, md):
        from .signals import register_markdown_shortcodes

        shortcode_preprocessor = ShortcodePreprocessor(self.__line_offset, md)

        register_markdown_shortcodes.send(
            self,
            preprocessor=shortcode_preprocessor)

        md.treeprocessors.register(HeadingLevelFixupProcessor(md),
                                   'heading-level-fixup',
                                   100)
        md.preprocessors.register(shortcode_preprocessor,
                                  'shortcode-preprocessor',
                                  100)
        md.registerExtension(self)

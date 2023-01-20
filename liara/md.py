from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.preprocessors import Preprocessor
from enum import Enum
import re


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


class CallPreprocessor(Preprocessor):
    def __init__(self, md=None):
        super().__init__(md)
        self.__functions = dict()
        self.__tag_start = re.compile(r'<%')
        self.__tag_end = re.compile(r'/%>')
        self.__name = re.compile(r'^([\w_]+)(?:\s+)')
        self.__arg = re.compile(r'^([\w_]+)(?:\s*)=(?:\s*)')
        self.__value = re.compile(r'(\w+)(?:\s*)')

    def register_function(self, name, function):
        self.__functions[name] = function

    class ParseState(Enum):
        Outside = 0
        Inside = 1

    def _parse_line(self, line, pending, state):
        if state == self.ParseState.Inside:
            if match := self.__tag_end.search(line):
                content = line[:match.start()]
                line = line[match.end():]
                content = self._call_function(pending + content)
                return (content, line, None, self.ParseState.Outside,)
            else:
                # No end tag, so append the whole line to the current state
                return (None, None, pending + line, self.ParseState.Inside,)
        else:
            # Outside a statement. Check if we have a starting tag here ...
            if match := self.__tag_start.search(line):
                content = line[match.end():]
                line = line[:match.start()]
                return (line, content, "", self.ParseState.Inside,)
            else:
                return (line, None, None, self.ParseState.Outside,)

    def _call_function(self, content: str):
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
                        args = args[arg_match.end()]
                        if value_match := self.__value.match(args):
                            args = args[value_match.end():]
                            function_args[arg_match.group(
                                1)] = value_match.group(1)
                        else:
                            # Raise error
                            pass
                else:
                    # Throw exception: Missing arg=
                    pass
        else:
            # Throw exception: Missing function name
            pass

        return self.__functions[function](**function_args)

    def run(self, lines):
        state = self.ParseState.Outside
        temp = ''

        for line in lines:
            while line:
                output, line, temp, state = self._parse_line(line, temp, state)
                if output:
                    yield output


class LiaraMarkdownExtensions(Extension):
    """Markdown extension for the :py:class:`HeadingLevelFixupProcessor`.
    """
    def extendMarkdown(self, md):
        from .signals import register_markdown_calls

        cp = CallPreprocessor(md)

        register_markdown_calls.send(self, preprocessor=cp)

        md.treeprocessors.register(HeadingLevelFixupProcessor(md),
                                   'heading-level-fixup',
                                   100)
        md.preprocessors.register(cp,
                                  'call-preprocessor',
                                  100)
        md.registerExtension(self)

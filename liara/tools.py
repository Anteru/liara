from typing import List
import subprocess
import sys
import logging
import abc


class Tool(abc.ABC):
    """Represents a command line tool that can be invoked by Liara."""
    @abc.abstractmethod
    def is_present(self) -> bool:
        """Returns ``true`` if the tool is available and ready to use."""
        ...

    @abc.abstractmethod
    def try_install(self) -> bool:
        """Try to install the tool if it's not present. This will produce
        a descriptive message if the installation fails."""
        ...

    @abc.abstractmethod
    def invoke(self, cmd_line_arguments: List[str]) \
            -> subprocess.CompletedProcess:
        """Invoke the tool, return a ``subprocess.CompletedProcess`` instance.
        `stderr` and `stdout` is redirected to a ``subprocess.PIPE`` by
        default."""
        ...


class SassCompiler(Tool):
    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    def is_present(self) -> bool:
        try:
            subprocess.check_output(
                ['sass', '--version'],
                # On Windows, we need to set shell=True, otherwise, the
                # sass binary installed using npm install -g sass won't
                # be found.
                shell=sys.platform == 'win32')

            return True
        except Exception:
            return False

    def invoke(self, cmd_line_arguments: List[str]):
        return subprocess.run(
            ['sass'] + cmd_line_arguments,
            # See above
            shell=sys.platform == 'win32',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    def try_install(self):
        try:
            subprocess.check_call(['npm', 'install', '-g', 'sass'])
        except subprocess.CalledProcessError:
            self.__log.error('Failed to install `sass` via `npm`. Use '
                             '`npm install -g sass` to install `sass`. Note: '
                             'You must have `npm` installed, this comes with '
                             '`node.js`.')
            return False

        return True


class TypescriptCompiler(Tool):
    def is_present(self) -> bool:
        try:
            subprocess.check_output(
                ['tsc', '--version'],
                # See above
                shell=sys.platform == 'win32')

            return True
        except Exception:
            return False

    def invoke(self, cmd_line_arguments: List[str]) -> bool:
        return subprocess.run(
            ['tsc'] + cmd_line_arguments,
            # See above
            shell=sys.platform == 'win32',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    def try_install(self):
        try:
            subprocess.check_call(['npm', 'install', '-g', 'typescript'])
        except subprocess.CalledProcessError:
            self.__log.error('Failed to install `typescript` via `npm`. Use '
                             '`npm install -g '
                             'typescript` to install `typescript`. Note: '
                             'You must have `npm` installed, this comes with '
                             '`node.js`.')
            return False

        return True

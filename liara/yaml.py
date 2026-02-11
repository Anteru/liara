# SPDX-FileCopyrightText: 2019 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import (
    IO,
    Optional,
    Text,
    Union
)


def load_yaml(s: Union[bytes, IO, IO[bytes], Text, IO[Text]]):
    """Load a Yaml document.

    This is a helper function which tries to use the fast ``CLoader``
    implementation and falls back to the native Python version on failure.
    """
    import yaml
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    return yaml.load(s, Loader=Loader)


def dump_yaml(data, stream: Optional[IO] = None):
    """Dump an object to Yaml.

    This is a helper function which tries to use the fast ``CDumper``
    implementation and falls back to the native Python version on failure.
    """
    import yaml
    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper

    return yaml.dump(data, stream, Dumper=Dumper)

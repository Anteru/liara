def load_yaml(s):
    import yaml
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    return yaml.load(s, Loader=Loader)


def dump_yaml(data, stream=None):
    import yaml
    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper

    return yaml.dump(data, stream, Dumper=Dumper)

from typing import (
    Dict,
    Any,
)


def create_default_configuration() -> Dict[str, Any]:
    """Creates a dictionary with the default configuration."""
    # When changing this, make sure to update the docs as well
    return {
        'content_directory': 'content',
        'resource_directory': 'resources',
        'static_directory': 'static',
        'output_directory': 'output',
        'generator_directory': 'generators',
        'build': {
            'clean_output': True,
            'cache.fs.directory': 'cache',
            'cache.db.directory': 'cache',
            'cache.redis.host': 'localhost',
            'cache.redis.port': 6379,
            'cache.redis.db': 0,
            'cache.redis.expiration_time': 60,
            'cache.type': 'fs',
            'resource.sass.compiler': 'libsass'
        },
        'ignore_files': ['*~'],
        'content': {
            'filters': ['date', 'status']
        },
        'template': 'templates/default.yaml',
        'routes': {
            'static': 'static_routes.yaml'
        },
        'collections': 'collections.yaml',
        'relaxed_date_parsing': False,
        'allow_relative_links': True,
        'feeds': 'feeds.yaml',
        'metadata': 'metadata.yaml'
    }


def create_default_template_configuration() -> Dict[str, Any]:
    """Creates the default template configuration."""
    return {
        'backend': 'jinja2',
        'backend_options': {
            'jinja2': {
                'trim_blocks': True,
                'lstrip_blocks': True
            }
        }
    }


def create_default_metadata() -> Dict[str, Any]:
    """Creates a dictionary with the default metadata."""
    return {
        'title': 'Default title',
        'base_url': 'https://example.org',
        'description': 'Default description',
        'language': 'en-US',
        'copyright': 'Licensed under the '
                     '<a href="http://creativecommons.org/licenses/by/4.0/"> '
                     'Creative Commons Attribution 4.0 International License.'
    }

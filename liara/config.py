from typing import (
    Dict,
    Any,
)


def create_default_configuration() -> Dict[str, Any]:
    return {
        'content_directory': 'content',
        'resource_directory': 'resources',
        'static_directory': 'static',
        'output_directory': 'output',
        'build': {
            'clean_output': True,
            'cache_directory': 'cache'
        },
        'content': {
            'filters': ['date', 'status']
        },
        'template': 'templates/default.yaml',
        'routes': {
            'static': 'static_routes.yaml'
        },
        'base_url': 'http://localhost:8000',
        'collections': {},
        'relaxed_date_parsing': False,
        'allow_relative_links': True,
        'feeds': 'feeds.yaml',
        'metadata': 'metadata.yaml'
    }


def create_default_metadata() -> Dict[str, Any]:
    return {
        'title': 'Default title',
        'base_url': 'https://example.org',
        'description': 'Default description',
        'language': 'en-US',
        'copyright': 'Licensed under the '
                     '<a href="http://creativecommons.org/licenses/by/4.0/"> '
                     'Creative Commons Attribution 4.0 International License.'
    }
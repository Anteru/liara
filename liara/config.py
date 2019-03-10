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
        'allow_relative_links': True
    }
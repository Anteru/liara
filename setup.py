from setuptools import setup, find_packages
import liara.version

setup(
    name='Liara',
    version=liara.version,
    packages=find_packages(exclude=['*.test', 'test.*', '*.test.*']),
    install_requires=open('requirements.txt', 'r').readlines(),
    python_requires='>=3.6',

    author="Matthäus G. Chajdas",
    author_email="dev@anteru.net",
    description="Static page generator",
    long_description=open('README.md', 'r').read(),
    long_description_content_type="text/markdown",

    license="BSD",
    keywords=[],
    url="http://shelter13.net/projects/Liara",

    entry_points='''
        [console_scripts]
        liara=liara.cmdline:cli
    ''',
    tests_require=['pytest'],
    extras_require={
        'dev': [
            'flake8',
            'flake8-mypy',
        ],
        'mako': [
            'Mako~=1.0.7'
        ]
    },

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
    ]
)

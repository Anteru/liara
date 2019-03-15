from setuptools import setup, find_packages
import liara

setup(
    name='Liara',
    version=liara.__version__,
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
    setup_requires=['pytest-runner', 'sphinx'],
    tests_require=['pytest'],
    extras_require={
        'dev': [
            'flake8',
            'flake8-mypy',
        ]
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
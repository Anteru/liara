from setuptools import setup

setup(
    name='liara',
    version='0.1',
    py_modules=['liara'],
    install_requires=open('requirements.txt', 'r').readlines(),
    entry_points='''
        [console_scripts]
        liara=liara.cmdline:cli
    ''',
)
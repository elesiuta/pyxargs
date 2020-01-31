import setuptools
import pyxargs

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyxargs",
    version=pyxargs.VERSION,
    description="A mostly complete implementation of xargs in python with some added features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elesiuta/pyxargs",
    py_modules=['pyxargs'],
    entry_points={
        'console_scripts': [
            'pyxargs = pyxargs:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: System :: Shells",
        "Topic :: System :: System Shells",
        "Topic :: Terminals",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Environment :: Console",
        "Development Status :: 5 - Production/Stable",
    ],
    test_suite = 'tests',
)

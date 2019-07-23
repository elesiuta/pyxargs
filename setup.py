import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyxargs",
    version="0.9.1",
    description="Build and execute command lines from standard input or file paths, a partial implementation of xargs in python with some added pythonic features.",
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
    ],
)
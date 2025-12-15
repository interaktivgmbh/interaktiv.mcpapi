from setuptools import find_packages, setup

# Package metadata
NAME = 'interaktiv.mcpapi'
DESCRIPTION = 'MCP API integration for Plone.'
URL = 'https://github.com/interaktiv/interaktiv.mcpapi'
EMAIL = 'support@interaktiv.de'
AUTHOR = 'Interaktiv GmbH'
REQUIRES_PYTHON = '~=3.11'
VERSION = '1.0.0'
REQUIRED = [
    'setuptools',
    'Plone',
]
EXTRAS = {
    'test': ['plone.app.testing']
}

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    long_description_content_type='text/markdown',
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: Addon",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='plone mcp api',
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    license='proprietary',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['interaktiv', ],
    include_package_data=True,
    zip_safe=False,
    python_requires=REQUIRES_PYTHON,
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone
    """
)
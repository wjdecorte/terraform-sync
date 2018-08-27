from setuptools import setup, find_packages

version = "0.1"

setup(
    name='cattle',
    version=version,
    packages=find_packages(),
    # url='http://,
    license='GNU General Public License (GPL)',
    author='jdecorte',
    author_email='jdecorte@decorteindustries.com',
    description='CLI for syncing Terraform configuration, State and environment',
    install_requires=[],
    extras_require={},
    include_package_data=False,
    entry_points={
        'console_scripts': [
            'tfsync = tfsync.cli:main'
        ]
    },
    scripts=[]
)

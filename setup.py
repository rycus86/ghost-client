from distutils.core import setup

setup(
    name='ghost_client',
    packages=['ghost_client'],
    version='0.0.4',
    description='API client for the Ghost blogging platform',
    long_description=open('README.md').read(),
    license='MIT',
    author='Viktor Adam',
    author_email='rycus86@gmail.com',
    url='https://github.com/rycus86/ghost-client',
    download_url='https://github.com/rycus86/ghost-client/archive/0.0.4.tar.gz',
    keywords=['ghost', 'blog', 'api', 'client'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],
    install_requires=['six', 'requests'],
)

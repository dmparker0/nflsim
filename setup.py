from setuptools import setup

setup(
    name='nflsim',
    url='https://github.com/dmparker0/nflsim/',
    author='Dan Parker',
    author_email='dan.m.parker0@gmail.com',
    packages=['nflsim'],
    install_requires=['numpy','pandas','scipy','bs4','requests','joblib'],
    version='1.1.3',
    license='MIT',
    description='A tool for simulating the NFL regular season and playoffs',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    download_url = 'https://github.com/dmparker0/nflsim/archive/v1.1.3.tar.gz',
    keywords = ['NFL', 'football', 'sports','simulation','statistics'], 
)


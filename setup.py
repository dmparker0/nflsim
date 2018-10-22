from setuptools import setup

setup(
    name='NFLSim',
    url='https://github.com/dmparker0/nflsim/',
    author='Dan Parker',
    author_email='dan.m.parker0@gmail.com',
    packages=['nflsim'],
    install_requires=['numpy','pandas','scipy','bs4','requests','joblib'],
    version='0.1',
    license='MIT',
    description='A tool for simulating the NFL regular season and playoffs',
    #long_description=open('README.txt').read(),
)

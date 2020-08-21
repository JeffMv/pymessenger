from setuptools import setup

installation_requirements = [
    'requests',
    'requests-toolbelt',
    'six'
]

try:
    import enum
    del enum
except ImportError:
    installation_requirements.append('enum')

setup(
    name='pymessenger',
    packages=['pymessenger'],
    version='0.0.7.0',
    install_requires=installation_requirements,
    description="Python Wrapper for Facebook Messenger Platform",
    author='Rohit Ner',
    author_email='rohitner1@gmail.com',
    url='https://github.com/rohitner/pymessenger',
    download_url='https://github.com/davidchua/pymessenger/tarball/1.0.0',
    keywords=['facebook messenger', 'python', 'wrapper', 'bot', 'messenger bot'],
    classifiers=[],
)

"""Install threepseat as module"""
import setuptools

with open('requirements.txt') as f:
    install_requires = f.readlines()

with open('README.md') as f:
    long_desc = f.read()

setuptools.setup(
    name="3pseatBot",
    version="1.0.0",
    author="Greg Pauloski",
    author_email="jgpauloski@uchicago.edu",
    description="3pseatBot for Discord",
    long_description=long_desc,
    url="https://github.com/gpauloski/3pseatBot",
    packages=["threepseat"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=install_requires,
)

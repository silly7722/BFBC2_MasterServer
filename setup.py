from setuptools import find_packages, setup

with open("requirements.txt", "r") as f:
    requirements = f.read()

setup(
    name="BFBC2_MasterServer",
    version="",
    packages=find_packages(),
    url="",
    license="",
    author="GrzybDev",
    author_email="grzybdev@gmail.com",
    description="",
    install_requires=requirements,
)

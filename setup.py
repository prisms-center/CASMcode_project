__version__ = "1.0a1"

# Available at setup time due to pyproject.toml
from setuptools import setup

setup(
    name="casm-project",
    version=__version__,
    packages=["casm", "casm.project", "casm.project.commands"],
    install_requires=[],
)

from setuptools import find_packages, setup

setup(
    name="load_chapters",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "mkdocs.plugins": [
            "load_chapters = plugins.load_chapters:LoadChaptersPlugin",
        ]
    },
)

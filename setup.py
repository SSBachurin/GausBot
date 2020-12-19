import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="GauBot",
    version="0.0.1",
    author="Stan Bachurin",
    author_email="bachurin.rostgmu@gmail.com",
    description="Gaussian bot runner for telegram",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SSBachurin/GausBot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=required,
    python_requires='>=3.6',
)
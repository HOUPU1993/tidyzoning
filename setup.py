from setuptools import setup, find_packages

setup(
    name="tidyzoning",  # The name of your package
    version="0.1.0",  # The version of your package
    description="A Python package for tidy zoning analysis",  # A short description of the package
    long_description=open("README.md").read(),  # Use README.md as the long description
    long_description_content_type="text/markdown",  # The format of the long description
    author="Your Name",  # Your name as the package author
    author_email="your.email@example.com",  # Your email
    url="https://github.com/HOUPU1993/tidyzoning",  # The URL to your project repository
    license="MIT",  # The license of your package (e.g., MIT, Apache, etc.)
    packages=find_packages(),  # Automatically find all Python packages in your project
    include_package_data=True,  # Include non-Python files specified in MANIFEST.in
    install_requires=[
        # Add your dependencies here, e.g.:
        # "numpy>=1.21.0",
        # "pandas>=1.3.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",  # Your project is compatible with Python 3
        "License :: OSI Approved :: MIT License",  # The license type
        "Operating System :: OS Independent",  # OS compatibility
    ],
    python_requires=">=3.7",  # Specify the minimum Python version your package supports
)
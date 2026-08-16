from setuptools import setup, find_packages

setup(
    name="pdfalchemy",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyMuPDF>=1.23.0",
        "pikepdf>=8.0.0",
        "python-docx>=0.8.11",
        "beautifulsoup4>=4.12.0",
        "markdownify>=0.11.6",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "pillow>=10.0.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": ["pdfalchemy=pdfalchemy.cli:main"],
    },
)

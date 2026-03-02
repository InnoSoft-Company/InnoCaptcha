from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
_HERE = Path(__file__).parent
_LONG_DESC = (_HERE / "README.md").read_text(encoding="utf-8") if (_HERE / "README.md").exists() else ""

setup(
    name="captcha_lib",
    version="1.0.0",
    author="captcha-lib contributors",
    author_email="captcha-lib@example.com",
    description=(
        "A professional, pluggable CAPTCHA library with image, math, and "
        "custom challenge types, token-based security, and multiple storage backends."
    ),
    long_description=_LONG_DESC,
    long_description_content_type="text/markdown",
    url="https://github.com/example/captcha_lib",
    license="MIT",
    package_dir={"captcha_lib": "."},
    packages=[
        "captcha_lib",
        "captcha_lib.core",
        "captcha_lib.utils",
        "captcha_lib.types",
        "captcha_lib.storage",
    ],
    package_data={
        "captcha_lib": ["data/*.ttf", "data/*.otf"],
    },
    python_requires=">=3.10",
    install_requires=[
        "Pillow>=10.0.0",
    ],
    extras_require={
        "redis": [
            "redis>=4.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "all": [
            "redis>=4.0.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Graphics",
        "Typing :: Typed",
    ],
    keywords=[
        "captcha", "image", "security", "bot-protection",
        "text-captcha", "math-captcha", "plugin",
    ],
    entry_points={},
    zip_safe=False,
)

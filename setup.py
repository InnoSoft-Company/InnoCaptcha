from setuptools import setup, find_packages

__version__ = "1.1.1"

setup(
  name="InnoCaptcha",
  version=__version__,
  author="InnoSoft Company",
  author_email="midoghanam@hotmail.com",
  description=("A professional, pluggable CAPTCHA library with image, math, and custom challenge types, token-based security, and multiple storage backends."),
  long_description=open("README.md", encoding="utf-8").read(),
  long_description_content_type="text/markdown",
  url="https://www.midoghanam.site/",
  license="MIT",
  project_urls={
    "Source Code": "https://github.com/InnoSoft-Company/InnoCaptcha",
    "Bug Tracker": "https://github.com/InnoSoft-Company/InnoCaptcha/issues",
    "Documentation": "https://github.com/InnoSoft-Company/InnoCaptcha#readme",
  },
  packages=find_packages(),
  package_data={"InnoCaptcha": ["data/*.*", "*.*"],
},
  entry_points={"console_scripts": ["InnoCaptcha=InnoCaptcha.cli:main", ],},
  python_requires=">=3.9",
  install_requires=["Pillow>=10.0.0", ],
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
  keywords=["captcha", "image", "security", "bot-protection", "text-captcha", "math-captcha", "plugin",],
)

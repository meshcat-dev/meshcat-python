from setuptools import setup, find_packages

setup(name="meshcat",
    version="0.0.5",
    description="WebGL-based visualizer for 3D geometries and scenes",
    url="https://github.com/rdeits/meshcat-python",
    download_url="https://github.com/rdeits/meshcat-python/archive/v0.0.5.tar.gz",
    author="Robin Deits",
    author_email="mail@robindeits.com",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
      "u-msgpack-python >= 2.4.1",
      "numpy >= 1.14.0",
      "websockets >= 4.0.1",
    ],
    zip_safe=False,
    include_package_data=True
)

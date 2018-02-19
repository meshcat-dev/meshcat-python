from setuptools import setup

setup(name="meshcat",
    version="0.0.1",
    description="WebGL-based visualizer for 3D geometries and scenes",
    url="https://github.com/rdeits/meshcat-python",
    author="Robin Deits",
    author_email="mail@robindeits.com",
    license="MIT",
    packages=["meshcat"],
    install_requires=[
      "u-msgpack-python >= 2.4.1",
      "numpy >= 1.14.0",
      "websockets >= 4.0.1",
    ],
    zip_safe=False,
    include_package_data=True
)

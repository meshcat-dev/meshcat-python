from setuptools import setup, find_packages

setup(name="meshcat",
    version="0.0.9",
    description="WebGL-based visualizer for 3D geometries and scenes",
    url="https://github.com/rdeits/meshcat-python",
    download_url="https://github.com/rdeits/meshcat-python/archive/v0.0.9.tar.gz",
    author="Robin Deits",
    author_email="mail@robindeits.com",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"": "src"},
    test_suite="meshcat",
    entry_points={
        "console_scripts": [
            "meshcat-server=meshcat.servers.zmqserver:main"
        ]
    },
    install_requires=[
      "u-msgpack-python >= 2.4.1",
      "numpy >= 1.14.0",
      "tornado >= 4.0.0",
      "pyzmq >= 17.0.0"
    ],
    zip_safe=False,
    include_package_data=True
)

from glob import glob
from setuptools import find_packages, setup


package_name = "elfin_tcp_driver"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="cjw",
    maintainer_email="cjw@todo.todo",
    description="ROS 2 adapter for the HansRobot Elfin TCP protocol",
    license="BSD-3-Clause",
    entry_points={
        "console_scripts": [
            "elfin_tcp_adapter = elfin_tcp_driver.adapter_node:main",
        ],
    },
)

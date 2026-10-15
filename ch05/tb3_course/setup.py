from setuptools import setup

package_name = 'tb3_course'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Course maintainer',
    maintainer_email='at44565685@gmail.com',
    description='Chapter 5 ROS 2 examples for TurtleBot3 on Gazebo Fortress',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'obstacle_stop = tb3_course.obstacle_stop:main',
            'drive_distance = tb3_course.drive_distance:main',
            'patrol = tb3_course.patrol:main',
        ],
    },
)

from setuptools import setup
import os.path

setup_directory = os.path.abspath(os.path.dirname(__file__))

setup(
    name='glfw-types',
    version='1.0.0',
    description='A ctypes-based wrapper for GLFW3 (with typing).',
    url='https://github.com/romanin-rf/glfw-types',
    author='Florian Rhiem',
    author_email='florian.rhiem@gmail.com',
    license='MIT',
    packages=['glfw'],
    package_data={'glfw': ['__init__.pyi']},
    install_requires=["glfw"],
    setup_requires=["glfw"]
)

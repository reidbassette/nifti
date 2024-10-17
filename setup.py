from setuptools import setup, find_packages

setup(
    name='NIFTI Setup',
    version=0.1,
    packages= find_packages(),
    entry_points={
        'console_scripts': [
            'my_start=nifti_v0.app:main'
        ]
    },
    install_requires=[
        'numpy',
        'PyQt6',
        'ctREFPROP',
        'CoolProp',
        'scipy',
        'matplotlib',
        'PIL'
    ]
)

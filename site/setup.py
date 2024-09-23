from setuptools import setup, find_packages

setup(
    name='turath-inveniordm',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'invenio-app-rdm>=10.0.0,<11.0.0',
        'invenio-previewer-mirador>=1.0.0',
    ],
    entry_points={
        # Добавьте точки входа, если определяете свои
    },
)

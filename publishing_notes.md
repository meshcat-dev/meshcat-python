1. Update version and URL in setup.py
2. `python -m pip install --upgrade setuptools wheel`
3. `python setup.py sdist bdist_wheel`
4. `python -m pip install --upgrade twine`
5. `twine upload dist/*`

1. Update version and URL in setup.py
2. Create a new tag:

    git tag -a "v1.2.3"

3. Upload

    python -m pip install --upgrade setuptools wheel
    rm dist/*
    python setup.py sdist bdist_wheel
    python -m pip install --upgrade twine
    twine upload dist/*

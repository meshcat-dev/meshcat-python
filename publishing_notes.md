1. Update version and URL in setup.py
2. Create a new tag:

    git tag -a "v1.2.3"
    git push
    git push --tags

3. Upload

    python3 -m pip install --upgrade setuptools wheel
    rm dist/*
    python3 setup.py sdist bdist_wheel
    python3 -m pip install --upgrade twine
    twine upload dist/*

1. Update version and URL in setup.py

    python -m pip install --upgrade setuptools wheel
    rm dist/*
    python setup.py sdist bdist_wheel
    python -m pip install --upgrade twine
    twine upload dist/*

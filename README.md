# public-workflow-sdk

# Steps to build
rm -rf dist/ build/ *.egg-info
python -m build
python -m twine upload dist/*
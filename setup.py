from setuptools import setup

setup(
    name='zamp_public_workflow_sdk',
    version='0.0.37',    
    description='Workflow Manager',
    url='https://github.com/zamp-engineering/workflow_manager',
    author='Zamp Engineering',
    author_email='engineering@zamp.com',
    license='MIT',
    packages=[
        'zamp_public_workflow_sdk',
        'zamp_public_workflow_sdk.temporal',
        'zamp_public_workflow_sdk.temporal.models',
        'zamp_public_workflow_sdk.temporal.codec',
        'zamp_public_workflow_sdk.temporal.data_converters',
        'zamp_public_workflow_sdk.temporal.data_converters.transformers',
        'zamp_public_workflow_sdk.temporal.interceptors',
    ],
    install_requires=[
        'pydantic',
        'temporalio',
        'python-dateutil',
        'python-dotenv'
    ],
    classifiers=[],
)
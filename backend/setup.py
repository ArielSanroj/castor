"""
Setup script for CASTOR ELECCIONES backend.
"""
from setuptools import setup, find_packages

setup(
    name='castor-elecciones',
    version='1.0.0',
    description='CASTOR ELECCIONES - Campaña Electoral Inteligente',
    author='Carlos Ariel Sánchez Torres',
    packages=find_packages(),
    install_requires=[
        'Flask==3.0.0',
        'Flask-CORS==4.0.0',
        'Flask-JWT-Extended==4.6.0',
        'python-dotenv==1.0.0',
        'tweepy==4.14.0',
        'openai==1.3.0',
        'supabase==2.0.0',
        'twilio==8.10.0',
        'transformers==4.35.0',
        'torch==2.1.0',
        'pydantic==2.5.0',
    ],
    python_requires='>=3.9',
)


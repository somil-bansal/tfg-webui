from setuptools import setup, find_packages

setup(
    name="open-webui",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "python-multipart>=0.0.5",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "aiohttp>=3.8.0",
        "aiocache>=0.12.0",
        "alembic>=1.7.0",
        "sqlalchemy>=1.4.0",
        "pydantic>=1.8.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0",
        "watchfiles>=0.18.0",
    ],
    python_requires=">=3.8",
) 
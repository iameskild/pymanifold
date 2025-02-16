# pymanifold

> Warning: this is an experimental project.

The goal of this repo is to take the manifold.markets API and autogenerate a set of Pydantic models for each of the publicly available endpoints. However in the meantime, interactions with the API can be performed using the `Session` object.

Because the Manifold Markets API is still in alpha, this was the simpliest way interface I could come up with that didn't require maintaining a one-to-one mapping between the API and Python-specific objects. Under the hood, I am pulling the API schema and other information directly from the Manifold GitHub repo (see `scripts/make_models.py` for more details) so if their API gets an update, all I need to do I regenerate the models.

> pymanifold already exists on PyPI so a new name is likely needed.

## Getting started

1. Create an API key from the Manifold Markets site under account settings.

```bash
cp .env.example .env
```
Add your API key to the newly created `.env` file.

2. Install this package.

```bash
pip install .
```

> This will build the package and generate the models and `endpoints.json` file.

3. To interact with the API, please use the `Session` object.

```python
from pymanifold import Session

user = Session("/user/[username]")

response = user.execute({"username": "iameskild"})
```

> See `example.ipynb` for more details.

## License

This project is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

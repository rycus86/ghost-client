# Unofficial Ghost API client

[![Travis](https://img.shields.io/travis/rycus86/ghost-client.svg)](https://travis-ci.org/rycus86/ghost-client)
[![PyPI](https://img.shields.io/pypi/v/ghost-client.svg)](https://pypi.python.org/pypi/ghost-client)
[![PyPI](https://img.shields.io/pypi/pyversions/ghost-client.svg)](https://pypi.python.org/pypi/ghost-client)
[![Coverage Status](https://coveralls.io/repos/github/rycus86/ghost-client/badge.svg?branch=master)](https://coveralls.io/github/rycus86/ghost-client?branch=master)
[![Maintainability](https://api.codeclimate.com/v1/badges/45f2a5020caa37777f5a/maintainability)](https://codeclimate.com/github/rycus86/ghost-client/maintainability)

This is a client library for the [Ghost blogging platform API](https://api.ghost.org).

## Installation

```shell
$ pip install ghost-client
```

## Usage

See [https://api.ghost.org](https://api.ghost.org/) for documentation on the REST endpoints and available fields and parameters.

```python
from ghost_client import Ghost

# to read the client ID and secret from the database
ghost = Ghost.from_sqlite(
    '/var/lib/ghost/content/data/ghost.db',
    'http://localhost:2368'
)

# or to use a specific client ID and secret
ghost = Ghost(
    'http://localhost:2368',
    client_id='ghost-admin', client_secret='secret_key'
)

# log in
ghost.login('username', 'password')

# print the server's version
print(ghost.version)

# create a new tag
tag = ghost.tags.create(name='API sample')

# create a new post using it
post = ghost.posts.create(
    title='Example post', slug='custom-slug',
    markdown='',  # yes, even on v1.+
    custom_excerpt='An example post created from Python',
    tags=[tag]
)

# list posts, tags and users
posts = ghost.posts.list(
    status='all',
    fields=('id', 'title', 'slug'),
    formats=('html', 'mobiledoc', 'plaintext'),
)
tags = ghost.tags.list(fields='name', limit='all')
users = ghost.users.list(include='count.posts')

# use pagination
while posts:
    for post in posts:
        print(post)
        posts = posts.next_page()

print(posts.total)
print(posts.pages)

# update a post & tag
updated_post = ghost.posts.update(post.id, title='Updated title')
updated_tag = ghost.tags.update(tag.id, name='Updated tag')

# note: creating, updating and deleting a user is not allowed by the API

# access fields as properties
print(post.title)
print(post.markdown)     # needs formats='mobiledoc'
print(post.author.name)  # needs include='author'

# delete a post & tag
ghost.posts.delete(post.id)
ghost.tags.delete(tag.id)

# upload an image
ghost.upload(file_obj=open('sample.png', 'rb'))
ghost.upload(file_path='/path/to/image.jpeg', 'rb')
ghost.upload(name='image.gif', data=open('local.gif', 'rb').read())

# log out
ghost.logout()
```

The logged in credentials will be saved in memory and on HTTP 401 errors the client will attempt to re-authenticate once automatically.

Responses are wrapped in `models.ModelList` and `models.Model` types to allow pagination and retrieving fields as properties.

## License

MIT

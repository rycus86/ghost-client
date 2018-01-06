import json

from .errors import GhostException


class Model(dict):
    """
    Wrapper around the response objects
    to allow accessing fields as properties.
    """

    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value


class Post(Model):
    """
    Model for posts.
    Allows getting Markdown content through the
    `markdown` property (both on v0.+ and v1.+ servers).
    """

    def __getattr__(self, item):
        if item == 'markdown':
            return self._get_markdown()

        elif item == 'tags' and 'tags' in self:
            return list(map(Model, self['tags']))

        elif item == 'author':
            return Model(self['author'])

        else:
            return super(Post, self).__getattr__(item)

    def _get_markdown(self):
        if 'markdown' in self:
            return self['markdown']

        if self.mobiledoc:
            doc = json.loads(self.mobiledoc)
            return doc['cards'][0][1]['markdown']


class ModelList(list):
    """
    Wrapper around lists returned by the API.
    Exposes methods related to pagination and
    wraps each item in their respective model type.
    """

    def __init__(self, data, type_name, controller, list_kwargs, model_type=Model):
        """
        Enhances a regular list.

        :param data: The original iterable
        :param type_name: The name of the type as the API knows it
        :param controller: The controller that returned the list
        :param list_kwargs: Parameters to use when fetching pages from the API
        :param model_type: The model type of the items
        """

        super(ModelList, self).__init__(map(model_type, data[type_name]))
        self.meta = data['meta']['pagination']
        self._controller = controller
        self._list_kwargs = list_kwargs

    @property
    def total(self):
        """
        :return: The total number of results available for the query
        """

        return self.meta['total']

    @property
    def pages(self):
        """
        :return: The number of pages available for the query
        """

        return self.meta['pages']

    @property
    def limit(self):
        """
        :return: The limit used for queries
        """

        return self.meta['limit']

    def next_page(self):
        """
        :return: The next page fetched from the API for the query
        """

        return self.get_page(self.meta['next'])

    def prev_page(self):
        """
        :return: The previous page fetched from the API for the query
        """

        return self.get_page(self.meta['prev'])

    def get_page(self, page_number):
        """
        :param page_number: The page number to fetch (1-indexed)
        :return: The requested page fetched from the API for the query
        """

        if page_number:
            kwargs = dict(self._list_kwargs)
            kwargs['limit'] = self.limit
            kwargs['page'] = page_number

            return self._controller.list(**kwargs)


class Controller(object):
    """
    The API controller dealing with requests for a specific type.
    """

    def __init__(self, ghost, type_name, model_type=Model):
        """
        Initializes a new controller.

        :param ghost: An instance of the API client
        :param type_name: The type name as the API knows it
        :param model_type: The model type to wrap response items as
        """

        self.ghost = ghost
        self._type_name = type_name
        self._model_type = model_type

    def list(self, **kwargs):
        """
        Fetch a list of resources from the API.

        :param kwargs: Parameters for the request
            (see from and below https://api.ghost.org/docs/limit)
        :return: The list of items returned by the API
            wrapped as `Model` objects with pagination by `ModelList`
        """

        return ModelList(
            self.ghost.execute_get('%s/' % self._type_name, **kwargs),
            self._type_name, self, kwargs, model_type=self._model_type
        )

    def get(self, id=None, slug=None, **kwargs):
        """
        Fetch a resource from the API.
        Either the `id` or the `slug` has to be present.

        :param id: The ID of the resource
        :param slug: The slug of the resource
        :param kwargs: Parameters for the request
            (see from and below https://api.ghost.org/docs/limit)
        :return: The item returned by the API
            wrapped as a `Model` object
        """

        if id:
            items = self.ghost.execute_get('%s/%s/' % (self._type_name, id), **kwargs)

        elif slug:
            items = self.ghost.execute_get('%s/slug/%s/' % (self._type_name, slug), **kwargs)

        else:
            raise GhostException(
                500, 'Either the ID or the Slug of the resource needs to be specified'
            )

        return self._model_type(items[self._type_name][0])

    def create(self, **kwargs):
        """
        Creates a new resource.

        :param kwargs: The properties of the resource
        :return: The created item returned by the API
            wrapped as a `Model` object
        """

        response = self.ghost.execute_post('%s/' % self._type_name, json={
            self._type_name: [
                kwargs
            ]
        })

        return self._model_type(response.get(self._type_name)[0])

    def update(self, id, **kwargs):
        """
        Updates an existing resource.

        :param id: The ID of the resource
        :param kwargs: The properties of the resource to change
        :return: The updated item returned by the API
            wrapped as a `Model` object
        """

        response = self.ghost.execute_put('%s/%s/' % (self._type_name, id), json={
            self._type_name: [
                kwargs
            ]
        })

        return self._model_type(response.get(self._type_name)[0])

    def delete(self, id):
        """
        Deletes an existing resource.
        Does not return anything but raises an exception when failed.

        :param id: The ID of the resource
        """

        self.ghost.execute_delete('%s/%s/' % (self._type_name, id))


class PostController(Controller):
    """
    Controller extension for managing posts.
    """

    def __init__(self, ghost):
        """
        Initialize a new controller for posts.

        :param ghost: An instance of the API client
        """

        super(PostController, self).__init__(ghost, 'posts', model_type=Post)

    def create(self, **kwargs):
        """
        Creates a new post.
        When the `markdown` property is present, it will be
        automatically converted to `mobiledoc` on v1.+ of the server.

        :param kwargs: The properties of the post
        :return: The created `Post` object
        """

        return super(PostController, self).create(**self._with_markdown(kwargs))

    def update(self, id, **kwargs):
        """
        Updates an existing post.
        When the `markdown` property is present, it will be
        automatically converted to `mobiledoc` on v1.+ of the server.

        :param id: The ID of the existing post
        :param kwargs: The properties of the post to change
        :return: The updated `Post` object
        """

        return super(PostController, self).update(id, **self._with_markdown(kwargs))

    def _with_markdown(self, kwargs):
        markdown = kwargs.pop('markdown', None)

        if markdown:
            if self.ghost.version.startswith('0'):
                # put it back as is for version 0.x
                kwargs['markdown'] = markdown

            else:
                updated = dict(kwargs)
                updated['mobiledoc'] = json.dumps({
                    "version": "0.3.1", "markups": [], "atoms": [],
                    "cards": [["card-markdown", {"cardName": "card-markdown", "markdown": markdown}]],
                    "sections": [[10, 0]]})
                return updated

        return kwargs

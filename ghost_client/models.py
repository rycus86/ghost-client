import json


class Model(dict):
    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value


class Post(Model):
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
    def __init__(self, data, type_name, controller, list_kwargs, model_type=Model):
        super(ModelList, self).__init__(map(model_type, data[type_name]))
        self.meta = data['meta']['pagination']
        self._controller = controller
        self._list_kwargs = list_kwargs

    @property
    def total(self):
        return self.meta['total']

    @property
    def pages(self):
        return self.meta['pages']

    @property
    def limit(self):
        return self.meta['limit']

    def next_page(self):
        return self.get_page(self.meta['next'])

    def prev_page(self):
        return self.get_page(self.meta['prev'])

    def get_page(self, page_number):
        if page_number:
            kwargs = dict(self._list_kwargs)
            kwargs['limit'] = self.limit
            kwargs['page'] = page_number

            return self._controller.list(**kwargs)


class Controller(object):
    def __init__(self, ghost, type_name, model_type=Model):
        self.ghost = ghost
        self._type_name = type_name
        self._model_type = model_type

    def list(self, **kwargs):
        return ModelList(
            self.ghost.execute_get('%s/' % self._type_name, **kwargs),
            self._type_name, self, kwargs, model_type=self._model_type
        )

    def get(self, id=None, slug=None, **kwargs):
        if id:
            items = self.ghost.execute_get('%s/%s/' % (self._type_name, id), **kwargs)

        elif slug:
            items = self.ghost.execute_get('%s/slug/%s/' % (self._type_name, slug), **kwargs)

        return self._model_type(items[self._type_name][0])

    def create(self, **kwargs):
        response = self.ghost.execute_post('%s/' % self._type_name, json={
            self._type_name: [
                kwargs
            ]
        })

        return self._model_type(response.get(self._type_name)[0])

    def update(self, id, **kwargs):
        response = self.ghost.execute_put('%s/%s/' % (self._type_name, id), json={
            self._type_name: [
                kwargs
            ]
        })

        return self._model_type(response.get(self._type_name)[0])

    def delete(self, id):
        return self.ghost.execute_delete('%s/%s/' % (self._type_name, id))


class PostController(Controller):
    def __init__(self, ghost):
        super(PostController, self).__init__(ghost, 'posts', model_type=Post)

    def create(self, **kwargs):
        return super(PostController, self).create(**self._with_markdown(kwargs))

    def update(self, id, **kwargs):
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

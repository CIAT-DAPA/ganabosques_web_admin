"""Utilidades compartidas para simular MongoEngine sin conexión a base de datos."""

class FakeQuerySet:
    """Emula el QuerySet de MongoEngine para pruebas unitarias.

    Los métodos encadenables (filter, order_by, skip, limit, select_related,
    only) devuelven el mismo objeto, de modo que las rutas pueden encadenarlos
    libremente. Las llamadas recibidas quedan registradas para poder afirmar
    sobre ellas.
    """

    def __init__(self, items=None):
        self.items = list(items or [])
        self.filter_calls = []
        self.order_by_calls = []
        self.skip_calls = []
        self.limit_calls = []
        self.deleted = False

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def first(self):
        return self.items[0] if self.items else None

    def count(self):
        return len(self.items)

    def filter(self, *args, **kwargs):
        self.filter_calls.append((args, kwargs))
        return self

    def order_by(self, *args):
        self.order_by_calls.append(args)
        return self

    def skip(self, number):
        self.skip_calls.append(number)
        return self

    def limit(self, number):
        self.limit_calls.append(number)
        return self

    def select_related(self, *args, **kwargs):
        return self

    def only(self, *args):
        return self

    def delete(self):
        self.deleted = True
        return len(self.items)

    def get(self, *args, **kwargs):
        if not self.items:
            raise LookupError("Documento no encontrado")
        return self.items[0]


class FakeObjectsManager:
    """Emula el atributo ``objects`` de un Document de MongoEngine.

    Se puede invocar como función (``Adm1.objects(ext_id='1')``) y también
    usar como objeto con métodos (``Adm1.objects.only('ext_id')``), que es
    como lo utilizan las rutas del proyecto.
    """

    def __init__(self, queryset=None):
        self.queryset = queryset if queryset is not None else FakeQuerySet()
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.queryset

    def __iter__(self):
        return iter(self.queryset)

    def only(self, *args):
        return self.queryset.only(*args)

    def order_by(self, *args):
        return self.queryset.order_by(*args)

    def filter(self, *args, **kwargs):
        return self.queryset.filter(*args, **kwargs)

    def count(self):
        return self.queryset.count()

    def first(self):
        return self.queryset.first()

    def get(self, *args, **kwargs):
        return self.queryset.get(*args, **kwargs)


def make_document_stub(items=None, save_side_effect=None):
    """Crea un doble de un Document de MongoEngine.

    Devuelve una clase cuyas instancias registran los kwargs recibidos y las
    llamadas a ``save()``; el atributo de clase ``objects`` se comporta como
    el manager de MongoEngine sobre ``items``.
    """

    class DocumentStub:
        objects = FakeObjectsManager(FakeQuerySet(items))
        created = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            for key, value in kwargs.items():
                setattr(self, key, value)
            DocumentStub.created.append(self)

        def save(self):
            if save_side_effect is not None:
                raise save_side_effect
            self.saved = True
            return self

        def delete(self):
            self.deleted = True
            return self

    DocumentStub.created = []
    return DocumentStub



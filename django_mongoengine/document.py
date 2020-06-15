from django.db.models import Model
from django.db.models.base import ModelState
from mongoengine import document as me, ValidationError
from mongoengine.base import metaclasses as mtc, NON_FIELD_ERRORS

from .forms.document_options import DocumentMetaWrapper
from .queryset import QuerySetManager
from .utils.patches import serializable_value


def django_meta(meta, *top_bases):
    class metaclass(meta):
        def __new__(cls, name, bases, attrs):
            change_bases = len(bases) == 1 and (
                    bases[0].__name__ == "temporary_meta"
            )
            if change_bases:
                new_bases = top_bases
            else:
                new_bases = ()
                for b in bases:
                    if getattr(b, 'swap_base', False):
                        new_bases += top_bases
                    else:
                        new_bases += (b,)
            new_cls = meta.__new__(cls, name, new_bases, attrs)
            new_cls._meta = DocumentMetaWrapper(new_cls)
            return new_cls

    return type.__new__(metaclass, 'temporary_meta', (), {})


class DjangoFlavor(object):
    objects = QuerySetManager()
    _default_manager = QuerySetManager()
    serializable_value = serializable_value
    _get_pk_val = Model.__dict__["_get_pk_val"]

    def __init__(self, *args, **kwargs):
        self._state = ModelState()
        self._state.db = self._meta.get("db_alias", me.DEFAULT_CONNECTION_NAME)
        super(DjangoFlavor, self).__init__(*args, **kwargs)

    def _get_unique_checks(self, exclude=None):
        # XXX: source: django/db/models/base.py
        # used in modelform validation
        unique_checks, date_checks = [], []
        return unique_checks, date_checks

    def full_clean(self, exclude=None, validate_unique=True):
        """
        Call clean_fields(), clean(), and validate_unique() on the model.
        Raise a ValidationError for any errors that occur.
        """
        errors = {}
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)

        try:
            self.clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Form.clean() is run even if other validation fails, so do the
        # same with Model.clean() for consistency.
        try:
            self.clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Run unique checks, but only for fields that passed validation.
        if validate_unique:
            for name in errors:
                if name != NON_FIELD_ERRORS and name not in exclude:
                    exclude.append(name)
            try:
                self.validate_unique(exclude=exclude)
            except ValidationError as e:
                errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean_fields(self, exclude=None):
        """
        Clean all fields and raise a ValidationError containing a dict
        of all validation errors if any occur.
        """
        if exclude is None:
            exclude = []

        errors = {}
        for f in self._meta.fields:
            if f.name in exclude:
                continue
            # Skip validation for empty fields with blank=True. The developer
            # is responsible for making sure they have a valid value.
            raw_value = getattr(self, f.attname)
            if f.blank and raw_value in f.empty_values:
                continue
            try:
                setattr(self, f.attname, f.clean(raw_value))
            except ValidationError as e:
                errors[f.name] = e.error_list

        if errors:
            raise ValidationError(errors)

    def validate_unique(self, exclude=None):
        ''' skip this validation as it is handled by mongonegine'''
        pass


class Document(django_meta(mtc.TopLevelDocumentMetaclass,
                           DjangoFlavor, me.Document)):
    swap_base = True


class DynamicDocument(django_meta(mtc.TopLevelDocumentMetaclass,
                                  DjangoFlavor, me.DynamicDocument)):
    swap_base = True


class EmbeddedDocument(django_meta(mtc.DocumentMetaclass,
                                   DjangoFlavor, me.EmbeddedDocument)):
    swap_base = True


class DynamicEmbeddedDocument(django_meta(mtc.DocumentMetaclass,
                                          DjangoFlavor, me.DynamicEmbeddedDocument)):
    swap_base = True

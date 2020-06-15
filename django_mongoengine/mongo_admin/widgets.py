from django.contrib.admin.widgets import RelatedFieldWidgetWrapper


class MongoRelatedFieldWidgetWrapper(RelatedFieldWidgetWrapper):
    def get_context(self, name, value, attrs):
        from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
        rel_opts = self.rel.model._meta
        info = (rel_opts.app_label, rel_opts.model_name)
        self.widget.choices = self.choices
        url_params = '&'.join("%s=%s" % param for param in [
            (TO_FIELD_VAR, self.rel.field_name),
            (IS_POPUP_VAR, 1),
        ])
        context = {
            'rendered_widget': self.widget.render(name, value, attrs),
            'is_hidden': self.is_hidden,
            'name': name,
            'url_params': url_params,
            'model': rel_opts.verbose_name,
            'can_add_related': self.can_add_related,
            'can_change_related': self.can_change_related,
            'can_delete_related': self.can_delete_related,
            'can_view_related': self.can_view_related,
        }
        if self.can_add_related:
            context['add_related_url'] = self.get_related_url(info, 'add')
        if self.can_delete_related:
            context['delete_related_template_url'] = self.get_related_url(info, 'delete', '__fk__')
        if self.can_view_related or self.can_change_related:
            context['change_related_template_url'] = self.get_related_url(info, 'change', '__fk__')
        return context

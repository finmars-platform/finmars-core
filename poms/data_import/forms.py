# from django import forms
# from .models import DataImport, DataImportSchema
# from django.contrib.contenttypes.models import ContentType
#
# from django import forms
#
# class ListTextWidget(forms.TextInput):
#     def __init__(self, data_list, name, *args, **kwargs):
#         super(ListTextWidget, self).__init__(*args, **kwargs)
#         self._name = name
#         self._list = data_list
#         self.attrs.update({'list':'list__%s' % self._name})
#
#     def render(self, name, value, attrs=None):
#         text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
#         data_list = '<datalist id="list__%s">' % self._name
#         for item in self._list:
#             data_list += '<option value="%s">' % item
#         data_list += '</datalist>'
#
#         return (text_html + data_list)
#
#
# class DataImportForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(DataImportForm, self).__init__(*args, **kwargs)
#         self.fields['master_user'].widget = forms.HiddenInput()
#
#     class Meta:
#         model = DataImport
#         fields = ['file', 'master_user']
#
#
# class DataImportSchemaForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(DataImportSchemaForm, self).__init__(*args, **kwargs)
#         self.fields['model'].queryset = ContentType.objects.filter(model__in=['portfolio'])
#
#     class Meta:
#         model = DataImportSchema
#         fields = ['model',]

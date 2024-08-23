import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from poms.common.admin import AbstractModelAdmin
from poms.history.models import HistoricalRecord


class HistoricalRecordAdmin(AbstractModelAdmin):
    model = HistoricalRecord
    list_display = ['id', 'created_at', 'member', 'action', 'user_code', 'content_type', 'notes']
    list_select_related = ['master_user', 'content_type']
    search_fields = ['id', 'created_at', 'user_code', 'content_type']
    raw_id_fields = ['master_user', 'member', 'content_type']

    readonly_fields = ['id', 'master_user', 'member', 'created_at', 'user_code', 'content_type', 'data_pretty']
    exclude = ['json_data']

    def data_pretty(self, instance):
        """Function to display pretty version of our data"""

        # Convert the data to sorted, indented JSON
        response = json.dumps(instance.data, sort_keys=True, indent=2)

        # Truncate the data. Alter as needed
        response = response[:5000]

        # Get the Pygments formatter
        formatter = HtmlFormatter(style='colorful')

        # Highlight the data
        response = highlight(response, JsonLexer(), formatter)

        # Get the stylesheet
        style = "<style>" + formatter.get_style_defs() + "</style><br>"

        # Safe the output
        return mark_safe(style + response)


admin.site.register(HistoricalRecord, HistoricalRecordAdmin)

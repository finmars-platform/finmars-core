from modeltranslation.translator import TranslationOptions


class AbstractClassModelOptions(TranslationOptions):
    fields = [
        "name",
        "description",
    ]

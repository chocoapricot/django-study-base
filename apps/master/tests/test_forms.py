from django.test import TestCase
from django import forms
from apps.master.models import UserParameter
from apps.master.forms import UserParameterForm

class UserParameterFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create UserParameter instances for testing different formats
        cls.param_text = UserParameter.objects.create(
            key='TEST_TEXT_PARAM',
            target_item='Test Text Param',
            format='text',
            value='Hello World'
        )
        cls.param_boolean = UserParameter.objects.create(
            key='TEST_BOOLEAN_PARAM',
            target_item='Test Boolean Param',
            format='boolean',
            value='true'
        )
        cls.param_number = UserParameter.objects.create(
            key='TEST_NUMBER_PARAM',
            target_item='Test Number Param',
            format='number',
            value='123'
        )
        cls.param_textarea = UserParameter.objects.create(
            key='TEST_TEXTAREA_PARAM',
            target_item='Test Textarea Param',
            format='textarea',  # Assuming a format that defaults to Textarea
            value='This is a long text.'
        )

    def test_widget_is_textinput_for_text_format(self):
        """
        Tests that the widget for the 'value' field is TextInput when format is 'text'.
        """
        form = UserParameterForm(instance=self.param_text)
        widget = form.fields['value'].widget
        self.assertIsInstance(widget, forms.TextInput, "The widget should be a TextInput for text format.")
        self.assertNotIsInstance(widget, forms.Textarea, "The widget should not be a Textarea for text format.")

    def test_widget_is_radioselect_for_boolean_format(self):
        """
        Tests that the widget for the 'value' field is RadioSelect when format is 'boolean'.
        """
        form = UserParameterForm(instance=self.param_boolean)
        widget = form.fields['value'].widget
        self.assertEqual(widget.__class__.__name__, 'MyRadioSelect', "The widget should be MyRadioSelect for boolean format.")

    def test_widget_is_numberinput_for_number_format(self):
        """
        Tests that the widget for the 'value' field is NumberInput when format is 'number'.
        """
        form = UserParameterForm(instance=self.param_number)
        widget = form.fields['value'].widget
        self.assertIsInstance(widget, forms.NumberInput, "The widget should be a NumberInput for number format.")

    def test_widget_is_textarea_for_default_format(self):
        """
        Tests that the widget for the 'value' field is Textarea for any other format.
        """
        form = UserParameterForm(instance=self.param_textarea)
        widget = form.fields['value'].widget
        self.assertIsInstance(widget, forms.Textarea, "The widget should be a Textarea for the default format.")

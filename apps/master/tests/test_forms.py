from django.test import TestCase
from django import forms
from apps.master.models import UserParameter
from apps.master.forms import UserParameterForm
from apps.common.forms import ColorInput

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

    def test_choice_format_field(self):
        """
        Tests the behavior of the 'value' field when format is 'choice'.
        """
        param_choice = UserParameter.objects.create(
            key='TEST_CHOICE_PARAM',
            target_item='Test Choice Param',
            format='choice',
            value='option1',
            choices='option1: Option 1, option2: Option 2'
        )

        # Test widget type
        form = UserParameterForm(instance=param_choice)
        field = form.fields['value']
        self.assertIsInstance(field, forms.ChoiceField, "The field should be a ChoiceField for choice format.")

        # Test choices are correctly parsed
        expected_choices = [('option1', 'Option 1'), ('option2', 'Option 2')]
        self.assertEqual(list(field.choices), expected_choices, "The choices are not parsed correctly.")

        # Test valid data
        form_data = {
            'target_item': param_choice.target_item,
            'format': param_choice.format,
            'value': 'option2',
            'choices': param_choice.choices,
        }
        form = UserParameterForm(instance=param_choice, data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid with a valid choice. Errors: {form.errors}")

        # Test invalid data
        form_data['value'] = 'invalid_option'
        form = UserParameterForm(instance=param_choice, data=form_data)
        self.assertFalse(form.is_valid(), "Form should be invalid with an invalid choice.")
        self.assertIn('value', form.errors, "There should be an error on the 'value' field.")

    def test_widget_is_colorinput_for_color_format(self):
        """
        Tests that the widget for the 'value' field is a TextInput with type 'color' when format is 'color'.
        """
        param_color = UserParameter.objects.create(
            key='TEST_COLOR_PARAM',
            target_item='Test Color Param',
            format='color',
            value='#ff0000'
        )
        form = UserParameterForm(instance=param_color)
        widget = form.fields['value'].widget
        self.assertIsInstance(widget, ColorInput, "The widget should be a ColorInput for color format.")
        self.assertEqual(widget.input_type, 'color', "The widget's input_type attribute should be 'color'.")

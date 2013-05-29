# -*- encoding: utf-8 -*-

from django.utils.safestring import mark_safe
from django.conf import settings
from django.forms.util import ValidationError
from django.utils.translation import ugettext as _
from django.utils.datastructures import SortedDict

from . import *

ENABLE_DOJANGO = False

if 'dojango' in settings.INSTALLED_APPS:
    ENABLE_DOJANGO = True

    from dojango.forms.widgets import TextInput
    from dojango.forms import Field

else:
    from django.forms.widgets import TextInput
    from django.forms import Field


format_desc = SortedDict([
    #('Y', 'years'),
    #('m', 'months'),
    ('D', 'days'),
    ('H', 'hours'),
    ('M', 'minutes'),
    ('S', 'seconds'),
    ('X', 'microseconds')])

if HAVE_RELATIVEDELTA:
    format_desc.insert(0, 'Y', 'years')
    format_desc.insert(1, 'm', 'months')

def check_format(format):
    for letter in format:
        if letter not in format_desc:
            raise ValueError("Format letter '%s' unknown" % letter)


class IntervalWidget(TextInput):
    class Media:
        css = {
            'all': ('interval.css', ),
        }

    def __init__(self, format='DHMSX', *args, **kw):
        TextInput.__init__(self, *args, **kw)
        self.format = format
        check_format(self.format)

    def render(self, name, value, attrs=None):
        if value is None:
            value = dict(days=0, hours=0, minutes=0, seconds=0, microseconds=0)
            if HAVE_RELATIVEDELTA:
                value['years'] = 0
                value['months'] = 0

        if is_delta(value):
            if HAVE_RELATIVEDELTA:
                years = value.years
                months = value.months
                days = value.days
                hours = value.hours
                minutes = value.minutes
                seconds = value.seconds

                value = dict(years=value.years, months=value.months,
                        days=value.days, hours=value.hours, minutes=value.minutes,
                        seconds=value.seconds, microseconds=value.microseconds)
            else:
                days = value.days
                seconds = value.seconds
                microseconds = value.microseconds
                hours = minutes = 0

                if 'H' in self.format:
                    hours = int(seconds / 3600)
                    seconds = int(seconds - hours * 3600)

                if 'M' in self.format:
                    minutes = int(seconds / 60)
                    seconds = int(seconds - minutes * 60)

                microseconds = value.microseconds

                value = dict(days=days, hours=hours, minutes=minutes,
                         seconds=seconds, microseconds=microseconds)

        attrs = self.build_attrs(attrs)

        ret = []
        para = dict(
            name=name, dojoType='', years_label=_('years'),
            months_label=_('months'), days_label=_('days'),
            hours_label=_('hours'), minutes_label=_('minutes'),
            seconds_label=_('seconds'), microseconds_label=_('microseconds'))
        para.update(value)

        if ENABLE_DOJANGO:
            para['dojoType'] = 'dojoType="dijit.form.NumberTextBox"'

        def _append(subfield):
            ret.append(
                '''<input type="text"
                value="%%(%(subfield)s)s"
                id="%%(name)s_%(subfield)s"
                name="%%(name)s_%(subfield)s"
                class="interval_field interval_%(subfield)s_field"
                %%(dojoType)s
                />
                <label
                for="%%(name)s_%(subfield)s"
                class="interval_label %%(name)s_%(subfield)s_label"
                > 
                %%(%(subfield)s_label)s
                </label>''' % dict(subfield=subfield))

        for letter, value in format_desc.items():
            if letter in self.format:
                _append(value)

        return mark_safe("".join(ret) % para)

    def value_from_datadict(self, data, files, name):
        kw = dict()

        # We get many data in the request: field_name_days, field_name_minutes,
        # and so on. It depends on what is the letter in self.format variable:
        # D(ays), H(ours), M(inutes), S(econds), X(microseconds):

        for letter, desc in format_desc.items():
            if letter not in self.format:
                continue

            # If this value is in self.format AND the user entered this value
            # we will use it:
            try:
                kw[desc] = int(data.get(name + "_" + desc))
            except (TypeError, KeyError, ValueError):
                kw[desc] = data.get(name + "_" + desc)
                kw['BAD'] = desc

        return kw  # timedelta(**kw)


class IntervalFormField(Field):

    widget = IntervalWidget
    dojo_type = 'dijit.form.NumberTextBox'

    def __init__(
        self, format='DHMSX', min_value=None, max_value=None, *args, **kw):
        Field.__init__(self, *args, **kw)
        self.format = format
        self.min_value = min_value
        self.max_value = max_value
        self.widget = IntervalWidget(format)

    def clean(self, value):

        kw = dict(days=0, hours=0, minutes=0, seconds=0, microseconds=0)

        if HAVE_RELATIVEDELTA:
            kw['years'] = 0
            kw['months'] = 0

        for letter, desc in format_desc.items():

            if letter not in self.format:
                continue

            def raiseError(fieldName):
                raise ValidationError(
                    _("Bad value in ''%s'' subfield.") % _(fieldName))

            if 'BAD' in value:
                raiseError(value['BAD'])

            try:
                kw[desc] = int(value[desc])
            except ValueError:
                raiseError(desc)

        try:
            if HAVE_RELATIVEDELTA:
                cleaned_value = relativedelta(**kw)
            else:
                cleaned_value = timedelta(**kw)

        except OverflowError:
            raise ValidationError(_("This value is too large"))

        if cleaned_value is not None:
            if self.min_value is not None:
                if cleaned_value < self.min_value:
                    raise ValidationError(
                    _("This interval must be at least: %s") % self.min_value)

            if self.max_value is not None:
                if cleaned_value > self.max_value:
                    raise ValidationError(
                        _("This interval must be no more than: %s"
                          ) % self.max_value)

        if self.required:
            if (cleaned_value == timedelta(0)) or (HAVE_RELATIVEDELTA and cleaned_value == relativedelta(0)):
                raise ValidationError(self.default_error_messages['required'])

        return Field.clean(self, cleaned_value)

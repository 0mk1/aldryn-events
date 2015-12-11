import datetime

from django.utils import timezone
from django.utils.dates import MONTHS
from django.utils.translation import (
    ugettext_lazy as _, get_language_from_request
)
try:
    from django.contrib.sites.shortcuts import get_current_site
except ImportError:
    # Django 1.6
    from django.contrib.sites.models import get_current_site

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .utils import (
    build_calendar, is_valid_namespace_for_language,
    get_valid_languages,
)
from .models import (
    UpcomingPluginItem, Event, EventListPlugin, EventCalendarPlugin
)

from .forms import (
    UpcomingPluginForm, EventListPluginForm, EventCalendarPluginForm,
)


NO_APPHOOK_ERROR_MESSAGE = _(
    'There is an error in plugin configuration: selected Events '
    'config is not available. Please switch to edit mode and '
    'change plugin app_config settings to use valid config. '
    'Also note that aldryn-events should be used at least once '
    'as an apphook for that config.')


class NameSpaceCheckMixin(object):

    def get_namespace(self, instance):
        if instance.app_config_id and instance.app_config.namespace:
            return instance.app_config.namespace
        return ''

    def get_language(self, request):
        return get_language_from_request(request, check_path=True)

    def render(self, context, instance, placeholder):
        # translated filter the events, language set current language
        language = self.get_language(context['request'])
        namespace = self.get_namespace(instance)

        # check if we can reverse list view for configured namespace
        # if no prepare a message to admin users.
        if not is_valid_namespace_for_language(namespace,
                                               language_code=language):
            # add message, should be properly handled in template
            context['plugin_configuration_error'] = NO_APPHOOK_ERROR_MESSAGE
        return super(NameSpaceCheckMixin, self).render(
            context, instance, placeholder)


class UpcomingPlugin(NameSpaceCheckMixin, CMSPluginBase):
    render_template = False
    name = _('Upcoming or Past Events')
    module = _('Events')
    model = UpcomingPluginItem
    form = UpcomingPluginForm

    def render(self, context, instance, placeholder):
        self.render_template = (
            'aldryn_events/plugins/upcoming/%s/upcoming.html' % instance.style
        )
        context = super(UpcomingPlugin, self).render(context, instance,
                                                     placeholder)
        if context.get('plugin_configuration_error') is not None:
            return context

        context['instance'] = instance
        language = self.get_language(context['request'])
        namespace = self.get_namespace(instance)
        site_id = getattr(get_current_site(context['request']), 'id', None)
        valid_languages = get_valid_languages(
            namespace, language_code=language, site_id=site_id)
        events = (Event.objects.namespace(namespace)
                               .active_translations(language)
                               .language(language))
        events = events.translated(*valid_languages)
        if instance.past_events:
            events = events.past(count=instance.latest_entries)
        else:
            events = events.upcoming(count=instance.latest_entries)

        context['events'] = events
        return context

plugin_pool.register_plugin(UpcomingPlugin)


class EventListCMSPlugin(NameSpaceCheckMixin, CMSPluginBase):
    render_template = False
    module = _('Events')
    name = _('List')
    model = EventListPlugin
    form = EventListPluginForm

    def render(self, context, instance, placeholder):
        context = super(EventListCMSPlugin, self).render(context, instance,
                                                         placeholder)
        if context.get('plugin_configuration_error') is not None:
            return context
        self.render_template = (
            'aldryn_events/plugins/list/%s/list.html' % instance.style
        )
        language = self.get_language(context['request'])
        namespace = self.get_namespace(instance)
        site_id = getattr(get_current_site(context['request']), 'id', None)
        valid_languages = get_valid_languages(
            namespace, language_code=language, site_id=site_id)
        context['instance'] = instance

        events = (instance.events.namespace(namespace)
                                 .active_translations(language)
                                 .language(language))
        events = events.translated(*valid_languages)
        context['events'] = events
        return context

plugin_pool.register_plugin(EventListCMSPlugin)


class CalendarPlugin(NameSpaceCheckMixin, CMSPluginBase):
    render_template = 'aldryn_events/plugins/calendar.html'
    name = _('Calendar')
    module = _('Events')
    cache = False
    model = EventCalendarPlugin
    form = EventCalendarPluginForm

    def render(self, context, instance, placeholder):
        context = super(CalendarPlugin, self).render(context, instance,
                                                     placeholder)
        if context.get('plugin_configuration_error') is not None:
            return context
        namespace = self.get_namespace(instance)
        language = self.get_language(context['request'])
        site_id = getattr(get_current_site(context['request']), 'id', None)
        year = context.get('event_year')
        month = context.get('event_month')

        if not all([year, month]):
            year = str(timezone.now().date().year)
            month = str(timezone.now().date().month)

        current_date = datetime.date(int(year), int(month), 1)

        context['event_year'] = year
        context['event_month'] = month
        context['days'] = build_calendar(
            year, month, language, namespace, site_id)
        context['current_date'] = current_date
        context['last_month'] = current_date + datetime.timedelta(days=-1)
        context['next_month'] = current_date + datetime.timedelta(days=35)
        context['calendar_label'] = u'%s %s' % (MONTHS.get(int(month)), year)
        context['calendar_namespace'] = namespace
        context['calendar_language'] = language
        return context

plugin_pool.register_plugin(CalendarPlugin)

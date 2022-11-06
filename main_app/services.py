from datetime import date, timedelta, datetime

from django.utils.translation import gettext as _

from spacepython.constraints import (
    С_morning_time, С_morning_time_markup, C_evening_time_markup,
    C_evening_time, C_salary_common, C_salary_high, C_lesson_threshold,
    C_timedelta, C_datedelta
)


def get_weekdays():
    date_choices = []
    weekdays = {
        'Monday': _('Monday'),
        'Tuesday': _('Tuesday'),
        'Wednesday': _('Wednesday'),
        'Thursday': _('Thursday'),
        'Friday': _('Friday'),
        'Saturday': _('Saturday'),
        'Sunday': _('Sunday'),
    }
    for i in range(C_datedelta.days+1):
        if i == 0:
            day = date.today() + timedelta(days=i)
            day_title = (f"{_('Today')}, "
                         f"{datetime.strftime(day, r'%d-%m')}")
            date_choices.append((day, day_title))
            continue
        day = date.today() + timedelta(days=i)
        day_title = (f"{weekdays[day.strftime('%A')]}, "
                     f"{datetime.strftime(day, r'%d-%m')}")
        date_choices.append((day, day_title))

    return date_choices

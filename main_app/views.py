from copy import deepcopy
from datetime import date, timedelta, datetime
import json

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.views.generic import (
    ListView, CreateView, DeleteView, View, TemplateView, DetailView
)
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView

from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Lesson, UserDetail, TimeBlock, User
from .forms import (
    RegisterUserForm, AuthUserForm, AddLessonForm, AddLessonAdminForm,
    TimeBlockerAPForm, StudentUpdateForm
)
from .serializers import (
    UserSerializer, TokenRequestSerializer, ReceivingTokenSerializer,
    LessonSerializer, LessonAdminSerializer, RegistrationSerializer,
    DelUserSerializer, TimeBlockSerializer, TimeBlockAdminSerializer,
    StudentAdminSerializer
)
from spacepython.constraints import (
    С_morning_time, С_morning_time_markup, C_evening_time_markup,
    C_evening_time, C_salary_common, C_salary_high, C_lesson_threshold,
    C_timedelta, C_datedelta
)
from .services import get_weekdays


class LessonView(ListView):
    """ Get relevant lesson list """

    model = Lesson
    template_name = 'main_app/index.html'
    context_object_name = 'lessons'

    def get_queryset(self):
        today = date.today()
        lessons = self.model.objects.filter(
            date__gte=today
        ).select_related(
            'student',
            'student__details'
        )
        lessons = list(lessons)
        blocked_times = TimeBlock.objects.filter(
            date__gte=today,
            date__lte=today + C_datedelta
        )
        blocked_times = list(blocked_times)
        query = {today + timedelta(days=i): [] for i in range(
            C_datedelta.days+1
        )}
        for _ in range(len(lessons) + len(blocked_times)):
            if lessons and blocked_times:
                condition_1 = lessons[0].date < blocked_times[0].date
                condition_2 = (
                    lessons[0].date == blocked_times[0].date and
                    lessons[0].time < blocked_times[0].start_time
                )
                if condition_1 or condition_2:
                    day = lessons[0].date
                    query[day].append(lessons.pop(0))
                else:
                    day = blocked_times[0].date
                    query[day].append(blocked_times.pop(0))
            else:
                exists = lessons or blocked_times
                day = exists[0].date
                query[day].append(exists.pop(0))
        return query


class LessonByUserView(LoginRequiredMixin, ListView):
    """ Get relevant lesson list for every student """

    model = Lesson
    template_name = 'main_app/lessons_by_student.html'
    context_object_name = 'lessons'
    login_url = 'login_url'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect('home_url')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        lessons = self.model.objects.filter(
            date__gte=date.today(),
            student_id=self.request.user.id
        )
        return lessons


class CustomLoginView(TemplateView, FormMixin):
    """Authentication"""

    model = User
    template_name = "main_app/login.html"
    form_class = AuthUserForm
    success_url = reverse_lazy('home_url')

    def get_success_url(self):
        return self.success_url

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home_url')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(request, form)
        else:
            messages.error(
                request,
                _("You can write to me on telegram @spacepython if you can't "
                  "login")
            )
            return self.form_invalid(form)

    def form_valid(self, request, form):
        input_field = form.cleaned_data['field']
        user = self.get_user(input_field)

        if user:
            login(self.request, user)
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(
                request,
                _("You can write to me on telegram @spacepython if you can't "
                  "login")
            )
            return HttpResponseRedirect(reverse_lazy('login_url'))

    def get_user(self, field):
        """ Getting user object by phone or telegram """

        try:
            user = self.model.objects.get(details__phone=field)
        except self.model.DoesNotExist:
            user = None
        except self.model.MultipleObjectsReturned:
            user = self.model.objects.filter(details__phone=field)[0]

        if not user:
            try:
                user = self.model.objects.get(details__telegram=field)
            except self.model.DoesNotExist:
                user = None
            except self.model.MultipleObjectsReturned:
                user = self.model.objects.filter(details__telegram=field)[0]

        return user


class CustomRegistrationView(CreateView):
    """Registration"""

    model = User
    template_name = 'main_app/registration.html'
    success_url = reverse_lazy('home_url')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home_url')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = RegisterUserForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = RegisterUserForm(request.POST)
        if form.is_valid(request, form):
            return self.form_valid(request, form)
        else:
            return redirect('registration_url')

    def form_valid(self, request, form):
        """ Create user and userdetail records and also added
        auto-authentication """

        first_name = form.cleaned_data['first_name']
        phone = form.cleaned_data['phone']
        telegram = form.cleaned_data['telegram']

        if not self.check_unique(request, phone, telegram):
            return redirect('registration_url')

        user = self.create_user(first_name, phone, telegram)
        messages.success(
            request,
            _("Registration completed")
        )

        login(self.request, user)
        return redirect('home_url')

    def create_user(self, first_name, phone, telegram):
        """ Creating new user """

        user = self.model()
        userdetail = UserDetail()

        user.first_name = first_name
        user.username = user.date_joined  # username must be unique
        userdetail.user = user
        userdetail.phone = phone
        userdetail.telegram = telegram

        user.save()
        userdetail.save()
        Token.objects.create(user=user)
        return user

    def check_unique(self, request, phone, telegram):
        """ Phone and telegram must be unique but they may be null """

        fields = UserDetail.objects.values_list('phone', 'telegram')
        phones = {i[0] for i in fields}
        telegrams = {i[1] for i in fields}
        if phone in phones and phone and phone == '89001234567':
            messages.error(
                request,
                _("This phone already exists")
            )
            return False
        elif telegram in telegrams and telegram and telegram == '@nickname':
            messages.error(
                request,
                _("This telegram nickname already exists")
            )
            return False
        return True


class CustomLogOutView(LogoutView):
    """LogOut"""

    next_page = reverse_lazy('home_url')


class AddLessonView(LoginRequiredMixin, CreateView):
    """ Create a new lesson """

    model = Lesson
    template_name = 'main_app/add_lesson.html'
    form_class = AddLessonForm
    success_url = 'home_url'
    login_url = 'login_url'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect('add_lesson_AP_url')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name,
                      self.get_context_data(request))

    def get_context_data(self, request, **kwargs):
        context = {}
        # value existence check can be disabled in the future
        user_detail = UserDetail.objects.get(user_id=request.user.id)
        if user_detail.usual_cost and user_detail.high_cost:
            usual_cost = user_detail.usual_cost
            high_cost = user_detail.high_cost
        else:
            usual_cost = C_salary_common
            high_cost = C_salary_high

        cost_messages = []
        cost_messages.append(_(
                "The cost of a usual lesson is {} ₽"
            ).format(usual_cost)
        )
        cost_messages.append(_(
                "The cost of a lesson in the early morning to {} is {} ₽."
            ).format(С_morning_time_markup.strftime(r'%H:%M'), high_cost)
        )
        cost_messages.append(_(
                "The cost of a lesson in the late evening to {} is {} ₽."
            ).format(C_evening_time_markup.strftime(r'%H:%M'), high_cost)
        )
        cost_messages.append(_(
                "The cost of a lesson when day is full ({} lessons per day) "
                "is {} ₽."
            ).format(C_lesson_threshold - 1, high_cost)
        )
        context['cost_messages'] = cost_messages

        context['C_timedelta'] = C_timedelta.seconds // 3600

        form = self.get_form(self.form_class)
        context['form'] = form
        return context

    def get_form(self, form_class):
        form = super().get_form(form_class)
        date_choices = get_weekdays()
        form.fields['date'].widget.choices = date_choices
        return form

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid(request, form):
            return self.form_valid(request, form)
        else:
            return redirect('add_lesson_url')

    def form_valid(self, request, form):
        time = str(form.cleaned_data['time']).split(':')[0]
        time = datetime.strptime(time, r"%H").time()
        date = datetime.strptime(
            form.cleaned_data['date'],
            r"%Y-%m-%d"
        ).date()

        lesson = self.model()
        lesson.time = time
        lesson.date = date
        lesson.student_id = request.user.pk

        is_morning = С_morning_time <= time < С_morning_time_markup
        is_evening = C_evening_time_markup < time <= C_evening_time
        is_over = len(Lesson.objects.filter(date=date)
                      ) >= C_lesson_threshold - 1
        # value existence check can be disabled in the future
        user_detail = UserDetail.objects.get(user_id=request.user.id)
        if is_morning or is_evening or is_over:
            if user_detail.high_cost:
                lesson.salary = user_detail.high_cost
            else:
                lesson.salary = C_salary_high
        else:
            if user_detail.usual_cost:
                lesson.salary = user_detail.usual_cost
            else:
                lesson.salary = C_salary_common

        lesson.save()

        if lesson.salary == user_detail.high_cost:
            msg = _(
                "Lesson successfully created. Date: {0}. "
                "Time: {1}. Cost: {2} ₽. "
                "Cost is higher because a lot of people "
                "signed up today").format(
                    date.strftime(r'%d-%m-%Y'), time.strftime(r'%H:%M'),
                    lesson.salary
                )
        else:
            msg = _(
                "Lesson successfully created. Date: {0}. "
                "Time: {1}. Cost: {2} ₽").format(
                    date.strftime(r'%d-%m-%Y'), time.strftime(r'%H:%M'),
                    lesson.salary
                )

        messages.success(
            request,
            msg
        )
        return HttpResponseRedirect(reverse_lazy(self.success_url))


class DeleteLessonView(LoginRequiredMixin, DeleteView):
    """ Delete lesson by user """

    model = Lesson
    template_name = 'lesson_by_student_url'

    def get_success_url(self, **kwargs):
        return reverse_lazy('lesson_by_student_url')

    def post(self, request, *args, **kwargs):
        # passes the request to form_valid()
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(request, form)
        else:
            messages.error(
                request,
                _("Error: the lesson wasn't deleted")
            )
            return self.form_invalid(form)

    def form_valid(self, request, form):
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(
            request,
            _("The lesson successfully deleted")
        )
        return HttpResponseRedirect(success_url)


class InfoView(View):
    """ All information about me """

    def get(self, request, *arg, **kwargs):
        context = self.get_context_data()
        return render(request, 'main_app/info.html', context)

    def get_context_data(self, **kwargs):
        context = {}
        context['age'] = self.get_my_age()
        context['C_salary_common'] = C_salary_common
        context['C_salary_high'] = C_salary_high
        context['С_morning_time_markup'] = С_morning_time_markup.strftime(
            '%H:%M')
        context['C_evening_time_markup'] = C_evening_time_markup.strftime(
            '%H:%M')
        context['C_lesson_threshold'] = C_lesson_threshold
        context['C_timedelta'] = C_timedelta.seconds // 3600
        return context

    def get_my_age(self):
        """this function shows my age today"""

        today = date.today()
        birthday = date(year=today.year, month=5, day=18)
        birthdate = date(year=1996, month=8, day=23)

        age = today.year - birthdate.year
        if today >= birthday:
            return age
        else:
            return age - 1


#################################################################
#                        ADMIN PANEL (AP)                       #
#################################################################


class AdminAccessMixin:
    """ Admin access only. Other users go to the homepage """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('home_url')
        return super().dispatch(request, *args, **kwargs)


class SettingsAP(AdminAccessMixin, TemplateView):
    title = _('Settings')
    template_name = 'main_app/management/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = admin_panel
        context['title'] = self.title
        context['С_morning_time'] = С_morning_time
        context['С_morning_time_markup'] = С_morning_time_markup
        context['C_evening_time_markup'] = C_evening_time_markup
        context['C_evening_time'] = C_evening_time
        context['C_salary_common'] = C_salary_common
        context['C_salary_high'] = C_salary_high
        C_timedelta_hours = str(C_timedelta.seconds // 3600)
        C_timedelta_minutes = str(C_timedelta.seconds % 60).ljust(2, '0')
        context['C_timedelta'] = C_timedelta_hours + ':' + C_timedelta_minutes
        context['C_datedelta'] = C_datedelta.days
        context['C_lesson_threshold'] = C_lesson_threshold - 1
        return context


class AddLessonAP(AdminAccessMixin, CreateView):
    """ Create lesson for students by admin """

    model = Lesson
    template_name = 'main_app/management/add_lesson_admin.html'
    form_class = AddLessonAdminForm
    success_url = 'home_url'
    title = _('Add lesson by admin')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = {}

        cost_messages = []
        cost_messages.append(_(
                "The cost of a usual lesson is {} ₽"
            ).format(C_salary_common)
        )
        cost_messages.append(_(
                "The cost of a lesson in the early morning to {} is {} ₽."
            ).format(С_morning_time_markup.strftime(r'%H:%M'), C_salary_high)
        )
        cost_messages.append(_(
                "The cost of a lesson in the late evening to {} is {} ₽."
            ).format(C_evening_time_markup.strftime(r'%H:%M'), C_salary_high)
        )
        cost_messages.append(_(
                "The cost of a lesson when day is full ({} lessons per day) "
                "is {} ₽."
            ).format(C_lesson_threshold - 1, C_salary_high)
        )
        context['cost_messages'] = cost_messages

        context['menu'] = admin_panel
        context['title'] = self.title

        form = self.get_form(self.form_class)
        context['form'] = form
        return context

    def get_form(self, form_class):
        form = super().get_form(form_class)

        student_choices = []
        students = User.objects.filter(
            is_staff=False, is_active=True
        ).select_related('details').order_by('details__alias')
        for student in students:
            if student.details.alias:
                student_choices.append((
                    student.id,
                    f"{student.details.alias} ({student.first_name})"
                ))
            else:
                student_choices.append((
                    student.id,
                    f"{student.first_name}"
                ))
        form.fields['student'].widget.choices = student_choices

        date_choices = get_weekdays()
        form.fields['date'].widget.choices = date_choices

        return form

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid(request, form):
            return self.form_valid(request, form)
        else:
            return redirect('add_lesson_url')

    def form_valid(self, request, form):
        time = str(form.cleaned_data['time']).split(':')[0]
        time = datetime.strptime(time, r"%H").time()
        date = datetime.strptime(
            form.cleaned_data['date'],
            r"%Y-%m-%d"
        ).date()

        lesson = self.model()
        lesson.student_id = form.cleaned_data['student']

        is_morning = С_morning_time <= time < С_morning_time_markup
        is_evening = C_evening_time_markup < time <= C_evening_time
        is_over = len(Lesson.objects.filter(date=date)
                      ) >= C_lesson_threshold - 1
        # value existence check can be disabled in the future
        user_detail = UserDetail.objects.get(
            user_id=form.cleaned_data['student']
        )
        if is_morning or is_evening or is_over:
            if user_detail.high_cost:
                lesson.salary = user_detail.high_cost
            else:
                lesson.salary = C_salary_high
        else:
            if user_detail.usual_cost:
                lesson.salary = user_detail.usual_cost
            else:
                lesson.salary = C_salary_common

        lesson.time = time
        lesson.date = date

        lesson.save()

        if lesson.salary == user_detail.high_cost:
            msg = _(
                "Lesson successfully created. Date: {0}. "
                "Time: {1}. Cost: {2} ₽. "
                "Cost is higher because a lot of people "
                "signed up today").format(
                    date.strftime(r'%d-%m-%Y'), time.strftime(r'%H:%M'),
                    lesson.salary
                )
        else:
            msg = _(
                "Lesson successfully created. Date: {0}. "
                "Time: {1}. Cost: {2} ₽").format(
                    date.strftime(r'%d-%m-%Y'), time.strftime(r'%H:%M'),
                    lesson.salary
                )

        messages.success(
            request,
            msg
        )
        return HttpResponseRedirect(reverse_lazy(self.success_url))


class TimeBlockerAP(AdminAccessMixin, FormMixin, ListView):
    """ Blocks specified time in the admin panel """

    model = TimeBlock
    context_object_name = 'blocked_times'
    title = _('Time blocker')
    template_name = 'main_app/management/time_blocker.html'
    form_class = TimeBlockerAPForm

    def get_queryset(self):
        return self.model.objects.filter(date__gte=date.today())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = admin_panel
        context['title'] = self.title
        form = self.get_form()
        context['form'] = form
        return context

    def get_form(self):
        form = super().get_form()
        date_choices = get_weekdays()
        form.fields['date'].widget.choices = date_choices
        return form

    def post(self, request, *args, **kwargs):
        if request.POST.get('delete block'):
            return self.remove_block(request)
        form = self.form_class(request.POST)
        if form.is_valid(request):
            return self.form_valid(request, form)
        else:
            return redirect(reverse_lazy('time_blocker_AP_url'))

    def remove_block(self, request, *args, **kwargs):
        pk = request.POST.get('delete block')
        self.model.objects.get(pk=pk).delete()
        messages.success(
            request,
            _("Block deleted successfully")
        )
        return redirect(reverse_lazy('time_blocker_AP_url'))

    def form_valid(self, request, form):
        date = form.cleaned_data['date']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        date = datetime.strptime(date, r"%Y-%m-%d").date()
        start_time = datetime.strptime(str(start_time), r"%H").time()
        end_time = datetime.strptime(str(end_time), r"%H").time()

        blocked_time = self.model()
        blocked_time.date = date
        blocked_time.start_time = start_time
        blocked_time.end_time = end_time
        blocked_time.save()

        messages.success(
            request,
            _("Block created successfully")
        )
        return redirect(reverse_lazy('time_blocker_AP_url'))


class StudentsAP(AdminAccessMixin, ListView):
    """ Student list in the admin panel """

    model = User
    context_object_name = 'students'
    title = _('Students')
    template_name = 'main_app/management/students_info.html'

    def get_queryset(self):
        return self.model.objects.filter(
            is_staff=False
        ).select_related('details').order_by('details__alias', 'first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = admin_panel
        context['title'] = self.title
        return context


class StudentDetailAP(AdminAccessMixin, DetailView):
    """ User details in the admin panel """

    model = User
    template_name = 'main_app/management/student_info.html'
    context_object_name = 'user_details'
    form_class = StudentUpdateForm

    def post(self, request, *args, **kwargs):
        if request.POST.get('delete lesson'):
            return self.delete_lesson(request)
        form = self.form_class(request.POST)
        if form.is_valid():
            return self.form_valid(request, form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = admin_panel

        user_pk = self.kwargs.get(self.pk_url_kwarg)
        user = self.model.objects.select_related('details').get(pk=user_pk)
        context['form'] = self.form_class(initial={
            'pk': user.pk,
            'first_name': user.first_name,
            'alias': user.details.alias,
            'usual_cost': user.details.usual_cost,
            'high_cost': user.details.high_cost,
            'phone': user.details.phone,
            'telegram': user.details.telegram,
            'discord': user.details.discord,
            'skype': user.details.skype,
            'last_login': user.last_login,
            'is_active': user.is_active
            })

        context['student_lessons'] = Lesson.objects.filter(
            student_id=user_pk,
            date__gte=date.today()
        )
        context['title'] = StudentsAP.title
        return context

    def form_valid(self, request, form):
        pk = form.cleaned_data['pk']
        user = self.model.objects.select_related('details').get(pk=pk)

        user.first_name = form.cleaned_data['first_name']
        user.details.alias = form.cleaned_data['alias']
        user.details.usual_cost = form.cleaned_data['usual_cost']
        user.details.high_cost = form.cleaned_data['high_cost']
        user.details.phone = form.cleaned_data['phone']
        user.details.telegram = form.cleaned_data['telegram']
        user.details.discord = form.cleaned_data['discord']
        user.details.skype = form.cleaned_data['skype']
        user.is_active = form.cleaned_data['is_active']

        user.details.save()
        user.save()
        messages.success(request, _('User information changed successfully'))
        return redirect(reverse_lazy('student_detail_AP_url',
                                     kwargs={'pk': form.cleaned_data['pk']}))

    def delete_lesson(self, request):
        lesson_id = request.POST.get('delete lesson')
        lesson = Lesson.objects.get(pk=lesson_id)
        lesson.delete()
        messages.success(
            request,
            _("Lesson deleted successfully")
        )
        url_pk = self.kwargs.get(self.pk_url_kwarg)
        return redirect(reverse_lazy('student_detail_AP_url',
                                     kwargs={'pk': url_pk}))


admin_panel = [
    (SettingsAP.title, 'settingAP_url'),
    (AddLessonAP.title, 'add_lesson_AP_url'),
    (TimeBlockerAP.title, 'time_blocker_AP_url'),
    (StudentsAP.title, 'students_AP_url')
]


#################################################################
#                            DRF API                            #
#################################################################


class RegistrationAPI(CreateAPIView):
    """ Registration new users.
    get_serializer(), get_serializer_class(), get_serializer_context()
    uses from GenericAPIView.
    get_success_headers() uses from CreateModelMixin"""

    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        first_name = serializer.data['first_name']
        phone = serializer.data['phone']
        telegram = serializer.data['telegram']

        check = self.check_unique(phone, telegram)
        if check is not True:
            return Response(
                check,
                status=status.HTTP_400_BAD_REQUEST
            )

        user = self.create_user(first_name, phone, telegram)

        obj = deepcopy(serializer.data)
        obj['id'] = user.id

        headers = self.get_success_headers(serializer.data)
        return Response(
            obj,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def create_user(self, first_name, phone, telegram):
        """ Creating new user """

        user = User()
        userdetail = UserDetail()

        user.first_name = first_name
        userdetail.user = user
        userdetail.phone = phone
        userdetail.telegram = telegram

        user.save()
        userdetail.save()
        Token.objects.create(user=user)
        return user

    def check_unique(self, phone, telegram):
        """ Phone and telegram must be unique but they may be null """

        fields = UserDetail.objects.values_list('phone', 'telegram')
        phones = {i[0] for i in fields}
        telegrams = {i[1] for i in fields}
        if phone in phones and phone:
            return _("This phone already exists")
        elif telegram in telegrams and telegram:
            return _("This telegram nickname already exists")
        return True


class GetTokenAPI(GenericAPIView):
    """ Getting an authorization token """

    serializer_class = TokenRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_user(
            phone=serializer.data.get('phone'),
            telegram=serializer.data.get('telegram')  # like @nickname
        )
        if user is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        token = self.get_or_set_token(user)
        token_serializer = ReceivingTokenSerializer(data={"token": token.key})
        token_serializer.is_valid()

        return Response(
            token_serializer.data,
            status=status.HTTP_200_OK
        )

    def get_user(self, phone: str, telegram: str):
        if phone and telegram:
            try:
                return User.objects.get(
                    details__phone=phone,
                    details__telegram=telegram
                )
            except Exception:
                return None

        elif phone:
            try:
                return User.objects.get(details__phone=phone)
            except Exception:
                return None

        elif telegram:
            try:
                return User.objects.get(details__telegram=telegram)
            except Exception:
                return None

        else:
            return None

    def get_or_set_token(self, user):
        try:
            token = Token.objects.get(user=user)
        except Exception:
            token = Token.objects.create(user=user)
        return token


class DeleteUserAPI(DestroyAPIView):
    """ Delete user """

    queryset = User.objects.all()
    serializer_class = DelUserSerializer
    permission_classes = [IsAdminUser]


class UsersAPI(ListAPIView):
    """ Gets user list """

    queryset = User.objects.all().order_by('pk').select_related('details')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RelevantLessonsAPI(ListAPIView):
    """ Gets relevant lesson list """

    serializer_class = LessonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Lesson.objects.filter(
            date__gte=date.today()
        )
        return queryset


class LessonsViewSet(viewsets.ModelViewSet):
    """ ViewSet of own relevant lessons for authenticated user.
    Request type: GET, POST, PUT, PATCH, DELETE """

    queryset = Lesson.objects.filter(date__gte=date.today())
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        time = serializer.validated_data['time']
        date = serializer.validated_data['date']
        is_morning = С_morning_time <= time < С_morning_time_markup
        is_evening = C_evening_time_markup < time <= C_evening_time
        is_over = len(Lesson.objects.filter(date=date)
                      ) >= C_lesson_threshold - 1
        # value existence check can be disabled in the future
        user_detail = UserDetail.objects.get(user_id=self.request.user.id)
        if is_morning or is_evening or is_over:
            if user_detail.high_cost:
                salary = user_detail.high_cost
            else:
                salary = C_salary_high
        else:
            if user_detail.usual_cost:
                salary = user_detail.usual_cost
            else:
                salary = C_salary_common

        serializer.save(student_id=self.request.user.pk, salary=salary)


class LessonsAdminViewSet(viewsets.ModelViewSet):
    """ ViewSet of all lessons """

    queryset = Lesson.objects.all()
    serializer_class = LessonAdminSerializer
    permission_classes = [IsAdminUser]


class RelevantLessonsAdminViewSet(viewsets.ModelViewSet):
    """ ViewSet of all relevant lessons """

    queryset = Lesson.objects.filter(date__gte=date.today())
    serializer_class = LessonAdminSerializer
    permission_classes = [IsAdminUser]


#################################################################
#                      ADMIN PANEL (AP) API                     #
#################################################################


class TimeBlockAPI(ListAPIView):
    """ Getting block list """

    queryset = TimeBlock.objects.filter(
        date__gte=date.today(),
        date__lte=date.today() + C_datedelta
    )
    serializer_class = TimeBlockSerializer
    permission_classes = [AllowAny]


class TimeBlockAdminAPI(viewsets.ModelViewSet):
    """ ViewSet of all future Timeblocks for admin """

    queryset = TimeBlock.objects.filter(date__gte=date.today())
    serializer_class = TimeBlockAdminSerializer
    permission_classes = [IsAdminUser]


class StudentAdminAPI(mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    """ ViewSet to receive and change students for admin """

    queryset = User.objects.select_related('details').filter(is_staff=False)
    serializer_class = StudentAdminSerializer
    permission_classes = [IsAdminUser]

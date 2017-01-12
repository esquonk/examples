# coding: utf-8
from __future__ import unicode_literals
 
import datetime
import re
import pytz
 
from django import forms
 
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import case
 
from aether import get_session, EntityForm
from aether.forms.choice_provider import EntityChoiceProvider
from aether.forms.widgets import AjaxChoiceWidget
from aether.forms.aether_form import layout, tabs, tab, subform, fieldset,\
    InlineLab
 
from togudb.personality.db import Person, Passport
from togudb.abitur.db import AbiturPerson
from togudb.directory.db import PassportType, Country
   
from portal_apps.finance.db import update_person_account
 
class PassportForm(EntityForm):
    class Meta:
        entity = Passport
        fields = (
            'type',
            'series',
            'number',  
            'issue_date',
            'authority',
            'authority_code',
        )
 
    def clean_series(self):        
        data = self.cleaned_data['series']
        return re.sub('\s', '', data) if data else data
 
    def clean_number(self):        
        data = self.cleaned_data['number']
        return re.sub('\s', '', data) if data else data
 
    def clean_authority(self):
        data = self.cleaned_data['authority']
        return data.strip() if data else data
 
    def clean_authority_code(self):
        data = self.cleaned_data['authority_code']
        data = re.sub(r'[^0-9]', '', data)
        if len(data) > 6:
            raise forms.ValidationError('Введите не более 6 цифр')
        return data
 
    def clean_issue_date(self):
        data = self.cleaned_data['issue_date']
        if data > datetime.date.today():
            raise forms.ValidationError('Дата ещё не наступила')
        if data.year < 1950:
            raise forms.ValidationError('Дата слишком старая')
        return data
 
class NewPersonForm(EntityForm):
    def __init__(self, data=None, files=None):
        session = get_session()
        pt = session.query(PassportType).filter(PassportType.name == 'паспорт гражданина РФ').one()
        self.passport_form = PassportForm(data=data, files=files,
                                          initial={'type': pt},
                                          prefix='new_person')
       
        super(NewPersonForm, self).__init__(data=data, files=files)
                   
    class Meta:
        entity = Person
        fields = (
            'last_name',
            'first_name',
            'mid_name',
            'latin_name',
            'gender',
            'birthday',            
        )
   
    def clean_last_name(self):
        data = self.cleaned_data['last_name']        
        return data.strip().title() if data else data
       
    def clean_first_name(self):
        data = self.cleaned_data['first_name']        
        return data.strip().title() if data else data
   
    def clean_mid_name(self):
        data = self.cleaned_data['mid_name']        
        return data.strip().title() if data else data
 
    def clean_latin_name(self):
        data = self.cleaned_data['latin_name']        
        return data.strip().title() if data else data
   
    def clean_birthday(self):
        data = self.cleaned_data['birthday']
        if data > datetime.date.today():
            raise forms.ValidationError('Дата ещё не наступила')
        if data.year < 1900:
            raise forms.ValidationError('Дата слишком старая')
        return data
   
    def is_valid(self):
        return super(NewPersonForm, self).is_valid() and self.passport_form.is_valid()
   
    def save(self, commit=True):
        session = get_session()        
        try:
            person = session.query(Person)\
                .join(Person.passports)\
                .filter(Person.last_name==self.cleaned_data['last_name'],
                        Person.first_name==self.cleaned_data['first_name'],
                        Passport.series==self.passport_form.cleaned_data['series'],
                        Passport.number==self.passport_form.cleaned_data['number'],
                ).one()                
        except NoResultFound:
            person = super(NewPersonForm, self).save(commit=True)
            passport = self.passport_form.save(commit=False)
            passport.person = person
            session.add(passport)
       
        if not person.abitur_data:
            person.abitur_data = AbiturPerson()
            session.add(person.abitur_data)    
       
        session.flush()
       
        update_person_account(person)
       
        return person
       
 
class PersonInlineLab(InlineLab):
    def get_option_value(self, form):
        return form.instance.person.id
 
from portal_apps.abitur.person.person_apps.lab import lab as person_apps_lab
from portal_apps.abitur.person.person_ege_certs.lab import lab as person_ege_lab
from portal_apps.abitur.person.person_parents.lab import lab as person_parents_lab
from portal_apps.abitur.person.person_planned_ege.lab import lab as planned_ege_lab
from portal_apps.abitur.person.person_specials.lab import special_lab, olymp_lab
from portal_apps.abitur.person.person_education.lab import lab as person_education_lab
from portal_apps.abitur.person.person_address.lab import lab as person_address_lab
from portal_apps.abitur.person.person_phones.lab import lab as person_phones_lab
from portal_apps.abitur.person.person_int_exams.lab import lab as person_int_exams_lab
 
class Apps(PersonInlineLab):
    lab = person_apps_lab
 
class EGEExams(PersonInlineLab):
    lab = person_ege_lab
       
class PlannedEGE(PersonInlineLab):
    lab = planned_ege_lab
 
class IntExams(PersonInlineLab):
    lab = person_int_exams_lab
 
class Parents(PersonInlineLab):
    lab = person_parents_lab
       
class SpecialLab(PersonInlineLab):
    lab = special_lab
   
class OlympLab(PersonInlineLab):
    lab = olymp_lab
   
class Education(PersonInlineLab):
    lab = person_education_lab
       
class Addresses(PersonInlineLab):
    lab = person_address_lab
   
class Phones(PersonInlineLab):
    lab = person_phones_lab
   
class AbiturPersonForm(EntityForm):
    class Meta:
        entity = AbiturPerson
        fields = (
            'russian_abroad',      
            'needs_dorm',
            'return_documents_by',
            'achievements',
            'voen_number',
            'voen_start',
            'voen_end',
            'original_edu_document',
            'original_edu_document_place',
            'original_edu_document_date',
            'photo_number',
        )
   
    layout = layout([
        tabs([
            tab('Приём', [
                'photo_number',            
                'needs_dorm',
                'achievements',
                'return_documents_by',
                'original_edu_document',
                'original_edu_document_date',
                'original_edu_document_place',                
            ]),
            tab('Личные данные', [
                subform('person_form'),
                'russian_abroad',                
                fieldset('Паспорт', [
                    subform('passport_form'),
                ]),
                fieldset('Образование', [                
                    Education,            
                ]),
                fieldset('Телефон', [
                    Phones,
                ]),
                fieldset('Адрес', [
                    Addresses,
                ])      
            ]),
           
            tab('Карточки', [
               Apps,    
            ]),
            tab('Особые права', [
                fieldset('Особые права', [
                    SpecialLab,
                ]),
                fieldset('Олимпиады', [
                    OlympLab,
                ]),                    
            ]),                        
            tab('Экзамены', [
                fieldset('Оценки ЕГЭ', [
                    EGEExams,
                ]),
                fieldset('Внутренние экзамены', [
                    IntExams,
                ]),
                fieldset('Планируемые экзамены во 2 волне', [
                    PlannedEGE,                                          
                ])
                       
            ]),
            tab('Родители', [
                Parents,
            ]),
        ]),
    ])
   
    def __init__(self, data=None, files=None, initial=None, instance=None, request=None):                
       
        self.passport_form = PassportForm(prefix='passport',
                                          data=data, files=files,
                                          instance=instance.person.passports[0],
                                          request=request)
       
        self.person_form = PersonForm(prefix='person',
                                      data=data,
                                      files=files,
                                      instance=instance.person,
                                      request=request)
   
        super(AbiturPersonForm, self).__init__(data=data, files=files, initial=initial, instance=instance, request=request)
   
    def is_valid(self):
        return super(AbiturPersonForm, self).is_valid() and \
            self.passport_form.is_valid() and \
            self.person_form.is_valid()
       
    def non_field_errors(self):
        return super(AbiturPersonForm, self).non_field_errors() + \
            self.passport_form.non_field_errors() + \
            self.person_form.non_field_errors()
           
           
    def save(self, commit=True):        
        passport = self.passport_form.save()
        person = self.person_form.save()
           
        instance = super(AbiturPersonForm, self).save(commit)
       
        update_person_account(person)
       
        return instance                            
       
       
class CountryChoiceProvider(EntityChoiceProvider):
    entity = Country
       
    def get_query(self, form_context=None):
        session = get_session()
        return session.query(self.entity).order_by(case([(Country.name=='Россия', 1),
                                                         (Country.name=='Китай', 2)],
                                                        else_=99,
                                                        ))
 
class PersonForm(EntityForm):    
    class Meta:
        entity = Person
        fields = (            
            'last_name',
            'first_name',
            'mid_name',
            'latin_name',    
            'gender',
            'citizenship',
            'email',        
            'birthday',                        
        )
        choices = {
            'citizenship': CountryChoiceProvider,
        }
        widgets = {
            'citizenship': AjaxChoiceWidget(min_length=0),
        }
 
   
    def __init__(self, data=None, files=None, initial=None, instance=None, request=None, prefix=None):                        
        super(PersonForm, self).__init__(data=data, files=files, initial=initial, instance=instance, request=request, prefix=prefix)
        if not self.user_can_change_name():
            self.fields['last_name'].widget = forms.HiddenInput()
            self.fields['first_name'].widget = forms.HiddenInput()
            self.fields['mid_name'].widget = forms.HiddenInput()
            self.fields['latin_name'].widget = forms.HiddenInput()
               
    def user_can_change_name(self):
        # ФИО можно редактировать, если есть права, или в течение суток
 
        return self.request.user.has_perm('Абитуриент|Без ограничений')\
            or datetime.timedelta(days=1) > (datetime.datetime.now(pytz.utc) - self.instance.abitur_data.created_timestamp)
 
 
    def clean_last_name(self):
        if not self.user_can_change_name():
            return self.instance.last_name
       
        data = self.cleaned_data['last_name']
        return data.strip().title() if data else data
       
    def clean_first_name(self):
        if not self.user_can_change_name():
            return self.instance.first_name
       
        data = self.cleaned_data['first_name']
        return data.strip().title() if data else data
   
    def clean_mid_name(self):
        if not self.user_can_change_name():
            return self.instance.mid_name        
       
        data = self.cleaned_data['mid_name']        
        return data.strip().title() if data else data
 
    def clean_latin_name(self):
        if not self.user_can_change_name():
            return self.instance.latin_name
       
        data = self.cleaned_data['latin_name']        
        return data.strip().title() if data else data
   
    def clean_birthday(self):
        data = self.cleaned_data['birthday']
        if data > datetime.date.today():
            raise forms.ValidationError('Дата ещё не наступила')
        if data.year < 1900:
            raise forms.ValidationError('Дата слишком старая')
        return data

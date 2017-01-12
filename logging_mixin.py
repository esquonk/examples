# coding: utf-8
from __future__ import unicode_literals
 
import datetime
import pytz
 
from sqlalchemy.orm.session import object_session
from sqlalchemy.inspection import inspect
from sqlalchemy.util.langhelpers import symbol
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import select, cast, and_
from sqlalchemy.sql.sqltypes import String
from sqlalchemy.sql.functions import func
 
from togudb.logger.db import LoggerEntry, ChangedField
 
def get_identity(obj):
    ''' Идентификатор объекта '''
     
    state = inspect(obj)
    mapper = inspect(state.class_)
    ids = []
    for pkey in mapper.primary_key:
        ids.append(getattr(obj, pkey.key))
    if len(ids) == 1:
        identity = unicode(ids[0])
    else:
        identity = unicode(tuple(ids))        
   
    return identity
 
def get_identity_expr(entity):
    ''' Идентификатор объекта (выражение)'''
   
    mapper = inspect(entity)
 
    pkeys = mapper.primary_key
   
    if len(pkeys) == 1:
        return cast(pkeys[0], String)
   
    else:            
        return '(' + func.concat_ws(', ', *pkeys) + ')'        
   
def get_entity_name(obj):
    return inspect(obj).class_.__name__
       
class LoggedEntity(object):
    '''
   Класс для журналирования изменений.
   Для использования добавить в родительские классы модели sqlalchemy.
   Например:
   class MyModel(LoggedEntity, Base):        
   '''
   
    def _get_changed_fields(self, creating=False):
        state = inspect(self)
        mapper = inspect(state.class_)
        fields = []
        for attr in state.attrs:
            if mapper.attrs[attr.key].info.get('logged', True) and attr.history.has_changes():
                old = None if creating else state.committed_state.get(attr.key, None)
                new = attr.value
                fields.append((unicode(attr.key),
                               self._get_log_field_value(old),
                               self._get_log_field_value(new)))
       
        return fields    
 
    def _get_log_field_value(self, value):
        if isinstance(value, list):
            return '[{}]'.format(','.join(self._get_log_field_value(x) for x in value))
        else:
            return unicode(value)
       
    def _get_log_related_objects(self):
        state = inspect(self)
        mapper = inspect(state.class_)
        rels = set()
        for rel in mapper.relationships:            
            if rel.direction == symbol('MANYTOONE') and rel.info.get('logged', True):
                attr = state.attrs[rel.key]
                if isinstance(attr.value, list):
                    vals = attr.value
                elif attr.value is None:
                    vals = []
                else:
                    vals = [attr.value]
               
                for val in vals:
                    rels.add(val)
        return list(rels)        
   
    def _save_log(self,session, event_type, fields=None):
        entry = LoggerEntry(
            timestamp = datetime.datetime.now(pytz.utc),
            type = event_type,
            entity = get_entity_name(self),
            identity = get_identity(self),
            username = getattr(session, 'username', None),
            ip = getattr(session, 'ip', None),
            related_objects = [
                '{}|{}'.format(
                get_entity_name(val),
                get_identity(val)) for val in self._get_log_related_objects()
            ],
        )
       
        session.add(entry)
       
        if fields is not None:
            for f in fields:
                field = ChangedField(
                    entry = entry,
                    name = f[0],
                    value_old = f[1],
                    value_new = f[2],
                    value_old_pretty = f[1],
                    value_new_pretty = f[2],    
                )
                session.add(field)
       
    def log_created(self, session):                    
        fields = self._get_changed_fields(True)
        self._save_log(session, 'create', fields)
   
    def log_changed(self, session, event_type='change'):
        fields = self._get_changed_fields(True)
       
        if not fields:
            return
       
        self._save_log(session, 'change', fields)            
   
    def log_deleted(self, session):
        self._save_log(session, 'delete')        
       
    @hybrid_property
    def created_timestamp(self):    
        ''' Дата и время создания '''
       
        return object_session(self)\
            .query(LoggerEntry.timestamp)\
            .filter(LoggerEntry.entity == get_entity_name(self),
                    LoggerEntry.identity == get_identity(self),
                    LoggerEntry.type == 'create')\
            .scalar()
       
    @created_timestamp.expression
    def created_timestamp(self):        
        ''' Дата и время создания (выражение)'''
       
        return select([LoggerEntry.timestamp])\
            .where(and_(
                LoggerEntry.type =='create',
                LoggerEntry.entity == self.__name__,
                LoggerEntry.identity == get_identity_expr(self)))\
            .correlate(self)\
            .as_scalar()\
            .label('created_timestamp')

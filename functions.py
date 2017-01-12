# -*- coding: utf-8 -*-

import sys
import locale
import logging
import threading

from time import time
from functools import wraps

from notes.notesapi.libnotes import libnotes
from notes.notesapi.datatypes import *
from notes.notesapi.strings import strings

logger = logging.getLogger("notes.notesapi") 

class NotesError(Exception):
    def __init__(self, context_message, status_code=0):
        self.context_message = context_message
        self.status_code = status_code & 0x3fff
        
    def __unicode__(self):        
        return u"%s: %s (%s)" % (self.context_message,
                                 self.get_notes_error_message(),
                                 self.status_code) 
        
    def __str__(self):
        return self.__unicode__().encode(locale.getpreferredencoding())
        
    def get_notes_error_message(self):        
        if self.status_code:
            return strings.get(self.status_code, u'')
        else:
            return u''

class NotesCompileError(NotesError):
    pass
       
       
def status_func_errcheck(result, func, arguments):
    if result:
        logger.debug(u'Error on call: {}({}) -> {}'.format(func.__name__, arguments, result))
        raise NotesError(func.__name__, result)
    
    return result    

def add_func(lib, name, restype, argtypes, is_status=True):
    func = getattr(lib, name)
    func.restype = restype
    func.argtypes = argtypes
    
    if is_status:
        func.errcheck = status_func_errcheck
    
    @wraps(func)    
    def wrapped(*args, **kwargs):
        start_time = time()
        try:
            result = func(*args, **kwargs)
        except NotesError, e:
            if e.status_code == 7286: # Connection has timed out
                result = func(*args, **kwargs)
            else:
                raise                    
            
        total_time = time() - start_time
        logger.debug(u'[{}][{}ms] {}{} -> {}'.format(
            threading.current_thread().ident,
            total_time * 1000,
            func.__name__,
            unicode(args),
            unicode(result),                         
        ))
        return result

    setattr(sys.modules[__name__], name, wrapped)

add_func(libnotes, "NotesInitExtended", STATUS, (c_int, POINTER(c_char_p),))
add_func(libnotes, "NotesInitThread", STATUS, ())
add_func(libnotes, "NotesTermThread", None, (), False) 
add_func(libnotes, "NotesTerm", None, (), False)

add_func(libnotes, "NIFOpenCollection", STATUS, (DBHANDLE, DBHANDLE, NOTEID, WORD, DHANDLE, POINTER(HCOLLECTION), POINTER(NOTEHANDLE), POINTER(UNID), POINTER(DHANDLE), POINTER(DHANDLE),))
add_func(libnotes, "NIFGetCollectionData", STATUS, (HCOLLECTION, POINTER(DHANDLE),))
add_func(libnotes, "NIFUpdateCollection", STATUS, (HCOLLECTION,))
add_func(libnotes, "NIFCloseCollection", STATUS, (HCOLLECTION,))

add_func(libnotes, "NIFReadEntries", STATUS, (HCOLLECTION, POINTER(COLLECTIONPOSITION), WORD, DWORD, WORD, DWORD, DWORD, POINTER(DHANDLE), POINTER(WORD), POINTER(DWORD), POINTER(DWORD), POINTER(WORD),))
add_func(libnotes, "NIFFindByKey", STATUS, (HCOLLECTION, c_char_p, WORD, POINTER(COLLECTIONPOSITION), POINTER(DWORD),))    
add_func(libnotes, "NIFFindDesignNote", STATUS, (DBHANDLE, c_char_p, WORD, POINTER(NOTEID)))
        
add_func(libnotes, "NSFDbOpen", STATUS, (c_char_p, POINTER(DBHANDLE),))
add_func(libnotes, "NSFDbReopen", STATUS, (DBHANDLE, POINTER(DBHANDLE),))
add_func(libnotes, "NSFDbInfoGet", STATUS, (DBHANDLE, c_char_p,))
add_func(libnotes, "NSFDbInfoParse", None, (c_char_p, WORD, c_char_p, WORD,), False)
add_func(libnotes, "NSFDbClose", STATUS, (DBHANDLE,))

add_func(libnotes, "NSFDbCreateAndCopyExtended", STATUS, (c_char_p, c_char_p, WORD, WORD, DWORD, DHANDLE, POINTER(DBHANDLE),))

add_func(libnotes, "NSFSearch", STATUS, (DBHANDLE, FORMULAHANDLE, c_void_p, WORD, WORD, POINTER(TIMEDATE), NSFSEARCHPROC, POINTER(TIMEDATE),))

add_func(libnotes, "NSFFormulaCompile", STATUS, (c_char_p, WORD, c_char_p, WORD, POINTER(FORMULAHANDLE), POINTER(WORD), POINTER(STATUS), POINTER(WORD), POINTER(WORD), POINTER(WORD), POINTER(WORD),))

add_func(libnotes, "NSFItemInfo", STATUS, (NOTEHANDLE, c_char_p, WORD, POINTER(BLOCKID), WORD, POINTER(BLOCKID), DWORD,))
add_func(libnotes, "NSFItemGetText", WORD, (NOTEHANDLE, c_char_p, c_char_p, WORD,))
add_func(libnotes, "NSFItemQueryEx", None, (NOTEHANDLE, BLOCKID, c_char_p, WORD, POINTER(WORD), POINTER(WORD), POINTER(WORD), POINTER(BLOCKID), POINTER(DWORD), POINTER(BYTE), POINTER(BYTE),))
add_func(libnotes, "NSFItemQuery", None, (NOTEHANDLE, BLOCKID, c_char_p, WORD, POINTER(WORD), POINTER(WORD), POINTER(WORD), POINTER(BLOCKID), POINTER(DWORD),))
add_func(libnotes, "NSFItemDeleteByBLOCKID", STATUS, (NOTEHANDLE, BLOCKID,))
add_func(libnotes, "NSFItemDelete", STATUS, (NOTEHANDLE, c_char_p, WORD,))
add_func(libnotes, "NSFItemAppend", STATUS, (NOTEHANDLE, WORD, c_char_p, WORD, WORD, c_void_p, DWORD,))

add_func(libnotes, "NSFItemInfo", STATUS, (NOTEHANDLE, c_char_p, WORD, POINTER(BLOCKID), POINTER(WORD), POINTER(BLOCKID), POINTER(DWORD),))
add_func(libnotes, "NSFItemInfoNext", STATUS, (NOTEHANDLE, BLOCKID, c_char_p, WORD, POINTER(BLOCKID), POINTER(WORD), POINTER(BLOCKID), POINTER(DWORD),))

add_func(libnotes, "NSFNoteOpen", STATUS, (DBHANDLE, NOTEID, WORD, POINTER(NOTEHANDLE),))
add_func(libnotes, "NSFNoteClose", STATUS, (NOTEHANDLE,))
add_func(libnotes, "NSFNoteUpdate", STATUS, (NOTEHANDLE, WORD,))
add_func(libnotes, "NSFNoteCreate", STATUS, (DBHANDLE, POINTER(NOTEHANDLE),)) 
add_func(libnotes, "NSFNoteGetInfo", None, (NOTEHANDLE, WORD, c_void_p), False) 
add_func(libnotes, "NSFNoteDeleteExtended", STATUS, (DBHANDLE, NOTEID, DWORD))
add_func(libnotes, "NSFProfileOpen", STATUS, (DBHANDLE, c_char_p, WORD, c_char_p, WORD, BOOL, POINTER(NOTEHANDLE)))    
add_func(libnotes, "NSFProfileUpdate", STATUS, (NOTEHANDLE, c_char_p, WORD, c_char_p, WORD))

add_func(libnotes, "SECKFMSwitchToIDFile", STATUS, (c_char_p, c_char_p, c_char_p, WORD, DWORD, c_void_p,))
add_func(libnotes, "SECKFMUserInfo", STATUS, (WORD, c_char_p, c_void_p,)) # FIXME: need proper LICENSEID
add_func(libnotes, "SECKFMCreatePassword", None, (c_char_p, POINTER(KFM_PASSWORD)), False)

add_func(libnotes, "OSLockObject", c_void_p, (DHANDLE,), False)
add_func(libnotes, "OSUnlockObject", BOOL, (DHANDLE,), False)
add_func(libnotes, "OSMemAlloc", STATUS, (WORD, DWORD, POINTER(DHANDLE),), False)
add_func(libnotes, "OSMemFree", STATUS, (DHANDLE,), False)

add_func(libnotes, "OSPathNetConstruct", STATUS, (c_char_p, c_char_p, c_char_p, c_char_p,), False)
add_func(libnotes, "OSTranslate", WORD, (WORD, c_char_p, WORD, c_char_p, WORD,), False)
add_func(libnotes, "OSLoadString", WORD, (HMODULE, STATUS, c_char_p, WORD,), False)

def OSLockBlock(blockid):
    return cast(OSLockObject(blockid.pool), c_void_p)

def OSUnlockBlock(blockid):
    return OSUnlockObject(blockid.pool)

add_func(libnotes, "ConvertTIMEDATEToText", STATUS, (c_void_p, POINTER(TFMT), POINTER(TIMEDATE), c_char_p, WORD, POINTER(WORD),))
add_func(libnotes, "TimeGMToLocal", BOOL, (POINTER(TIME),), False)
add_func(libnotes, "TimeGMToLocalZone", BOOL, (POINTER(TIME),), False)
add_func(libnotes, "TimeLocalToGM", BOOL, (POINTER(TIME),), False)

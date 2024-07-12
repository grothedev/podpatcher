#!/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

import sys
import csv
import sqlite3 as sq

#a simple abstraction between a sqlite db and patch code

patches = [] #associate id with filename and other attributes

db = sq.connect('patches.db')
dbc = db.cursor()
res = dbc.execute('SELECT name FROM sqlite_master WHERE name="patches"')
if res.fetchone() == None:
    res = dbc.execute('CREATE TABLE patches(hash,filename,tag)')
    
def __init__():
    global db
    global dbc
    try:
        db = sq.connect('patches.db')
        dbc = db.cursor()
    except sq.ProgrammingError:
        return None

def get_patches():
    try:
        res = dbc.execute('SELECT * FROM patches')
        return res.fetchall() 
    except sq.ProgrammingError:
        return None

def add_patch(pchID, filename, tag=None):
    try:
        res = dbc.execute('INSERT INTO patches(hash,filename) VALUES(?,?)', (pchID, filename))
        db.commit()
        return res
    except sq.ProgrammingError:
        return None

def remove_patch(pchID):
    try:
        res = db.execute(f'DELETE FROM patches WHERE hash={pchID}')
        db.commit()
        return res
    except sq.ProgrammingError:
        return None

def set_patch_tag(pchID, tag):
    try:
        res = dbc.execute(f'UPDATE patches SET tag={tag} WHERE hash={pchID}')
        db.commit()
        return res
    except sq.ProgrammingError:
        return None

def close():
    dbc.close()
    db.close()

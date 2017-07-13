#!/usr/bin/env python
# -*- coding: utf-8 -*-
import web
import json
from web import form
import MySQLdb
import time
import logging
import datetime
from StringIO import StringIO
import csv
from secret import enviroment

logging.basicConfig(filename=u'/home/icinga2/inventory/errors.log', level=logging.DEBUG)
web.config.debug = True

ERROR_MESSAGE = ''   # Глобальная переменная для вывода ошибок
NET_WAREHOUSE = 33   # id виртуального склада "Сеть"
MIN_HOUSE_ID = 50000 # минимальное значение house_id
ACTIVE_CLASS_ID = 2  # class_id активного оборудования

# константы типов документов
INCOME = 1
MOVE = 2
DELETE = 3
MOUNT = 4
UNMOUNT = 5
REQUEST = 6
MOUNTFAKE = 7

def error_message():
	global ERROR_MESSAGE
	#logging.error(ERROR_MESSAGE)
	tmp = ERROR_MESSAGE
	ERROR_MESSAGE = ""
	return tmp

urls = (
  '/', 'index',
  '/positions', 'positions',
  '/positions/new', 'positions_new',
  '/positions/edit/(.*)', 'positions_edit',
  '/classes', 'classes',
  '/classes/new', 'classes_new',
  '/items', 'items',
  '/items/new', 'items_new',
  '/people', 'people',
  '/people/newperson', 'person_new',
  '/people/newwarehouse', 'warehouse_new',
  '/people/editperson/(.*)', 'person_edit',
  '/people/editwarehouse/(.*)', 'warehouse_edit',
  '/people/fire/(.*)', 'person_fire',
  '/menu', 'menu',
  '/welcome', 'welcome',
  '/income/new', 'income_new',
  '/income', 'income',
  '/incomes/(.*)', 'income',
  #'/documents/view/(.*)/(.*)', 'document_view',
  '/documents/view/(.*)', 'document_view',
  '/documents/save/(.*)', 'document_save',
  '/documents/akt/(.*)', 'document_akt',
  '/documents/aktversionmount/(.*)', 'document_akt_version_mount',
  '/documents/aktmount/(.*)', 'document_akt_mount',
  '/documents/delete/(.*)', 'document_delete',
  '/documents/uploadscan/(.*)/(.*)', 'upload_scan',
  '/documents/uploadscan/(.*)', 'upload_scan',
  '/movement/delete/(.*)', 'movement_delete',
  '/move', 'move',
  '/moves/(.*)', 'move',
  '/move/new', 'move_new',
  '/genmove/(.*)', 'generate_move',
  '/requests', 'request',   
  '/requests/new', 'request_new',   
  '/requests/(.*)', 'request',
  '/request_delete/(.*)', 'request_delete',
  '/delete', 'delete',
  '/deletes/(.*)', 'delete',
  '/delete/new', 'delete_new',
  '/mount/new', 'mount_new',
  '/mount/(.*)', 'mount',
  '/mount', 'mount',
  '/unmount/new', 'unmount_new',
  '/unmount/(.*)', 'unmount',
  '/unmount', 'unmount',
  '/referens', 'referens',
  '/warehouse_rights', 'warehouse_rights',
  '/warehouse_rights/new', 'new_warehouse_right',
  '/warehouse_rights/delete/(.*)', 'delete_warehouse_right',
  '/mountfake', 'mount_fake',
  '/mountfake/new', 'mount_fake_new',
  '/mountfake/(.*)', 'mount_fake',
  #'/documents', 'documents',
  #'/documents/new', 'documents_new',
  #'/movements', 'movements',
  #'/movements/new', 'movements_new',
  '/reports', 'reports',
  '/remains', 'remains',
  '/mounts', 'mounts',
  '/remainsbyperson', 'remains_by_person',
  '/remainspositionsbyperson', 'remains_by_positions_on_person',
  '/posremains', 'position_remains',
  '/period', 'period',
  '/perioddetailed', 'period_detailed',
  '/remains/person/(.*)', 'remains_person',
  '/remains/positionsonperson/(.*)', 'remains_positions_on_person',
  '/remainsbyaddress', 'remains_by_address',
  '/oldserials', 'old_serials',
  '/oldserials/(.*)', 'old_serials',
  '/itemmovements', 'item_movements',
  '/findmounted', 'find_mounted',
  '/findunmounted', 'find_unmounted',
  '/releasebyperiod', 'release_by_period',
  '/denied', 'denied',
  '/api/classes', 'classes_json',
  '/api/positions', 'positions_json',
  '/react', 'react',
)

#model functions

def redirect_to(doc_id, refer = 'by_id'):
	doc = doc_id
	if type(doc) is str or type(doc) is int:
		doc = document_by_id(doc_id)
	if refer == 'home':
		raise web.seeother(web.ctx.homepath)
	if refer == 'doc':
		raise web.seeother('/documents/view/' + str(doc_id))
	if refer == 'income' or (refer == 'by_id' and is_income(doc)):
		raise web.seeother('/income')
	if refer == 'move' or (refer == 'by_id' and is_move(doc)):
		raise web.seeother('/move')
	if refer == 'delete' or (refer == 'by_id' and is_delete(doc)):
		raise web.seeother('/delete')
	if refer == 'mount' or (refer == 'by_id' and is_mount(doc)):
		raise web.seeother('/mount')
	if refer == 'mountfake' or (refer == 'by_id' and is_mount_fake(doc)):
		raise web.seeother('/mountfake')
	if refer == 'unmount' or (refer == 'by_id' and is_unmount(doc)):
		raise web.seeother('/unmount')
	if refer == 'request' or (refer == 'by_id' and is_request(doc)):
		raise web.seeother('/requests')

def people_names():
	people = db.select('people')
	r = {None: ''}
	for p in people:
		r[p.person_id] = person_presentation(p)
	# all id > MIN_HOUSE_ID is house_id
	r.update(house_addresses())
	return r

def positions_names():
	positions = db.select('positions', what = 'position_id, name')
	r = {None: ''}
	for p in positions:
		r[p.position_id] = p.name
	return r
	
def positions_all():
	pos = list(db.select('positions'))
	c = classes_by_id()
	for i in range(0, len(pos)):
		pos[i]['c'] = c[pos[i]['class_id']]
	return pos
	
def positions_by_id():
	c = classes_by_id()
	r = {None: {'unit': '', 'name': '', 'c': None, 'class_id': None}}
	for p in list(db.select('positions')):
		r[p.position_id] = p
		r[p.position_id]['c'] = c[p.class_id]
	return r
	
def classes_all():
	return list(db.select('classes'))

def classes_all_id():
	r = [int(p.id) for p in db.select('classes', what = 'id')]
	return r

def classes_by_id():
	classes = db.select('classes')
	r = {}
	for c in classes:
		r[c.id] = c
	return r

def class_by_id(class_id):
	w = "id = " + str(class_id)
	return db.select('classes', where = w)[0]


def positions_names():
	positions = db.select('positions', what = 'position_id, name')
	r = {None: ''}
	for p in positions:
		r[p.position_id] = p.name
	return r

def positions_units():
	positions = db.select('positions', what = 'position_id, unit')
	r = {0: ''}
	for p in positions:
		r[p.position_id] = p.unit
	return r
	
def documents_by_id():
	docs = db.select('documents')
	r = {0: ''}
	for d in docs:
		r[d.document_id] = d
	return r


def items_serials():
	items = db.select('items', what = 'items_id, serial')
	r = {None: ''}
	for i in items:
		r[i.items_id] = i.serial
	return r

def remains_all(current_doc_id = -1, person = 0):
	h = {}
	on_person = int(person)
	query = ("SELECT m.document_id, m.item_id, m.position_id, m.amount, " +
		"d.person_from, d.person_to " +
		"FROM movements AS m, documents AS d " +
		"WHERE m.document_id = d.document_id " +
		"AND d.document_type != " + str(REQUEST) + " " +
		"AND (d.saved = 1 OR d.document_id = " + str(current_doc_id) + ")")
	if person != 0:
		query += (" AND (d.person_from = " + str(on_person) + 
			" OR d.person_to = " + str(on_person) + ")")
	movements = db.query(query)
	for m in movements:
		if m.person_from != 0	and (on_person == 0 or on_person == m.person_from):
			person_from = m.person_from
			person = h.get(person_from, {})
			current = person.get((m.position_id, m.item_id), 0)
			person[(m.position_id, m.item_id)] = current - m.amount
			h[person_from] = person
		if m.person_to != 0	and (on_person == 0 or on_person == m.person_to):
			person_to = m.person_to
			person = h.get(person_to, {})
			current = person.get((m.position_id, m.item_id), 0)
			person[(m.position_id, m.item_id)] = current + m.amount
			h[person_to] = person
	hclear = {}
	for p in h.keys():
		pclear = {}
		for i in h[p].keys():
			if int(h[p][i]) > 0:
				pclear[i] = int(h[p][i])
		if len(pclear) > 0:
			hclear[p] = pclear
	return hclear
	
def remains_on_person_1(on_person, current_doc_id = -1):
	h = {}
	on_person = str(on_person)
	query = ("SELECT m.item_id, m.position_id, p.name, " +
		" i.serial, " +
		"SUM(IF(d.person_from = " + on_person + 
		", -m.amount, m.amount)) AS amount " +
		"FROM movements AS m INNER JOIN documents AS d ON m.document_id = d.document_id " + 
		"LEFT OUTER JOIN positions AS p ON p.position_id = m.position_id " +  
		"LEFT OUTER JOIN items AS i ON i.items_id = m.item_id " +
		"WHERE d.document_type != " + str(REQUEST) + " " +
		"AND (d.saved = 1 OR d.document_id = " + str(current_doc_id) + ") " +
		"AND (d.person_from = " + on_person + 
		" OR d.person_to = " + on_person + ") "+ 
		"GROUP BY item_id, position_id " +
		"HAVING amount > 0 " +
		"ORDER BY name, serial"
		)
	#for m in movements:
	#	if m.person_from != 0	and (on_person == 0 or on_person == m.person_from):
	#		person_from = m.person_from
	#		person = h.get(person_from, {})
	#		current = person.get((m.position_id, m.item_id), 0)
	#		person[(m.position_id, m.item_id)] = current - m.amount
	#		h[person_from] = person
	#	if m.person_to != 0	and (on_person == 0 or on_person == m.person_to):
	#		person_to = m.person_to
	#		person = h.get(person_to, {})
	#		current = person.get((m.position_id, m.item_id), 0)
	#		person[(m.position_id, m.item_id)] = current + m.amount
	#		h[person_to] = person
	#hclear = {}
	#for p in h.keys():
	#	pclear = {}
	#	for i in h[p].keys():
	#		if int(h[p][i]) > 0:
	#			pclear[i] = int(h[p][i])
	#	if len(pclear) > 0:
	#		hclear[p] = pclear
	#return hclear


	
def remains_on_person(person_id):
	logging.info(remains_all(person = person_id).get(int(person_id), {}))
	return remains_all(person = person_id).get(int(person_id), {})
	

def remains_on_document(doc, include_document = False):
	p = int(doc.person_from)
	if include_document:
		remains = remains_all(current_doc_id = doc.document_id, person = p)
	else: 
		remains = remains_all(person = p)
	return remains.get(p, {})

	
def remains_on_person_names(person_id):
	r = remains_on_person(person_id)
	pos_n = positions_names()
	pos_u = positions_units()
	i_s = items_serials()
	res = {}
	for i in r.keys():
		unit = ''
		if i[1] == None:
			unit = pos_u[i[0]]
		res[(pos_n[i[0]], i_s[i[1]], unit)] = int(r[i])
	return res
	
def remains_by_positions_on_person_query(person_id):
	query = (
		"SELECT m.item_id, m.position_id, p.name, p.unit, " +
		"SUM(IF(d.person_from = " + person_id + 
		", -m.amount, m.amount)) AS amount " +
		"FROM movements AS m " + 
		"INNER JOIN documents AS d ON m.document_id = d.document_id " + 
		"LEFT OUTER JOIN positions AS p ON p.position_id = m.position_id " +  
		"WHERE d.document_type != " + str(REQUEST) + " " +
		"AND d.saved = 1 AND p.inactive = 0 " +
		"AND (d.person_from = " + person_id + 
		" OR d.person_to = " + person_id + ") "+ 
		"GROUP BY position_id " +
		"HAVING amount > 0 " +
		"ORDER BY name"
	)
	return db.query(query)


def period_all(start, end):
	h = {}
	docs = documents_by_id()
	movements = db.select('movements',
		what = 'document_id, item_id, position_id, amount'
		)
	for m in movements:
		d = docs[m.document_id]
		date = str(d.date)
		if m.amount == 0:
			continue
		if not d.saved:
			continue
		if d.document_type == REQUEST:
			continue
		if start <> '' and start > date[:len(start)]:
			continue
		if end <> '' and end < date[:len(end)]:
			continue
		if d.person_from != 0 and d.person_from != None:
			person = h.get(d.person_from, {})
			current = person.get((m.position_id, m.item_id), (0, 0, set()))
			l = current[2]
			l.add(int(m.document_id))
			person[(m.position_id, m.item_id)] = (current[0],
				current[1] + m.amount, l)
			h[d.person_from] = person
		if d.person_to != 0 and d.person_to != None:
			person = h.get(d.person_to, {})
			current = person.get((m.position_id, m.item_id), (0, 0, set()))
			l = current[2]
			l.add( int(m.document_id), )
			person[(m.position_id, m.item_id)] = (current[0] + m.amount,
				current[1], l)
			h[d.person_to] = person
	#logging.info(h)
	return h
	
def period_all_names(start, end):
	r = period_all(start, end)
	p_n = people_names()
	pos_n = positions_names()
	pos_u = positions_units()
	i_s = items_serials()
	h = {}
	for p in r.keys():
		res = {}
		for i in r[p].keys():
			unit = ''
			if i[1] == None:
				unit = pos_u[i[0]]
			res[(pos_n[i[0]], i_s[i[1]], unit)] = r[p][i]
		h[p_n[p]] = res
	return h
	
def period_person_id_names(person_id, start, end):
	r = period_all(start, end).get(int(person_id), {})
	pos_n = positions_names()
	pos_u = positions_units()
	i_s = items_serials()
	h = {}
	for i in r.keys():
		unit = ''
		if i[1] == None:
			unit = pos_u[i[0]]
		h[(pos_n[i[0]], i_s[i[1]], unit)] = r[i]
	return h
	
def movements_by_item(item_id):
	docs = documents_by_id()
	movements = db.select('movements',
		what = 'document_id, item_id',
		where = 'item_id = ' + str(item_id) 
		)	
	r = [ docs[m.document_id] for m in movements]
	r.sort(key = lambda d: d.date)
	return r
				

def remains_position(position):
	h = {}
	movements = db.select('movements', 
		what = 'document_id, item_id, position_id, amount'
		)
	docs = documents_by_id()
	for m in movements:
		if int(m.position_id) <> int(position):
			continue
		d = docs[m.document_id]
		if not d.saved or d.document_type == REQUEST:
			continue
		if d.person_from != 0 and d.person_from < MIN_HOUSE_ID:
			person = h.get(d.person_from, {})
			current = person.get((m.position_id, m.item_id), 0)
			person[(m.position_id, m.item_id)] = current - m.amount
			h[d.person_from] = person
		if d.person_to != 0 and d.person_to < MIN_HOUSE_ID:
			person = h.get(d.person_to, {})
			current = person.get((m.position_id, m.item_id), 0)
			person[(m.position_id, m.item_id)] = current + m.amount
			h[d.person_to] = person
	hclear = {}
	for p in h.keys():
		pclear = {}
		for i in h[p].keys():
			if int(h[p][i]) > 0:
				pclear[i] = int(h[p][i])
		if len(pclear) > 0:
			hclear[p] = pclear
	return hclear

def remains_position_names(position):
	r = remains_position(position)
	p_n = people_names()
	pos_n = positions_names()
	pos_u = positions_units()
	i_s = items_serials()
	h = {}
	for p in r.keys():
		res = {}
		for i in r[p].keys():
			unit = ''
			if i[1] == None:
				unit = pos_u[i[0]]
			res[(pos_n[i[0]], i_s[i[1]], unit)] = int(r[p][i])
		h[p_n[p]] = res
	return h

def document_by_id(document_id):
	w = "document_id = " + str(document_id)
	doc = db.select('documents', where = w)[0]
	doc["movements"] = movements_by_document(document_id)
	doc["string"] =  doc_to_string(doc)
	doc["string1"] =  doc_to_string1(doc)
	doc["string2"] =  doc_to_string2(doc)
	return doc
	
def document_based_on(document_id):
	w = ("based_on = " + str(document_id) +
		" AND saved = 1") 
	docs = list(db.select('documents', where = w))
	if len(docs) == 0:
		return None
	return docs[0]
	
def documents_all():
	doc = list(db.select('documents'))
	for i in range(0, len(doc)):
		doc[i]["string"] = doc_to_string(doc[i])
	return doc
	
def date_convert(date):
	date = str(date)
	return date[8:10] + '.' + date[5:7] + '.' + date[0:4]

def date_to_nice_string(date):
	date = str(date)
	day = '"' + date[8:10] + '"'
	year = date[0:4] + " г."
	month = int(date[5:7])
	month = (['января', 'февраля', 'марта',
						'апреля', 'мая', 'июня',
			      'июля', 'августа', 'сентября',
						'октября', 'ноября', 'декабря'])[month -1]
	return day + " " + month + " " + year
	


def date_month(date):
	date = str(date)
	return date[0:7]


def doc_to_string1(d):
	ds = u'Документ № ' + str(d.document_id) + u' от ' + date_convert(d.date)
	return ds


def doc_to_string2(d):
	#ds = ''
	if is_income(d):
		ds = 'Поступление на ' + person_presentation_by_id(d.person_to)
	elif is_delete(d):
		ds = 'Списание с ' + person_presentation_by_id(d.person_from)
	elif is_mount(d):
		ds =  'Акт монтажа с ' + person_presentation_by_id(d.person_from) 
		ds +=	' по адресу ' + house_address(d.person_to)
	elif is_mount_fake(d):
		ds =  'Акт корректировки монтажа по адресу ' + house_address(d.person_to)
	elif is_unmount(d):
		ds =  'Акт демонтажа провел ' + person_presentation_by_id(d.person_to) 
		ds +=	' по адресу ' + house_address(d.person_from)
	elif is_move(d):
		ds = 'Перемещение с ' + person_presentation_name_by_id(d.person_from)
		ds += ' на ' + person_presentation_name_by_id(d.person_to)
	elif is_request(d):
		ds = 'Заявка на выдачу с ' + person_presentation_name_by_id(d.person_from)
		ds += ' на ' + person_presentation_name_by_id(d.person_to)
	else:
		ds = 'Неизвестный тип движения'
	return ds
	

def doc_to_string(d):
	ds = u'№ ' + str(d.document_id) + u' от ' + date_convert(d.date) + u' '
	ds = ds.encode('utf-8')
	if is_income(d):
		ds += 'Поступление на ' + person_presentation_by_id(d.person_to)
	elif is_delete(d):
		ds += 'Списание с ' + person_presentation_by_id(d.person_from)
		#ds += 'Поступление на ' + person_presentation_by_id(d.person_to)
	elif is_mount(d):
		ds +=  'Акт монтажа с ' + person_presentation_by_id(d.person_from) 
		ds +=	' по адресу ' + house_address(d.person_to)
	elif is_mount_fake(d):
		ds +=  'Акт корректировки монтажа по адресу ' + house_address(d.person_to)
	elif is_unmount(d):
		ds +=  'Акт демонтажа провел ' + person_presentation_by_id(d.person_to) 
		ds +=	' по адресу ' + house_address(d.person_from)
	elif is_move(d):
		ds += 'Перемещение с ' + person_presentation_name_by_id(d.person_from)
		ds += ' на ' + person_presentation_name_by_id(d.person_to)
	elif is_request(d):
		ds += 'Заявка на выдачу с ' + person_presentation_name_by_id(d.person_from)
		ds += ' на ' + person_presentation_name_by_id(d.person_to)
	else:
		ds = 'Неизвестный тип движения'
	return ds
	
def document_string(document_id):
	d = document_by_id(document_id)
	return doc_to_string(d)

def person_by_id(person_id):
	#logging.info(person_id)
	w = "person_id = " + str(person_id)
	return db.select('people', where = w)[0]
	
def in_charge_by_id(person_id):
	if int(person_id) == 0:
		return ''
	p = person_by_id(person_id)
	if not p.warehouse:
		return person_presentation(p)
	return person_presentation(person_by_id(p.in_charge))

def full_in_charge_by_id(person_id):
	if int(person_id) == 0:
		return ''
	p = person_by_id(person_id)
	if not p.warehouse:
		return person_presentation_name_dad(p)
	return  person_presentation(person_by_id(p.in_charge)) + ' ответственный за склад '+ person_presentation(p)

def person_presentation(person):
	if person.warehouse:
		return person.name
	else:
		first_name = person.first_name
		dad_name = person.dad_name
		person_name = person.name.decode('utf-8')
		if len(first_name) == 0:
			initials = u''
		elif len(dad_name) == 0:
			initials = u' ' + first_name.decode('utf-8')[0] + u'.'
		else:
			initials = u' ' + first_name.decode('utf-8')[0] + u'.' + dad_name.decode('utf-8')[0] + u'.'
			#initials = initials.encode('utf-8')
			return (person_name + initials).encode('utf-8')

def person_presentation_name(person):
	if person.warehouse:
		return person.name
	else:
		first_name = person.first_name
		dad_name = person.dad_name
		person_name = person.name.decode('utf-8')
		if len(first_name) == 0:
			initials = u''
		elif len(dad_name) == 0:
			initials = u' ' + first_name.decode('utf-8')
		else:
			initials = u' ' + first_name.decode('utf-8')
			#initials = initials.encode('utf-8')
			return (person_name + initials).encode('utf-8')

def person_presentation_name_dad(person):
	if person.warehouse:
		return person.name
	else:
		first_name = person.first_name
		dad_name = person.dad_name
		person_name = person.name.decode('utf-8')
		if len(first_name) == 0:
			initials = u''
		elif len(dad_name) == 0:
			initials = u' ' + first_name.decode('utf-8')
		else:
			initials = u' ' + first_name.decode('utf-8') + u' ' + dad_name.decode('utf-8')
			#initials = initials.encode('utf-8')
			return (person_name + initials).encode('utf-8')

def warehouse_rights_all():
	rights= list(db.select('warehouse_rights'))
	return rights

def people_all(include_fired = False):
	people = list(db.select('people'))
	people = [p for p in people 
		if p.person_id != NET_WAREHOUSE and (not p.fired or include_fired)]
	#for i in range(len(people)):
		#people[i]['presentation'] = person_presentation(people[i])
	return people

def people_list(what = 'all'):
	people = people_all()
	p_l = [('', '')]
	p_l += [(p.person_id, person_presentation_name(p)) 
		for p in people if ((p.warehouse and what != 'p') 
			or (not p.warehouse and what != 'w'))]
	p_l.sort(key = lambda p: p[1])
	return p_l

def people_user_can_get_from(user):
	w_from = can_get_from_warehouses(user)
	people = people_all()
	p_l = [('', '')]
	p_l += [(p.person_id, person_presentation_name(p)) 
		for p in people if ((not p.warehouse) 
			or (p.warehouse and p.person_id in w_from))]
	p_l.sort(key = lambda p: p[1])
	return p_l
	

def streets_by_city(city_id):
	streets = list(db.select('streets'))
	streets = [s for s in streets if s.city_id == int(city_id)]
	return streets
	
def streets_unempty_all():
	h_b_s = {}
	for h in db.select('houses'):
		h_b_s[h.street_id] = 1
	return [s for s in db.select('streets') if s.street_id in h_b_s.keys()]

def streets_mounted_all():
	h_b_s = {}
	for h in houses_mounted_all():
		h_b_s[h.street_id] = 1
	return [s for s in db.select('streets') if s.street_id in h_b_s.keys()]
	
def houses_mounted_all():
	return [house_by_id(h) for h in remains_all().keys() if h > MIN_HOUSE_ID]


def streets_unempty_by_city(city_id):
	streets = streets_unempty_all()
	streets = [s for s in streets if s.city_id == int(city_id)]
	return streets

def streets_mounted_by_city(city_id):
	streets = streets_mounted_all()
	streets = [s for s in streets if s.city_id == int(city_id)]
	return streets


def street_by_id(street_id):
	#logging.info(person_id)
	w = "street_id = " + str(street_id)
	return db.select('streets', where = w)[0]

def streets_by_id():
	#logging.info(person_id)
	r = {}
	streets = list(db.select('streets'))
	for s in streets:
		r[s.street_id] = s
	return r

def houses_by_street(street_id):
	return [h for h in db.select('houses') if h.street_id == int(street_id)]

def houses_mounted_by_street(street_id):
	return [h for h in houses_mounted_all() if h.street_id == int(street_id)]
	
def house_by_id(house_id):
	#logging.info(person_id)
	w = "house_id = " + str(house_id)
	return db.select('houses', where = w)[0]

def house_by_nfs(nfs):
	#logging.info(person_id)
	if nfs == '':
		return None
	w = "nfs = '" + str(nfs) + "'"
	houses = db.select('houses', where =  w )
	if len(houses) == 0:
		return None
	return db.select('houses', where =  w )[0]

def switch_by_serial(serial):
	if serial == '':
		return None
	w = "sn = '" + str(serial) + "'"
	switches = db_switches.select('al_switches', where = w)
	if len(switches) == 0:
		return None
	return switches[0]

def switch_old_by_serial(serial):
	if serial == '':
		return None
	w = "sn = '" + str(serial) + "' AND TO_DAYS(NOW()) - TO_DAYS(date) <= 30"
	switches = db_switches.select('old_device', where = w)
	if len(switches) == 0:
		return None
	return switches[0]


def house_address(house_id):
	house = house_by_id(house_id)
	street = street_by_id(house.street_id)
	if int(street.city_id) == 6:
		address = "г. Волгоград, "
	elif int(street.city_id) == 16:
		address = "г. Волжский, "
	else:
		address = "г. Херня, "
	return address + street.street_name + ", " + house.house_name

def house_addresses():
	houses = list(db.select('houses'))
	streets = streets_by_id()
	r = {}
	for h in houses:
		street = streets[h.street_id]
		if int(street.city_id) == 6:
			address = "г. Волгоград, "
		elif int(street.city_id) == 16:
			address = "г. Волжский, "
		else:
			address = "г. Херня, "
		r[h.house_id] = address + street.street_name + ", " + h.house_name
	return r

def position_by_id(position_id):
	w = "position_id = " + str(position_id)
	pos = db.select('positions', where = w)[0]
	#pos["items"] = items_by_position(position_id)
	#pos["c"] = class_by_id(pos.class_id)
	return pos
	
def item_by_id(item_id):
	w = "items_id = " + str(item_id)
	return db.select('items', where = w)[0]

def add_new_item(pos, serial):
	if serial == "" or serial == None:
		return 0
	items = items_by_position(pos)
	for i in items:
		if i.serial == serial:
			return int(i.items_id)
	return db.insert('items', position = pos, serial = serial)

def item_by_serial(serial):
	if serial == "" or serial == None:
		return None
	w = "serial = '" + str(serial) + "'"
	items = db.select('items', what = 'items_id, serial, position', where = w)
	#for i in items:
	#	if i.serial == serial:
	#		return (i.items_id, i.position)
	if len(items) > 0:
		item = items[0]
		return (item.items_id, item.position)
	return None
	
def movement_by_id(movement_id):
	w = "movement_id = " + str(movement_id)
	return db.select('movements', where = w)[0]

def movements_by_document(document_id):
	w = "document_id = " + str(document_id)
	return list(db.select('movements', where = w))

def items_by_position(position_id):
	if position_id == 0:
		return list(db.select('items'))
	w = "position = " + str(position_id)
	return list(db.select('items', where = w))

def remains_all_names():
	r = remains_all()
	p_n = people_names()
	pos_n = positions_names()
	pos_u = positions_units()
	i_s = items_serials()
	h = {}
	for p in r.keys():
		res = {}
		for i in r[p].keys():
			unit = ''
			if i[1] == None:
				unit = pos_u[i[0]]
			res[(pos_n[i[0]], i_s[i[1]], unit)] = int(r[p][i])
		h[p_n[p]] = res
	return h
	
def person_name(person_id):
	if person_id == 0:
		return u'Никто'
	person = person_by_id(person_id)
	return person.name

def person_presentation_by_id(person_id):
	if person_id == 0:
		return ''
	person = person_by_id(person_id)
	return person_presentation(person)

def person_presentation_name_by_id(person_id):
	if person_id == 0:
		return ''
	person = person_by_id(person_id)
	return person_presentation_name(person)


def incomes_all():
	doc = list(db.select('documents', where = "document_type = " +
		str(INCOME)))
	return doc
	
def moves_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(MOVE))) 
	return doc

def requests_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(REQUEST))) 
	return doc

def deletes_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(DELETE)))
	return doc

def mounts_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(MOUNT)))
	return doc

def mounts_fake_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(MOUNTFAKE)))
	return doc


def unmounts_all():
	doc = list(db.select('documents', 
		where = "document_type = " + str(UNMOUNT)))
	return doc

def user():
	return web.ctx.get('environ',{}).get('REMOTE_USER', None)

def user_name(user):
	if user == None:
		return "Not Logged"
	w = "login = '" + user + "'"
	user_data = db_users.select('users', where = w)
	if len(user_data) == 0:
		return ""
	user_data = user_data[0]	
	return user_data.family + " " + user_data.name

def user_initials(user):
	if user == None:
		return "Not Logged"
	w = "login = '" + user + "'"
	user_data = db_users.select('users', where = w)
	if len(user_data) == 0:
		return ""
	user_data = user_data[0]	
	return (user_data.family + " " + user_data.name[0] + "." + 
		user_data.dadname[0] + ".")

def user_rights(user):
	if user == None:
		return ""
	w = "login = '" + user + "'"
	user_data = db_users.select('users', where = w)
	if len(user_data) == 0:
		return ""
	user_data = user_data[0]	
	return user_data.inventory
	
def users_all():
	users = db_users.select('users')
	return filter(lambda u: u.inventory != '', users)
	
def check_rights(*rlist):
	if len(rlist) > 0:
		if not is_rights(*rlist):
			raise web.seeother('/denied')
	rights = user_rights(user())
	if rights == None:
		raise web.seeother('/denied')
	if rights <> "basic" and rights <> "full" and	rights <> "admin" and rights <>"keeper":
		raise web.seeother('/denied')

def is_rights(*rights):
	role = user_rights(user())
	for r in rights:
		if role == r:
			return True
	return False
	
def can_get_from_warehouses(user):
	w = "user='" + user + "' AND get=1"  
	rights = db.select('warehouse_rights', where = w)
	return map(lambda r: r.warehouse_id, rights)
	
def current_datetime():
	return datetime.datetime.now()

# classes

class InputInt(form.Input):
	def get_type(self):
		return 'number'
		
class InputDate(form.Input):
	def get_type(self):
		return 'date'


class denied:
	def GET(self):
#		check_rights()
		return render.denied()

class index:
	def GET(self):
		check_rights()
		i = web.input(name=None)
		return render.index(i.name)

class reports:
	def GET(self):
		check_rights()
		return render.reports()

class mounts:
	def GET(self):
		check_rights()
		return render.mounts()

		
class remains:
	def GET(self): 
		check_rights()
		return render.remains_all(remains_all_names())

class remains_person:
	def GET(self, person_id): 
		check_rights()
		#remains_on_person_1(person_id)
		return render.remains_person(remains_on_person_names(person_id), person_id)

class remains_positions_on_person:
	def GET(self, person_id): 
		check_rights()
		return render.remains_by_positions_on_person(
			remains_by_positions_on_person_query(person_id), person_id
		)


class find_mounted:
	def GET(self): 
		check_rights()
		result = []
		positions = positions_by_id()
		for p, r in remains_all().items():
			if p < MIN_HOUSE_ID:
				for p_i in r.keys():
					pos = positions[p_i[0]]
					if pos.c.id == ACTIVE_CLASS_ID and pos.serial and p_i[1] != None:
						item = item_by_id(p_i[1])
						switch = switch_by_serial(item.serial)
						if switch:
							result.append({
									'person': person_presentation_by_id(p),
									'position': pos, 
									'item': item, 
									'switch': switch
							})
		#logging.info(result)
		return render.find_mounted(result)

class find_unmounted:
	def GET(self): 
		check_rights()
		result = []
		positions = positions_by_id()
		for p, r in remains_all().items():
			if p >= MIN_HOUSE_ID:
				for p_i in r.keys():
					pos = positions[p_i[0]]
					if pos.c.id == ACTIVE_CLASS_ID and pos.serial and p_i[1] != None:
						item = item_by_id(p_i[1])
						switch = switch_old_by_serial(item.serial)
						if switch:
							result.append({
									'house': house_address(p),
									'position': pos, 
									'item': item, 
									'switch': switch
							})
		#logging.info(result)
		return render.find_unmounted(result)


class positions:
	def GET(self):
		check_rights()
		return render.positions(positions_all())

class classes:
	def GET(self):
		check_rights()
		return render.classes(classes_all())


class positions_new:
	position_form = form.Form(
		form.Dropdown('class_id', args = [], description = u'Классификация'),
		form.Textbox('name', description = u'Наименование'),
		form.Textbox('unit', description = u'ед. изм.'),
		form.Checkbox('serial', value = False, description = u'серийная?'),
		form.Textbox('full_name', description = u'Полное наименование'),
		form.Textbox('code', description = u'код (НФС или 1С)'),
		form.Button('save', html = u'Сохранить' )
	)
	def GET(self):
		check_rights()
		f = self.position_form()
		f.class_id.args = [(c.id, c.name) for c in classes_all()]
		return render.positions_new(f)
		
	def POST(self):
		check_rights()
		f = self.position_form()
		if not f.validates():
			return render.positions_new(f)
			#return f.d
		db.insert('positions', name = f.d.name,
			class_id = f.d.class_id,
			unit = f.d.unit,
			serial = f.d.serial,
			full_name = f.d.full_name,
			code = f.d.code
			)
		return render.positions(positions_all())

class positions_edit:
	position_form = form.Form(
		#form.Hidden('position_id'),
		form.Dropdown('class_id', args = [], description = u'Классификация'),
		form.Textbox('name', description = u'Наименование'),
		form.Textbox('unit', description = u'ед. изм.'),
		form.Checkbox('serial', value = False, description = u'серийная?'),
		form.Checkbox('inactive', value = False, description = u'неактивная?'),
		form.Textbox('full_name', description = u'Полное наименование'),
		form.Textbox('code', description = u'код (НФС или 1С)'),
		form.Button('save', html = u'Сохранить' )
	)
	def GET(self, position_id):
		check_rights()
		pos = position_by_id(position_id)
		f = self.position_form()
		f.class_id.args = [(c.id, c.name) for c in classes_all()]
		f.class_id.value = class_by_id(pos.class_id)
		#f.position_id = position_id
		f.name.value = pos.name
		f.unit.value = pos.unit 
		f.serial.checked = pos.serial 
		f.inactive.checked =  pos.inactive
		f.full_name.value = pos.full_name
		f.code.value = pos.code
		return render.positions_new(f)
		
	def POST(self, position_id):
		check_rights()
		f = self.position_form()
		if not f.validates():
			return render.positions_new(f)
			#return f.d
		w = "position_id = " + str(position_id)
		db.update('positions', where = w, 
			name = f.d.name,
			class_id = f.d.class_id,
			unit = f.d.unit,
			serial = f.d.serial,
			inactive = f.d.inactive,
			full_name = f.d.full_name,
			code = f.d.code
			)
		return render.positions(positions_all())


class classes_new:
	class_form = form.Form(
		form.Textbox('name', description = 'Наименование'),
		form.Button('save', html = u'Сохранить' )
	)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.class_form()
		return render.class_new(f)
		
	def POST(self):
		check_rights('admin', 'full', 'keeper')
		f = self.class_form()
		if not f.validates():
			return render.class_new(f)
		if f.d.name == '':
			return render.class_new(f)
		db.insert('classes', name = f.d.name)
		return render.classes(classes_all())

class referens:
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		return render.referens()

class document_akt:
	def GET(self, doc_id):
		check_rights()
		doc = document_by_id(doc_id)
		return render.income_act(doc)

class document_akt_version_mount:
	def GET(self, doc_id):
		check_rights()
		doc = document_by_id(doc_id)
		return render.income_act_version_mount(doc)


class document_akt_mount:
	def GET(self, doc_id):
		check_rights()
		doc = document_by_id(doc_id)
		if is_mount(doc):
			return render.mount_act(doc)
		if is_unmount(doc):
			return render.unmount_act(doc)
		return None


class documents:
	def GET(self):
		check_rights()
		documents = db.select('documents', 
			what = 'document_id')
		documents_view = []
		for d in documents:
			documents_view.append(document_string(d["document_id"]))
		return render.documents(documents_view)

class documents_new:
	person_form = form.Form(
		form.Dropdown('person_from', []),
		form.Dropdown('person_to',   []),
		form.Button('save', html = u'\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c')
		)
	def GET(self):
		check_rights()
		p_l = people_list()
		f = self.person_form()
		f.person_from.args = p_l
		f.person_to.args   = p_l
		return render.documents_new(f)
	def POST(self):
		check_rights()
		f = self.person_form()
		if not f.validates():
			return render.documents_new(f)
		elif f.d.person_from == '' and f.d.person_to == '':
			return render.documents_new(f)
		else:
			db.insert('documents', person_from = f.d.person_from, 
				person_to = f.d.person_to, creator = user())
			raise web.seeother('/documents')
			
	

class movements:
	def GET(self):
		check_rights()
		movements = db.select('movements', 
			what = 'document_id, position_id, item_id, amount')
		new_movs = []
		for m in movements:
			w = "position_id = " + str(m["position_id"])
			p = (db.select('positions', what = 'name', 
				where = w))[0]["name"]
			itm_id = m["item_id"]
			s = None
			if itm_id != None:
				w = "items_id = " + str(itm_id)
				s = (db.select('items', what = 'serial', 
				where = w))[0]["serial"]
			d = document_string(m["document_id"])
			new_movs.append({'position': p,
					'serial': s,
					'document': d,
					'amount': m["amount"]
			})
		return render.movements(new_movs)

class movements_new:
	def movement_form(self, stage):
		fields = [
			form.Dropdown('document', []),
			form.Dropdown('position', [], onchange="this.form.submit()")
		]
		if stage == 1 or stage == 3:
			fields.append(form.Textbox('amount'))
		if stage == 2 or stage == 3:
			fields.append(form.Dropdown('item', []))
		if stage > 0:
			fields.append(form.Button('save', html = u'Сохранить'))
		return form.Form(*fields)
	def show_form(self, values):
		serial = False
		if values.get('position', 0) == 0:
			f = self.movement_form(0)
		else:
			w = 'position_id = ' + str(values.get('position', 0))
			pos_s = db.select('positions', 
				what = 'position_id, serial',	where = w)[0]
			if pos_s.serial == '1':
				serial = True 
				f = self.movement_form(2)
			else:
				f = self.movement_form(1)
		docs = db.select('documents', what = 'document_id')
		d_view = [(0, '')]
		d_view += [(d.document_id, document_string(d.document_id)) for d in docs]
		f.document.args = d_view
		pos = db.select('positions', what = 'position_id, name')
		p_view = [(0, '')]
		p_view += [(p.position_id, p.name) for p in pos]
		f.position.args = p_view
		f.document.value = int(values.get('document', 0))
		f.position.value = int(values.get('position', 0))
		if serial:
			w = 'position = ' + str(f.position.value)
			itms = db.select('items', what = 'items_id, serial', where = w)
			i_view = [(0, '')]
			i_view += [(i.items_id, i.serial) for i in itms]
			f.item.args = i_view
		return render.movements_new(f)
	def GET(self):
		check_rights()
		return self.show_form({})
	def POST(self):
		check_rights()
		f = self.movement_form(3)
		if not f.validates():
			return self.show_form(f.d)
		elif f.d.save == None:
			return self.show_form(f.d)
		elif f.d.document == '0':
			return self.show_form(f.d)
		elif f.d.position == '0':
			return self.show_form(f.d)
		elif not f.d.item > '0' and not f.d.amount > '0':
			return self.show_form(f.d)
		else:
			amount = '1'
			if f.d.amount != None:
				amount = f.d.amount
			db.insert('movements', 
				document_id = f.d.document,
				item_id = f.d.item,
				position_id = f.d.position,
				amount = amount
				)
			raise web.seeother('/movements') 

class movement_delete:
	def GET(self, movement_id):
		check_rights()
		m = movement_by_id(movement_id)
		d = document_by_id(m.document_id)
		if d.saved:
			raise web.seeother('/documents/view/' + str(m.document_id))
		if m.item_id <> None and (is_income(d) or is_mount_fake(d)):
			w = 'items_id = ' + str(m.item_id)
			db.delete('items', where = w)
		w = 'movement_id = ' + str(movement_id)
		db.delete('movements', where = w)
		raise web.seeother('/documents/view/' + str(m.document_id))

class request_delete:
	def GET(self, doc_id):
		check_rights()
		d = document_by_id(doc_id)
		if document_based_on(doc_id) or not d.document_type == REQUEST:
			raise web.seeother('/requests')
		w = 'document_id = ' + str(doc_id)
		db.delete('movements', where = w)
		db.delete('documents', where = w)
		raise web.seeother('/requests')


class document_delete:
	def GET(self, document_id):
		check_rights()
		d = document_by_id(document_id)
		if d.saved or len(d.movements) > 0:
			raise web.seeother('/documents/view/' + str(m.document_id))
		w = 'document_id = ' + str(document_id)
		db.delete('documents', where = w)
		redirect_to(d)

class items:
	def GET(self):
		check_rights()
		items = db.select('items', what = 'position, serial')
		new_items = []
		for i in range(0, len(items)):
			curr_i =  items[i]
			w = "position_id =" + str(curr_i["position"])
			pos = db.select('positions', what = 'name', 
				where = w)
			new_items.append({'pos_name': pos[0]["name"],
					'serial': curr_i["serial"]
			})
		return render.items(new_items)

class items_new:
	item_form = form.Form(
		form.Dropdown('position', args = []),
		form.Textbox('serial', description = "Серийный №"),
	  form.Button('save', html = u'Сохранить' )
	  )
	def GET(self):
		check_rights()
		f = self.item_form()
		positions = db.select('positions', what = 'position_id, name',
			where = "serial = '1'"
			)
		f.position.args = [(p.position_id, p.name) for p in positions 
		if not p.inactive]
		return render.items_new(f)
		
	def POST(self):
		check_rights()
		f = self.item_form()
		if not f.validates():
			return render.items_new(f)
		else:
			db.insert('items', position = f.d.position, serial = f.d.serial)
			raise web.seeother('/items')
			
class people:
	def GET(self):
		check_rights()
		p_all = people_all(True)
		p_all.sort(key = lambda p: person_presentation_name(p))
		return render.people(p_all)


class warehouse_new:
	person_form = form.Form(
		form.Textbox('name', description = u'Наименование склада'),
		form.Dropdown('in_charge', [], description = u'Ответственный'),
		form.Button('save', html = u'Сохранить' )
		)
	def GET(self):
		check_rights()
		f = self.person_form()
		f.in_charge.args   = people_list('p')
		return render.warehouse_new(f)
		
	def POST(self):
		check_rights()
		f = self.person_form()
		if not f.validates():
			return render.warehouse_new(f)
		elif f.d.in_charge == '':
			return render.warehouse_new(f)
		db.insert('people', name = f.d.name, warehouse = True, 
			in_charge = f.d.in_charge)
		raise web.seeother('/people')

class warehouse_edit:
	person_form = form.Form(
		form.Textbox('name', description = u'Наименование склада'),
		form.Dropdown('in_charge', [], description = u'Ответственный'),
		form.Button('save', html = u'Сохранить' )
		)
	def GET(self, warehouse_id):
		check_rights()
		f = self.person_form()
		warehouse = person_by_id(warehouse_id)
		f.name.value = warehouse.name
		f.in_charge.value = warehouse.in_charge
		f.in_charge.args   = people_list('p')
		return render.warehouse_new(f)
		
	def POST(self, warehouse_id):
		check_rights()
		f = self.person_form()
		if not f.validates():
			return render.warehouse_new(f)
		elif f.d.in_charge == '':
			return render.warehouse_new(f)
		w = "person_id = " + str(warehouse_id)
		db.update('people', where = w, name = f.d.name, warehouse = True, 
			in_charge = f.d.in_charge)
		raise web.seeother('/people')


class person_new:
	person_form = form.Form(
		form.Textbox('family_name', description = u'Фамилия'),
		form.Textbox('first_name', description = u'Имя'),
		form.Textbox('dad_name', description = u'Отчество'),
		form.Textbox('function', description = u'Должность'),
		form.Textbox('employee_id', description = u'Табельный номер'),
		form.Textbox('district', description = u'Структурное подразделение'),
		InputDate('entry_date', description = u'Дата приема на работу'),
		form.Checkbox('female', value = False, description = u'пол женский'),
		form.Textbox('height', description = u'Рост'),
		form.Textbox('shoe_size', description = u'Размер обуви'),
		form.Textbox('cloth_size', description = u'Размер одежды'),
		form.Button('save', html = u'Сохранить' )
		)
	def GET(self):
		check_rights()
		f = self.person_form()
		return render.person_new(f)
		
	def POST(self):
		check_rights()
		f = self.person_form()
		if not f.validates():
			return render.person_new(f)
		db.insert('people',	name = f.d.family_name, first_name = f.d.first_name,
				dad_name = f.d.dad_name, function = f.d.function,	warehouse = False,
				employee_id = f.d.employee_id, district = f.d.district,
				female = f.d.female, height = f.d.height,
				shoe_size = f.d.shoe_size, cloth_size = f.d.cloth_size,
				entry_date = f.d.entry_date
			)
		raise web.seeother('/people')
		
class person_edit:
	person_form = form.Form(
		form.Textbox('family_name', description = u'Фамилия'),
		form.Textbox('first_name', description = u'Имя'),
		form.Textbox('dad_name', description = u'Отчество'),
		form.Textbox('function', description = u'Должность'),
		form.Textbox('employee_id', description = u'Табельный номер'),
		form.Textbox('district', description = u'Структурное подразделение'),
		InputDate('entry_date', description = u'Дата приема на работу'),
		form.Checkbox('female', description = u'пол женский'),
		form.Textbox('height', description = u'Рост'),
		form.Textbox('shoe_size', description = u'Размер обуви'),
		form.Textbox('cloth_size', description = u'Размер одежды'),
		form.Button('save', html = u'Сохранить' )
		)
	def GET(self, person_id):
		check_rights()
		person = person_by_id(person_id)
		f = self.person_form()
		f.family_name.value = person.name
		f.first_name.value = person.first_name
		f.dad_name.value = person.dad_name
		f.function.value = person.function
		f.employee_id.value = person.employee_id
		f.district.value = person.district
		f.female.value = person.female
		f.entry_date.value = person.entry_date
		f.height.value = person.height
		f.shoe_size.value = person.shoe_size
		f.cloth_size.value = person.cloth_size
		return render.person_new(f)
		
	def POST(self, person_id):
		check_rights()
		f = self.person_form()
		if not f.validates():
			return render.person_new(f)
		w = "person_id = " + str(person_id)
		db.update('people',	where = w, name = f.d.family_name, 
				first_name = f.d.first_name, dad_name = f.d.dad_name, 
				function = f.d.function,	warehouse = False,
				employee_id = f.d.employee_id, district = f.d.district,
				female = f.d.female, height = f.d.height,
				shoe_size = f.d.shoe_size, cloth_size = f.d.cloth_size,
				entry_date = f.d.entry_date
			)
		raise web.seeother('/people')

		
class person_fire:
	def GET(self, person_id):
		check_rights()
		person = person_by_id(person_id)
		new = "1"
		if person.fired:
			new = "0"
		db.update('people', where = "person_id = " + str(person_id), fired = new)
		raise web.seeother('/people')

class warehouse_rights:
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		r_all = warehouse_rights_all()
		r_all.sort(key = lambda r: r.warehouse_id)
		r_all.sort(key = lambda r: r.user)
		return render.warehouse_rights(r_all)

class new_warehouse_right:
	right_form = form.Form(
		form.Dropdown('user', [], description = u'Пользователь'),
		form.Dropdown('warehouse_id', [], description = u'Склад'),
		form.Button('save', html = u'Сохранить' )
		)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.right_form()
		f.warehouse_id.args   = people_list('w')
		users = [(u.login, u.login) for u in users_all()]
		f.user.args   = [('', '')] + sorted(users, key = lambda t:t[1])
		return render.warehouse_right_new(f)
		
	def POST(self):
		check_rights('admin', 'full', 'keeper')
		f = self.right_form()
		if not f.validates():
			return render.warehouse_right_new(f)
		if f.d.warehouse_id == '':
			return render.warehouse_right_new(f)
		db.insert('warehouse_rights',	user = f.d.user, 
			warehouse_id = f.d.warehouse_id, get = True, put = True)
		raise web.seeother('/warehouse_rights')
	
class delete_warehouse_right:
	def GET(self, right_id):
		check_rights('admin', 'full', 'keeper')
		db.delete('warehouse_rights', where = "right_id = " + str(right_id))
		raise web.seeother('/warehouse_rights')

class menu:
	def GET(self):
		return render.menu(user_name(user()))

class income:
	def GET(self, month = None):
		check_rights()
		inc = incomes_all()
		months = {}
		for i in inc:
			months[date_month(i.date)] = 1
		inc.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			inc = inc[:20]
		else:
			inc = filter(lambda d: date_month(d.date) == month, inc)
		
		return render.income(inc, sorted(months.keys()), month)
		
class move:
	def GET(self, month = None):
		check_rights()
		moves = moves_all()
		months = {}
		for m in moves:
			months[date_month(m.date)] = 1
		moves.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			moves = moves[:20]
		else:
			moves = filter(lambda d: date_month(d.date) == month, moves)
		return render.moves(moves, sorted(months.keys()), month)

class request:
	def GET(self, month = None):
		check_rights()
		requests = requests_all()
		months = {}
		for r in requests:
			months[date_month(r.date)] = 1
		requests.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			requests = requests[:20]
		else:
			requests = filter(lambda d: date_month(d.date) == month, requests)
		return render.requests(requests, sorted(months.keys()), month)

class delete:
	def GET(self, month = None):
		check_rights('admin', 'full', 'keeper')
		deletes = deletes_all()
		months = {}
		for d in deletes:
			months[date_month(d.date)] = 1
		deletes.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			deletes = deletes[:20]
		else:
			deletes = filter(lambda d: date_month(d.date) == month, deletes)
		return render.deletes(deletes, sorted(months.keys()), month)

class mount:
	def GET(self, month = None):
		check_rights('admin', 'full', 'keeper')
		mounts = mounts_all()
		months = {}
		for d in mounts:
			months[date_month(d.date)] = 1
		mounts.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			mounts = mounts[:20]
		else:
			mounts = filter(lambda d: date_month(d.date) == month, mounts)
		return render.mount(mounts, sorted(months.keys()), month)

class mount_fake:
	def GET(self, month = None):
		check_rights('admin', 'full', 'keeper')
		mounts = mounts_fake_all()
		months = {}
		for d in mounts:
			months[date_month(d.date)] = 1
		mounts.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			mounts = mounts[:20]
		else:
			mounts = filter(lambda d: date_month(d.date) == month, mounts)
		return render.mount_fake(mounts, sorted(months.keys()), month)

class unmount:
	def GET(self, month = None):
		check_rights('admin', 'full', 'keeper')
		unmounts = unmounts_all()
		months = {}
		for d in unmounts:
			months[date_month(d.date)] = 1
		unmounts.sort(key = lambda d: str(d.date), reverse = True)
		if month == None:
			unmounts = unmounts[:20]
		else:
			mounts = filter(lambda d: date_month(d.date) == month, unmounts)
		return render.unmount(unmounts, sorted(months.keys()), month)


def is_income(doc):
	return doc.document_type == INCOME
	#return int(doc.person_from) == 0 and int(doc.person_to) != NET_WAREHOUSE

def is_delete(doc):
	return doc.document_type == DELETE
	#return int(doc.person_to) == 0

def is_mount(doc):
	return doc.document_type == MOUNT
	#return int(doc.person_to) == NET_WAREHOUSE and int(doc.person_from) > 0

def is_mount_fake(doc):
	return doc.document_type == MOUNTFAKE
	#return int(doc.person_to) == NET_WAREHOUSE and int(doc.person_from) == 0

def is_unmount(doc):
	return doc.document_type == UNMOUNT 
	#return int(doc.person_from) == NET_WAREHOUSE

def is_move(doc):
	return doc.document_type == MOVE
	#return (not is_income(doc) and not is_delete(doc) 
	#	and not is_mount(doc) and not is_unmount(doc) and not is_mount_fake(doc))

def is_request(doc):
	return doc.document_type == REQUEST
	
def need_check_remains(doc):
	return not is_income(doc) and not is_mount_fake(doc) and not is_request(doc)

class income_new:
	def person_form(self):
		fields = [form.Dropdown('person_to', [], description = u'Выберите склад')]
		classes = classes_all()
		classes.sort(key = lambda c: c.name)
		for c in classes:
			fields.append(form.Checkbox('chk' + str(c.id),
				value = True,
				description = c.name))
		fields.append(form.Button('save', html = u'Далее'))
		return form.Form(*fields)
	def GET(self):
		check_rights('full', 'admin', 'keeper')
		f = self.person_form()
		f.person_to.args   = people_list('w')
		return render.income_new(f)
	def POST(self):
		check_rights('full', 'admin', 'keeper')
		f = self.person_form()
		if not f.validates():
			return self.GET()
		if f.d.person_to == '':
			return self.GET()
		c = []
		for k, v in f.d.items():
			#logging.info(k[0:3] + ' - ' + str(v))
			if k[0:3] == 'chk' and v:
				c.append(k[3:])
		if len(c) == 0:
			c = 'all'
		else:
			c = '_'.join(c)
		#logging.info(c)
		q = db.insert('documents', person_from = 0, classes = c,
			person_to = f.d.person_to, creator = user(), document_type = INCOME)
		raise web.seeother('/documents/view/' + str(q))

class move_new:
	def person_form(self):
		fields = [
		form.Dropdown('person_from', [], description = u'Склад отгрузки'),
		form.Dropdown('person_to', [], description = u'Склад получателя')]
		classes = classes_all()
		classes.sort(key = lambda c: c.name)
		for c in classes:
			fields.append(form.Checkbox('chk' + str(c.id),
				value = True,
				description = c.name))
		fields.append(form.Button('save', html = u'Далее'))
		return form.Form(*fields)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		f.person_from.args = people_user_can_get_from(user())
		f.person_to.args   = people_list()
		return render.move_new(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person_to == '':
			ERROR_MESSAGE = u'Пустой получатель!'
			return self.GET()
		if f.d.person_from == '':
			ERROR_MESSAGE = u'Пустой выдающий!'
			return self.GET()
		if f.d.person_to == f.d.person_from:
			ERROR_MESSAGE = u'Выдает сам себе!'
			return self.GET()
		r_p = remains_all().get(int(f.d.person_from), {})
		if r_p == {}:
			ERROR_MESSAGE = u'У него ничего нет!'
			return self.GET()
		c = []
		for k, v in f.d.items():
			#logging.info(k[0:3] + ' - ' + str(v))
			if k[0:3] == 'chk' and v:
				c.append(k[3:])
		if len(c) == 0:
			c = 'all'
		else:
			c = '_'.join(c)
		q = db.insert('documents', person_from = f.d.person_from, 
			classes = c, person_to = f.d.person_to, creator = user(), 
			document_type = MOVE)
		raise web.seeother('/documents/view/' + str(q))

class move_new:
	def person_form(self):
		fields = [
		form.Dropdown('person_from', [], description = u'Склад отгрузки'),
		form.Dropdown('person_to', [], description = u'Склад получателя')]
		classes = classes_all()
		classes.sort(key = lambda c: c.name)
		for c in classes:
			fields.append(form.Checkbox('chk' + str(c.id),
				value = True,
				description = c.name))
		fields.append(form.Button('save', html = u'Далее'))
		return form.Form(*fields)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		f.person_from.args = people_user_can_get_from(user())
		f.person_to.args   = people_list()
		return render.move_new(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person_to == '':
			ERROR_MESSAGE = u'Пустой получатель!'
			return self.GET()
		if f.d.person_from == '':
			ERROR_MESSAGE = u'Пустой выдающий!'
			return self.GET()
		if f.d.person_to == f.d.person_from:
			ERROR_MESSAGE = u'Выдает сам себе!'
			return self.GET()
		r_p = remains_all().get(int(f.d.person_from), {})
		if r_p == {}:
			ERROR_MESSAGE = u'У него ничего нет!'
			return self.GET()
		c = []
		for k, v in f.d.items():
			#logging.info(k[0:3] + ' - ' + str(v))
			if k[0:3] == 'chk' and v:
				c.append(k[3:])
		if len(c) == 0:
			c = 'all'
		else:
			c = '_'.join(c)
		q = db.insert('documents', person_from = f.d.person_from, 
			classes = c, person_to = f.d.person_to, creator = user(), 
			document_type = MOVE)
		raise web.seeother('/documents/view/' + str(q))
		
class request_new:
	def person_form(self):
		fields = [
		form.Dropdown('person_from', [], description = u'Склад отгрузки'),
		form.Dropdown('person_to', [], description = u'Склад получателя')]
		classes = classes_all()
		classes.sort(key = lambda c: c.name)
		for c in classes:
			fields.append(form.Checkbox('chk' + str(c.id),
				value = True,
				description = c.name))
		fields.append(form.Button('save', html = u'Далее'))
		return form.Form(*fields)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		f.person_from.args = people_user_can_get_from(user())
		f.person_to.args   = people_list()
		return render.move_new(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person_to == '':
			ERROR_MESSAGE = u'Пустой получатель!'
			return self.GET()
		if f.d.person_from == '':
			ERROR_MESSAGE = u'Пустой выдающий!'
			return self.GET()
		if f.d.person_to == f.d.person_from:
			ERROR_MESSAGE = u'Выдает сам себе!'
			return self.GET()
		r_p = remains_all().get(int(f.d.person_from), {})
		if r_p == {}:
			ERROR_MESSAGE = u'У него ничего нет!'
			return self.GET()
		c = []
		for k, v in f.d.items():
			#logging.info(k[0:3] + ' - ' + str(v))
			if k[0:3] == 'chk' and v:
				c.append(k[3:])
		if len(c) == 0:
			c = 'all'
		else:
			c = '_'.join(c)
		q = db.insert('documents', person_from = f.d.person_from, 
			classes = c, person_to = f.d.person_to, creator = user(), 
			document_type = REQUEST)
		raise web.seeother('/documents/view/' + str(q))

class generate_move:
	def GET(self, req_id):
		check_rights('admin', 'full', 'keeper')
		req = document_by_id(req_id)
		doc_id = db.insert('documents', person_from = req.person_from, 
			classes = req.classes, person_to = req.person_to, creator = user(), 
			based_on = req.document_id, document_type = MOVE)
		raise web.seeother('/documents/view/' + str(doc_id))

class delete_new:
	person_form = form.Form(
		form.Dropdown('person_from',   [], description = u'Списание с'),
		form.Button('save', html = u'Проводки')
		)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		f.person_from.args = people_list()
		return render.delete_new(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		elif f.d.person_from == '':
			ERROR_MESSAGE = u'Не выбран МОЛ!'
			return self.GET()
		r_p = remains_all().get(int(f.d.person_from), {})
		if r_p == {}:
			ERROR_MESSAGE = u'Нечего списывать!'
			return self.GET()
		q = db.insert('documents', person_from = f.d.person_from,
			person_to = 0, creator = user(), document_type = DELETE)
		raise web.seeother('/documents/view/' + str(q))
		
class mount_new:
	def mount_form(self, stage):
		fields = [
			form.Hidden('current_city', description = ""),
			form.Hidden('current_street', description = ""),
			form.Dropdown('person_from',   [], description = u'Монтаж с'),
			form.Dropdown('city', [ (6, 'Волгоград'), (16, 'Волжский') ],
				description = u'Город монтажа',
				onchange="this.form.submit()"),
			form.Dropdown('street', [], description = u'Улица',
				onchange="this.form.submit()")
		]
		if stage > 0:
			fields.append(form.Dropdown('house', [], description = u'Дом',
				onchange="this.form.submit()"))
		else:
			fields.append(form.Hidden('house', [(0, '')], description = u'Дом'))
		if stage > 1:
			fields.append(form.Button('save', value = 'save',
				html = u'Далее'))
		else:
			fields.append(form.Hidden('save', description = " "))
		return form.Form(*fields)
	def show_form(self):
		if self.street == 0:
			f = self.mount_form(0)
		elif self.house == 0:
			f = self.mount_form(1)
		else:
			f = self.mount_form(2)
		f.person_from.args = people_list('p')
		f.person_from.value = self.person_from
		f.city.value = self.city
		f.current_city.value = self.city
		streets = [(0,'')]
		streets += [(s.street_id, s.street_name) for s 
			in streets_unempty_by_city(self.city)]
		streets.sort(key = lambda p: p[1])
		f.street.args = streets
		f.street.value = self.street
		f.current_street.value = self.street
		houses = [(0,'')] 
		houses += [(h.house_id, h.house_name) for h 
			in houses_by_street(self.street)]
		#houses.sort(key = lambda p: int(p[1]))
		f.house.args = houses
		f.house.value = self.house
		#logging.info(self.city)
		return render.mount_new(f)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		self.person_from = ''
		self.city = 6
		self.street = 0
		self.house = 0
		#logging.info(self.city)
		return self.show_form()
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.mount_form(2)
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form()
		if f.d.person_from == '':
			self.person_from = 0
		else:
			self.person_from = int(f.d.person_from)
		self.city   = int(f.d.city)
		self.street = int(f.d.street)
		self.house  = int(f.d.house)
		if int(f.d.current_city) != self.city:
			self.street = 0
			self.house = 0
			return self.show_form()
		if int(f.d.current_street) != self.street:
			self.house = 0
			return self.show_form()
		#logging.info(f.d.house)
		if f.d.save != u'save':
			return self.show_form()
		if self.person_from == 0:
			ERROR_MESSAGE = u'Выберите лицо, производящее монтаж!'
			return self.show_form()
		q = db.insert('documents', person_from = f.d.person_from,
			person_to = self.house, creator = user(),
			classes = 'all', document_type = MOUNT) #str(ACTIVE_CLASS_ID))
		raise web.seeother('/documents/view/' + str(q))

class mount_fake_new:
	def mount_form(self, stage):
		fields = [
			form.Hidden('current_city', description = ""),
			form.Hidden('current_street', description = ""),
			form.Dropdown('city', [ (6, 'Волгоград'), (16, 'Волжский') ],
				description = u'Город монтажа',
				onchange="this.form.submit()"),
			form.Dropdown('street', [], description = u'Улица',
				onchange="this.form.submit()")
		]
		if stage > 0:
			fields.append(form.Dropdown('house', [], description = u'Дом',
				onchange="this.form.submit()"))
		else:
			fields.append(form.Hidden('house', [(0, '')], description = u'Дом'))
		if stage > 1:
			fields.append(form.Button('save', value = 'save',
				html = u'Далее'))
		else:
			fields.append(form.Hidden('save', description = " "))
		return form.Form(*fields)
	def show_form(self):
		if self.street == 0:
			f = self.mount_form(0)
		elif self.house == 0:
			f = self.mount_form(1)
		else:
			f = self.mount_form(2)
		f.city.value = self.city
		f.current_city.value = self.city
		streets = [(0,'')]
		streets += [(s.street_id, s.street_name) for s 
			in streets_unempty_by_city(self.city)]
		streets.sort(key = lambda p: p[1])
		f.street.args = streets
		f.street.value = self.street
		f.current_street.value = self.street
		houses = [(0,'')] 
		houses += [(h.house_id, h.house_name) for h 
			in houses_by_street(self.street)]
		#houses.sort(key = lambda p: int(p[1]))
		f.house.args = houses
		f.house.value = self.house
		#logging.info(self.city)
		return render.mount_fake_new(f)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		self.city = 6
		self.street = 0
		self.house = 0
		#logging.info(self.city)
		return self.show_form()
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.mount_form(2)
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form()
		self.city   = int(f.d.city)
		self.street = int(f.d.street)
		self.house  = int(f.d.house)
		if int(f.d.current_city) != self.city:
			self.street = 0
			self.house = 0
			return self.show_form()
		if int(f.d.current_street) != self.street:
			self.house = 0
			return self.show_form()
		#logging.info(f.d.house)
		if f.d.save != u'save':
			return self.show_form()
		q = db.insert('documents', person_from = 0, document_type = MOUNTFAKE,
			person_to = self.house, creator = user())
		raise web.seeother('/documents/view/' + str(q))



class unmount_new:
	def mount_form(self, stage):
		fields = [
			form.Hidden('current_city', description = ""),
			form.Hidden('current_street', description = ""),
			form.Dropdown('person_to',   [], description = u'Демонтаж провел'),
			form.Dropdown('city', [ (6, 'Волгоград'), (16, 'Волжский') ],
				description = u'Город демонтажа',
				onchange="this.form.submit()"),
			form.Dropdown('street', [], description = u'Улица',
				onchange="this.form.submit()")
		]
		if stage > 0:
			fields.append(form.Dropdown('house', [], description = u'Дом',
				onchange="this.form.submit()"))
		else:
			fields.append(form.Hidden('house', [(0, '')], description = u'Дом'))
		if stage > 1:
			fields.append(form.Button('save', value = 'save',
				html = u'Далее'))
		else:
			fields.append(form.Hidden('save', description = " "))
		return form.Form(*fields)
	def show_form(self):
		if self.street == 0:
			f = self.mount_form(0)
		elif self.house == 0:
			f = self.mount_form(1)
		else:
			f = self.mount_form(2)
		f.person_to.args = people_list('p')
		f.person_to.value = self.person_to
		f.city.value = self.city
		f.current_city.value = self.city
		streets = [(0,'')]
		streets += [(s.street_id, s.street_name) for s 
			in streets_unempty_by_city(self.city)]
		#streets += [(s.street_id, s.street_name) for s 
		#	in streets_mounted_by_city(self.city)]
		streets.sort(key = lambda p: p[1])
		f.street.args = streets
		f.street.value = self.street
		f.current_street.value = self.street
		houses = [(0,'')] 
		houses += [(h.house_id, h.house_name) for h 
			in houses_by_street(self.street)]
		#houses += [(h.house_id, h.house_name) for h 
		#	in houses_mounted_by_street(self.street)]
		#houses.sort(key = lambda p: int(p[1]))
		f.house.args = houses
		f.house.value = self.house
		#logging.info(self.city)
		return render.unmount_new(f)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		self.person_to = ''
		self.city = 6
		self.street = 0
		self.house = 0
		#logging.info(self.city)
		return self.show_form()
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.mount_form(2)
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form()
		if f.d.person_to == '':
			self.person_to = 0
		else:
			self.person_to = int(f.d.person_to)
		self.city   = int(f.d.city)
		self.street = int(f.d.street)
		self.house  = int(f.d.house)
		if int(f.d.current_city) != self.city:
			self.street = 0
			self.house = 0
			return self.show_form()
		if int(f.d.current_street) != self.street:
			self.house = 0
			return self.show_form()
		#logging.info(f.d.house)
		if f.d.save != u'save':
			return self.show_form()
		if self.person_to == 0:
			ERROR_MESSAGE = u'Выберите лицо, производящее демонтаж!'
			return self.show_form()
		q = db.insert('documents', person_to = f.d.person_to,
			person_from = self.house, creator = user(), 
			document_type = UNMOUNT)
		raise web.seeother('/documents/view/' + str(q))
		
class remains_by_address:
	def mount_form(self, stage):
		fields = [
			form.Hidden('current_city', description = ""),
			form.Hidden('current_street', description = ""),
			form.Dropdown('city', [ (6, 'Волгоград'), (16, 'Волжский') ],
				description = u'Город демонтажа',
				onchange="this.form.submit()"),
			form.Dropdown('street', [], description = u'Улица',
				onchange="this.form.submit()")
		]
		if stage > 0:
			fields.append(form.Dropdown('house', [], description = u'Дом',
				onchange="this.form.submit()"))
		else:
			fields.append(form.Hidden('house', [(0, '')], description = u'Дом'))
		if stage > 1:
			fields.append(form.Button('save', value = 'save',
				html = u'Далее'))
		else:
			fields.append(form.Hidden('save', description = " "))
		return form.Form(*fields)
	def show_form(self):
		if self.street == 0:
			f = self.mount_form(0)
		elif self.house == 0:
			f = self.mount_form(1)
		else:
			f = self.mount_form(2)
		f.city.value = self.city
		f.current_city.value = self.city
		streets = [(0,'')]
		streets += [(s.street_id, s.street_name) for s 
			in streets_mounted_by_city(self.city)]
		streets.sort(key = lambda p: p[1])
		f.street.args = streets
		f.street.value = self.street
		f.current_street.value = self.street
		houses = [(0,'')] 
		houses += [(h.house_id, h.house_name) for h 
			in houses_mounted_by_street(self.street)]
		#houses.sort(key = lambda p: int(p[1]))
		f.house.args = houses
		f.house.value = self.house
		#logging.info(self.city)
		return render.remains_by_address_form(f)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		self.city = 6
		self.street = 0
		self.house = 0
		#logging.info(self.city)
		return self.show_form()
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.mount_form(2)
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form()
		self.city   = int(f.d.city)
		self.street = int(f.d.street)
		self.house  = int(f.d.house)
		if int(f.d.current_city) != self.city:
			self.street = 0
			self.house = 0
			return self.show_form()
		if int(f.d.current_street) != self.street:
			self.house = 0
			return self.show_form()
		#logging.info(f.d.house)
		if f.d.save != u'save':
			return self.show_form()
		remains = remains_on_person_names(self.house)
		return render.remains_address(remains, house_address(self.house))
		
class item_movements:
	item_form = form.Form(
		#form.Dropdown('position_id', args = [], description = u'Наименование', 
		#	onchange="this.form.submit()"),
		#form.Hidden('position_current', args = [], description = u'Наименование'),
		#form.Dropdown('item_id', args = [], description = u'Серийник'),
		form.Textbox('item', description = " ", onchange="this.form.submit()"),
		form.Button('save', value = 'save', html = u'Далее')
	)
	def show_form(self):
		f = self.item_form()
		#positions = [(0, '')]
		#positions += [(p.position_id, p.name) for p in positions_all() if p.serial]
		#positions.sort(key = lambda p: p[1])
		#f.position_id.args = positions
		#f.position_id.value = self.position_id
		#f.position_current.value = self.position_id
		#items = [(0, '')]
		#items += [(i.items_id, i.serial) for i in 
		#	items_by_position(self.position_id)]
		#items.sort(key = lambda i: i[1])
		#f.item_id.args = items
		#f.item_id.value = self.item_id
		f.item.value = ''
		#if self.item_id != 0:
			#f.item.value = item_by_id(self.item_id).serial
		return render.item_movements_form(f)
	def GET(self):
		check_rights('admin', 'full', 'keeper')
		#self.position_id = 0
		#self.item_id = 0
		return self.show_form()
	def POST(self):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		f = self.item_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form()
		#self.position_id = int(f.d.position_id)
		#self.item_id = int(f.d.item_id)
		#if int(f.d.position_current) != self.position_id:
		#	self.item_id = 0
		#	return self.show_form()
		#if self.item_id == 0 and f.d.item == '':
		#	return self.show_form()
		#if f.d.save != u'save' and f.d.item == '':
		#	return self.show_form()
		if f.d.item != '':
			self.item_id =  item_by_serial(f.d.item)
			if not self.item_id:
				self.item_id = 0
				ERROR_MESSAGE = u'Несуществующий серийник!'
				return self.show_form()
			self.item_id = self.item_id[0] 
		return render.item_movements(item_by_id(self.item_id), 
			movements_by_item(self.item_id))
		

class remains_by_person:
	person_form = form.Form(
		form.Dropdown('person_from',   [], description = u'Остатки на'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		f = self.person_form()
		f.person_from.args = people_user_can_get_from(user()) 
		#people_list()
		return render.remains_on_person_form(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		elif f.d.person_from == '':
			ERROR_MESSAGE = u'Не выбран МОЛ!'
			return self.GET()
		raise web.seeother('/remains/person/' + str(f.d.person_from))

class remains_by_positions_on_person:
	person_form = form.Form(
		form.Dropdown('person_from',   [], description = u'Остатки на'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		f = self.person_form()
		f.person_from.args = people_user_can_get_from(user())
		#people_list()
		return render.remains_by_positions_on_person_form(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.person_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		elif f.d.person_from == '':
			ERROR_MESSAGE = u'Не выбран МОЛ!'
			return self.GET()
		raise web.seeother('/remains/positionsonperson/' + str(f.d.person_from))

class period:
	period_form = form.Form(
		form.Dropdown('person',   [], description = u'Движения по'),
		InputDate('start', description = u'Начало периода'),
		InputDate('end', description = u'Конец периода'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		people = people_all()
		f = self.period_form()
		f.person.args = people_user_can_get_from(user())
		#people_list()
		return render.period_enter(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.period_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person == '':
			h = period_all_names(f.d.start, f.d.end)
			return render.period(h, f.d.start, f.d.end)
		else:
			h = period_person_id_names(f.d.person, f.d.start, f.d.end)
			return render.period_person(h, person_presentation_by_id(f.d.person), 
				f.d.start, f.d.end)

class period_detailed:
	period_form = form.Form(
		form.Dropdown('person',   [], description = u'Движения по'),
		InputDate('start', description = u'Начало периода'),
		InputDate('end', description = u'Конец периода'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		f = self.period_form()
		f.person.args = people_user_can_get_from(user())
		#people_list()
		return render.period_enter(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.period_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person == '':
			h = period_all_names(f.d.start, f.d.end)
			return render.period_detailed(h, f.d.start, f.d.end)
		else:
			h = period_person_id_names(f.d.person, f.d.start, f.d.end)
			return render.period_person_detailed(h,
				person_presentation_by_id(f.d.person), 
				f.d.start, f.d.end)

class release_by_period:
	period_form = form.Form(
		form.Dropdown('person',   [], description = u'Выдача с'),
		InputDate('start', description = u'Начало периода'),
		InputDate('end', description = u'Конец периода'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		people = people_all()
		f = self.period_form()
		f.person.args = people_user_can_get_from(user())
		#people_list()
		return render.period_enter(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.period_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.person == '':
			ERROR_MESSAGE = u'Выберите склад!'
			return self.GET()
		query = (
			"SELECT d.person_to, p.name, i.serial, p.unit, SUM(m.amount) AS amount " +
			"FROM movements as m " +
			"INNER JOIN documents as d ON m.document_id = d.document_id "+
			"LEFT OUTER JOIN positions AS p ON p.position_id = m.position_id "+
			"LEFT OUTER JOIN items AS i ON i.items_id = m.item_id " +
			"WHERE d.document_type = {0} AND d.saved = 1 AND d.person_from = {1} "
		)
		if f.d.start != '': 	
			query += "AND d.date >= '{2}' "
		if f.d.end != '':
			query += "AND d.date < '{3}' + interval 1 day "
		query += (
			"GROUP BY person_to, m.position_id, serial " + 
			"ORDER BY person_to, name, serial" 
		)
		query = query.format(MOVE, f.d.person, f.d.start, f.d.end)
		#logging.info(query)
		csv_file = StringIO()
		csv_writer = csv.writer(csv_file)
		csv_writer.writerow(
			['получил', 'позиция', 'серийник', 'ед.изм.', 'количество']
		)
		for r in db.query(query):
				csv_writer.writerow(
					[person_presentation_by_id(r.person_to),
					r.name, r.serial, r.unit, r.amount]
				)
		web.header('Content-Type','text/css; charset=utf-8')
		web.header('Content-disposition', 'attachment; filename=release.csv')
		return csv_file.getvalue()

class position_remains:
	position_form = form.Form(
		form.Dropdown('position',   [], description = u'Позиция'),
		form.Button('save', html = u'Вывести')
		)
	def GET(self):
		check_rights()
		pos = positions_all()
		pos_list = [('', '')] 
		pos_list += map(lambda x:(x.position_id, x.name), pos)
		pos_list.sort(key = lambda p: p[1])
		f = self.position_form()
		f.position.args = pos_list
		return render.position_select(f)
	def POST(self):
		global ERROR_MESSAGE
		check_rights()
		f = self.position_form()
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.GET()
		if f.d.position == '':
			ERROR_MESSAGE = u'Не выбрана позиция!'
			return self.GET()
		r = remains_position_names(f.d.position)
		return render.remains_all(r)

class old_serials:
	def GET(self, interval = 30):
		check_rights()
		query = (
			"SELECT p.name, p.first_name, " +
			"DATEDIFF(CURDATE(), l.latest) AS offset, " + 
			"pos.name AS pos_name, i.serial FROM people AS p " +
			"INNER JOIN documents AS docs " + 
			"ON docs.person_to = p.person_id " +		
			"INNER JOIN ( " +
			"SELECT dates.items_id, MAX( dates.date ) AS latest " +
			"FROM ( " +
			"SELECT i.items_id, d.date " +
			"FROM items AS i " +
			"INNER JOIN movements AS m ON m.item_id = i.items_id " +
			"AND m.position_id = i.position " +
			"INNER JOIN documents AS d " + 
			"ON m.document_id = d.document_id " +
			") AS dates " + 
			"GROUP BY  items_id) AS l ON l.latest = docs.date " +
			"AND DATEDIFF(CURDATE(), l.latest) > " + 
			str(int(interval) - 1) + " " +
			"INNER JOIN items AS i ON i.items_id = l.items_id " +
			"INNER JOIN positions AS pos  " +
			"ON pos.position_id = i.position " +
			"WHERE p.fired =0 AND p.warehouse = 0  " +
			"AND docs.document_type = 2 " + 
			"ORDER BY name, first_name, latest"
		)
		return render.old_serials(db.query(query))


class document_view:
	def document_form(self, stage, is_req, drop = False, empty = True):
		fields = [
			form.Dropdown('position', [], 
				onchange="this.form.submit()", 
				description = " "
				)
		]
		if stage == 1 or stage == 3:
			a = form.AttributeList(type='number', value=20)
			fields.append(InputInt('amount', 
				description = " ", autofocus = 1, min="0"))
		else:
			fields.append(form.Hidden('amount', description = " "))
		if stage == 2 or stage == 3:
			fields.append(form.Textbox('item', description = " ", autofocus = 1))
		else:
			fields.append(form.Hidden('item', description = " "))
		if drop and stage == 2:
			fields.append(form.Dropdown('item_drop', [], 
				onchange="this.form.submit()", 
				description = " "
				))
		else:
			fields.append(form.Hidden('item_drop', description = " "))
		if not empty:
			# you can save document if you keeper
			# or it's a request
			if user_rights(user()) == 'keeper' or is_req:
				fields.append(form.Button('save', value = 'save',
					html = u'Провести документ'))
			else:
				fields.append(form.Button('save', value = 'save',
					html = u'Выйти (документ сохранится)'))
		else:
			fields.append(form.Hidden('save', description = " "))
		return form.Form(*fields)
		
	def positions_in_document(self, document):
		classes = self.classes_list(document.classes)
		classes = '( ' + ', '.join(map(str, classes)) + ') '
		doc_id = str(document.document_id)
		person_id = str(document.person_from)
		query = (
			"SELECT m.position_id, p.name, " +
			"SUM(IF(d.person_from = " + person_id + 
			", -m.amount, m.amount)) AS amount " +
			"FROM movements AS m INNER JOIN documents " +
			"AS d ON m.document_id = d.document_id " + 
			"LEFT OUTER JOIN positions AS p ON p.position_id = m.position_id " +  
			"WHERE d.document_type != " + str(REQUEST) + " " +
			"AND (d.saved = 1 OR d.document_id = " + doc_id + ") " + 
			"AND p.inactive = 0 " +
			"AND p.class_id IN " + classes +
			"AND (d.person_from = " + person_id + 
			" OR d.person_to = " + person_id + ") "+ 
			"GROUP BY position_id " +
			"HAVING amount > 0 " +  
			"ORDER BY name"
		)
		return db.query(query)
		
	def serials_on_position(self, document, pos_id):
		doc_id = str(document.document_id)
		person_id = str(document.person_from)
		query = (
			"SELECT m.item_id, i.serial " +
			"FROM movements AS m INNER JOIN documents "+
			"AS d ON m.document_id = d.document_id " + 
			"LEFT OUTER JOIN items AS i ON i.items_id = m.item_id " +
			"WHERE d.document_type != " + str(REQUEST) + " " +
			"AND (d.saved = 1 OR d.document_id = " + doc_id + ") " + 
			"AND m.position_id = " + str(pos_id) + " " + 
			"AND (d.person_from = " + person_id + 
			" OR d.person_to = " + person_id + ") "+ 
			"GROUP BY item_id " +
			"HAVING SUM(IF(d.person_from = " + person_id +  
			", -m.amount, m.amount)) > 0 " +
			"ORDER BY serial"
		)
		return [(r.item_id, r.serial) for r in db.query(query)]
	
	def check_item(self, document, pos_id, item_id):
		for r in self.serials_on_position(document, pos_id):
			if r[0] == item_id:
				return True
		return False

	def remains_on_position_item(self, document, pos_id, item_id):
		doc_id = str(document.document_id)
		person_id = str(document.person_from)
		query = (
			"SELECT m.item_id, m.position_id, " +  
			"SUM(IF(d.person_from = " + person_id +  
			", -m.amount, m.amount)) AS amount " +
			"FROM movements AS m INNER JOIN documents "+
			"AS d ON m.document_id = d.document_id " + 
			"LEFT OUTER JOIN items AS i ON i.items_id = m.item_id " +
			"WHERE d.document_type != " + str(REQUEST) + " " +
			"AND (d.saved = 1 OR d.document_id = " + doc_id + ") " + 
			"AND m.position_id = " + str(pos_id) + " "
		)
		if item_id:
			query += "AND m.item_id = " + str(item_id) + " "
		query += ("AND (d.person_from = " + person_id + 
			" OR d.person_to = " + person_id + ") "+ 
			"GROUP BY position_id, item_id " +
			"HAVING amount > 0"
		)
		r = db.query(query)
		if len(r) == 0:
			return 0
		return r[0].amount

	def reserves_on_position(self, document, pos_id):
		doc_id = str(document.document_id)
		person_id = str(document.person_from)
		query = (
			"SELECT m.position_id, " +  
			"SUM(m.amount) AS amount " +
			"FROM movements AS m INNER JOIN documents "+
			"AS d ON m.document_id = d.document_id " + 
			"LEFT OUTER JOIN documents AS db ON db.based_on = d.document_id " +
			"WHERE d.document_type = " + str(REQUEST) + " " +
			"AND db.document_id is null " + " " +
			"AND m.position_id = " + str(pos_id) + " " +
			"AND d.person_from = " + person_id + " " +
			#"AND d.document_id > " + str(int(doc_id) - 40) + " " +
			"AND (d.saved = 1 OR d.document_id = " + doc_id + ") " + 
			"GROUP BY position_id " +
			"HAVING amount > 0"
		)
		r = db.query(query)
		if len(r) == 0:
			return 0
		return r[0].amount


	def document_by_id(self, document_id):
		w = "document_id = " + str(document_id)
		doc = db.select('documents', where = w)[0]
		doc["string"] =  doc_to_string(doc)
		doc["string1"] =  doc_to_string1(doc)
		doc["string2"] =  doc_to_string2(doc)
		doc["movements"] = self.movements_by_document_id(document_id)
		return doc
		
	def movements_by_document_id(self, document_id):
		doc_id = str(int(document_id))
		query = ("SELECT p.name, i.serial, m.amount, p.unit, p.position_id, " +
			"m.movement_id, p.code, p.serial AS is_serial " +
			"FROM movements AS m " + 
			"LEFT OUTER JOIN positions AS p ON p.position_id = m.position_id " +  
			"LEFT OUTER JOIN items AS i ON i.items_id = m.item_id " +
			"WHERE m.document_id = " + doc_id + " " +
			"ORDER BY movement_id"
		)
		return list(db.query(query))
	
	def movements_number(self, doc_id):
		return db.query(
			"SELECT COUNT(*) as count FROM movements AS m " +
			"WHERE m.document_id = " + str(doc_id)
			)[0].count
		
	def show_form(self, document, values):
		is_req = is_request(document)
		drop = need_check_remains(document) and not is_req
		empty = (len(document.movements) == 0)
		pos_id = int(values.get('position', 0))
		p_view = [(0, '')]
		remain = -1
		reserve = -1
		if drop or is_req:
			for p in self.positions_in_document(document):
				p_view += [(p.position_id, p.name)]
				if p.position_id == pos_id:
					remain = p.amount
			if not (remain > 0):
				pos_id = 0
			elif is_req:
				reserve = self.reserves_on_position(document, pos_id)
				remain -= reserve
				if remain < 0:
					remain = 0 
		else:
			p_view += [(p.position_id, p.name) for p in positions_all() 
				if not p.inactive and p.class_id in 
				self.classes_list(document.classes)]
			p_view.sort(key = lambda p: p[1])
		if pos_id == 0:
			f = self.document_form(0, is_req,	False, empty)
		else:
			pos = position_by_id(pos_id)
			if pos.serial and not is_req:
				f = self.document_form(2, is_req, drop, empty)
				f.item.value = values.get('item', '')
			else:
				f = self.document_form(1, is_req, False, empty)
				f.item.value = ''
		f.position.args = p_view
		f.position.value = pos_id
		if pos_id > 0 and drop:
			if pos.serial:
				i_view = [(0, '')]
				i_view += self.serials_on_position(document, pos_id)
				f.item_drop.args = i_view
				f.amount.value = ''
				remain = -1
			else:
				if remain > 0:
					f.amount.attrs = form.AttributeList(autofocus="1",
						id = "amount",
						min = 0,
						max = remain
						)
				amount = values.get('amount', 0)
				if amount > 0 and amount <= remain:
					f.amount.value = amount
				else:
					f.amount.value = ''
		return render.document_view(document, f, drop, remain, reserve)
		
	def classes_list(self, c):
		if c == 'all':
			return set(classes_all_id())
		return set([int(p) for p in c.split('_')])
		
	def next_line(self, doc):
		req = self.movements_by_document_id(doc.based_on)
		line_number = len(doc.movements)
		counter = 0
		i = 0
		result = {}
		while counter <= line_number and i < len(req):
			pos = req[i].position_id 
			amount = req[i].amount 
			if req[i].is_serial:
				result = {'position': pos}
				counter += amount
			else:
				result = {'position': pos, 'amount': amount}
				counter += 1
			i += 1
		if counter <= line_number:
			result = {}
		return result
		
	def GET(self, doc_id, c = 'all'):
		check_rights() 
		doc = self.document_by_id(doc_id)
		#movements = self.movements_by_document_id(doc_id)
		if doc.saved:
			return render.document_view(doc)
		else:
			check_rights('admin', 'full', 'keeper')
			if doc.based_on > 0:
				return self.show_form(doc, self.next_line(doc))
			elif len(doc.movements) == 0:
				return self.show_form(doc, {})
			else:
				return self.show_form(doc, 
					{'position': doc.movements[-1].position_id})
				
	def POST(self, doc_id, c = 'all'):
		global ERROR_MESSAGE
		check_rights('admin', 'full', 'keeper')
		doc = self.document_by_id(doc_id)
		f = self.document_form(3, is_request(doc))
		if not f.validates():
			ERROR_MESSAGE = u'Инвалид!'
			return self.show_form(doc, f.d)
		if f.d.amount == None:
			amount = 0
		elif len(f.d.amount) == 0:
			amount = 0
		else:
			amount = int(f.d.amount)
		if f.d.save == u'save' and amount == 0 and (f.d.item == u'' or
			f.d.item == None):
			raise web.seeother('/documents/save/' + str(doc_id))
		if f.d.position == '0':
			#ERROR_MESSAGE = u'Позиция не должна быть пустой'
			return self.show_form(doc, f.d)
		if position_by_id(f.d.position).serial and \
		f.d.item == '' and (f.d.item_drop == '' or f.d.item_drop == None):
			#ERROR_MESSAGE = u'Выберите или введите серийник'
			return self.show_form(doc, f.d)
		if not position_by_id(f.d.position).serial and amount == 0:
			#ERROR_MESSAGE = u'Нулевое количество!'
			return self.show_form(doc, f.d)
		pos_id = f.d.position
		item_id = None
		if position_by_id(pos_id).serial and not is_request(doc):
			amount = 1
			if is_income(doc) or is_mount_fake(doc):
				if item_by_serial(f.d.item) <> None:
					#ERROR_MESSAGE = str(f.d.item) + u' такой серийник уже оприходовали!'
					ERROR_MESSAGE = u' такой серийник уже оприходовали!'
					return self.show_form(doc, f.d)
				item_id = add_new_item(f.d.position, f.d.item)
			else:
				if f.d.item == '':
					if f.d.item_drop == '0' or f.d.item_drop == '':
						#ERROR_MESSAGE = u'Выберите илии введите серийник'
						return self.show_form(doc, f.d)
					item_id = int(f.d.item_drop)
				else:
					item_tuple = item_by_serial(f.d.item)
					if item_tuple == None:
						#ERROR_MESSAGE = str(f.d.item) + u' такой серийник не приходовали!'
						ERROR_MESSAGE = u' такой серийник не приходовали!'
						return self.show_form(doc, {'position': f.d.position})
					item_id = int(item_tuple[0])
					if int(pos_id) <> int(item_tuple[1]):
						if not self.check_item(doc, int(item_tuple[1]), item_id): 
							#ERROR_MESSAGE = (str(f.d.item) + u' приходовали под позицией '+ 
							#	position_by_id(item_tuple[1]).name.decode('utf-8')  +  u'!')
							ERROR_MESSAGE = str(f.d.item) + u' нет на этом складе !'
							return self.show_form(doc, f.d)
						else:
							pos_id = int(item_tuple[1])
		if need_check_remains(doc):
			#r_p = remains_on_document(doc)
			remain = self.remains_on_position_item(doc, pos_id, item_id)
			#remain = r_p.get((int(pos_id), item_id), 0)
			if amount > remain:
				ERROR_MESSAGE = u'Этой позиции осталось ' + str(remain)
				return self.show_form(doc, f.d)
		if is_request(doc):
			#r_p = remains_on_document(doc)
			remain = 0
			for p in self.positions_in_document(doc):
				if int(p.position_id) == int(pos_id):
					remain = int(p.amount)
			reserve = self.reserves_on_position(doc, pos_id)
			if amount > (remain - reserve):
				ERROR_MESSAGE = (u'Позиция зарезервирована, можно выдать ' + 
					str(remain - reserve))
				return self.show_form(doc, f.d)
		if amount == 0:
			#ERROR_MESSAGE = u'Нулевое количество!'
			return self.show_form(doc, f.d)
		db.insert('movements', 
			document_id = doc_id,
			item_id = item_id,
			position_id = pos_id,
			amount = amount
			)
		raise web.seeother('/documents/view/' + str(doc_id)) 
		
class document_save:
	def GET(self, doc_id):
		global ERROR_MESSAGE
		dv = document_view()
		check_rights()
		doc = document_by_id(doc_id)
		if (not user_rights(user()) == 'keeper' and 
			not doc.document_type == REQUEST):
			redirect_to(doc)
		if doc.saved:
			ERROR_MESSAGE = "Документ уже проведен"
			return dv.GET(doc_id)
		if len(doc.movements) == 0:
			ERROR_MESSAGE = "Нельзя провести пустой документ"
			return dv.GET(doc_id)
		if need_check_remains(doc):
			r = remains_on_document(doc)
			m_sum = {}
			for m in doc.movements:
				m_sum[(m.position_id, m.item_id)] = m_sum.get(
					(m.position_id, m.item_id), 0) + m.amount
			#logging.info(r)				
			#logging.info(m_sum)
			for mk, mv in m_sum.items():
				if mv > r.get(mk, 0):
					what = position_by_id(mk[0]).name
					#if mk[1] <> None:
						#what += u' (' +  item_by_id(mk[1]).serial + u')'
					ERROR_MESSAGE = "Слишком много хотите" 
					  #(u'По документу нужно ' +	str(mv)  
						#+ u' ' + what
						#+ u' есть только ' + str(r.get(mk, 0)))
					#logging.info(ERROR_MESSAGE)
					return dv.GET(doc_id)
		w = "document_id = " + str(doc_id)
		db.update('documents', where = w, 
			saved = '1', signed_by = user()
			)
		raise web.seeother('/documents/view/' + str(doc_id))



class upload_scan:
	refer = ""
	def GET(self, doc_id, refer = 'home'):
		check_rights()
		return render.upload_scan(doc_id)
	def POST(self, doc_id, refer = 'home'):
		check_rights()
		x = web.input(scan={})
		fn = 'scan_{0:09d}_{1:%Y%m%d%H%M%S}{2}'.format(int(doc_id),
			datetime.datetime.now(), 
			x.scan.filename[-4:])
		if x.scan.filename:
			open('scans/' + fn, 'wb').write(x.scan.file.read())
			w = "document_id = " + str(doc_id)
			db.update('documents', where = w, scan = fn)
			redirect_to(doc_id, refer)
		return render.upload_scan(doc_id)
		
class welcome:
	def GET(self):
		check_rights()
		i = web.input(name=None)
		return render.welcome(i.name)

class classes_json:
	def GET(self):
		check_rights()
		web.header('Content-Type', 'application/json')
		return json.dumps(list(db.select('classes')))

class positions_json:
	def GET(self):
		check_rights()
		web.header('Content-Type', 'application/json')
		return json.dumps(list(db.select('positions')))

class react:
	def GET(self):
		check_rights()
		return render.react()



template_globals = {
    'app_path': lambda p: web.ctx.homepath + p,
    'frame_target': 'target=workplace',
    'positions_names': positions_names,
    'positions_units': positions_units,
    'positions_by_id': positions_by_id,
    'position_by_id': position_by_id,
    'items_serials': items_serials,
    'error_message': error_message,
    'user_name': lambda u: user_name(u),
    'user_initials': lambda u: user_initials(u),
    'document_string': document_string,
    'person_presentation': lambda p: person_presentation_by_id(p),
    'person_presentation_name':  person_presentation_name_by_id,
    'in_charge_by_id': in_charge_by_id,
    'full_in_charge_by_id': full_in_charge_by_id,
    'is_rights': is_rights,
    'is_mount': is_mount,
    'is_unmount': is_unmount,
    'is_request': is_request,
    'house_by_id': house_by_id,
    'house_address': house_address,
    'person_by_id': person_by_id,
    'switch_by_serial': switch_by_serial,
    'date_convert': date_convert,
    'date_to_nice_string': date_to_nice_string,
    'current_datetime': current_datetime,
    'doc_to_string': doc_to_string,
    'document_based_on': document_based_on
}



render = web.template.render('templates/', globals = template_globals)

db = web.database(
	host=enviroment.db['host'],
	dbn=enviroment.db['dbn'], 
	user=enviroment.db['user'], 
	pw=enviroment.db['pw'], 
	db=enviroment.db['db']
)
db_users = web.database(
	host=enviroment.users['host'],
	dbn=enviroment.users['dbn'], 
	user=enviroment.users['user'], 
	pw=enviroment.users['pw'], 
	db=enviroment.users['db']
)
db_switches = web.database(
	host=enviroment.switches['host'],
	dbn=enviroment.switches['dbn'], 
	user=enviroment.switches['user'], 
	pw=enviroment.switches['pw'], 
	db=enviroment.switches['db']
)

web.config.debug = True

app = web.application(urls, globals())

logging.error(enviroment.db['host'])

if __name__ == "__main__": 
    app.run()        



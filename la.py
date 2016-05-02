#!/usr/bin/env python
import os
import requests
from bs4 import BeautifulSoup as bs

import pygtk
pygtk.require('2.0')
import pango
import gtk
from gtk import gdk

from kiwi.ui.delegates import GladeDelegate
from kiwi.ui.objectlist import Column

config = {
    'adminurl': 'http://{domain}/mailman/admindb/{list}',
}
lists = []


def read_config():
    conf = open(os.path.expanduser('~/.listadmin.ini')).readlines()
    lists = []

    i = 0
    while i < len(conf):
        line = conf[i].strip(' \n')
        if line.startswith('#') or not line:
            i += 1
            continue
        parts = line.split(' ')
        if len(parts) > 1:
            # This is a configuration directive
            key = parts[0]
            value = ' '.join(parts[1:])
            if value[-1] == '\\':
                value = value[:-1]
                while line[-1] == '\\':
                    i += 1
                    line = conf[i].strip(' \n')
                    value += line[:-1]
            config[key] = value
        else:
            # This is a list
            print line
            lists.append(List(line, config.copy()))

        i += 1

    return lists


class Message(object):
    (DEFER, APPROVE, REJECT, DISCARD) = range(4)

    def __init__(self, table):
        rows = table.find_all(name='tr', recursive=False)
        self.sender = self._get_data(rows[0]).text.decode('utf8')
        self.subject = self._get_data(rows[1]).text.decode('utf8')
        self.reason = self._get_data(rows[2]).text.decode('utf8')
        self.received = self._get_data(rows[3]).text.decode('utf8')
        headers = self._get_data(rows[8])()[0]
        self.excerpt = self._get_data(rows[9])()[0].text.decode('utf8')
        self.auto = False

        self.id = headers.attrs['name'].split('-')[1]
        self.action = self.DEFER

    @property
    def approved(self):
        return self.action == self.APPROVE

    def _get_data(self, row):
        return row.find_all('td')[1]

    def approve(self):
        self.action = self.APPROVE
        return True

    def discard(self):
        self.action = self.DISCARD
        return True

    def auto_approve(self, msg):
        # Only discard messages that were not changed
        if self.action != self.DEFER:
            return

        if self.subject == msg.subject:
            print 'approving based on subject'
            self.auto = True
            return self.approve()
        if self.sender == msg.sender:
            print 'approving based on sender'
            self.auto = True
            return self.approve()

    def auto_discard(self, msg):
        # Only discard messages that were not changed
        if self.action != self.DEFER:
            return

        if self.subject == msg.subject and len(self.subject) > 60:
            print 'discarding based on subject'
            self.auto = True
            return self.discard()
        if self.sender == msg.sender:
            print 'discarding based on sender'
            self.auto = True
            return self.discard()


class List(object):

    def __init__(self, address, config):
        self.config = config
        self.address = address
        name, domain = address.split('@')
        subdomain = domain.split('.')[0]
        self.url = config['adminurl'].format(list=name, domain=domain,
                                             subdomain=subdomain)
        self.params = dict(adminpw=config.get('password', ''))
        if config.get('username', None):
            self.params['username'] = config.get('username')

        self.messages = []

    def fetch(self):
        print 'reading', self.url, self.params
        data = requests.post(self.url + '?details=all', data=self.params)
        self.cookies = data.cookies
        self._parse(data.text)

    def _parse(self, data):
        print 'parsing'
        tree = bs(data, 'lxml')
        form = tree.form
        if not form:
            return

        tables = form.find_all(name='table', recursive=False)
        self.messages = [Message(table) for table in tables]
        print '%s messages' % len(self.messages)

    def submit(self):
        form_data = {}
        for msg in self.messages:
            form_data[msg.id] = msg.action

        requests.post(self.url, data=form_data, cookies=self.cookies)
        print 'done'


class Form(GladeDelegate):
    widgets = ['sender', 'subject', 'excerpt']

    def __init__(self, lists):
        self.lists = lists
        self.l = lists.pop(0)

        GladeDelegate.__init__(self,
                               gladefile="browser.ui",
                               delete_handler=self.quit_if_last)
        self.proxy = None
        self.msg = None
        self.setup_widgets()

        self.update_list()

    def _on_messages__cell_data_func(self, column, renderer, msg, text):
        unread = msg.action == 0
        renderer.set_property('weight-set', unread)
        if unread:
            renderer.set_property('weight', pango.WEIGHT_BOLD)
        return text

    def _format_action(self, obj, data):
        values = {0: 'defer', 1: 'approve', 2: 'reject', 3: 'discard'}
        value = values[obj.action]
        if obj.auto:
            return 'auto ' + value
        return value

    def setup_widgets(self):
        self.messages.set_columns([
            Column('id', data_type=int, sorted=True),
            Column('action', data_type=int, format_func=self._format_action,
                   format_func_data=True),
            Column('received', data_type=str),
            Column('sender', data_type=str),
            Column('subject', expand=True, data_type=str),
        ])
        self.messages.set_cell_data_func(self._on_messages__cell_data_func)

        # Install a Control-Q handler that forcefully exits
        # the program without saving any kind of state
        def event_handler(event):
            if event.type == gdk.KEY_PRESS:
                if event.keyval == gtk.keysyms.q:
                    gtk.main_quit()

                if self.msg and event.keyval == gtk.keysyms.a:
                    self.approve(self.msg)
                if self.msg and event.keyval == gtk.keysyms.d:
                    self.discard(self.msg)
                if self.msg and event.keyval == gtk.keysyms.s:
                    self.skip(self.msg)
            gtk.main_do_event(event)
        gdk.event_handler_set(event_handler)

    def update_list(self):
        self.list_name.set_text(self.l.address)
        self.l.fetch()
        self.messages.add_list(self.l.messages, clear=True)
        if self.l.messages:
            self.messages.select(self.l.messages[0])
        self.messages.grab_focus()

    def select_next(self):
        next_index = self.messages.index(self.msg) + 1
        for msg in self.messages[next_index:]:
            if msg.action == Message.DEFER:
                self.messages.select(msg)
                break

    def approve(self, msg):
        msg.approve()
        self.messages.update(msg)
        self.auto_approve(msg)
        self.select_next()

    def discard(self, msg):
        msg.discard()
        self.messages.update(msg)
        self.auto_discard(msg)
        self.select_next()

    def skip(self, msg):
        self.select_next()

    def auto_approve(self, msg):
        index = self.messages.index(self.msg)
        for other in self.messages[index + 1:]:
            other.auto_approve(msg)

    def auto_discard(self, msg):
        index = self.messages.index(self.msg)
        for other in self.messages[index + 1:]:
            other.auto_discard(msg)

    def submit(self):
        self.l.submit()
        self.messages.clear()
        if self.lists:
            self.l = self.lists.pop(0)
            self.update_list()
        else:
            gtk.main_quit()

    #
    # Callbacks
    #

    def on_messages__selection_changed(self, widget, msg):
        self.msg = msg
        if not self.proxy:
            self.proxy = self.add_proxy(msg, self.widgets)
        self.proxy.set_model(msg)

    def on_skip_btn__clicked(self, button):
        self.skip(self.msg)

    def on_approve_btn__clicked(self, button):
        self.approve(self.msg)

    def on_discard_btn__clicked(self, button):
        self.discard(self.msg)

    def on_submit_btn__clicked(self, button):
        self.submit()


def main():
    lists = read_config()
    browser = Form(lists)
    browser.show_all()
    gtk.main()


if __name__ == '__main__':
    main()

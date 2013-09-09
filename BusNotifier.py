#!/usr/bin/env python
import re
import json
import urlparse
import socket
import select
from datetime import datetime, time
from time import sleep
from webscraping import download, xpath

baseURL='http://9292.nl/'
place='arnhem'
jsonName='%s.json'

class Location():
    def __init__(self, name):
        self.name = name
        self.normalizedName = self.name.lower().replace(' ', '-')
        jsonFile = open(jsonName % self.normalizedName, 'r+')
        jsonString = json.load(jsonFile)
        jsonFile.close()
        self.busStops = dict()
        for line in jsonString['busstops']:
            self.busStops[line['name']] = BusStop(line['name'])

    def getNext(self):
        retTime = None
        retStop = None
        retBus = None
        for name, busStop in self.busStops.items():
            bus, time = busStop.getNext()
            if retTime is None or time < retTime:
                retTime = time
                retStop = busStop
                retBus = bus
        if retTime is None:
            raise Exception("Sorry, no more busses today!")
        return (retStop, retBus, retTime)

    def getNextJSON(self):
        try:
            stop, bus, time = self.getNext()
            return '{%s, %s, %s, %s}' % (stop.__repr__(), bus.__repr__(), time.__repr__(), time.wait().__repr__())
        except Exception, err:
            return '{"error": "%s"}' % str(err)

class BusStop():
    def __init__(self, name):
        self.name = name
        self.normalizedName = self.name.lower().replace(' ', '-')
        self.url = '%s/%s/bushalte-%s' % (baseURL, place, self.normalizedName)
        self.downloader = download.Download()
        jsonFile = open(jsonName % self.normalizedName, 'r+')
        jsonString = json.load(jsonFile)
        jsonFile.close()
        self.id = jsonString['busstop-id']
        self.lines = dict()
        for line in jsonString['lines']:
            self.lines[str(line['number']) + line['destination']] = BusLine(self, line)
        self.update()

    def needUpdate(self):
        return (datetime.now() - self.lastUpdate).seconds > 60

    def getNext(self):
        if self.needUpdate():
            self.update()
        retTime = None
        retBus = None
        for linenumber, bus in self.lines.items():
            try:
                time = bus.getNext(self.lastUpdate)
                if retTime is None or time < retTime:
                    retTime = time
                    retBus = bus
            except KeyError, err:
                pass
            except:
                raise
        return (retBus, retTime)

    def update(self):
        self.lastUpdate = datetime.now()
        for linenumber, bus in self.lines.items():
            bus.reset()
        html = self.downloader.get(self.url)
        for line in xpath.search(html, '//table//tr'):
            counter=0
            time = ''
            delay = ''
            destination = ''
            linenumber = ''
            details = ''
            for item in xpath.search(line, '/td'):
                if counter == 0:
                    hour, minutes = xpath.get(item, '/span').strip().split(':');
                    time = Time(hour, minutes)
                    delay = xpath.get(item, '/span[@class="block exclamation bold mts"]').strip().split(':')
                    if len(delay) > 1:
                        delay=Time(delay[0], delay[1], "delay")
                    else:
                        delay=Time(0, delay[0], "delay")
                elif counter == 1:
                    destination = item.strip()
                elif counter == 2:
                    linenumber = item.strip()
                elif counter == 4:
                    details = re.sub('<span.*</span>', '', item).strip()
                counter+=1
            if delay != '':
                if self.lines.has_key(linenumber + destination):
                    self.lines[linenumber + destination].find(time).delay = delay

    def __repr__(self):
        return '"stop": "%s"' % self.name

class BusLine(object):
    def __init__(self, parent, json):
        self.parent = parent
        self.destination = json['destination']
        self.linenumber = json['number']
        self.details = json['details']
        self.schedule = dict()
        for day in json['schedule']:
            self.schedule[day['D']] = Schedule(self, day['table'])

    def getNext(self, time):
        return self.schedule[time.weekday()+1].getNext(time.hour, time.minute)

    def find(self, time):
        return self.schedule[time.weekday()+1].find(time)

    def reset(self):
        for item in self.schedule:
            self.schedule[item].reset()

    def __repr__(self):
        return '"bus": {"linenumber": "%s", "destination": "%s", "details": "%s"}' % (self.linenumber, self.destination, self.details)

    """
        Overridden __str__: Human readable busline info
    """
    def __str__(self):
        return '%s, lijn %s naar %s' % (self.details, self.linenumber, self.destination)

class Schedule():
    def __init__(self, parent, json):
        self.parent = parent
        self.schedule = []
        for item in json:
            for minutes in  item['M']:
                self.schedule.append(Time(item['H'], minutes))

    def getNext(self, hour, minutes):
        now = Time(hour, minutes)
        retItem = None
        for item in self.schedule:
            if item.getActualTime() < now:
                continue
            else:
                if retItem is None or item.getActualTime() < retItem:
                    retItem = item
        return retItem

    def find(self, time):
        for item in self.schedule:
            if item.time == time:
                return item
        return None

    def reset(self):
        for item in self.schedule:
            item.delay = None

class Time():
    def __init__(self, hour, minutes, label="time"):
        self.hour = hour
        self.minutes = minutes
        self.label = label
        self.delay = None
 
    def getActualTime(self):
        return self + self.delay

    def diff(self, now):
        if isinstance(now, datetime):
            now = Time(now.hour, now.minute)
        assert isinstance(now, Time)
        return -now+self

    def wait(self):
        now = datetime.now()
        diff = self.getActualTime()-Time(now.hour, now.minute)
        diff.label = "wait"
        return diff
 
    def __eq__(self, other):
        assert isinstance(other, Time)
        return (self.hour, self.minutes) == (other.hour, other.minutes)

    def __lt__(self, other):
        assert isinstance(other, Time)
        return (self.hour, self.minutes) < (other.hour, other.minutes)

    def __gt__(self, other):
        return other<self

    def __le__(self, other):
        return not other<self

    def __ge__(self, other):
        return not self<other

    def __add__(self, other):
        if other is None:
            return Time(self.hour, self.minutes, self.label)
        assert isinstance(other, Time)
        hour = self.hour + other.hour
        minutes = self.minutes + other.minutes
        while minutes > 60:
            hour+=1
            minutes-=60
        while hour > 23:
            hour -= 23
        while minutes < 0:
            hour-=1
            minutes+=60
        return Time(hour, minutes, self.label)

    def __neg__(self):
        return Time(-self.hour, -self.minutes, self.label)

    def __sub__(self, other):
        return -other+self

    def __repr__(self):
        time = self.getActualTime()
        return '"%s": "%2.2d:%2.2d"' % (time.label, time.hour, time.minutes)

    def __str__(self):
        time = self.getActualTime()
        return "%2.2d:%2.2d" % (time.hour, time.minutes)

class Listener(socket.socket):
    def __init__(self, name, port):
        self._name = name
        self._port = port
        self._location = Location(self._name)
        super(Listener, self).__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(('', self._port))
        self.listen(5)

    def run(self):
        connection, address = self.accept()
        connection.sendall(self._location.getNextJSON() + '\n')
        connection.close()

if __name__ == "__main__":
    sockList = []
    sockList.append(Listener('Hack42', 4242))
    sockList.append(Listener('Centraalstation', 2424))
    while True:
        try:
            read, write, error = select.select(sockList,[],[])
            for item in read:
               item.run() 
            #prevOutput = ''
            #while True:
            #    output=location.getNextJSON()
            #    if not output == prevOutput:
            #        conn.sendall(output + '\n')
            #        prevOutput = output
            #    sleep(10)
        except Exception, err:
            print err
    

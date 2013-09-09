
BusNotifier.py

==Purpose==

Bus notifier is a python script that will tell you when the next bus is going
towards Hack42 or when (and where) the next bus to Arnhem station leaves. It 
makes use of a webscraping module to get the latest scheduling information
including delays and such.

There are only two lines in this system, and two mayor end points. The two end
points are Hack42 and Arnhem Centraal (Central Station). There are two busstops
near Hack42, one right in front of the gate, another a little further away.
There is one busline that stops at the nearest busstop but not in the evening
or on weekend days. Both buslines stop at the busstop further away.

==Why==

This script was built as a backend for an old-style flip clock style display we
have at the space. These units were used by the Dutch railroad company (NS) but
have been replaced by LCD screens. This software part works but we still have
to figure out how to drive the display.

In the meantime the software is used by BBFH, our irc-bot. Operators in the
#hack42 channel (irc.oftc.net) can request bus information using "!bus".

==The code==
The code consists of a few files, one python script (BusNotifier.py) to 
rule them all. BusNotifier reads the various json-data files and uses
the webscraping module to retrieve up to date schedule information. It starts
in the background and opens two network sockets on the localhost interface.
When a connection is made to these sockets it will print either the information
about the next bus leaving Hack42 or the next bus coming to Hack42.

==Files==
BusNotifier.py          The main code
*.json                  Scheduling information (lines, stops and destinations)
webscraping/            Webscraping module

==Todo==
* Connect the flipping displays.
* Add a reminder function
* Connect to the Spacesound system (for reminders)
* Clean up the code
* Make the code more generic

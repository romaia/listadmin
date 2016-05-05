# listadmin
A modern listadmin for mailman

This will read your current listadmin configuration file (not all options
are supported yet), and has a somewhat similar behaviour.

The cool feature that drove me to write this is that when you approve or
discard a message, it will automatically approve/discard other messages in
the queue that match the sender or subject of the message, making
maintaining lists a lot easier.

Keyboard shortcuts:

  - `a`: Aprove a message
  - `d`: Discard a message
  - `s`: Skip the message
  - `q`: Quit without submiting changes
  - `p`: Post changes to this list

TODO:
- [ ] Process more listadmin options
- [ ] Save list of discarded/approved senders/subjects reuse later
- [ ] Loading progress.
- [x] List progress

![screenshot](https://raw.githubusercontent.com/romaia/listadmin/master/listadmin.png)

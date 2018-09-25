from prog import basic


class Command(object):
    ' abstract base class for flow command '

    def __init__(self, **kwargs):
        """ kwargsdic is a option dictionary {optionname1: optionvalue1, ...}
            which will be saved in self.__dict__ without deepcopy
        """
        for k, v in kwargs.items():
            self.__dict__[k] = v
        self.__executed = False

    def do(self):
        """ execute (or redos) the command
            returns True if success
        """
        if self.__executed:
            basic.log_message("**************************")
            basic.log_message("REDO: " + str(self.__class__.__name__))
            self._redo()
        else:
            basic.log_message("**************************")
            basic.log_message("DO: " + str(self.__class__.__name__))
            self.__executed = self._exec()
            assert isinstance(self.__executed, bool)
        return self.__executed

    def undo(self):
        """ undo the command
        """
        if self.__executed:
            basic.log_message("**************************")
            basic.log_message("UNDO: " + str(self.__class__.__name__))
            self._undo()

    def reset(self):
        ' clears all backups. Undo operation is not possible after reset call '
        if self.__executed:
            self.__executed = False
            self._clear()

    # ------------ methods to override
    def _exec(self):
        """ command execution returns True
            if success and False otherwise
        """
        raise NotImplementedError

    def _clear(self):
        pass

    def _undo(self):
        raise NotImplementedError

    def _redo(self):
        self._exec()


class CommandFlow(object):
    def __init__(self):
        self.maxundo = 20
        # command list
        self._commands = []
        # commands[i > curposition] can be redone
        self._curpos = -1
        # commands[i <= startposition] cannot be undone
        self._startpos = -1

    def com(self, i):
        "-> Command. Get a command by index"
        return self._commands[i]

    def com_count(self):
        return len(self._commands)

    # can undo/redo from current position
    def can_undo(self):
        return self._curpos > self._startpos

    def can_redo(self):
        return len(self._commands) > self._curpos + 1

    # removes all commands after curpos, adds the command to list
    # and executes it
    def exec_command(self, com):
        # remove all commands from current position to last command
        if self.can_redo():
            for c in self._commands[self._curpos+1:]:
                c.reset()
            self._commands = self._commands[:self._curpos+1]
        # add command
        self.append_command(com)
        # execute
        self.exec_next()

    # Adds the command to the end of the commands list.
    # Doesn't execute it
    def append_command(self, c):
        self._commands.append(c)

    # commands execution procedures
    def exec_next(self):
        "executes or redoes the next command"
        if (self.can_redo()):
            # execution
            if self._commands[self._curpos+1].do():
                self._curpos += 1
                self.adjust_commands_count()

    def adjust_commands_count(self):
        while self._curpos > self.maxundo:
            self._commands[0].reset()
            self._commands.pop(0)
            self._curpos -= 1

    def set_maxundo(self, val):
        self.maxundo = val
        self.adjust_commands_count()

    def exec_all(self):
        while (self.can_redo()):
            a = self._curpos
            self.exec_next()
            # if no progress was made (error or cancel)
            # stop execution
            if (a == self._curpos):
                break

    def undo_prev(self):
        if (self.can_undo()):
            self._curpos -= 1
            self._commands[self._curpos + 1].undo()

    def undo_all(self):
        while (self.can_undo()):
            self.undo_prev()


class ActRemoveListEntry:
    def __init__(self, lst, entry):
        self.lst = lst
        self.e = entry
        try:
            self.ind = lst.index(entry)
        except ValueError:
            self.ind = -1

    def redo(self):
        if self.ind >= 0:
            self.lst.pop(self.ind)

    def undo(self):
        if self.ind >= 0:
            self.lst.insert(self.ind, self.e)


class ActReorderList:
    def __init__(self, lst, order):
        assert len(lst) == len(order)
        self.lst = lst
        self.order = order

    def redo(self):
        a = [None] * len(self.order)
        for i, oldi in enumerate(self.order):
            a[i] = self.lst[oldi]
        self.lst.clear()
        self.lst.extend(a)

    def undo(self):
        a = [None] * len(self.order)
        for i, oldi in enumerate(self.order):
            a[oldi] = self.lst[i]
        self.lst.clear()
        self.lst.extend(a)


class ActMoveListEntry:
    def __init__(self, lst, entry, newind):
        assert newind >= 0 and newind < len(lst) and entry in lst
        self.lst = lst
        self.e = entry
        self.newind = newind
        self.oldind = self.lst.index(entry)

    def redo(self):
        if self.oldind > self.newind:
            self.lst.insert(self.newind, self.e)
            self.lst.pop(self.oldind + 1)
        elif self.newind > self.oldind:
            self.lst.insert(self.newind+1, self.e)
            self.lst.pop(self.oldind)

    def undo(self):
        if self.oldind > self.newind:
            self.lst.insert(self.oldind + 1, self.e)
            self.lst.pop(self.newind)
        elif self.newind > self.oldind:
            self.lst.insert(self.oldind, self.e)
            self.lst.pop(self.newind + 1)


class ActChangeAttr:
    def __init__(self, obj, attr, newval):
        self.obj = obj
        self.attr = attr
        self.newval = newval
        self.oldval = self.obj.__dict__[self.attr]

    def redo(self):
        self.obj.__dict__[self.attr] = self.newval

    def undo(self):
        self.obj.__dict__[self.attr] = self.oldval


class ActFromCommand:
    def __init__(self, com):
        self.com = com

    def redo(self):
        self.com.do()

    def undo(self):
        self.com.undo()

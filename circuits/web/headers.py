# Module:   headers
# Date:     1st February 2009 November 2008
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Headers Support

This module implements support for parsing and handling headers.
"""

import re
from circuits.six import iteritems, u, b

# Regular expression that matches `special' characters in parameters, the
# existance of which force quoting of the parameter value.

tspecials = re.compile(r'[ \(\)<>@,;:\\"/\[\]\?=]')
q_separator = re.compile(r'; *q *=')


def _formatparam(param, value=None, quote=1):
    """Convenience function to format and return a key=value pair.

    This will quote the value if needed or if quote is true.
    """
    if value is not None and len(value) > 0:
        if quote or tspecials.search(value):
            value = value.replace('\\', '\\\\').replace('"', r'\"')
            return '%s="%s"' % (param, value)
        else:
            return '%s=%s' % (param, value)
    else:
        return param


def header_elements(fieldname, fieldvalue):
    """Return a sorted HeaderElement list from a comma-separated header string."""
    if not fieldvalue:
        return []

    result = []
    for element in fieldvalue.split(","):
        if fieldname.startswith("Accept") or fieldname == 'TE':
            hv = AcceptElement.from_str(element)
        else:
            hv = HeaderElement.from_str(element)
        result.append(hv)

    return list(reversed(sorted(result)))


class HeaderElement(object):
    """An element (with parameters) from an HTTP header's element list."""

    def __init__(self, value, params=None):
        self.value = value
        if params is None:
            params = {}
        self.params = params

    def __cmp__(self, other):
        return cmp(self.value, other.value)

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        p = [";%s=%s" % (k, v) for k, v in iteritems(self.params)]
        return "%s%s" % (self.value, "".join(p))

    def __bytes__(self):
        return b(self.__str__())

    def __unicode__(self):
        return u(self.__str__())

    def parse(elementstr):
        """Transform 'token;key=val' to ('token', {'key': 'val'})."""
        # Split the element into a value and parameters. The 'value' may
        # be of the form, "token=token", but we don't split that here.
        atoms = [x.strip() for x in elementstr.split(";") if x.strip()]
        if not atoms:
            initial_value = ''
        else:
            initial_value = atoms.pop(0).strip()
        params = {}
        for atom in atoms:
            atom = [x.strip() for x in atom.split("=", 1) if x.strip()]
            key = atom.pop(0)
            if atom:
                val = atom[0]
            else:
                val = ""
            params[key] = val
        return initial_value, params
    parse = staticmethod(parse)

    def from_str(cls, elementstr):
        """Construct an instance from a string of the form 'token;key=val'."""
        ival, params = cls.parse(elementstr)
        return cls(ival, params)
    from_str = classmethod(from_str)


class AcceptElement(HeaderElement):
    """An element (with parameters) from an Accept* header's element list.

    AcceptElement objects are comparable; the more-preferred object will be
    "less than" the less-preferred object. They are also therefore sortable;
    if you sort a list of AcceptElement objects, they will be listed in
    priority order; the most preferred value will be first. Yes, it should
    have been the other way around, but it's too late to fix now.
    """

    def from_str(cls, elementstr):
        qvalue = None
        # The first "q" parameter (if any) separates the initial
        # media-range parameter(s) (if any) from the accept-params.
        atoms = q_separator.split(elementstr, 1)
        media_range = atoms.pop(0).strip()
        if atoms:
            # The qvalue for an Accept header can have extensions. The other
            # headers cannot, but it's easier to parse them as if they did.
            qvalue = HeaderElement.from_str(atoms[0].strip())

        media_type, params = cls.parse(media_range)
        if qvalue is not None:
            params["q"] = qvalue
        return cls(media_type, params)
    from_str = classmethod(from_str)

    def qvalue(self):
        val = self.params.get("q", "1")
        if isinstance(val, HeaderElement):
            val = val.value
        return float(val)
    qvalue = property(qvalue, doc="The qvalue, or priority, of this value.")

    def __cmp__(self, other):
        diff = cmp(self.qvalue, other.qvalue)
        if diff == 0:
            diff = cmp(str(self), str(other))
        return diff

    def __lt__(self, other):
        if self.qvalue == other.qvalue:
            return str(self) < str(other)
        else:
            return self.qvalue < other.qvalue

class CaseInsensitiveDict(dict):
    """A case-insensitive dict subclass.

    Each key is changed on entry to str(key).title().
    """

    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).title())

    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key).title(), value)

    def __delitem__(self, key):
        dict.__delitem__(self, str(key).title())

    def __contains__(self, key):
        return dict.__contains__(self, str(key).title())

    def get(self, key, default=None):
        return dict.get(self, str(key).title(), default)

    if hasattr({}, 'has_key'):
        def has_key(self, key):
            return dict.has_key(self, str(key).title())

    def update(self, E):
        for k in E.keys():
            self[str(k).title()] = E[k]

    def fromkeys(cls, seq, value=None):
        newdict = cls()
        for k in seq:
            newdict[str(k).title()] = value
        return newdict
    fromkeys = classmethod(fromkeys)

    def setdefault(self, key, x=None):
        key = str(key).title()
        try:
            return self[key]
        except KeyError:
            self[key] = x
            return x

    def pop(self, key, default):
        return dict.pop(self, str(key).title(), default)


class Headers(CaseInsensitiveDict):
    def elements(self, key):
        """Return a sorted list of HeaderElements for the given header."""
        key = str(key).title()
        value = self.get(key)
        return header_elements(key, value)

    def values(self, key):
        """Return a sorted list of HeaderElement.value for the given header."""
        return [e.value for e in self.elements(key)]

#class Headers(dict):
#    """Manage a collection of HTTP response headers"""
#
#    def __init__(self, headers=[]):
#        if not isinstance(headers, list):
#            raise TypeError("Headers must be a list of name/value tuples")
#        self._headers = headers
#
#    def __len__(self):
#        """Return the total number of headers, including duplicates."""
#        return len(self._headers)
#
#    def __setitem__(self, name, val):
#        """Set the value of a header."""
#        del self[name]
#        self._headers.append((name, val))
#
    def __delitem__(self, name):
        """Delete all occurrences of a header, if present.

        Does *not* raise an exception if the header is missing.
        """
        name = name.title()
        if name in self:
            super(Headers, self).__delitem__(name)
#        self._headers[:] = [
#            kv for kv in self._headers
#            if kv[0].title() != name
#        ]

    def __getitem__(self, name):
        """Get the first header value for 'name'

        Return None if the header is missing instead of raising an exception.

        Note that if the header appeared multiple times, the first exactly
        which occurrance gets returned is undefined. Use getall() to get all
        the values matching a header field name.
        """
        return self.get(name)

#    def pop(self, name, default=None):
#        value = self.get(name, default)
#        del self[name]
#        return value
#
#    def has_key(self, name):
#        """Return true if the message contains the header."""
#        return self.get(name) is not None
#
#    __contains__ = has_key

    def get_all(self, name):
        """Return a list of all the values for the named field.

        These will be sorted in the order they appeared in the original header
        list or were added to this instance, and may contain duplicates. Any
        fields deleted and re-inserted are always appended to the header list.
        If no fields exist with the given name, returns an empty list.
        """
        name = name.title()
        return [] if name not in self else self[name].split(', ')
#        return [kv[1] for kv in self._headers if kv[0].title() == name]

#    def get(self, name, default=None):
#        """Get the first header value for 'name', or return 'default'"""
#
#        name = name.title()
#        for k, v in self._headers:
#            if k.title() == name:
#                return v
#        return default
#
#    def keys(self):
#        """Return a list of all the header field names.
#
#        These will be sorted in the order they appeared in the original header
#        list, or were added to this instance, and may contain duplicates.
#        Any fields deleted and re-inserted are always appended to the header
#        list.
#        """
#        return [k for k, v in self._headers]

#    def values(self):
#        """Return a list of all header values.
#
#        These will be sorted in the order they appeared in the original header
#        list, or were added to this instance, and may contain duplicates.
#        Any fields deleted and re-inserted are always appended to the header
#        list.
#        """
#        return [v for k, v in self._headers]
#
#    def items(self):
#        """Get all the header fields and values.
#
#        These will be sorted in the order they were in the original header
#        list, or were added to this instance, and may contain duplicates.
#        Any fields deleted and re-inserted are always appended to the header
#        list.
#        """
#        return self._headers[:]

    def __repr__(self):
        return "Headers(%s)" % repr(self._headers)

    def __str__(self):
        """str() returns the formatted headers, complete with end line,
        suitable for direct HTTP transmission."""
        # TODO: make Date and Server the first entries
        headers = ["%s: %s\r\n" % (k, v) for k, v in self.items()]
        return "".join(headers) + '\r\n'

#    def setdefault(self, name, value):
#        """Return first matching header value for 'name', or 'value'
#
#        If there is no header named 'name', add a new header with name 'name'
#        and value 'value'."""
#        result = self.get(name)
#        if result is None:
#            self._headers.append((name, value))
#            return value
#        else:
#            return result

    def append(self, key, value):
        if not value in self:
            self[key] = value
        else:
            self[key] = ', '.join([self[key], value])

    def add_header(self, _name, _value, **_params):
        """Extended header setting.

        _name is the header field to add. keyword arguments can be used to set
        additional parameters for the header field, with underscores converted
        to dashes. Normally the parameter will be added as key="value" unless
        value is None, in which case only the key will be added.

        Example:

        h.add_header('content-disposition', 'attachment', filename='bud.gif')

        Note that unlike the corresponding 'email.Message' method, this does
        *not* handle '(charset, language, value)' tuples: all values must be
        strings or None.
        """
        parts = []
        if _value is not None:
            parts.append(_value)
        for k, v in list(_params.items()):
            if v is None:
                parts.append(k.replace('_', '-'))
            else:
                parts.append(_formatparam(k.replace('_', '-'), v))
        self.append(_name, "; ".join(parts))

#    def elements(self, key):
#        """Return a list of HeaderElements for the given header (or None)."""
#        key = str(key).title()
#        h = self.get(key)
#        if h is None:
#            return []
#        return header_elements(key, h)

#TODO: remvoe or make it classmethod
def parse_headers(data):
    headers = Headers([])

    for line in data.split("\r\n"):
        if line[0] in " \t":
            # It's a continuation line.
            v = line.strip()
        else:
            k, v = line.split(":", 1) if ":" in line else (line, "")
            k, v = k.strip(), v.strip()

        headers.add_header(k, v)

    return headers

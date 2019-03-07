# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""OS-agnostic, system-level binary package manager."""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from os.path import dirname
import sys

from ._vendor.auxlib.packaging import get_version
from .common.compat import text_type

__all__ = (
    "__name__", "__version__", "__author__", "__email__", "__license__", "__summary__", "__url__",
    "CONDA_PACKAGE_ROOT", "CondaError", "CondaMultiError", "CondaExitZero", "conda_signal_handler",
    "__copyright__",
)

__name__ = "conda"
__version__ = get_version(__file__)
__author__ = "Anaconda, Inc."
__email__ = "conda@continuum.io"
__license__ = "BSD-3-Clause"
__copyright__ = "Copyright (c) 2012, Anaconda, Inc."
__summary__ = __doc__
__url__ = "https://github.com/conda/conda"

if os.getenv('CONDA_ROOT') is None:
    os.environ[str('CONDA_ROOT')] = sys.prefix

CONDA_PACKAGE_ROOT = dirname(__file__)


class CondaError(Exception):
    return_code = 1
    reportable = False  # Exception may be reported to core maintainers

    def __init__(self, message, caused_by=None, **kwargs):
        self.message = message
        self._kwargs = kwargs
        self._caused_by = caused_by
        super(CondaError, self).__init__(message)

    if sys.version_info[0] > 2:
        def __repr__(self):
            return '%s: %s' % (self.__class__.__name__, text_type(self))
    else:

        def __unicode__(self):
            res = u'%s: %s' % (self.__class__.__name__, self.message % self._kwargs)
            return res

        def __repr__(self):
            return self.__unicode__().encode('utf-8')

    def __str__(self):
        try:
            if sys.version_info[0] == 2:
                return (self.message % self._kwargs).encode('utf-8')
            else:
                return (self.message % self._kwargs)
        except Exception:
            debug_message = "\n".join((
                "class: " + self.__class__.__name__,
                "message:",
                self.message,
                "kwargs:",
                text_type(self._kwargs),
                "",
            ))
            print(debug_message, file=sys.stderr)
            raise

    def dump_map(self):
        result = dict((k, v) for k, v in vars(self).items() if not k.startswith('_'))
        result.update(exception_type=text_type(type(self)),
                      exception_name=self.__class__.__name__,
                      message=text_type(self),
                      error=repr(self),
                      caused_by=repr(self._caused_by),
                      **self._kwargs)
        return result


class CondaMultiError(CondaError):

    def __init__(self, errors):
        self.errors = errors
        super(CondaMultiError, self).__init__(None)

    def __repr__(self):
        return '\n'.join(text_type(e)
                         if isinstance(e, EnvironmentError) and not isinstance(e, CondaError)
                         else repr(e)
                         for e in self.errors) + '\n'

    def __str__(self):
        return str('\n').join(str(e) for e in self.errors) + str('\n')

    def dump_map(self):
        return dict(exception_type=text_type(type(self)),
                    exception_name=self.__class__.__name__,
                    errors=tuple(error.dump_map() for error in self.errors),
                    error="Multiple Errors Encountered.",
                    )

    def contains(self, exception_class):
        return any(isinstance(e, exception_class) for e in self.errors)


class CondaExitZero(CondaError):
    return_code = 0


ACTIVE_SUBPROCESSES = set()


def conda_signal_handler(signum, frame):
    # This function is in the base __init__.py so that it can be monkey-patched by other code
    #   if downstream conda users so choose.  The biggest danger of monkey-patching is that
    #   unlink/link transactions don't get rolled back if interrupted mid-transaction.
    for p in ACTIVE_SUBPROCESSES:
        if p.poll() is None:
            p.send_signal(signum)

    from .exceptions import CondaSignalInterrupt
    raise CondaSignalInterrupt(signum)

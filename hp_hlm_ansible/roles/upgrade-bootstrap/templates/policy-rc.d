#!/bin/bash
#
# (c) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

DEFAULTS="/etc/default/policy-rc.d"

DO_RUN=check
BEQUIET=
INITSCRIPTID=
ACTION=

SERVICES=""
DEFAULT_BLOCK_ACTIONS=""
# include defaults if available
[ -r "$DEFAULTS" ] && . "$DEFAULTS"

dohelp() {
 #
 # outputs help and usage
 #
cat <<EOF

policy-rc.d, Debian/SysVinit (/etc/rc?.d) initscript subsystem.
Copyright (c) 2015 Hewlett Packard Enterprise Development Company LP

Usage:
  policy-rc.d [options] <initscript ID> <actions> [<runlevel>]
  policy-rc.d [options] --list <initscript ID> [<runlevel> ...]

  initscript ID - Initscript ID, as per update-rc.d(8)
  actions       - Initscript actions. Known actions are:
                      start, [force-]stop, restart,
                      [force-]reload, status
      WARNING: not all initscripts implement all of the above actions.
  runlevel      - Runlevel initscript is being executed under

Options:
  --quiet
     Quiet mode, no error messages are generated.
  --help
     Outputs help message to stdout
  --list
     instead of verifying policy, list (in a "human parseable" way) all
     policies defined for the given initscript id (for all runlevels if no
     runlevels are specified; otherwise, list it only for the runlevels
     specified), as well as all known actions and their fallbacks for the
     given initscript id (note that actions and fallback actions might be
     global and not particular to a single initscript id).

EOF
}

printerror () {
 #
 # prints an error message
 #  $* - error message
 #
if test x${BEQUIET} = x ; then
    echo `basename $0`: "$*" >&2
fi
}

verifyparameter () {
 #
 # Verifies if $1 is not null, and $# = 1
 #
if test $# -eq 0 ; then
    printerror syntax error: invalid empty parameter
    exit 103
elif test $# -ne 1 ; then
    printerror syntax error: embedded blanks are not allowed in \"$*\"
    exit 103
fi
return
}

check_is_in () {
 #
 # check if a string is in a space separated list of strings
 #
[[ ${2} =~ (^| )"${1}"($| ) ]] && return 0 || return 1
}

get_blocked_actions () {
 #
 # gets the list of blocked actions for the service or default
 # and saves it in the first argument provided
 #
local blocked_actions_var=${2}_block
# nested substitution trick in bash
local blocked_actions=${!blocked_actions_var}
if test "x${blocked_actions}" = "x" ; then
    blocked_actions="${DEFAULT_BLOCK_ACTIONS}"
fi
eval "$1=\${blocked_actions}"
}

state=I
while test $# -gt 0 && test ${state} != IIII ; do
    case "$1" in
      --help)   dohelp
                exit 0
                ;;
      --quiet)  BEQUIET=--quiet
                ;;
      --list)   DO_RUN=list
                ;;
      --*)      printerror syntax error: unknown option \"$1\"
                exit 103
                ;;
        *)      case ${state} in
                I)  verifyparameter $1
                    INITSCRIPTID=$1
                    ;;
                II) verifyparameter "$1"
                    ACTIONS="$1"
                    ;;
                III) verifyparameter $1
                    RUNLEVEL=$1
                    ;;
                esac
                state=${state}I
                ;;
    esac
    shift
done

if test "x${INITSCRIPTID}" = "x" ; then
    printerror syntax error: must provide an INITSCRIPTID argument
    exit 103
fi

if test "x${DO_RUN}" = "xlist" ; then
    if check_is_in "${INITSCRIPTID}" "${SERVICES}" ; then
        get_blocked_actions BLOCKED_ACTIONS "${INITSCRIPTID}"
        printf "service ${INITSCRIPTID}:\n"
        printf "    runlevel: all\n"
        printf "    deny actions: ${BLOCKED_ACTIONS}\n"
    else
        printf "no policy defined for initscript ID: ${INITSCRIPTID}\n"
    fi
    exit 0
fi

if test "x${SERVICES}" = "x" ; then
    # no services defined to block, so return straight away
    exit 0
fi

if test "x${ACTIONS}" = "x" ; then
    printerror syntax error: <ACTIONS> required
    exit 103
fi

# NOTE: this construct requires bash
if check_is_in "${INITSCRIPTID}" "${SERVICES}" ; then
    get_blocked_actions BLOCKED_ACTIONS ${INITSCRIPTID}
    for action in ${ACTIONS} ; do
        if check_is_in "${action}" "${BLOCKED_ACTIONS}" ; then
            echo "blocking '${action}' for ${INITSCRIPTID}" >&2
            exit 101
        fi
    done
fi

echo "Allowing '${ACTIONS}' for ${INITSCRIPTID}" >&2
exit 0

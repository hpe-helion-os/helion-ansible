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

import datetime
import os
import copy
import time
import sys
import socket
import threading
import tempfile
import uuid
import subprocess
import getpass
import shutil
from subprocess import CalledProcessError

from vertica.network.scp import Scp
from vertica.tools import DBfunctions
from vertica.config import DBinclude
from vertica.config import DBname
from vertica.config import VDatabase
import re # regular expressions
import vsql
from vertica.log.BasicLogger import BasicLogger
from vertica.log.SysLogger import SysLogger

from vertica.network.adapters import *
from vertica.network import adapterpool
from vertica.network import SystemProfileFactory
from vertica.config.Configurator import Configurator
from vertica.shared.termcolor import colored
from vertica.shared.util import shell_repr
from vertica.shared import vconst
from vertica.system import ifconfig


import traceback

# Constant definition
TERMINAL_PROMPT = "(?i)terminal type\?"
SSH_NEWKEY = "(?i)are you sure you want to continue connecting"
STOP_JOBS = "(?i)there are stopped jobs"
PASSWORD = "(?i)password"
PERMISSION_DENIED = "(?i)permission denied"

binDir = DBinclude.binDir
interactive = True

def agentMsgFormatSendMultiNodeInfo(nodeInfoList, type, state, dbName="", maxSteps=1, currStep=1, msg="", logger=BasicLogger()):

      try:
          for theNodeInfo in nodeInfoList:
              theNode = theNodeInfo[0]
              theHost = theNodeInfo[1]
              theMsg = agentMsgFormat(theNode, type, state, dbName, maxSteps, currStep, msg, theHost)
              logger.event("Status", theMsg)
      except:
          pass


def agentMsgFormatSendMultiNode(nodeList, type, state, dbName="", maxSteps=1, currStep=1, msg="", logger=BasicLogger()):
      for theNode in nodeList:
         theMsg = agentMsgFormat(theNode, type, state, dbName, maxSteps, currStep, msg)
         logger.event("Status", theMsg)


def agentMsgFormatSendMultiHost(hostList, type, state, dbName="", maxSteps=1, currStep=1, msg="", logger=BasicLogger()):

      theNode = None;
      if dbName == None or dbName == "":
        return
      try:
        ci = Configurator.Instance()
        dbDict = ci.getconfig(dbName)
        siteConfigs = dbDict['nodes_new']

        for theHost in hostList:
           theNode = None
           for site in siteConfigs:
              if site['host'] == theHost:
                 theNode = site['id']
                 break
           theMsg = agentMsgFormat(theNode, type, state, dbName, maxSteps, currStep, msg, theHost)
           logger.event("Status", theMsg)
      except:
        pass


def agentMsgFormat(node, type, state, dbName="", maxSteps=1, currStep=1, msg="", host=None):
      try:
         msgFormat = '{"type":"%s", "state":"%s"' % (type, state)
         if type == "NODEHOST":
            if host == None:
              ci = Configurator.Instance()
              hostDict = ci.getsiteconfig(node);
              host = hostDict['host']
            msgFormat += ', "host":"%s", "node":"%s"' % (host, node)

      except Exception, ee:
         print "In AgentMsgFormat Exception"
         print ee 
         pass

      msgFormat += ', "dbname":"%s", "msg":"%s", "maxSteps":"%s", "currStep":"%s"}' % (dbName, msg, maxSteps, currStep )
      return msgFormat

 
# returns true if the string corresponds to the "UP" node state
# (do not include READY since the node can't yet initiate requests)
def isUpState( val ):
    return val == "UP" or val == "STANDBY"

# returns true if the string corresponds to a queryable state
def isQueryableState( val ):
    return val == "UP"

# for nodes that are completely down
def isDownState( val ):
    return val == "DOWN"

# returns true if the string corresponds to the "INVALID_LICENSE" node state.
def isNeedLicenseState( val ):
    return val == "VALIDATING LICENSE"

# returns true if the string corresponds to the "INITIALIZING" node state.
def isInitializingState( val ):
    return val == "INITIALIZING"

# returns true if the string corresponds to a recovering node state.
#
# this will work for raw or filtered (human readable) output, because
# we consider RECOVER_ERROR to be OK, since recovery retries several
# times before giving up -- we wouldn't want to report that we're not
# recovering when we are
def isRecoveryState( val ):
    return val in ( "RECOVERING","NEEDS_CATCHUP","RECOVER_ERROR","RECOVERED" )

def rpmVersion( rpmFileName):
    foundOK = False
    brand = None
    version = None
    release = None
    arch = None

    if os.path.isfile('/etc/debian_version'):
        cmd = "dpkg --info " + rpmFileName + " | grep Version"
        try:
            line = os.popen(cmd, 'r').readline().strip()
            line = line.split(":")
            line = line[1].split("-")
            (brand, version, release, arch) = (DBname.package, line[0].strip(), line[1], "all")

            foundOK = True
        except ValueError:
            DBfunctions.record("[rpmVersion] invalid rpm file (%s)provided." % (rpmFileName))
            print "Error: The file provided does not appear to be a valid rpm."
            return (False, None, None, None, None)

    else:
        cmd = "rpm -qp " + rpmFileName + " --qf \"%{NAME} %{VERSION} %{RELEASE} %{ARCH}\\n\""
        #DBfunctions.record("[rpmVersion] %s" % cmd)
        try:
            line = os.popen(cmd, 'r').readline().strip()
            (brand, version, release, arch) = line.split()
            foundOK = True
        except ValueError:
            foundOK = False
            DBfunctions.record("[rpmVersion] invalid rpm file (%s)provided." % (rpmFileName))
            print "Error: The file provided does not appear to be a valid rpm."


    if not foundOK:
        return (foundOK, None, None, None, None)


    if len(brand) > 0 and len(version) > 0 and len(release) > 0 and len(arch) > 0:
       foundOK = True
    else:    #trip it back to false.
       foundOK = False

    try:
       if(version):
          # To allow special RPM names like DEVBRANCHsomethingelse_1_4_1.3.0
          # Wet get rid of the prefix: everything up to the last '_' character inclusive
          r = re.compile('.*_')
          version = r.sub('', version)             
          vals = version.split(".")
          if len(vals) != 3:
             DBfunctions.record("[rpmVersion] can't parse version '%s'" % version)
          else:
             # parse OK, munge string for correct lexicographic comparison
             (maj, min, pat) = vals
             if(maj.isdigit() and min.isdigit() and pat.isdigit()):
                 version = (int(maj), int(min), int(pat))
       if(release and release.isdigit()):
          release = "%03d" % (int(release))
    except:
       DBfunctions.record("[rpmVersion] can't parse integers from version '%s' release '%s'" % (version, release))
    
    return (foundOK, brand, version, release, arch)


################################################################
# Function name: installedVersion
# Description: determine if database system is installed on a given host
# Argument:
#   . userName - the username that we will SSH as.
#   . host
# Return: (foundInstalled, brand, version, release, arch)
################################################################
def installedVersion(host, pool, pkgname=None):
    if pkgname is None:
        # XXX: assuming that local /etc/debian_version means debian on all machines
        if os.path.isfile("/etc/debian_version"):
            pkgname = "dpkg"
        else:
            pkgname = "rpm"

    if "dpkg" == pkgname:
        cmd = "dpkg -l " + DBname.package + " | tail -1 | awk '{print $3}'"
    else:
        cmd = "rpm -q " + DBname.package + " --qf \"%{NAME} %{VERSION} %{RELEASE} %{ARCH}\\n\""


    foundInstalled = False
    installedBrand = None
    installedVersion = None
    installedRelease = None
    arch = None

    with pool.setHosts([host]):
        (status, host_results) = pool.execute(cmd, info_msg="package version check")
        output = ' '.join(host_results[host][1])

        if output.find("waiting for shared lock on") >= 0 :
            # VER-3753. Rpm request may fail with the following warning: waiting
            # for shared lock on /var/lib/rpm/Packages so we wait and try again
            time.sleep(5)
            (status, host_results) = pool.execute(cmd, info_msg="retry package version check")
            output = ' '.join(host_results[host][1])

    # not installed at all.
    if output == "<none>" or output.find("is not installed") >= 0:
        DBfunctions.record("[SSH.installedVersion] package not installed")
        return (False, None, None, None, None)

    # Fill in the number vector
    vec = output.split('\n')[0].split()

    # for dpkg, we have to split up the string that's returned
    if "dpkg" == pkgname:
        verstring = vec[0]
        vec = []

        # changed this for Deb 5 and vertica 4.
        vervec = verstring.split("-")

        # parse out the Version string
        vec.append(DBname.package)
        vec.append(vervec[0])
        vec.append(vervec[1])
        vec.append("all")

    # verify it's been filled. If not, uh... claim it's not installed.
    if len(vec) != 4:
        DBfunctions.record("[SSH.installedVersion] ERROR parsing len vec is %d vec is '%s'!" % (len(vec), "**".join(vec)))
        return (False, None, None, None, None)

    (installedBrand, installedVersion, installedRelease, arch) = vec

    # now handling installedVersion - turning it into a tripple of ints.
    try:
        if installedVersion:
            # To allow special RPM names like DEVBRANCHsomethingelse_1_4_1.3.0
            # Wet get rid of the prefix: everything up to the last '_' character inclusive
            r = re.compile('.*_')
            installedVersion = r.sub('', installedVersion)
            vals = installedVersion.split(".")
            if len(vals) != 3:
                DBfunctions.record("[installedVersion] can't parse version '%s'" % installedVersion)
            else:
                # parse OK, munge string for correct lexicographic comparison
                (maj, min, pat) = vals
                if maj.isdigit() and min.isdigit() and pat.isdigit():
                    installedVersion = (int(maj), int(min), int(pat))
        if installedRelease and installedRelease.isdigit():
            installedRelease = "%03d" % int(installedRelease)
    except:
        DBfunctions.record("[installedVersion] can't parse integers from version '%s' release '%s'" %
                (installedVersion, installedRelease))

    return (True, installedBrand, installedVersion, installedRelease, arch)

################################################################
# Function name: installRPM
# Description: install on a given machine
# Used by installNode only
################################################################
def installRPM(pool, host, rpmFile):

    with pool.setHosts([host]):
        (status, _) = pool.execute("[ -f '/etc/debian_version' ]",
                info_msg="determine dpkg vs rpm")

    if status:
        # debian: /etc/debian_version was found.
        pkgname = 'dpkg'
        cmd = "dpkg -i %s" % rpmFile
    else:
        pkgname = 'rpm'
        cmd = "rpm --upgrade %s" % rpmFile

    (status, host_results) = pool.execute(cmd, info_msg="rpm installation")
    output = ' '.join(host_results[host][1])

    # Not sure why we allow output to be None
    lower_out = output.lower()
    if not status or 'error' in lower_out or 'failed' in lower_out:
        return "(%s) Installation failed: %s" % (host, output)

    #
    # Now go check what version of the software is installed by querying the
    # package manager.  We should find that vertica is installed, now.
    #
    (installed, brand, version, release, arch) = \
            installedVersion(host, pool, pkgname=pkgname)

    if not installed:
        DBfunctions.record("[installRPM] installedVersion reports not installed")
        return "Post-install check failed."

    DBfunctions.record("[installRPM] installedVersion reports: %s %s %s %s %s" %
            (installed, brand, version, release, arch))

    return None

def checkVerticaProcessRunning(inputNodes, catalogpath, catalogs, userName, logger=BasicLogger()):
    """Checks if Vertica processes are running on the provided nodes.

    The vertica processes are found in ps and only those processes using the
    associated catalog path are selected.

    `inputNodes`
        a list of hostnames
    `catalogpath`
        the common catalog path prefix
    `catalogs`
        a corresponding list of catalog paths. Must be the same length as
        `inputNodes`
    `userName`
        The userName to use to connect to the host.

    returns (bool, hostlist) where hostlist is the hosts with vertica still
    running and bool True of hostlist is non-empty, False otherwise.
    """

    pool = adapterpool.AdapterConnectionPool_3.Instance()
    pool.connect2(
          inputNodes, userName,
          None, logger=get_logger()
    )

    # building commands to run
    cmds = {}
    for (host, catalog) in zip(inputNodes, catalogs):
        # XXX: Why are we ignoring hosts which we aren't connected to?
        # Shouldn't this be an error? We didn't even check the results of
        # connect2, above.  Yikes.
        if not pool.is_connected(host):
            continue

        catalog = os.path.join(catalogpath, catalog)

        # Check for vertica by using the `vertica --status` command.  But don't
        # trust it.  If it says vertica is not running, check `ps` for a running
        # vertica process with the catalog as an argument.
        #
        # TODO: Why fall back to `ps`?  If the binary doesn't exist, vertica is
        # clearly not running.  If it does, it should answer correctly, no?
        statuscmd = "%s --status -D %s" % (os.path.join(DBinclude.binDir, DBname.BINARY_NAME), catalog)
        pscmd =  "ps -C \"%s\" -o args | grep -F \"%s\"" % (DBname.BINARY_NAME, catalog)
        cmds[host] = ["%s || %s" % (statuscmd, pscmd)]

    status, result = pool.execute(cmds)

    # Seeing which nodes have vertica running
    stillUpNodes = []
    for host in result.keys():
        # errcode 0 exits have vertica running.
        if result[host][0][0] != '0':
            continue
        stillUpNodes.append(host)
        DBfunctions.record ("[SSH.checkVerticaProcessRunning] Vertica running on %s:  %s" % (host, result[host][1]))

    return len(stillUpNodes) > 0, stillUpNodes


################################################################
# Function name: checkForRunning
# Description:
#
# Connects to spread and checks the status of all hosts in the
# specified database. Returns one of the above CHECK_FOR_RUNNING
# constants.
#
# It will try up to MAXTRIES times to find one node that is up. Once 
# all nodes are up it will return CHECK_FOR_RUNNING_ALLUP, and once at
# least one node is up and all others are up or recovering, if will
# return CHECK_FOR_RUNNING_UPRECOVERING
#
# If after MAXTRIES, all nodes are down, it returns
# CHECK_FOR_RUNNING_ALLDOWN and the list of the down nodes.
#
# If there are some number of nodes that are neither up or down, it
# prompts the user if they want to keep waiting (and suggests that
# they do). If they choose not to wait, we return
# CHECK_FOR_RUNNING_PARTIAL with an empty list.
################################################################

# checkForRunning return code: all nodes are up
CHECK_FOR_RUNNING_ALLUP = 1;

# checkForRunning return code: no node is up.
CHECK_FOR_RUNNING_ALLDOWN = 2; 

# checkForRunning return code: no node is up, but they are not all
# down. This is an indeterminate state, usually indicates a problem...
CHECK_FOR_RUNNING_PARTIAL = 3;

# checkForRunning return code: at least one node is up and all others
# are up or in a recovering state
CHECK_FOR_RUNNING_UPRECOVERING = 4;

# checkForRunning return code: at least one node is in an INITIALIZING
# state (can indicate a cluster catalog inconsistency)
CHECK_FOR_RUNNING_SOMEINIT = 5;

# need to provide a valid license
CHECK_FOR_LICENSE = 6;

CHECK_FOR_RUNNING_KSAFE = 7;

CHECK_FOR_RUNNING_STATE_UNKNOWN = "DOWN"
CHECK_FOR_RUNNING_STATE_LOSTCONTACT = "LOSTCONTACT"
# max times we will try between asking the user if they want to continue
CHECK_FOR_RUNNING_MAXTRIES = 10 

CHECK_FOR_RUNNING_SLEEP_MODIFIER = 2
CHECK_FOR_RUNNING_SLEEP_TIME = 1

def checkForRunning( dbName, nodeMap, port, askForContinue=True, KSafety=0, procCheck=None, logger=BasicLogger(), requires_all_up=False):
      nodeState = { node: CHECK_FOR_RUNNING_STATE_UNKNOWN for node in nodeMap.iterkeys()}
      someInitializing = False

      # Since nodes could take a long time to come up, we sit in a loop
      # here waiting. We ask the user if they want to continue waiting.

      userSaysContinue = True
      while userSaysContinue:
         upNodeList = {}
         for curTry in range(0, CHECK_FOR_RUNNING_MAXTRIES):
            
            # increase sleep timeout for each check.
            # this should give us a good 110s total of looking for
            # a valid  startup
            time.sleep(CHECK_FOR_RUNNING_SLEEP_TIME * CHECK_FOR_RUNNING_SLEEP_MODIFIER * curTry)
            
            # retrieve info from spread
            observeddbname, newNodeState = checkDatabaseState(dbName, nodeMap, port);
            #DBfunctions.record("[SSH.checkForRunning] procInfo: %s" % procInfo)

            # gather new states for each of the nodes in the specified database
            for curNodeName,curNodeState in newNodeState.iteritems():
               if isUpState(curNodeState):
                   upNodeList[curNodeName] = 1

            # if we have nodes in the old node state that we don't have
            # in the new node state, that means that a node we previously
            # saw has gone away. If this happens, update our view of
            # things to be LOSTCONTACT
            for curNodeName,curNodeState in nodeState.iteritems(): # each node we know about
               if curNodeName not in newNodeState: # missing node
                  if (curNodeState == CHECK_FOR_RUNNING_STATE_UNKNOWN):
                     newNodeState[curNodeName] = curNodeState # still heard nothing
                  else: # had heard something, but not this time
                     newNodeState[curNodeName] = CHECK_FOR_RUNNING_STATE_LOSTCONTACT

            # now we are sure that newNodeState has the same values
            nodeState = { node: state for node,state in newNodeState.iteritems() if node in nodeMap }

            # form and print a nodeStatusString
            nodeStatusString = "\tNode Status: "
            sortedkeys = nodeState.keys()
            sortedkeys.sort()
            for node in sortedkeys:
                state = nodeState[node]
                nodeStatusString = nodeStatusString + "%s: (%s) " % (node, state)
                theMsg = agentMsgFormat(node, "NODEHOST", state, dbName=dbName)
                logger.event("Status", theMsg) 
                
            print nodeStatusString
            DBfunctions.record("[SSH.checkForRunning] nodeStatusString: %s" % nodeStatusString)

            # count up, recovered, and initializing nodes
            upNodes = 0
            downNodes = 0
            recNodes = 0
            lostNodes = 0
            initNodes = 0
            needLicenseNodes = 0
            for node,state in nodeState.iteritems() :
               if isUpState(state):
                  upNodes += 1
               elif isDownState(state):
                  downNodes += 1
               elif isRecoveryState(state):
                  recNodes += 1
               elif isNeedLicenseState(state):
                  needLicenseNodes += 1
               elif state == CHECK_FOR_RUNNING_STATE_LOSTCONTACT:
                  lostNodes += 1
               elif isInitializingState(state):
                  initNodes += 1

            if lostNodes == len(nodeState):
               # short circuit remaining loops - go check if vertica is
               # still running at all 
               (status, stillUpNodes) = checkVerticaProcessRunning(procCheck[0], procCheck[1], procCheck[2], procCheck[3], logger=logger)
               if  not status:
                  break
                 
            # if all nodes are in the UP state, we are good
            if upNodes == len(nodeState):
               return CHECK_FOR_RUNNING_ALLUP

            # if all nodes need a License 
            if needLicenseNodes:
               return CHECK_FOR_LICENSE

            # if at least one node is in the UP state and the rest are
            # RECOVERING/DOWN, we are also good
            if (not requires_all_up) and ( upNodes + recNodes > len(nodeState) and upNodes > 0):
               return CHECK_FOR_RUNNING_UPRECOVERING

            if initNodes > 0:
               someInitializing = True

         # out of loop, determine if any node is in a state that is
         # down (either UNKNOWN or LOSTCONTACT)
         anyNodeNotDownFlag = False
         for node in nodeState:
            if not (nodeState[node] == CHECK_FOR_RUNNING_STATE_UNKNOWN or
                    nodeState[node] == CHECK_FOR_RUNNING_STATE_LOSTCONTACT):
               DBfunctions.record("[SSH.checkForRunning]: node %s not down (%s)" % 
                                  (node, nodeState[node]))
               anyNodeNotDownFlag = True

         # if all nodes are down, we are done
         # except in the case of VER-5512 where a database might be _really_
         # slow to initialize, in which case, we want to see if the vertica
         # process is still running - it which case, its probably in 'someinit' mode.
         stillUpNodes = []
         if (not anyNodeNotDownFlag):
            if askForContinue and procCheck != None:
                (status, stillUpNodes) = checkVerticaProcessRunning(procCheck[0], procCheck[1], procCheck[2], procCheck[3], logger=logger)
                if status:
                    anyNodeNotDownFlag = True
                else:
                    DBfunctions.record("[SSH.checkForRunning]: bad news, all nodes down")
                    return CHECK_FOR_RUNNING_ALLDOWN

            else:
                DBfunctions.record("[checkForRunning]: bad news, all nodes down")
                return CHECK_FOR_RUNNING_ALLDOWN

         # When we get here, we have tried MAXTRIES times for a nodes
         # to be up and there is at least one node that is not
         # down. Ask the user if they want to continue waiting:
         if (anyNodeNotDownFlag):
            if askForContinue: 
                downNodes = [node for node in nodeState if node not in upNodeList]
                downCount = len(downNodes)
                if len(upNodeList.keys()) > 0:
                    logger.display("Nodes UP: %s" % (', '.join(upNodeList.keys())))

                if len(stillUpNodes) > 0:
                    logger.display("Nodes in TRANSITIONAL state: %s" % (', '.join([ n for n in stillUpNodes if not n in upNodeList ])))

                logger.display("Nodes DOWN: %s (may be still initializing)." % (', '.join(downNodes)))
                if downCount > KSafety:
                    print "It is suggested that you continue waiting."
                    sys.stdout.write("Do you want to continue waiting? (yes/no) [yes] ")
                    answer = sys.stdin.readline().strip().upper()
                    if not (answer == "YES" or answer == "Y" or answer == ""):
                       userSaysContinue = False
                else:
                    #self.logger.display("Database K-Safety is: %s. "%KSafety)
                    #self.logger.display("K-safety property of vertica database will let you continue the operations")
                    #if downCount ==1 :
                    #    self.logger.display("Node %s is down."%(', '.join(downNodes)))
                    #else:
                    #    self.logger.display("Nodes %s are down."%(', '.join(downNodes)))
                    userSaysContinue = False
                    return CHECK_FOR_RUNNING_KSAFE
            else:
                # ick - in non interactive mode, QA wants us to wait here.. could be a very
                # long wait for long recoveries.
                downCount = len(nodeState) - len(upNodeList)
                if downCount > KSafety:
                    userSaysContinue = True
                else:
                    userSaysContinue = False
                    return CHECK_FOR_RUNNING_KSAFE

      # If we get here, there is at least one bad host and the user
      # doesn't want to wait any longer
      DBfunctions.record("[checkForRunning] at least one bad host, user doesn't want to keep waiting")

      if(someInitializing):
         return CHECK_FOR_RUNNING_SOMEINIT
      
      return CHECK_FOR_RUNNING_PARTIAL



   # uses spread to check that all the nodes in a database are down. If
   # after polling spread up to MAXTRIES times waiting for all nodes to
   # be down they are all down, returns a 2-tuple of
   # CHECK_FOR_RUNNING_ALLDOWN,[]. If after polling at least one node
   # is not down returns CHECK_FOR_RUNNING_PARTIAL and the list of
   # nodes that are still not down
def checkForNotRunning( dbName, nodeMap, port, logger=BasicLogger()):
       upNodes = []
       for curTry in range(0, CHECK_FOR_RUNNING_MAXTRIES):
           
           time.sleep(CHECK_FOR_RUNNING_SLEEP_TIME * CHECK_FOR_RUNNING_SLEEP_MODIFIER * curTry)
           
           DBfunctions.record("[checkForNotRunning] Checking for not running ")
           observeddbname, nodeStatus = checkDatabaseState(dbName, nodeMap, port)
           
           upNodes = [node for node,state in nodeStatus.iteritems() if state != "DOWN"]
           # basically, if we have information for any of the nodes, they aren't down
           if not upNodes:
               DBfunctions.record("[checkForNotRunning]  all nodes down")
               return CHECK_FOR_RUNNING_ALLDOWN, []
           
           # if we do have some proc info, tell the user about it
           nodeStatusString = "\tNode Status: "
           sortedkeys = nodeStatus.keys()
           sortedkeys.sort()
           for node in sortedkeys:
               state = nodeStatus[node]
               nodeStatusString = nodeStatusString + "%s: (%s) " % (node, state)
               theMsg = agentMsgFormat(node, "NODEHOST", state, dbName=dbName)
               logger.event("Status", theMsg)

          
           print nodeStatusString
           DBfunctions.record("[checkForNotRunning] node status: %s" % nodeStatusString)
               
       # at the end of the loop, if we haven't seen all nodes go down,
       # return partial and the list of nodes that are still up
       DBfunctions.record("[checkForNotRunning] some nodes not down after MAX tries: '%s'" % upNodes)
       return CHECK_FOR_RUNNING_PARTIAL, upNodes

#################################
# Start database on given nodes #
# (NEW) BV 08/12/2013           #
#################################
def startDatabaseNodes( db, startHostList, userName, clusterStart,  # starting single nodes is not clusterStart
                        lastEpoch=None, # None means don't start db using -S flag
                        delete_corrupted_data=False, # False means no -c flag
                        logger=BasicLogger()):

    # get full list of hosts and determine "initiator"
    allhosts = db.getHosts()
    myHostName = allhosts[0]
    for h in allhosts:
        if DBfunctions.IsLocalHost(h):
            myHostName = h

    # discover hosts that are down (not SSH'able)
    pool = adapterpool.AdapterConnectionPool_3.Instance()
    pool.connect2(
          allhosts,userName,
          None, logger=get_logger()
    )
    downHosts = []
    for host in allhosts:
        if not pool.is_connected(host):
            logger.display("Could not login with SSH to host %s \n " % (host))
            downHosts.append(host)

    # discover nodes
    logger.display( "\tStarting nodes: ")
    largeCluster = db.isLargeCluster()
    startNodeList = []
    downNodes = []
    for n in db.nodes:
        opts = ""
        if n.host in downHosts:
            opts += " ***UNAVAILABLE***"
            downNodes.append(n.name)
        if n.host in startHostList:
            if n.host not in downHosts:
                startNodeList.append(n)
            if largeCluster and n.oid == n.controlnode:
                opts += " [CONTROL]"
            logger.display( "\t\t%s (%s)%s"% (n.name, n.host, opts))
         
    # confirm that starting this set of nodes satisfies quorum & node deps
    nHosts = len(allhosts)
    nDown  = len(downHosts)
    KSafety = db.getK()

    logger.debug("KSafety: %s Total hosts:%s Down hosts:%s"%(KSafety,nHosts,downHosts))

    if clusterStart:  # don't bother with check if cluster is already up
        # start with cluster partition check
        if nHosts - nDown <= nDown:
            logger.display("The cluster is partitioned with %s down.  Over half (%s/%s) of the nodes must be available." % (', '.join(downHosts), nHosts//2 + 1,nHosts))
            return False, int(KSafety), "Cluster partitioned."

        # then look to dependencies
        failures = db.findUnsatisfiedDependencies(downNodes)
        if failures:
            logger.display("The cluster cannot start due to failed dependencies:\n%s"%(" AND\n".join(["One of %s must be available" % ", ".join(x) for x in failures])))
            return False, int(KSafety), "Failed node dependency checks."

    if not startNodeList:
        logger.display("\nAll nodes to start have failed startup tests.  Nothing to do.")
        return False, KSafety, "Failed startup tests. Nothing to do." 

    # run simplified version check: vertica -V must be IDENTICAL for ALL NODES in the database
    vcheckcmds = { h: "%s -V"%(os.path.join(DBinclude.binDir,"vertica")) for h in allhosts}
    pool.setHosts(allhosts)
    (status, res) = pool.execute (vcheckcmds)
    agreedversion = None
    for host,response in res.iteritems():
        if host in downHosts:
              continue
        if response[0]!= "0":
            logger.display("Error: %s failed; %s not installed on %s" % (vcheckcmds[host],DBname.dbname,host))
            return False, KSafety, "%s not installed" % DBname.dbname
        elif not agreedversion:
            agreedversion = (host, response[1])
        elif agreedversion[1] != response[1]:
            logger.display("""Error: version mismatch
%s: %s
%s: %s"""%(agreedversion[0],agreedversion[1],host,response[1]))
            return False, KSafety, "Version mismatch"
    
    # check to see if the vertica process is running on the remote systems first.
    stillUpNodes = []
    cmds = { node.host: node.statusDbStr(os.path.join(DBinclude.binDir, DBname.BINARY_NAME)) for node in startNodeList}
    status, result = pool.execute(cmds)

    for host,response in result.iteritems():
        if response[0] == '0': #look only for errcode 0 exits - these are the running hosts.
            stillUpNodes.append(host)
            DBfunctions.record ("[SSH.StartDatabaseNodes] Vertica running on %s:  %s" % (host, response[1]))

    if stillUpNodes:
        logger.display("""Error: the vertica process for the database is running on the following hosts:
%s
This may be because the process has not completed previous shutdown activities.  Please
wait and retry again.

""" % "\n".join(stillUpNodes))
        return False, KSafety, "Processes still running."
          
    # compute extra options passed to vertica startup
    extras = ""
    if delete_corrupted_data:
        extras += " -c"
    if lastEpoch:
        extras += " -S %s" % lastEpoch

    # send start commands
    cmds = {}
    for node in startNodeList:
        cmdlist = [DBinclude.binPathCmdSetting+"",        # set path                    - necessary?
                   "chmod 700 %s"%node.catalogpath,       # (re)establish cat dir perms - necessary?
                   node.startDbStr(extras)]               # run db start command
        #print "%s - %s"%(node.host,node.startDbStr(extras))
        logger.info("%s - %s"%(node.host,node.startDbStr(extras)))
        cmds[node.host] = "(" + to_echo(cmdlist) + ") | sh "

    logger.display( """
\tStarting Vertica on all nodes. Please wait, databases with large catalogs may take a while to initialize.
""" )

    status, result = pool.execute(cmds)
    pool.resetHosts()

    return status, KSafety, result

# Please ignore that this function exists.  It was originally part of netverify,
# which we have taken out back to be shot.  However, it became used by
# startDBMultiNodes, and we don't know how to get rid of it yet.
def to_echo(lines):
    cmd = ""
    for l in lines:
        nl = ""
        for c in l:
            #if c == "\"": nl += "\\"
            nl += c
        if cmd != "": cmd += " && "
        cmd += "echo \'" + nl + "\'"
    return cmd

def deleteClusterConfiguration( fileName, dirName, nodeHostList, userName):
      """ for some reason, just run an rm -rf on the given file """
      for host in nodeHostList:
           connection = adapterpool.DefaultAdapter(host, logger=get_logger())
           try:
               connection.connect( host, userName, None )
           except:
               continue
           cmd = "rm -rf " + os.path.join(dirName,fileName)
           connection.execute( cmd )

def scpToPool(pool, filename):
    """scp the local file `filename` to all nodes in the pool."""

    try:
        dest_hosts = pool.remote_connected_hosts()

        if len(dest_hosts) == 0:
            # all hosts were local. Nothing to do.
            return

        adapterpool.copyLocalFileToHosts(pool, filename, dest_hosts, filename)
    except Exception, e:
          DBfunctions.record("[scpToPool] failure %s" % e)
          DBfunctions.record("[scpToPool] You will need to manually synch your admintools meta data.")


def parseClusterStatusSummary(summary,target):
    # did the node know about only itself?
    if summary.startswith("--"):
        return "UNKNOWN", {target: summary[2:]}
    dbname = re.findall(r"^Cluster State: (\S+)",summary,re.S|re.M)
    if not dbname:
        return "UNKNOWN", {target: "UNKNOWN"}
    dbname = dbname[0]
    # break out lines
    result = {}
    lines = re.findall(r"^(\S+): ([0-9]+) of ([0-9]+) \(([\S,_ ]*)\)",summary,re.S|re.M)
    for line in lines:
        for node in line[3].split(","):
            result[node.strip()] = line[0]
    return dbname, result

def collectProcessResult(largs,myenv):
    try:
        result = subprocess.check_output(largs,
                                         stderr=subprocess.STDOUT,
                                         env=myenv)
        return 0, result
    except CalledProcessError, e:
        return e.returncode, e.output

def checkDatabaseState(dbName, nodemap, port):
    DBfunctions.record (
            "[SSH.checkDatabaseState] dbName=%s, port=%s, nodemap=%r" % (
            dbName, port, nodemap))

    unknowns = dict(nodemap)
    nodestates = {}
    myenv = dict(os.environ)
    myenv["VSQL_OPTIONS"]="clusterstatus"
    args = [os.path.join(DBinclude.binDir,"vsql"),
            "--no-vsqlrc",
            "-n",
            "-p","%d"%port]
    while unknowns:
        # pick a target to connect to
        target,targethost = unknowns.popitem()
        summary = ""
        # attempt connection, asking about query state
        largs = [x for x in args]
        largs.append("-h")
        largs.append(targethost)
        if dbName:
            largs.append(dbName)
        DBfunctions.record ("[SSH.checkDatabaseState] vsql_cmd = %s" % shell_repr(largs))
        ret = collectProcessResult(largs,myenv)
        DBfunctions.record ("[SSH.checkDatabaseState] vsql return code = %s" % ret[0])
        # if failed to connect -- look for hint
        #print proc.returncode, result
        if ret[0] == 2:
            summary = re.findall(r'^HINT:  (.*)----', ret[1], re.S | re.M)
            if summary:
                summary = summary[0]     # should only be one match
            else:
                nodestates[target] = "DOWN"
        # if we got a summary, it contains information about a lot of nodes
        if summary:
            newdbName,newnodestates = parseClusterStatusSummary(summary,target)
            if not dbName:          # did we not know the running db?
                dbName = newdbName
            elif dbName != newdbName and newdbName != "UNKNOWN":  # wrong dbname?
                return newdbName, {}
            for node,state in newnodestates.iteritems():
                nodestates[node] = state
                if node in unknowns:
                    del unknowns[node]
    return dbName,nodestates

def installLicense(licenseFile, host, portNo, dbName, DBpassword, logger=BasicLogger()):
      if(licenseFile != None):
              
          cmd = "select install_license('%s');" % licenseFile
          vsqlQuery = vsql.vsql(None, host, dbName, DBpassword, portNo)
          ret = vsqlQuery.executeSql(cmd)
          DBfunctions.record ("[SSH.createDBMultiNodes] install license return '%s'" % ret)
          return ret
              
      else:
          logger.error("[SSH.createDBMultiNodes] valid license file must be provided.")
          DBfunctions.record ("[SSH.createDBMultiNodes] valid license file must be provided.")
          print "\tERROR:  Database requires valid license file!"
          return CHECK_FOR_LICENSE

def getNetworkProfiles(nodeHosts, userName, subnet):
    def choose_addr_bcast(host, interfaces):
        """
        Returns a suitable (addr, broadcast).

        If the requested broadcast address (`subnet`) is found, the address
        for that entry is used.  Otherwise the address which matches the host
        is used.
        """
        answer = None
        for (name, iface) in interfaces.iteritems():
            if answer is None and iface['address'] == host:
                answer = iface
            if iface['broadcast'] == subnet:
                answer = iface

        if answer is None:
            raise StandardError("Could not find a suitable network interface: %s" % host)

        return [answer['address'], answer['broadcast']]

    try:
        pool = adapterpool.AdapterConnectionPool_3.Instance()
        pool.connect2(
              nodeHosts, userName,
              None, logger=get_logger()
        )
        with pool.setHosts(nodeHosts):
            hostnets = {}

            # run ip on all nodes
            cmd = 'LANG=C ' + shell_repr(ifconfig.get_ipv4_interfaces_cmd())
            (status, res) = pool.execute(cmd)
            print cmd
            for (host, (rcode, lines)) in res.iteritems():
                if str(rcode) != '0':
                    print('Raising StandardError')
                    raise StandardError("Unable to run /sbin/ip on node %s: %s"
                            % (host, lines) )
                while True:
                    try:
                        output = "\n".join(lines)
                        interfaces = ifconfig.get_ipv4_interfaces_str(output)
                        hostnets[host] = choose_addr_bcast(host, interfaces)
                        break
                    except StandardError as err:
			# Try removing the last line
                        lines = lines[:-1]
                        if not lines:
                            raise err

            return True, hostnets

    except StandardError as err:
        print "\tError: failed to get network profiles"
        print "\t%s" % sys.exc_info()[1]
        return False, "Failed to get network profiles"

def getRemoteVDatabaseCommand(catalogpath):
    return "%s -m vertica.config.VDatabase %s silent"%(DBinclude.PYTHON_BINARY,
                                                       catalogpath)

#
# Input: list of triples (node,host,catalogpath)
# Output: VDatabase,SpreadConfSourceNode,[NodesNeedingSpreadConf]
def computeVDatabase(locations,userName):
    hosts = [x[1] for x in locations]
    hosttoname = { x[1] : x[0] for x in locations }
    locsbyname = { x[0] : x for x in locations }

    pool = adapterpool.AdapterConnectionPool_3.Instance()
    pool.connect2( hosts, userName, None, logger=get_logger())
    
    cmds = {x[1]:getRemoteVDatabaseCommand(x[2]) for x in locations}
    status, res = pool.execute(cmds)
    
    spreadversions = []
    bestspread = ["unknown",0]
    db = VDatabase.VDatabase()
    for host,result in res.iteritems():
        spver = 0
        if result[0] == '0':
            newdb = VDatabase.VDatabase(jsonString="\n".join(result[1]))
            spver  = newdb.spreadversion
            if spver > bestspread[1] or (spver == bestspread[1] and DBfunctions.IsLocalHost(host)):
                bestspread = [hosttoname[host],spver]
            if newdb.betterThan(db):
                db = newdb
        spreadversions.append([hosttoname[host],spver])

    # no db or spread info?
    # eventually, we could repair the spread info from the catalog
    if not db.isValid() or bestspread[1] == 0:
        return db, None, []

    return (db, 
            locsbyname[bestspread[0]], 
            [locsbyname[x[0]] for x in spreadversions if db.isSpreadNode(x[0]) and x[1] < bestspread[1]])

def distributeSpreadConf(bestspread,needspconf,userName,logger = BasicLogger()):
    # for all needspconf
    # scp bestspread[1]:bestspread[2] XXX
    if not needspconf:
        return

    logger.info("Repairing spread.conf for %s from %s(%s)"%(",".join([x[0] for x in needspconf]),
                                                            bestspread[0],bestspread[1]))
    hosts = [bestspread[1]]
    localhost = None
    # if localhost is not a node in the cluster, we will need a temp
    # location to stash the spread.conf
    localfname = os.path.join(DBinclude.CONFIG_DIR,"best.spread.conf.tmp")
    for x in needspconf:
        hosts.append(x[1])
        if DBfunctions.IsLocalHost(x[1]):
            localfname = os.path.join(x[2],"spread.conf")
            localhost = x[1]
    hosts.append(bestspread[1])

    pool = adapterpool.AdapterConnectionPool_3.Instance()
    pool.connect2( hosts, userName, None, logger=get_logger())

    if DBfunctions.IsLocalHost(bestspread[1]):
        localfname = os.path.join(bestspread[2],"spread.conf")
        localhost = bestspread[1]
    else:
        scp = Scp(Scp.INBOUND)
        scp.remote_host = bestspread[1]
        scp.remote_user = userName
        scp.remote_file = os.path.join(bestspread[2],"spread.conf")
        scp.local_file = localfname

        (returncode, output) = scp.run()
        if returncode != 0:
            logger.info("Failed SCP to local temp: %s" % output)

    # copy file out to target nodes
    for l in needspconf:
        if l[0] == bestspread[0]:
            continue  # already repaired
        try:
            destfname = os.path.join(l[2],"spread.conf")
            logger.info("Repairing spread.conf on %s(%s:%s)"%(l[0],l[1],
                                                              os.path.join(l[2],"spread.conf")))
            adapterpool.copyLocalFileToHosts(pool, localfname,
                    [ l[1] ], destfname)
        except:
            traceback.print_exc()
            logger.error( traceback.format_exc() )

###################################################################
# Function name: createDBMultiNodes
# Process:
# 1) bootstrap node 1 on initiator & install license
# 2) start node 1
# 3) wait for node 1 to come up
# 4) configure database cluster options
# 5) create nodes 2-N
# 6) have node 1 generate spread config for cluster
# 7) distribute spread conf to cluster
# 8) start nodes 2-N
# 9) wait for all nodes to join the cluster
# Return:
#   . 1: success
#   . 2: partial success - creation OK, but starting might not be
#   . 0: error
###################################################################
def createDBMultiNodes(
        dbName,         # name of the database (string)
        dbPassword,     # password for dbadmin (string)
        logFile,        # dbLog path (unused)
        catalogPath,    # the initiator's catalog path (minus node name)
        dataPath,       # the initiator's data path (minus node name)
        nodes,
        nodeHosts,
        nodeCatalogs,
        nodeDatas,
        userName,
        host,           # initiator
        spreadInfo,
        password="",
        portNo=0,
        logger=BasicLogger()):

    logger.info ("[SSH.createDBMultiNodes]  dbName '%s', logFile '%s', catalogPath '%s', dataPath '%s', nodes '%s', nodeHosts '%s', nodeCatalogs '%s', nodeDatas '%s', userName '%s', host '%s', spreadInfo '%s', portNo = '%s')" %
             (dbName, logFile, catalogPath, dataPath, nodes,
                 nodeHosts, nodeCatalogs, nodeDatas, userName, host,
                 spreadInfo, str(portNo)))

    success, bcastAddrs = getNetworkProfiles(nodeHosts, userName,
                                             spreadInfo['controlsubnet'])

    if not success:
        return 0, bcastAddrs
    else:
        logger.info("NetworkProfiles: %s"%repr(bcastAddrs))

    idx = 0
    initiatorOffset = -1
    for h in nodeHosts:
        if host == h:
            initiatorOffset = idx
        idx += 1

    if initiatorOffset == -1:
        initiatorOffset = 0
        print "Warning: could not map ", host, " to known nodes"
        print "Using host ", nodeHosts[0], " instead."

    logger.info("\tCreating database", dbName)
    print "\tCreating database", dbName

    ################# step 1: bootstrap node 1 on initiator #############
    connection = adapterpool.DefaultAdapter(host, logger=get_logger())
    try:
        connection.connect( host, userName, password )
    except:
        logger.error("User", userName, "cannot login to host", host)
        print "User", userName, "cannot login to host", host
        return 0, "User %s could not login to host: %s" % (userName, host)

    logger.info(
            "[SSH.createDBMultiNodes] bootstrapping with idx %d node %s on host %s" %
            (initiatorOffset, nodes[initiatorOffset], host))

    # this assumes license.key exists on initiator node
    extraopts = ""    # can add configparams here: "-X VerticaRunsSpread=1"
    if spreadInfo['largecluster']:
        extraopts = extraopts + " -N %s" % spreadInfo['largecluster']
    if spreadInfo['mode'] == 'pt2pt':
        extraopts = extraopts + " -T"
    if spreadInfo['logging'] != 'False':
        extraopts = extraopts + " -l"
    # if we aren't running vertica on usual port, also move spread to relative port
    if portNo != 5433:
        extraopts = extraopts + " -x %s" % (portNo+2)
    cmd = "%s/bootstrap-catalog -C '%s' -H '%s' -s '%s' -D '%s' -S '%s' -L '%s' -p '%s' -c '%s' -B '%s' %s" \
          % (binDir, dbName, host, nodes[ initiatorOffset ], 
             os.path.join(catalogPath, nodeCatalogs[ initiatorOffset ]), 
             os.path.join(dataPath, nodeDatas[ initiatorOffset ]),
             DBinclude.LICENSE_KEY,
             portNo,bcastAddrs[nodeHosts[initiatorOffset]][0],
             bcastAddrs[nodeHosts[initiatorOffset]][1],extraopts)
    logger.info ("[SSH.createDBMultiNodes] bootstrap cmd '%s'" % cmd)
    # Do not show password in log file
    printed_command = cmd
    if dbPassword != "":
        dbPassword1 = vsql.escape_password(dbPassword)
        cmd = cmd + " -A password -a %s " % dbPassword1
    # print the scrubbed command to the log and syslog log
    my_sys_logger = get_logger()
    if my_sys_logger is not None:
        logger.info(printed_command)
        my_sys_logger.info(printed_command)
    status, ret = connection.execute(cmd, info_msg="Bootstrapping database %s" % dbName, hide=True)
    if ret[0] != '0':
          print "ERROR: Unable to bootstrap database: %s" % "\n".join(ret[1])
          logger.info("Unable to bootstrap database: %s" % "\n".join(ret[1]))
          return 0, "Unable to bootstrap database: %s" % "\n".join(ret[1])
    logger.info ("[SSH.createDBMultiNodes] cmd output '%s'" % ret)

    ################ step 2: start node 1 #################

    print "\tStarting bootstrap node %s (%s)" % (nodes[initiatorOffset], host)

    # step 2a: build VDatabase object
    vdcmd = getRemoteVDatabaseCommand(
          os.path.join(catalogPath, nodeCatalogs[ initiatorOffset ])
    )
    status, ret = connection.execute(
          vdcmd, info_msg="Reading bootstrap catalog",
    )
    try:
          db = VDatabase.VDatabase(jsonString="\n".join(ret[1]))
    except ValueError, e:
          print "ERROR: Unable to read bootstrap node metadata"
          logger.info("Unable to read bootstrap node metadata.  Expected JSON DB desc, got: %s"%"\n".join(ret[1]))
          return 0, "Unable to read bootstrap node metadata"
    #print db.toString()

    status, k, results = startDatabaseNodes(db, host, userName, False)

    ############### step 3: wait for node 1 to come up ###############

    process_checker = []
    process_checker.append([host])
    process_checker.append(catalogPath)
    process_checker.append(nodeCatalogs)
    process_checker.append(userName)

    code = checkForRunning(dbName, {nodes[initiatorOffset]:
        nodeHosts[initiatorOffset]}, portNo, askForContinue=interactive,
        KSafety=k, procCheck=process_checker, logger=logger,
        requires_all_up=True)

    logger.info (
            "[SSH.createDBMultiNodes] Checking that initiator node %s is up" % 
            nodes[initiatorOffset])
    if (code != CHECK_FOR_RUNNING_ALLUP):
        DBfunctions.record ("[SSH.createDBMultiNodes] initiator node startup failed. Result %d" % code)
        print "ERROR:  Database did not start cleanly on initiator node!"
        print "        Stopping all nodes"
        vsqlQuery = vsql.vsql(None, host=nodeHosts[initiatorOffset], vsqlOptions="-P pager -A -t",
                              dbName=dbName, dbPassword=dbPassword, dbPort=portNo)
        ret = vsqlQuery.executeSql("select shutdown();")
        vsqlQuery.closeConnection()
        tmpMsg = "Database did not start cleanly on initiator node!  Stopping all nodes"
        if code == CHECK_FOR_LICENSE:
            tmpMsg += "  because the database %s reports an INVALID LICENSE" % dbName
        return 0, tmpMsg 

    # single node db?  we're done
    if len(nodes) == 1:
        return 1, ""

    ############## step 4:  create nodes 2-N ###########

    print "\tCreating database nodes"
    logger.info ("[createDBMultiNodes] making database nodes/sites...")

    # loop, creating nodes
    fail = False
    msg = None
    for i in range(0, len(nodes)):
        if i == initiatorOffset:
            continue

        print "\tCreating node %s (host %s)" % (nodes[i],nodeHosts[i])

        theMsg = agentMsgFormat(nodes[i], "NODEHOST", "CREATING_NODE", dbName=dbName)
        logger.event("Status", theMsg)


        sqlToRun = DBfunctions.makeSqlCreateNode(catalogPath, dataPath,
                                                 nodes[i], nodeHosts[i],
                                                 nodeCatalogs[i], nodeDatas[i],
                                                 bcastAddrs[nodeHosts[i]][0],
                                                 bcastAddrs[nodeHosts[i]][1])

        logger.info (sqlToRun)

        vsqlQuery = vsql.vsql(None, host=nodeHosts[initiatorOffset],
                dbName=dbName, dbPassword=dbPassword, dbPort=portNo)
        ret = vsqlQuery.executeSql(sqlToRun)
        vsqlQuery.closeConnection()
        if ret[0] != '0': # Must be an error
            logger.info ("[createDBMultiNodes] Error create nodes '%s'" % ret[0])
        if ret[1] != None:
            for line in ret[1]:
                logger.info ("[createDBMultiNodes] create nodes return '%s'" % line)
                if line.startswith( 'ROLLBACK' ):
                    msg = line
                    fail = True

    # regenerate spread.conf
    print "\tGenerating new configuration information"
    if not fail:
        vsqlQuery = vsql.vsql(None, host=nodeHosts[initiatorOffset],
                dbName=dbName, dbPassword=dbPassword, dbPort=portNo)
        ret = vsqlQuery.executeSql("select reload_spread(true);")
        vsqlQuery.closeConnection()
        if ret[0] != '0': # Must be an error
            logger.info ("[createDBMultiNodes] Error reload_spread '%s'" % ret[0])
        if ret[1] != None:
            for line in ret[1]:
                logger.info ("[createDBMultiNodes] reload_spread '%s'" % line)
                if line.startswith( 'ROLLBACK:' ):
                    msg = line
                    fail = True

    # step 6: build new VDatabase
    vsqlQuery = vsql.vsql(None, host=nodeHosts[initiatorOffset], vsqlOptions="-P pager -A -t",
                          dbName=dbName, dbPassword=dbPassword, dbPort=portNo)
    db = VDatabase.VDatabase(vsql=vsqlQuery)
    vsqlQuery.closeConnection()
    #print db.toString()

    # weird spread bug workaround.  Hopefully temporary (BV 5/14/2013)
    if spreadInfo['mode'] == 'broadcast':
        # stop bootstrap node
        print "\tStopping bootstrap node"
        vsqlQuery = vsql.vsql(None, host=nodeHosts[initiatorOffset], vsqlOptions="-P pager -A -t",
                              dbName=dbName, dbPassword=dbPassword, dbPort=portNo)
        ret = vsqlQuery.executeSql("select shutdown();")
        vsqlQuery.closeConnection()
        time.sleep(3)

    #
    # copy relevant files from initiator to executors, optionally staging them
    # locally, first.
    #
    def copyCatalogFileToNodes(fname, localfile):
        status = True
        scp = Scp(Scp.OUTBOUND)
        scp.local_file = localfile
        scp.remote_user = userName

        for (i, nh) in enumerate(nodeHosts):
            if host == nh:
                continue # skip the source of the data.
            scp.remote_file = os.path.join(catalogPath, nodeCatalogs[i], fname)
            scp.remote_host = nh
            (returncode, output) = scp.run()
            if returncode != 0:
                print "ERROR: scp to %s catalog failed (%s)" % (nh, localfile)
                status = False

        return status

    tempdir = tempfile.mkdtemp(suffix='.vstage')
    for f in ["vertica.conf","spread.conf"]:
        if DBfunctions.IsLocalHost(host):
            local_file = os.path.join(catalogPath,nodeCatalogs[initiatorOffset],f)
        else:
            # need to bring the remote file local in order to send it out.
            local_file = os.path.join(tempdir, f)
            scp = Scp(Scp.INBOUND)
            scp.local_file = local_file
            scp.remote_file = os.path.join(catalogPath,nodeCatalogs[initiatorOffset],f)
            scp.remote_host = host
            scp.remote_user = userName
            (returncode, output) = scp.run()
            if returncode != 0:
                print "ERROR: SCP to local staging failed: %s" % output
                shutil.rmtree(tempdir, ignore_errors=True)
                return False

        if not copyCatalogFileToNodes(f, local_file):
            print "ERROR: Failed to copy vertica.conf and spread.conf to all nodes"
            return False

    shutil.rmtree(tempdir, ignore_errors=True)

    ################### step 7: start rest of nodes
    print "\tStarting all nodes"
    
    # TODO: make this node based
    startHosts = nodeHosts
    def without(lst,i):
        return lst[:i] + lst[i+1:]
    if spreadInfo['mode'] != 'broadcast':
        startHosts = without(nodeHosts,initiatorOffset)

    status,k,results = startDatabaseNodes(db, startHosts, userName, False)

    # now, verify that all the nodes come back up
    nodeAndHosts = {node: host for node,host in zip(nodes,nodeHosts)}
    code = checkForRunning(dbName, nodeAndHosts, portNo, logger=logger,
            requires_all_up=True)
    if (code != CHECK_FOR_RUNNING_ALLUP):
        logger.info ("[createDBMultiNodes] node creation verification failed. Return code %d" % code)
        if (code == CHECK_FOR_RUNNING_ALLDOWN):
            print "ERROR: All nodes are down. Run scrutinize"
        elif (code == CHECK_FOR_RUNNING_UPRECOVERING):
            print "WARNING: All nodes are not up"
        else:
            # Covers CHECK_FOR_RUNNING_UPRECOVERING case, which shouldn't happen
            print "ERROR: Not all nodes came up, but not all down.  Run scrutinize."
        return 2, "node creation verification failed. Return code %d" % code

    return 1, ""

#################################################################
# Function name: prepareDBs
# Description: Check if rpm is installed on a given host;
#              then create the catalog and data directories
# Argument:
#   . dbName
#   . catalogDir: directory user entered for catalog
#   . catalogSubDir: catalog subdirectory name
#   . dataDir: directory user entered for data
#   . userName: data subdirectory name
#   . host 
#   . password
# Return:
#   . True: success - False: error
#################################################################
def prepareDBs(dbName, catalogDir, catalogSubDir, dataDir, dataSubDir, userName, host, previousHosts, password="", port=None):      
         created = False
         catalogDir = catalogDir.rstrip("/") # /home/dbadmin
         subDBCatalogDir = os.path.join(catalogDir,dbName) # /home/dbadmin/db1
         subCatalogDir = os.path.join(subDBCatalogDir,catalogSubDir) # /home/dbadmin/db1/node1_catalog
         
         dataDir = dataDir.rstrip("/") # /home/dbadmin
         subDBDataDir = os.path.join(dataDir,dbName) ## /home/dbadmin/db1
         subDataDir = os.path.join(subDBDataDir,dataSubDir) # /home/dbadmin/db1/node1_data

         connection = adapterpool.DefaultAdapter(host, logger=get_logger())
         try:
          connection.connect( host, userName, password )
         except:
             print "User", userName, "cannot login to host", host
             return False, "User %s cannot login to host %s" % ( userName, host )

         # Check if catalogDir/dbName directory exists
         if not host in previousHosts: 
            if ( connection.execute( "[ -e %s ]" % subDBCatalogDir)[0]):
                print "Directory", catalogDir, "is invalid because directory", subDBCatalogDir, "already exists on host", host
                return created, "Directory %s is invalid because %s already exists on host %s" % ( catalogDir, subDBCatalogDir, host )
            if ((dataDir != catalogDir) and connection.execute( "[ -e %s ]" % subDBDataDir)[0]):
                print "Directory", dataDir, "is invalid because directory", subDBDataDir, " already exists on host", host
                return created, "Directory %s is invalid because %s already exists on host %s" % ( dataDir, subDBDataDir, host )
    
         # Create catalog and data sub directories
         if (not (makeDirOnHost(subCatalogDir, connection) and makeDirOnHost(subDataDir, connection))):
             return created, "Failed to create catalog or data directories on %s" % host
    
         created = True
    
         # create port file
         if port != None:
             cmd = "echo %s >%s/port.dat" % (str(port), subDBCatalogDir)
             DBfunctions.record ("[prepareDBs] " + cmd)
             (status, result) = connection.execute(cmd)
             s = " ".join( result[1] )
             # TODO: check return value!
    
         # Create logrotate entry, if able
         logrotatedir = os.path.join(DBname.INSTALL_PREFIX,"config/logrotate")
         logrotateDBconffilename = os.path.join(logrotatedir,dbName)
         # if the logrotate dir exists here, assume it exists everywhere
         if(connection.execute( "[ -e %s ]" %logrotatedir)[0] ):
            # Create the logrotate config file for this db
            #
            # NOTE: no ' characters in this config file!
            #
            # TODO: since this is possibly platform-dependent so we
            # should probably have a platform-specific conf file
            # template that we instantiate.
            #
            logrotate_contents = """\
%s/vertica.log %s/UDxLogs/UDxFencedProcesses.log {
    # rotate weekly
    weekly
    # and keep for 52 weeks
    rotate 52
    # no complaining if vertica did not start yet
    missingok
    # compress log after rotation
    compress
    # no creating a new empty log, vertica will do that
    nocreate
    # if set, only rotates when log size is greater than X
    size 10M
    # delete files after 90 days (not all logrotate pkgs support this keyword)
#    maxage 90
    # we have 2 log files to rotate but only signal vertica once
    sharedscripts
    # signal vertica to reopen and create the log
    postrotate
       kill -USR1 `head -1 %s/vertica.pid 2> /dev/null` 2> /dev/null || true
    endscript
}

%s/dbLog {
    # rotate weekly
    weekly
    # and keep for 52 weeks
    rotate 52
    # no complaining if vertica did not start yet
    missingok
    # compress log after rotation
    compress
    # this log is stdout, so rotate by copying it aside and truncating
    copytruncate
}
""" % (subCatalogDir,subCatalogDir, subCatalogDir, subDBCatalogDir)
            cmd = "echo '" + logrotate_contents + "' > %s" % logrotateDBconffilename
            DBfunctions.record ("[prepareDBs] logrotate create file:" + cmd)
            (status, result) = connection.execute(cmd)
            s = " ".join( result[1] )
            if result[0]  != '0':
                DBfunctions.record("[prepareDBs] error creating logrotate config file: %s" % s)
         connection.execute( "touch %s" % DBinclude.ADMINTOOLS_CONF )
         connection.close()
         return created, "Success"

##########################################
# Kills vertica process
##########################################
def killVerticaProcess( dbName, catalogDir, catalogSubDir, userName, host, password=""):
    catalogDir = catalogDir.rstrip("/") # /home/dbadmin
    subDBCatalogDir = catalogDir + "/" + dbName # /home/dbadmin/db1
    subCatalogDir = subDBCatalogDir + "/" + catalogSubDir # /home/dbadmin/db1/node1_catalog

    connection = adapterpool.DefaultAdapter(host, logger=get_logger())
    try:
        connection.connect( host, userName, password )
    except:
        print "User", userName, "cannot login to host", host
        return

    # save dbLog and vertica.log files in adminTools-dbadmin.log file 
    cmd = "[ -e %s/%s.pid ]" % (subCatalogDir, DBname.dbname)
    DBfunctions.record ("[killVerticaProcess] " + cmd)
    (status, res) = connection.execute(cmd)

    if (res[0] == "0"):
        cmd = "cat %s/%s.pid" % (subCatalogDir, DBname.dbname)
        DBfunctions.record ("[killVerticaProcess] " + cmd)
        (status, result) = connection.execute( cmd )
        s = " ".join( result[1] )
        if (status):
            pid = s
        else:
            pid = 0
        if (pid != 0):
            cmd = "kill -9 %s" % pid
            DBfunctions.record ("[killVerticaProcess] " + cmd)
            (status, result) = connection.execute( cmd )
            s = " ".join( result[1] )
            if status:
                DBfunctions.record ("[killVerticaProcess] %s" % s)
                pid = s


##########################################
# Removes Catalog and Data directories
# Note: should not be run anywhere but in createDB procedure in case of errors.
##########################################
def removeCatDataDirs( dbName, catalogDir, catalogSubDir, dataDir, dataSubDir, userName, host, password=""):
    catalogDir = catalogDir.rstrip("/") # /home/dbadmin
    subDBCatalogDir = catalogDir + "/" + dbName # /home/dbadmin/db1
    subCatalogDir = subDBCatalogDir + "/" + catalogSubDir # /home/dbadmin/db1/node1_catalog

    dataDir = dataDir.rstrip("/") # /home/dbadmin
    subDBDataDir = dataDir + "/" + dbName ## /home/dbadmin/db1
    subDataDir = subDBDataDir + "/" + dataSubDir # /home/dbadmin/db1/node1_data

    connection = adapterpool.DefaultAdapter(host, logger=get_logger())
    try:
        connection.connect( host, userName, password)
    except:
        print "User ", userName, " cannot login ", host
        return

    # save dbLog and vertica.log files in adminTools-dbadmin.log file 
    cmd = "cat %s/dbLog >> %s" % (subDBCatalogDir, DBinclude.adminToolLog)
    DBfunctions.record ("[removeCatDataDirs] " + cmd)
    (status, result) = connection.execute(cmd)
    cmd = "cat %s/%s.log >> %s" % (subCatalogDir, DBname.dbname, DBinclude.adminToolLog)
    DBfunctions.record ("[removeCatDataDirs] " + cmd)
    (status, result) = connection.execute(cmd)

    (status, result) = connection.execute( "rm -rf %s" % subDBCatalogDir)
    if dataDir != catalogDir:
        (status, result) = connection.execute( "rm -rf %s" % subDBDataDir)



##########################################
# Creates directory on current host
##########################################
def makeDirOnHost( dirName, connection):
    cmd = "mkdir -p --mode=770 " + dirName
    DBfunctions.record ("[makeDir] " + cmd)
    (status, result ) = connection.execute(cmd)
    DBfunctions.record ("[makeDir ret] " + result[0])
    if (not status):
        DBfunctions.record ("[makeDir ret] %s" %result[1])
        print "\nError: unable to create directory '" + dirName + "' on host '" + connection.hostname + "'"
        print "       Check directory ownership and access rights."
        return False
    else:
        return True

# examines the last good epoch file on a host and returns a 5-tuple:
# code,
# lastGoodEpoch             (as an int)
# timestamp                 (as a string)
# last good catalog version (as an int)
# k-safety of the database  (as an int)
#
# return codes:
#      -1   : could not login
#      -2   : no epoch file
#      -3   : bad epoch value
#       0   : last known epoch follows
def getLastGoodEpoch(userName, host, cmd):
    DBfunctions.record("[getLastGoodEpoch] user %s host %s" % (userName, host))
    DBfunctions.record("[getLastGoodEpoch] cmd %s" % cmd)

    connection = adapterpool.DefaultAdapter(host, logger=get_logger())
    try:
        connection.connect( host, userName, None)
    except:
       # if connection fails, then return an epoch of -1
       return -1, -1, "", -1, 0

    (status, result) = connection.execute (cmd)
    (code, epoch, catver, ksafety, timestamp) = parseLastGoodEpoch(result[1])
    connection.close()
    return code, epoch, timestamp, catver, ksafety

def parseLastGoodEpoch( str):
    if isinstance(str, list):
        str = '\n'.join(str)

    # We expect that the last good epoch file has the following two lines:
    #
    # Last good epoch: 0x4 ended at '2007-06-19 11:47:22-04'
    # Last good catalog version: 0xc
    # K-safety: 0

    line_regexp = re.compile(r".*Last good epoch: (?P<epoch>.*) ended at '(?P<timestamp>.*)'.*Last good catalog version: (?P<catver>[x0123456789abcdef]+).*K-safety: (?P<ksafety>[0123456789]+).*", re.DOTALL)

    # Try to find the last good epoch information. Set epoch, code and timestamp
    DBfunctions.record("[getLastGoodEpoch] trying to parse: %s" % str)
    epoch_match = line_regexp.match(str)
    if (epoch_match != None):
        try:
            code = 0
            epoch = long(epoch_match.group("epoch"), 16)
            timestamp = epoch_match.group("timestamp")
            catver = long(epoch_match.group("catver").strip(), 16)
            ksafety = long(epoch_match.group("ksafety").strip(), 10)
            DBfunctions.record("[getLastGoodEpoch] found epoch '%s' at timestamp '%s' with catalog version '%s' and ksafety '%s'" % (epoch, timestamp, catver, ksafety))
        except ValueError:
            DBfunctions.record("getLastGoodEpoch] Error converting epoch information")
            code = -2
            epoch = 0
            timestamp = "error"
            catver = 0
            ksafety = 0
    else:
        DBfunctions.record("[getLastGoodEpoch] no regexp match")
        epoch = "0"
        catver = "0"
        code = -2
        ksafety = "0"
        timestamp = "error"

    return (code, epoch, catver, ksafety, timestamp)

# Used by the installer to install an RPM on a remote host.
def installNode(pool, nodeHost, rpm, as_user):
    print "installing node.... ", nodeHost

    # sanity check. Already handled by installer.
    if rpm is None:
        raise StandardError("Cannot install without an --rpm file!")

    with pool.setHosts([nodeHost]):

        # just in case.. delete any rpmDestFile that already exists
        # otherwise, the cluster may have some odd versions installed.
        # VER-17897
        pool.execute("rm -rf %s" % DBinclude.rpmDestFile)

        # Check to see if there is enough space on the nodes.  This returns space
        # free in kbytes, white st_size returns in bytes.  Use the portability/POSIX
        # output flag on df so that long mount points don't screw this up.
        cmd = "df --portability /tmp | tail -1 | awk '{print $4}'"
        (status, host_results) = pool.execute(cmd)

        if not status:
            return 'Unable to determine if there is sufficienct space in /tmp on %s' % nodeHost

        sz = os.stat(rpm).st_size/1024;
        df_out = host_results[nodeHost][1][0]
        # if we screw this up, we get an exception about invalid format for a number
        if int(df_out) < sz:
            return 'Insufficent space in /tmp on %s.  %d required, %d available.' % (nodeHost, sz, int(df_out))

        status, result = adapterpool.copyLocalFileToHosts(pool, rpm,
                [ nodeHost ], DBinclude.rpmDestFile)

        if not status:
            return 'Unable to SCP rpm to destination. See logs'

        error = installRPM(pool, nodeHost, rpmFile=DBinclude.rpmDestFile)

        # clean up, but ignore failures. whatever.
        pool.execute("rm -rf %s" % DBinclude.rpmDestFile)

        # error is None -> success
        return error

def makeDir( connection, dirName, permitions=None, group=None, owner=None, onerror="continue", recursive=""):
    """
    Returns: 
        boolean. True if successful, False if unsuccessful (on any host).
    """
    passed = True
    cmds = [
           [ "sh -c \"if ! [ -e %s ]; then mkdir -p %s; fi\"" % (dirName, dirName), True, "Checking %s directory" % dirName, -1 ],
           [ "sh -c \"if [ `stat -c \\\"%%a\\\" %s` -lt 700 ]; then chmod 700 %s; fi\"" % (dirName, dirName), True, "Testing permissions", -1 ],
           ["touch %s/vertica_touch_test " % (dirName), owner == None, "Write check for %s directory" % dirName, -1],
           ["rm -rf %s/vertica_touch_test " % (dirName), owner == None, None, -1],
           ["chown %s %s %s" % (recursive, owner, dirName), owner != None, "Changing the owner of %s directory to %s" % (dirName, owner), None ],
           ["chgrp %s %s %s" % (recursive, group, dirName), group != None, "Changing the group of %s directory to %s" % (dirName, group), None ],
           ["chmod %s %s %s" % (recursive, permitions, dirName), permitions != None, None, None],
           ["[ -e %s ]" % dirName, True, None, -1],
           ["su %s -c \"stty -echo; touch %s/vertica_touch_test\" " % (owner, dirName), owner != None, "Write check for %s directory" % dirName, -1],
           ["su %s -c \"stty -echo; rm -rf %s/vertica_touch_test\"" % (owner, dirName), owner != None, None, -1]
           ]
    for cmd in cmds:
        if cmd[1]:
            Status, res = connection.execute(cmd[0])
            passed = passed and Status

            if not passed:
                if onerror == "continue":
                    print res
                else:
                    raise StandardError("%s" % res)
    return passed

# Run from the installer, typically as root
def installOrRepairSSHKeys(pool, user, hosts):
    base_staging_dir = "/tmp"
    staging_dir = os.path.join(base_staging_dir, 'vstage-' + str(uuid.uuid4()))
    private_key = os.path.join(staging_dir, 'id_rsa')

    # Create a staging directory owned by the user, because all commands will be
    # run by that user, not by root.  Root cannot read the user's home directory
    # when that user's home might be NFS-mounted.
    with pool.setHosts(hosts):
        cmd = "install --owner %s --mode 700 -d %s" % (user, staging_dir)
        (status, host_results) = pool.execute(cmd)

    if not status:
        print "Failed to create a staging directory for SSH key setup"
        failed_hosts = []
        for (hostname, (exitcode, lines)) in host_results.iteritems():
            failed_hosts.append(hostname)
        if len(failed_hosts) > 0:
            print "Failed on hosts: %s" % (', '.join(failed_hosts), )
        return False

    try:
        # On localhost, create or export the SSH key
        bare_cmd = "%s/util/create-or-export-ssh-key -f %s -u %s" % (
                vconst.BINLIB_D, private_key, user)
        cmd = "su --login %s --command '%s'" % (user, bare_cmd)

        local_host = pool.first_local_host()
        if local_host is None:
            print "Internal error: Could not find a localhost connection"
            return False

        with pool.setHosts([ local_host ]):
            (status, host_results) = pool.execute(cmd)

            if not status:
                print "Failed to create or export SSH key on localhost"
                return False

        # Send the key to everyone, in the ssh staging dir.
        (status, host_results) = adapterpool.copyLocalFileToHosts(pool,
                private_key,
                [ x for x in pool.remote_connected_hosts() if x in hosts ],
                private_key,
                dest_owner=user)

        if not status:
            print "Failed to copy SSH key to remote machines."
            failed_hosts = []
            for (hostname, (exitcode, lines)) in host_results.iteritems():
                failed_hosts.append(hostname)
            if len(failed_hosts) > 0:
                print "Failed on hosts: %s" % (', '.join(failed_hosts), )
            return False

        # On all hosts, import the SSH key
        bare_cmd = "%s/util/install-ssh-key -f %s -u %s" % (
                vconst.BINLIB_D, private_key, user)
        cmd = "su --login %s --command '%s'" % (user, bare_cmd)

        with pool.setHosts(hosts):
            (status, host_results) = pool.execute(cmd)

            if not status:
                print "Failed to import SSH key."
                failed_hosts = []
                for (hostname, (exitcode, lines)) in host_results.iteritems():
                    failed_hosts.append(hostname)
                if len(failed_hosts) > 0:
                    print "Failed on hosts: %s" % (', '.join(failed_hosts), )
                return False

        return True
    finally:
        with pool.setHosts(hosts):
            pool.execute("rm -rf %s" % staging_dir)

def createDataDir(pool, username, datadir=None):
    """Creates a data directory on the pool.

    Returns:
        boolean: True if successful, False if failed on any host
    """

    if datadir == None:
        datadir = "~%s/" % username
    return makeDir(pool, datadir, owner=username)    

def do_local_verify(pool, localhost, options=None):
    """Runs vertica.local_coerce on the pool and collects results"""

    default_options = {}
    if options is not None:
        default_options.update(options)
    options= default_options

    # run local_coerce on all machines.
    if not _run_local_coerce_on_pool(pool, options):
        return False

    # gather results locally
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dist_results = '/opt/vertica/log/all-local-verify-%s' % timestamp
    if not _gather_distributed_verify_results(pool, localhost, dist_results):
        return False

    failure_level = 'FAIL'
    if 'failure_threshold' in options:
        t = options['failure_threshold']
        if t is not None:
            if t == 'NONE':
                failure_level = None
            else:
                failure_level = t

    if not _evaluate_distributed_verify_results(
            dist_results, failure_level=failure_level):
        return False

    return True

# part of do_local_verify
def _run_local_coerce_on_pool(pool, options):
    python = r'/opt/vertica/oss/python/bin/python'
    command = "%s -m vertica.local_coerce" % python

    if options.get('dry_run', False):
        command += " --dry-run"

    # FIXME: username should come from vconst

    env = {}

    if options.get('username', None) is not None:
        env['VERT_DBA_USR'] = options['username']
    if options.get('dbagroup', None) is not None:
        env['VERT_DBA_GRP'] = options['dbagroup']
    if options.get('dbahome', None) is not None:
        env['VERT_DBA_HOME'] = options['dbahome']

    command = "%s%s" % (command_env_prefix(env), command)

    (status, host_results) = pool.execute(command)

    all_successful = True
    for (hostname, (exitcode, lines)) in host_results.iteritems():
        if str(exitcode) != "0":    # exitcode is a string. Why?
            all_successful = False
            print "Error: Command failed on %r:" % hostname
            print "\t%s" % command
            print "\treturncode = %s" % exitcode

    return all_successful

# part of do_local_verify
def _gather_distributed_verify_results(pool, localhost, target_dir,
        make_dir=True):
    """
    Brings the cluster nodes' verify-latest.xml to the localhost node.

    Args:
        target_dir: Where to place the clusters results.
        make_dir: Whether or not to create the target_dir if it does not exist.
    """

    # creating the target directory
    if not os.path.exists(target_dir):
        if not make_dir:
            print "Error: Local directory %r does not exist" % target_dir
            return False

        try:
            os.mkdir(target_dir, 0755)
        except IOError as err:
            print "Error: Unable to prepare local directory %r" % target_dir
            return False

    remote_file = '/opt/vertica/log/verify-latest.xml'
    target_pattern = os.path.join(target_dir, 'verify-%(hostname)s.xml')

    # scp all results files to localhost
    (status, host_results) = adapterpool.copyRemoteFilesToLocal(pool,
            remote_file, pool.connected_hosts(), target_pattern)

    all_successful = True
    for (hostname, (exitcode, lines)) in host_results.iteritems():
        if str(exitcode) != "0":    # exitcode is a string. Why?
            all_successful = False
            print "Error: scp failed. Tried to retrieve %r from %r" % (
                    remote_file, hostname)

    return all_successful

# part of do_local_verify
def _evaluate_distributed_verify_results(results_dir, failure_level='FAIL'):
    from vertica.platform.check.multi_results_file import MultiResultsFile

    files = os.listdir(results_dir)
    files = [ os.path.join(results_dir, x) for x in files ]

    r = MultiResultsFile(files)
    r.load()
    if not r.is_all_loaded():
        print "Error: Unable to load files from %r" % results_dir
        print "\tspecifically: %r" % (r.get_failed_loads(), )
        return False

    r.do_print(options=dict(action='configuration'))

    if not r.do_print_stat_diffs(failure_level):
        return False

    if failure_level is not None and r.meets_severity_threshold(failure_level):
        return False

    return True

def checkClusterFullyReachable(pool, user=None):
        (returnStatus, unreachableMappings, sshRepairHost, unreachableHosts) = checkSSHKeysAndConnections(pool, user)
        return returnStatus, unreachableMappings

def checkSSHKeysAndConnections(pool, user, logger=BasicLogger(), use_su=False, onlyLocalhost=False):
        returnStatus = True
        unreachableMappings = {}
        unreachableHosts = []
        reachableCount = {}
        needToRepairSSH = False
        commands = []
        infos = []

        su_to_user = ""
        end_to_user = ""
        if use_su:
           su_to_user = "su %s -c\"" % user
           end_to_user = "\""

        as_user = user
        for host in pool.connected_hosts():
            if onlyLocalhost and not DBfunctions.IsLocalHost(host):
                continue
            commands.append(
                            ["%s ssh -o PreferredAuthentications=publickey -o StrictHostKeyChecking=no -l %s %s hostname%s" % (su_to_user,as_user, host, end_to_user),
                             "Checking SSH connection to host %s for user %s" % (host, as_user), host])
            unreachableMappings[host] = []
            reachableCount[host] = 0

         
        for cmd in commands:
            Status, res = pool.execute(cmd[0], concurrency=9)
            returnStatus = returnStatus and Status
            if not Status:
                for host in res.keys():
                    if res[host][0] != "0":
                        if host not in  unreachableMappings.keys():
                            unreachableMappings[host] = []
                        unreachableMappings[host].append(cmd[2])
                        if (res[host][0] == "-1") and (host not in unreachableHosts):
                            unreachableHosts.append(host)
                    else:
                        reachableCount[cmd[2]] += 1
        sshRepairHost = None
        if not returnStatus:
            maxGoodConnections = 0
            for host in reachableCount.keys():
                if reachableCount[host] > maxGoodConnections and host not in unreachableMappings[host]:
                    sshRepairHost = host
                    maxGoodConnections = reachableCount[host] 
        logger.record("%s %s %s %s" % (returnStatus, unreachableMappings, sshRepairHost, unreachableHosts))
        return returnStatus, unreachableMappings, sshRepairHost, unreachableHosts
    

def command_env_prefix(env_map):
    """Creates a string that sets up the environment for a command.

    This string prefixes a command.  For example, a dictionary with the value 5
    for key VAR would return the string 'VAR=5 '.
    """

    valid_key_re = re.compile(r'^\w+$')

    result = ""
    for (key, value) in env_map.iteritems():
        assert valid_key_re.match(key), "Invalid environment variable"
        result+="%s=%s " % (key, shell_repr(value))

    return result

def get_hosts_without_user(pool, username):
    """Returns a list of hosts that do not have the user."""

    if username is None:
        username = vconst.DBA_USR

    (status, host_results) = pool.execute('id %s' % username)

    hosts = []

    for (hostname, (exitcode, _)) in host_results.iteritems():
        if str(exitcode) != '0':
            hosts.append(hostname)

    return hosts

def do_create_dba(pool, options=None):
    """Creates the dbadmin user and verticadba group on all nodes.

    If the user and/or group already exist, does validation instead.  Fails
    if creation or validation fails.  (note: Validation is somewhat redundant
    with do_local_verify.)
    """

    default_options = {}
    if options is not None:
        default_options.update(options)
    options= default_options
    python = r'/opt/vertica/oss/python/bin/python'
    command = "%s -m vertica.create_dba --short --no-primary-group" % python

    # FIXME: username should come from vconst.
    # FIXME: remotely executed scripts should get the environment by default.

    env = {}

    if options.get('username', None) is not None:
        env['VERT_DBA_USR'] = options['username']
    if options.get('dbagroup', None) is not None:
        env['VERT_DBA_GRP'] = options['dbagroup']
    if options.get('dbahome', None) is not None:
        env['VERT_DBA_HOME'] = options['dbahome']
    if options.get('color', False):
        command = "%s --color=always" % command

    if options.get('password', None) is not None:
        env['_ENV_VPWD_VAR'] = options['password']
        command = "%s --password-env=_ENV_VPWD_VAR" % command
    elif not options.get('password-disabled', False):
        # VER-28110: Preserving behavior of prompting for a password if the user
        # needs to be created.
        uname = options.get('username', vconst.DBA_USR)
        if len(get_hosts_without_user(pool, uname)) != 0:
            prompt = "Password for new %s user (empty = disabled)" % uname
            password = getpass.getpass(prompt)
            if len(password) != 0:
                env['_ENV_VPWD_VAR'] = password
                command = "%s --password-env=_ENV_VPWD_VAR" % command

    command = "%s%s" % (command_env_prefix(env), command)

    # hide=True to prevent logging of the password
    (status, host_results) = pool.execute(command, hide=True)

    # These maps go from output text to hostnames (the opposite of what you
    # might expect) in order to avoid printing multiple things.
    success_output = {}
    fail_output = {}

    for (hostname, (exitcode, lines)) in host_results.iteritems():
        data = success_output

        if str(exitcode)!='0':
            data=fail_output
            BasicLogger().info("create_dba @ %s -> %s" % (hostname, exitcode))

        output = "\n".join([ "    %s" % x for x in lines if len(x.strip())>0])

        if output not in data:
            data[output] = []
        data[output].append(hostname)

    success_count = 0
    fail_count = 0

    for (output, hosts) in success_output.iteritems():
        msg = "Successful on hosts"
        if options.get('color', False):
            msg = colored(msg, color='green')
        print "%s (%d): %s" % (msg, len(hosts), ' '.join(hosts))
        print output
        print
        success_count += len(hosts)

    for (output, hosts) in fail_output.iteritems():
        msg = "Failed on hosts"
        if options.get('color', False):
            msg = colored(msg, color='red', attrs=['bold'])
        print "%s (%d): %s" % (msg, len(hosts), ' '.join(hosts))
        print output
        print
        fail_count += len(hosts)

    if fail_count > 0:
        # TODO: make production create_dba script, and include a reference to it
        # here, so that users can run it for more details. (as a fallback)

        return False
    else:
        return True

def sync_admintools_conf(pool, dbadmin, hosts=None, local_file=None):
    if local_file is None:
        local_file = DBinclude.ADMINTOOLS_CONF
    if hosts is None:
        hosts = pool.connected_hosts()

    return adapterpool.copyLocalFileToHosts(
            pool,
            local_file,
            hosts,
            DBinclude.ADMINTOOLS_CONF,  # dest file
            dest_owner = dbadmin)

def control_port(client_port):
    if int(client_port) == 5433:
        return 4803
    else:
        return int(client_port) + 2

def get_logger():
    """Retuns Syslogger instance if syslogging commands

    Returns None if not syslogging commands
    """
    cfg = Configurator.Instance()
    sys_log=None
    if cfg.use_syslog():
        sys_log = SysLogger()
    return sys_log

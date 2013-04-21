#!/usr/bin/env python

from datetime import date, timedelta, datetime
from argparse import ArgumentParser, FileType
from sys import argv, exit, stdout
from random import Random

from ConfigParser import ConfigParser

class Roster:
    def __init__(self, startDate, endDate, staffList,
                 shiftsPerDay,
                 rand=Random()):

        self.staffList = staffList
        self.shiftsPerDay = shiftsPerDay
        self.rand = rand

        nDays = (endDate - startDate).days + 1

        self.dates = [startDate + timedelta(i) for i in range(nDays)]
        self.weekdays = [day.weekday() for day in self.dates]

        self.populateRoster()

    def getFixedWorkers(self, day):
        """Get employees who will definitely be working on day."""

        fixedWorkers = []

        for staff in self.staffList:
            if not staff.fixed:
                continue
            if not day.weekday() in staff.canWorkWeekdays:
                continue
            if day in staff.cantWorkDates:
                continue

            fixedWorkers.append(staff)

        return (fixedWorkers)

    def getPotentialWorkers(self, day):
        """Get list of workers who can work today, sorted in
        order of preference."""

        canWork = []
        for staff in self.staffList:
            if staff.fixed:
                continue
            if not day.weekday() in staff.canWorkWeekdays:
                continue
            if day in staff.cantWorkDates:
                continue

            canWork.append(staff)

        # Shuffle lists to remove unfairness:
        self.rand.shuffle(canWork)

        # Sort list according to total number of holidays:
        def cmpfunTH(x,y):
            if x.holidaysTotal<y.holidaysTotal:
                return 1
            if x.holidaysTotal>y.holidaysTotal:
                return -1
            return 0
        canWork.sort(cmp=cmpfunTH)

        # Sort list according to number of days since holiday:
        def cmpfunDSH(x,y):
            if x.daysSinceHoliday>y.daysSinceHoliday:
                return 1
            if x.daysSinceHoliday<y.daysSinceHoliday:
                return -1
            return 0
        canWork.sort(cmp=cmpfunDSH)

        return canWork

    def updateCounters(self, workingToday):
        """Increment employee work/RDO counters."""  

        for staff in self.staffList:
            if staff in workingToday:
                staff.daysSinceHoliday += 1
                staff.onHoliday = -1
            else:
                staff.daysSinceHoliday = 0
                staff.holidaysTotal += 1
                if staff.onHoliday<0:
                    staff.onHoliday = 1
                else:
                    staff.onHoliday += 1

    def populateRoster(self):
        """Generate a roster subject to the given constraints."""

        # Initialise employee holiday counters
        for employee in self.staffList:
            employee.zeroCounters()

        self.working = {}

        for day in self.dates:
            workingToday = []
            shiftsLeft = self.shiftsPerDay[day.weekday()]
            
            # These people are definitely working today:
            workingToday.extend(self.getFixedWorkers(day))
            shiftsLeft -= len(workingToday)

            # Obtain a list of employees who can work today,
            # sorted in order of preference
            potentials = self.getPotentialWorkers(day)

            # Assign employees until we run out of shifts
            workingToday.extend(potentials[:shiftsLeft])

            # Update counters for all employees:
            self.updateCounters(workingToday)

            self.working[day] = workingToday

    def __str__(self):
        """Display roster."""

        out = ""

        dayNames = ['M','T','W','T','F','S','S']
        
        # Headers
        out += "Employee".ljust(10)
        for day in self.dates:
            out += dayNames[day.weekday()] + ' '
        out += '\n'

        # Values
        for staff in self.staffList:
            out += staff.name.ljust(10,' ')[:10]
            for day in self.dates:
                if staff in self.working[day]:
                    out += 'x '
                else:
                    out += '  '

            out += ' | ' + str(staff.holidaysTotal) + '\n'

        # Mark problem days
        out += ' '*10
        for day in self.dates:
            if len(self.working[day])<self.shiftsPerDay[day.weekday()]:
                out += '! '
            else:
                out += '= '

        out += '\n'

        return out

    def csv(self):
        """Generate CSV representation of roster."""

        out = ""

        dayNames = ['Mon','Tue','Wed','Thur','Fri','Sat','Sun']
        
        # Headers
        out += 'Employee, '
        for day in self.dates:
            out += '"' + dayNames[day.weekday()] + ' {}/{} '.format(day.day,day.month) + '", '
        out += '"RDOs"\n'

        # Values
        for staff in self.staffList:
            out += '"{}", '.format(staff.name)
            for day in self.dates:
                if staff in self.working[day]:
                    out += ', '
                else:
                    out += '"RDO",  '

            out += '"' + str(staff.holidaysTotal) + '"\n'

        # Mark problem days
        out += "Problems, "
        for day in self.dates:
            if len(self.working[day])<self.shiftsPerDay[day.weekday()]:
                out += '"Y", '
            else:
                out += '"N", '

        out += '\n'

        return out

    def ical(self):
        """Generate ICAL representation of roster."""
        return ""

class Employee:
    def __init__(self, name, canWorkWeekdays=range(7), cantWorkDates=[], fixed=False):
        self.name = name
        self.canWorkWeekdays = canWorkWeekdays
        self.cantWorkDates = cantWorkDates
        self.fixed = fixed

        self.daysSinceHoliday = 0
        self.onHoliday = -1
        self.holidaysTotal = 0

    def zeroCounters(self):
        self.daysSinceHoliday = 0
        self.onHoliday = -1
        self.holidaysTotal = 0


def readConstraintsFile(staff_file):
    """Retrieve staff constraints from staff config file."""

    parser = ConfigParser()
    parser.readfp(staff_file)

    staffList = []
    for staffName in parser.sections():
        if staffName == "General":
            continue

        if parser.has_option(staffName, "canworkweekdays"):
            strList = parser.get(staffName, "canworkweekdays").split()
            canWorkWeekdays = [int(s) for s in strList]
        else:
            canWorkWeekdays = range(7)

        if parser.has_option(staffName, "fixedShifts"):
            fixed = parser.getboolean(staffName, "fixedShifts")
        else:
            fixed = False

        cantWorkDates = []
        if parser.has_option(staffName, "cantworkdates"):
            strList = parser.get(staffName, "cantworkdates").split(',')
            for dateRangeStr in strList:
                dateRange = dateRangeStr.split('to')
                if len(dateRange) == 1:
                    thisdate = datetime.strptime(dateRange[0].strip(), "%d/%m/%y")
                    cantWorkDates.append(thisdate)
                else:
                    startDate = datetime.strptime(dateRange[0].strip(), "%d/%m/%y")
                    endDate = datetime.strptime(dateRange[1].strip(), "%d/%m/%y")
                    nDays = (endDate-startDate).days+1
                    dates = [startDate + timedelta(i) for i in range(nDays)]
                    cantWorkDates.extend(dates)

        print "{}: {}".format(staffName, cantWorkDates)

        staffList.append(Employee(staffName,
                                  canWorkWeekdays=canWorkWeekdays,
                                  cantWorkDates=cantWorkDates,
                                  fixed=fixed))


    if ("General" not in parser.sections()) or not parser.has_option("General", "shiftsPerDay"):
        print "Error: Shifts per day not specified in constraints file."
        exit(1)

    shiftsPerDay = [int(s) for s in parser.get("General", "shiftsPerDay").split()]

    return staffList, shiftsPerDay


### MAIN ###

if __name__=='__main__':

    # Set up command-line arguments
    parser = ArgumentParser(description="Simple employee shift roster generator.")
    parser.add_argument("constraints_file", type=FileType('r'),
                        help="Configuration file containing staff constraints.")
    parser.add_argument("first_day", type=str,
                        help="Date of first day of roster (dd/mm/yy)")
    parser.add_argument("last_day", type=str,
                        help="Date of last day of roster (dd/mm/yy)")
    parser.add_argument("-o","--output", metavar="file", type=FileType('w'), default=stdout,
                        help="Output file (default stdout).")
    parser.add_argument("-c","--csv", action="store_true",
                        help="Write output in CSV format.")

    # Parse arguments
    args = parser.parse_args(argv[1:])
    firstDay = datetime.strptime(args.first_day, "%d/%m/%y")
    lastDay = datetime.strptime(args.last_day, "%d/%m/%y")
    staffList, shiftsPerDay = readConstraintsFile(args.constraints_file)

    # Build roster
    roster = Roster(firstDay, lastDay, staffList, shiftsPerDay)

    # Generate output
    if args.csv:
        args.output.write(roster.csv())
    else:
        args.output.write(str(roster))

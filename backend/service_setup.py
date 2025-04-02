import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
from attendance_monitor import start_monitoring

class AttendanceService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AttendanceMonitorService"
    _svc_display_name_ = "Attendance Monitoring Service"
    _svc_description_ = "Monitors attendance using face recognition"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True

    def SvcStop(self):
        self.is_running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        start_monitoring()  # This starts the monitoring process

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AttendanceService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AttendanceService)
from escpos.printer import Usb, Network, Serial
from escpos.exceptions import USBNotFoundError
from typing import Optional, Union, List
import logging
from ..core.task import Task

logger = logging.getLogger(__name__)

class ReceiptPrinter:
    def __init__(self, printer_type: str = "usb", **kwargs):
        self.printer_type = printer_type
        self.printer = None
        self.config = kwargs
        self._connect()
    
    def _connect(self):
        try:
            if self.printer_type == "usb":
                vendor_id = self.config.get("vendor_id", 0x04b8)  # Default Epson
                product_id = self.config.get("product_id", 0x0202)
                self.printer = Usb(vendor_id, product_id)
            elif self.printer_type == "network":
                host = self.config.get("host", "192.168.1.100")
                port = self.config.get("port", 9100)
                self.printer = Network(host, port)
            elif self.printer_type == "serial":
                device = self.config.get("device", "/dev/ttyUSB0")
                baudrate = self.config.get("baudrate", 9600)
                self.printer = Serial(device, baudrate)
            else:
                raise ValueError(f"Unsupported printer type: {self.printer_type}")
            
            logger.info(f"Connected to {self.printer_type} printer")
            
        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}")
            self.printer = None
    
    def is_connected(self) -> bool:
        return self.printer is not None
    
    def print_task(self, task: Task) -> bool:
        if not self.is_connected():
            logger.error("Printer not connected")
            return False
        
        try:
            # Print task header
            self.printer.set(align="center", text_type="B", width=2, height=2)
            self.printer.text("TASK CARD\n")
            self.printer.text("=" * 20 + "\n")
            
            # Task title
            self.printer.set(align="left", text_type="B", width=1, height=1)
            self.printer.text(f"Title: {task.title}\n")
            
            # Task description
            if task.description:
                self.printer.set(align="left", text_type="normal")
                self.printer.text(f"Description:\n{task.description}\n")
            
            self.printer.text("-" * 30 + "\n")
            
            # Task details
            self.printer.text(f"Status: {task.status.value.title()}\n")
            self.printer.text(f"Priority: {task.priority.value.title()}\n")
            self.printer.text(f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n")
            
            if task.due_date:
                self.printer.text(f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}\n")
            
            if task.tags:
                self.printer.text(f"Tags: {', '.join(task.tags)}\n")
            
            self.printer.text("-" * 30 + "\n")
            
            # Task ID (smaller font)
            self.printer.set(text_type="normal", width=1, height=1)
            self.printer.text(f"ID: {task.id}\n")
            
            # Print timestamp
            from datetime import datetime
            print_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.printer.text(f"Printed: {print_time}\n")
            
            self.printer.text("=" * 30 + "\n")
            self.printer.cut()
            
            logger.info(f"Successfully printed task: {task.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error printing task: {e}")
            return False
    
    def print_task_list(self, tasks: List[Task], title: str = "TASK LIST") -> bool:
        if not self.is_connected():
            logger.error("Printer not connected")
            return False
        
        try:
            # Header
            self.printer.set(align="center", text_type="B", width=2, height=2)
            self.printer.text(f"{title}\n")
            self.printer.text("=" * 20 + "\n")
            
            if not tasks:
                self.printer.set(align="center", text_type="normal")
                self.printer.text("No tasks found\n")
            else:
                for i, task in enumerate(tasks, 1):
                    self.printer.set(align="left", text_type="B")
                    self.printer.text(f"{i}. {task.title}\n")
                    
                    self.printer.set(text_type="normal")
                    self.printer.text(f"   Status: {task.status.value.title()}\n")
                    self.printer.text(f"   Priority: {task.priority.value.title()}\n")
                    
                    if task.due_date:
                        self.printer.text(f"   Due: {task.due_date.strftime('%Y-%m-%d')}\n")
                    
                    self.printer.text("\n")
            
            # Print timestamp
            from datetime import datetime
            print_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.printer.text("-" * 30 + "\n")
            self.printer.text(f"Printed: {print_time}\n")
            self.printer.text("=" * 30 + "\n")
            self.printer.cut()
            
            logger.info(f"Successfully printed task list with {len(tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Error printing task list: {e}")
            return False
    
    def test_print(self) -> bool:
        if not self.is_connected():
            logger.error("Printer not connected")
            return False
        
        try:
            self.printer.set(align="center", text_type="B")
            self.printer.text("PRINTER TEST\n")
            self.printer.text("=" * 20 + "\n")
            self.printer.set(align="left", text_type="normal")
            self.printer.text("This is a test print\n")
            self.printer.text("from the Task Manager\n")
            self.printer.text("application.\n")
            
            from datetime import datetime
            test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.printer.text(f"Test time: {test_time}\n")
            self.printer.text("=" * 20 + "\n")
            self.printer.cut()
            
            logger.info("Test print completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during test print: {e}")
            return False
    
    def disconnect(self):
        if self.printer:
            try:
                self.printer.close()
                logger.info("Printer disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting printer: {e}")
            finally:
                self.printer = None
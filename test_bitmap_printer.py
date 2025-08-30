#!/usr/bin/env python3
"""
Test script for bitmap printer functionality
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.core.task import Task, TaskStatus, TaskPriority, TaskCategory
from task_manager.printer.receipt_printer import ReceiptPrinter
from datetime import datetime, timezone

def test_bitmap_creation():
    # Create a test task
    test_task = Task(
        title="Complete quarterly report and presentation for board meeting",
        description="This is a sample task description that demonstrates how longer text will be wrapped and displayed on the receipt. The bitmap should handle multiple lines gracefully.",
        category=TaskCategory.WORK,
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
        project="Q4 Financial Review",
        tags=["urgent", "presentation", "board-meeting"],
        due_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    )
    
    print("Creating test bitmap for task receipt...")
    
    # Create printer instance (won't actually connect to hardware)
    printer = ReceiptPrinter(printer_type="usb")
    
    # Save bitmap to file for visual inspection
    filename = printer.save_task_bitmap(test_task, "test_task_receipt.png")
    
    if filename:
        print(f"✅ Bitmap created successfully: {filename}")
        print("You can open this file to see how the receipt will look.")
        
        # Also test a personal task
        personal_task = Task(
            title="Buy groceries",
            description="Weekly grocery shopping",
            category=TaskCategory.PERSONAL,
            priority=TaskPriority.LOW,
            status=TaskStatus.PENDING,
            project="Home Management",
            tags=["shopping", "weekly"]
        )
        
        filename2 = printer.save_task_bitmap(personal_task, "test_personal_task_receipt.png")
        if filename2:
            print(f"✅ Personal task bitmap created: {filename2}")
        
    else:
        print("❌ Failed to create bitmap")

if __name__ == "__main__":
    test_bitmap_creation()
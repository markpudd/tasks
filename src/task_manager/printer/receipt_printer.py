from escpos.printer import Usb, Network, Serial
from escpos.exceptions import USBNotFoundError
from typing import Optional, Union, List
import logging
from PIL import Image, ImageDraw, ImageFont
import requests
import io
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
    
    def _get_default_font(self, size: int = 14) -> ImageFont.ImageFont:
        """Get a default font, falling back to system fonts if needed"""
        try:
            # Try to use a nice system font
            return ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
        except:
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                return ImageFont.load_default()
    
    def _create_task_bitmap(self, task: Task) -> Image.Image:
        """Create a bitmap image for the task card in the specified format"""
        # Receipt printer width is typically 384 pixels for 58mm or 512 for 80mm
        width = 384
        
        # Create initial image with estimated height
        estimated_height = 500  # Simpler format needs less height
        img = Image.new('RGB', (width, estimated_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Fonts
        title_font = self._get_default_font(48)  # Even larger for main title
        header_font = self._get_default_font(24)
        due_font = self._get_default_font(20)
        
        y_pos = 20
        margin = 20
        
        # Header
        header_text = "TASK CARD"
        header_bbox = draw.textbbox((0, 0), header_text, font=header_font)
        header_width = header_bbox[2] - header_bbox[0]
        draw.text(((width - header_width) // 2, y_pos), header_text, fill='black', font=header_font)
        y_pos += header_bbox[3] - header_bbox[1] + 30
        
        # Top separator line (thick black)
        draw.line([(margin, y_pos), (width - margin, y_pos)], fill='black', width=8)
        y_pos += 40
        
        # Task title (very large) - handle text wrapping
        title_words = task.title.split()
        title_lines = []
        current_line = ""
        
        for word in title_words:
            test_line = current_line + word + " "
            test_bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if test_bbox[2] - test_bbox[0] <= width - 2 * margin:
                current_line = test_line
            else:
                if current_line:
                    title_lines.append(current_line.strip())
                    current_line = word + " "
                else:
                    title_lines.append(word)
        
        if current_line:
            title_lines.append(current_line.strip())
        
        for line in title_lines:
            line_bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            draw.text((line_x, y_pos), line, fill='black', font=title_font)
            y_pos += line_bbox[3] - line_bbox[1] + 8
        
        y_pos += 40
        
        # Bottom separator line (thick black)
        draw.line([(margin, y_pos), (width - margin, y_pos)], fill='black', width=8)
        y_pos += 40
        
        # Bottom section with icons and due date
        # Left side: Category icon (person or building)
        category_icon = "🏢" if task.category.value == "WORK" else "👤"  # Person icon for personal
        
        # Create bottom row with category icon, due date, and priority icon
        bottom_elements = []
        
        # Category icon
        bottom_elements.append(category_icon)
        
        # Due date if exists
        if task.due_date:
            due_text = f"DUE: {task.due_date.strftime('%d %b %Y')}"
            bottom_elements.append(due_text)
        
        # Priority icon (warning triangle) if high priority
        if task.priority.value == "HIGH":
            bottom_elements.append("⚠️")
        
        # Layout bottom elements
        if len(bottom_elements) == 1:
            # Just category icon, center it
            element_bbox = draw.textbbox((0, 0), bottom_elements[0], font=due_font)
            element_width = element_bbox[2] - element_bbox[0]
            draw.text(((width - element_width) // 2, y_pos), bottom_elements[0], fill='black', font=due_font)
        elif len(bottom_elements) == 2:
            # Category icon on left, due date in center or right
            draw.text((margin, y_pos), bottom_elements[0], fill='black', font=due_font)
            
            element_bbox = draw.textbbox((0, 0), bottom_elements[1], font=due_font)
            element_width = element_bbox[2] - element_bbox[0]
            draw.text(((width - element_width) // 2, y_pos), bottom_elements[1], fill='black', font=due_font)
        else:
            # All three: category left, due center, priority right
            draw.text((margin, y_pos), bottom_elements[0], fill='black', font=due_font)
            
            # Center the due date
            due_bbox = draw.textbbox((0, 0), bottom_elements[1], font=due_font)
            due_width = due_bbox[2] - due_bbox[0]
            draw.text(((width - due_width) // 2, y_pos), bottom_elements[1], fill='black', font=due_font)
            
            # Right align the priority icon
            priority_bbox = draw.textbbox((0, 0), bottom_elements[2], font=due_font)
            priority_width = priority_bbox[2] - priority_bbox[0]
            draw.text((width - margin - priority_width, y_pos), bottom_elements[2], fill='black', font=due_font)
        
        y_pos += draw.textbbox((0, 0), "DUE: 01 Jan 2024", font=due_font)[3] + 20
        
        # Crop image to actual content height
        final_img = img.crop((0, 0, width, y_pos))
        
        return final_img
    
    def _print_task_text_fallback(self, task: Task) -> bool:
        """Fallback text printing method if bitmap fails"""
        try:
            # Print task header
            self.printer.set(align="center", bold=True, width=2, height=2)
            self.printer.text("TASK CARD\n")
            self.printer.text("=" * 32 + "\n")
            
            # Task title - Much bigger text
            self.printer.set(align="center", bold=True, width=3, height=3)
            self.printer.text(f"{task.title}\n")
            
            # Category and priority icons - larger and more prominent
            category_icon = "🏢" if task.category.value == "WORK" else "🏠"
            priority_icon = "⚡" if task.priority.value == "HIGH" else ""
            
            # Icons line with multiple icons for visibility
            self.printer.set(align="center", bold=False, width=2, height=2)
            icon_line = f"{category_icon}  {category_icon}  {category_icon}"
            if priority_icon:
                icon_line += f"  {priority_icon}  {priority_icon}  {priority_icon}"
            icon_line += "\n"
            self.printer.text(icon_line)
            
            # Project name if exists
            if hasattr(task, 'project') and task.project:
                self.printer.set(align="center", bold=True, width=1, height=1)
                self.printer.text(f"📁 Project: {task.project}\n")
            
            self.printer.text("=" * 32 + "\n")
            
            # Task description
            if task.description:
                self.printer.set(align="left", bold=False)
                self.printer.text(f"Description:\n{task.description}\n")
                self.printer.text("-" * 32 + "\n")
            
            # Task details
            self.printer.set(align="left", bold=False)
            self.printer.text(f"📊 Status: {task.status.value.title()}\n")
            self.printer.text(f"📅 Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n")
            
            if task.due_date:
                self.printer.text(f"⏰ Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}\n")
            
            if task.tags:
                self.printer.text(f"🏷️  Tags: {', '.join(task.tags)}\n")
            
            self.printer.text("=" * 32 + "\n")
            self.printer.cut()
            
            logger.info(f"Successfully printed task (text fallback): {task.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error in text fallback printing: {e}")
            return False
    
    def print_task(self, task: Task) -> bool:
        if not self.is_connected():
            logger.error("Printer not connected")
            return False
        
        try:
            # Create bitmap for the task
            img = self._create_task_bitmap(task)
            
            # Convert to black and white for thermal printer
            bw_img = img.convert('1')  # Convert to 1-bit black and white
            
            # Print the bitmap image
            self.printer.image(bw_img)
            self.printer.cut()
            
            logger.info(f"Successfully printed task bitmap: {task.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error printing task bitmap: {e}")
            # Fallback to text printing
            return self._print_task_text_fallback(task)
    
    def print_task_list(self, tasks: List[Task], title: str = "TASK LIST") -> bool:
        if not self.is_connected():
            logger.error("Printer not connected")
            return False
        
        try:
            # Header
            self.printer.set(align="center", bold=True, width=2, height=2)
            self.printer.text(f"{title}\n")
            self.printer.text("=" * 20 + "\n")
            
            if not tasks:
                self.printer.set(align="center", bold=False)
                self.printer.text("No tasks found\n")
            else:
                for i, task in enumerate(tasks, 1):
                    # Task title with icons
                    category_icon = "🏢" if task.category.value == "WORK" else "🏠"
                    priority_icon = "⚡" if task.priority.value == "HIGH" else ""
                    
                    self.printer.set(align="left", bold=True)
                    title_line = f"{i}. {category_icon} {task.title}"
                    if priority_icon:
                        title_line += f" {priority_icon}"
                    self.printer.text(f"{title_line}\n")
                    
                    # Project if exists
                    if hasattr(task, 'project') and task.project:
                        self.printer.set(bold=False)
                        self.printer.text(f"   📁 Project: {task.project}\n")
                    
                    self.printer.set(bold=False)
                    self.printer.text(f"   📊 Status: {task.status.value.title()}\n")
                    
                    if task.due_date:
                        self.printer.text(f"   ⏰ Due: {task.due_date.strftime('%Y-%m-%d')}\n")
                    
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
            self.printer.set(align="center", bold=True)
            self.printer.text("PRINTER TEST\n")
            self.printer.text("=" * 20 + "\n")
            self.printer.set(align="left", bold=False)
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
    
    def save_task_bitmap(self, task: Task, filename: str = None) -> str:
        """Save task bitmap to file for testing/preview purposes"""
        try:
            img = self._create_task_bitmap(task)
            bw_img = img.convert('1')  # Convert to 1-bit black and white
            
            if not filename:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"task_bitmap_{timestamp}.png"
            
            bw_img.save(filename)
            logger.info(f"Task bitmap saved to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving task bitmap: {e}")
            return None
    
    def disconnect(self):
        if self.printer:
            try:
                self.printer.close()
                logger.info("Printer disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting printer: {e}")
            finally:
                self.printer = None
#!/usr/bin/env python3
"""
Palo Alto Configuration Lab - GUI Application
Cross-platform GUI for managing Palo Alto firewall and Prisma Access configurations

Phase 1: Basic GUI Structure with all fields, copy/paste, and improved layout
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import sys
import pickle
import json
import glob
from datetime import datetime
import ipaddress
import re
import io
import threading
from contextlib import redirect_stdout, redirect_stderr

# Import pan-os-python modules for operations
try:
    from panos.firewall import Firewall
    from panos.device import NTPServerPrimary, NTPServerSecondary, SystemSettings
    from panos.ha import HighAvailability
    from panos.network import EthernetInterface, Zone, TunnelInterface, VirtualRouter, StaticRoute
    from panos.objects import AddressObject, AddressGroup
    from panos.policies import Rulebase, SecurityRule, NatRule
    PANOS_AVAILABLE = True
except ImportError:
    PANOS_AVAILABLE = False

# Import existing modules
try:
    import load_settings
    import get_settings
except ImportError:
    print("Warning: Could not import load_settings or get_settings modules")
    print("Make sure all existing scripts are in the same directory")
    load_settings = None
    get_settings = None


class PAConfigGUI:
    """Main GUI Application Class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Palo Alto Configuration Lab")
        self.root.geometry("1200x900")
        
        # Configuration state
        self.current_config = None
        self.config_cipher = None
        self.config_file_path = None
        self.last_directory = os.getcwd()  # Remember last directory
        self.recent_files = []  # Recent files list
        self.recent_files_max = 10  # Maximum recent files to remember
        self.config_modified = False  # Track if config has been modified
        
        # Field widgets storage
        self.fw_fields = {}
        self.pa_fields = {}
        self.password_fields = {}  # Track password fields for show/hide toggle
        
        # Output redirection
        self.stdout_redirector = None
        self.stderr_redirector = None
        
        # Load recent files and preferences
        self.load_preferences()
        
        # Setup UI
        self.setup_menu()
        self.setup_ui()
        
        # Setup styles for validation
        self.setup_styles()
        
        # Bind keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Setup change tracking
        self._setup_change_tracking()
        
        # Setup auto-calculation after all fields are created
        self._setup_auto_calculation()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Setup custom styles for validation feedback"""
        style = ttk.Style()
        # Create invalid entry style (red border)
        style.configure("Invalid.TEntry", fieldbackground="#ffcccc")
        
    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Configuration", command=self.new_config, accelerator="Ctrl+N")
        file_menu.add_command(label="Load Configuration...", command=self.load_config, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Configuration", command=self.save_config, accelerator="Ctrl+S")
        file_menu.add_command(label="Save Configuration As...", command=self.save_config_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        
        # Recent files submenu
        self.recent_files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_files_menu)
        self.update_recent_files_menu()
        file_menu.add_separator()
        
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self.copy_selected, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self.paste_selected, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Show/Hide Passwords", command=self.toggle_passwords)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Configure Initial Config", command=self.run_initial_config)
        tools_menu.add_command(label="Configure Firewall", command=self.run_configure_firewall)
        tools_menu.add_command(label="Configure Service Connection", command=self.run_service_connection)
        tools_menu.add_command(label="Get Firewall Version", command=self.get_fw_version)
        tools_menu.add_command(label="Print Settings", command=self.print_settings)
        tools_menu.add_separator()
        tools_menu.add_command(label="Load from SCM", command=self.load_from_scm)
        tools_menu.add_command(label="Load from SPOV File...", command=self.load_from_spov)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-n>', lambda e: self.new_config())
        self.root.bind('<Control-o>', lambda e: self.load_config())
        self.root.bind('<Control-s>', lambda e: self.save_config())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_config_as())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-c>', lambda e: self.copy_selected())
        self.root.bind('<Control-v>', lambda e: self.paste_selected())
        # Mac support (Command key)
        self.root.bind('<Command-n>', lambda e: self.new_config())
        self.root.bind('<Command-o>', lambda e: self.load_config())
        self.root.bind('<Command-s>', lambda e: self.save_config())
        self.root.bind('<Command-Shift-S>', lambda e: self.save_config_as())
        self.root.bind('<Command-q>', lambda e: self.on_closing())
    
    def load_preferences(self):
        """Load user preferences (recent files, last directory)"""
        prefs_file = os.path.join(os.path.expanduser("~"), ".pa_config_gui_prefs.json")
        try:
            if os.path.exists(prefs_file):
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                    self.recent_files = prefs.get('recent_files', [])
                    self.last_directory = prefs.get('last_directory', os.getcwd())
                    # Filter out files that no longer exist
                    self.recent_files = [f for f in self.recent_files if os.path.exists(f)]
        except Exception as e:
            self.log_output(f"Could not load preferences: {str(e)}")
            self.recent_files = []
            self.last_directory = os.getcwd()
    
    def save_preferences(self):
        """Save user preferences"""
        prefs_file = os.path.join(os.path.expanduser("~"), ".pa_config_gui_prefs.json")
        try:
            prefs = {
                'recent_files': self.recent_files[:self.recent_files_max],
                'last_directory': self.last_directory
            }
            with open(prefs_file, 'w') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            self.log_output(f"Could not save preferences: {str(e)}")
    
    def add_to_recent_files(self, file_path):
        """Add a file to recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.recent_files_max]
        self.update_recent_files_menu()
        self.save_preferences()
    
    def update_recent_files_menu(self):
        """Update the recent files menu"""
        self.recent_files_menu.delete(0, tk.END)
        if self.recent_files:
            for file_path in self.recent_files:
                file_name = os.path.basename(file_path)
                # Truncate if too long
                if len(file_name) > 50:
                    file_name = file_name[:47] + "..."
                self.recent_files_menu.add_command(
                    label=file_name,
                    command=lambda fp=file_path: self.load_recent_file(fp)
                )
        else:
            self.recent_files_menu.add_command(label="No recent files", state="disabled")
    
    def load_recent_file(self, file_path):
        """Load a file from recent files list"""
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            self.recent_files.remove(file_path)
            self.update_recent_files_menu()
            return
        
        # Prompt for password
        password = simpledialog.askstring("Password", "Enter encryption password:", show="*")
        if not password:
            return
        
        try:
            cipher = load_settings.derive_key(password)
            config_data = self.load_config_file_direct(file_path, cipher)
            
            if config_data:
                self.current_config = config_data
                self.config_cipher = cipher
                self.config_file_path = file_path
                self.populate_fields(config_data)
                self.status_var.set(f"Loaded: {os.path.basename(file_path)}")
                self.log_output(f"Configuration loaded successfully from {file_path}")
                self.add_to_recent_files(file_path)
            else:
                messagebox.showerror("Error", "Failed to load configuration. Check password.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
            self.log_output(f"Error loading config: {str(e)}")
    
    def on_closing(self):
        """Handle window closing event"""
        # Check for unsaved changes
        if self.config_modified:
            if not messagebox.askyesno("Unsaved Changes", 
                                      "You have unsaved changes. Exit anyway?"):
                return
        
        self.save_preferences()
        self.root.quit()
    
    def setup_ui(self):
        """Create the main UI layout"""
        # Create main container with canvas for scrolling
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        main_frame = scrollable_frame
        
        # Configuration name and password section
        config_header = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        config_header.columnconfigure(1, weight=1)
        
        ttk.Label(config_header, text="Config Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_name_var = tk.StringVar()
        config_name_entry = ttk.Entry(config_header, textvariable=self.config_name_var, width=40)
        config_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.add_copy_button(config_header, config_name_entry, 0, 2)
        
        ttk.Label(config_header, text="Encryption Password:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.encrypt_pass_var = tk.StringVar()
        encrypt_pass_entry = ttk.Entry(config_header, textvariable=self.encrypt_pass_var, show="*", width=40)
        encrypt_pass_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.password_fields['encrypt_pass'] = encrypt_pass_entry
        ttk.Button(config_header, text="Change Password", command=self.change_password).grid(row=1, column=2, padx=5)
        
        # Firewall Configuration Section - Two columns
        fw_frame = ttk.LabelFrame(main_frame, text="Firewall Configuration", padding="10")
        fw_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        fw_frame.columnconfigure(1, weight=1)
        fw_frame.columnconfigure(3, weight=1)
        
        # Create firewall fields in two columns
        self.create_firewall_fields(fw_frame)
        
        # Prisma Access Configuration Section - Two columns
        pa_frame = ttk.LabelFrame(main_frame, text="Prisma Access Configuration", padding="10")
        pa_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        pa_frame.columnconfigure(1, weight=1)
        pa_frame.columnconfigure(3, weight=1)
        
        # Create Prisma Access fields
        self.create_prisma_fields(pa_frame)
        
        # Operations Section
        ops_frame = ttk.LabelFrame(main_frame, text="Operations", padding="10")
        ops_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        
        ttk.Button(ops_frame, text="Configure Initial Config", command=self.run_initial_config).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(ops_frame, text="Configure Firewall", command=self.run_configure_firewall).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(ops_frame, text="Configure Service Connection", command=self.run_service_connection).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(ops_frame, text="Get FW Version", command=self.get_fw_version).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(ops_frame, text="Print Settings", command=self.print_settings).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(ops_frame, text="Load from SCM", command=self.load_from_scm).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(ops_frame, text="Load from SPOV File...", command=self.load_from_spov).grid(row=1, column=2, padx=5, pady=5)
        
        # Status/Output Section
        status_frame = ttk.LabelFrame(main_frame, text="Status/Output", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=10)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=12, wrap=tk.WORD, font=("Courier", 9))
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu to status text
        self.setup_context_menu(self.status_text)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, padding=5)
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=5)
        
        # Update canvas scroll region when window is resized
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        main_frame.bind("<Configure>", on_frame_configure)
    
    def create_firewall_fields(self, parent):
        """Create firewall configuration fields in two columns"""
        # All firewall fields from defaults and usage
        fields = [
            # Column 1
            ("Management URL", "mgmtUrl", False),
            ("Management User", "mgmtUser", False),
            ("Management Password", "mgmtPass", True),
            ("Untrust URL", "untrustURL", False),
            ("Untrust Address", "untrustAddr", False),
            ("Untrust Subnet", "untrustSubnet", False),
            ("Untrust Interface", "untrustInt", False),
            ("Untrust Default GW", "untrustDFGW", False),
            # Column 2
            ("Trust Address", "trustAddr", False),
            ("Trust Subnet", "trustSubnet", False),
            ("Trust Interface", "trustInt", False),
            ("Tunnel Interface", "tunnelInt", False),
            ("Tunnel Address", "tunnelAddr", False),
            ("Panorama Address", "panoramaAddr", False),
        ]
        
        # Split into two columns
        col1_fields = fields[:8]
        col2_fields = fields[8:]
        
        # Column 1
        row = 0
        for label, key, is_password in col1_fields:
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "")
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            # Add validation and auto-calculation
            self._setup_field_validation(entry, key, label)
            
            self.add_copy_button(parent, entry, row, 2)
            self.setup_context_menu(entry)
            
            self.fw_fields[key] = var
            row += 1
        
        # Column 2
        row = 0
        for label, key, is_password in col2_fields:
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=3, sticky=tk.W, padx=5, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "")
            entry.grid(row=row, column=4, sticky=(tk.W, tk.E), padx=5, pady=3)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            # Add validation and auto-calculation
            self._setup_field_validation(entry, key, label)
            
            self.add_copy_button(parent, entry, row, 5)
            self.setup_context_menu(entry)
            
            self.fw_fields[key] = var
            row += 1
    
    def create_prisma_fields(self, parent):
        """Create Prisma Access configuration fields in two columns"""
        # All Prisma Access fields from defaults and usage
        fields = [
            # Column 1
            ("Managed By", "paManagedBy", False, "dropdown"),
            ("TSG ID", "paTSGID", False, None),
            ("API User", "paApiUser", False, None),
            ("API Secret", "paApiSecret", True, None),
            ("Infrastructure Subnet", "paInfraSubnet", False, None),
            ("Infrastructure BGP AS", "paInfraBGPAS", False, None),
            ("Mobile User Subnet", "paMobUserSubnet", False, None),
            ("Portal Hostname", "paPortalHostname", False, None),
            # Column 2
            ("SC Endpoint", "paSCEndpoint", False, None),
            ("SC Name", "scName", False, None),
            ("SC Location", "scLocation", False, None),
            ("SC Subnet", "scSubnet", False, None),
            ("SC Tunnel Name", "scTunnelName", False, None),
            ("SC PSK", "paSCPsk", True, None),
            # Panorama fields
            ("Panorama Mgmt URL", "panMgmtUrl", False, None),
            ("Panorama User", "panUser", False, None),
            ("Panorama Password", "panPass", True, None),
        ]
        
        # Split into two columns
        col1_fields = fields[:8]
        col2_fields = fields[8:]
        
        # Column 1
        row = 0
        for field_info in col1_fields:
            if len(field_info) == 4 and field_info[3] == "dropdown":
                label, key, is_password, field_type = field_info
                ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
                var = tk.StringVar()
                combo = ttk.Combobox(parent, textvariable=var, values=["scm", "pan"], width=32, state="readonly")
                combo.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
                combo.set("scm")  # Default value
                self._add_tooltip(combo, self._get_field_tooltip(key))
                self.pa_fields[key] = var
            else:
                label, key, is_password = field_info[:3]
                ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
                var = tk.StringVar()
                entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "")
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
                
                # Add tooltip
                self._add_tooltip(entry, self._get_field_tooltip(key))
                
                if is_password:
                    self.password_fields[key] = entry
                
                self.add_copy_button(parent, entry, row, 2)
                self.setup_context_menu(entry)
                
                self.pa_fields[key] = var
            row += 1
        
        # Column 2
        row = 0
        for field_info in col2_fields:
            label, key, is_password = field_info[:3]
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=3, sticky=tk.W, padx=5, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "")
            entry.grid(row=row, column=4, sticky=(tk.W, tk.E), padx=5, pady=3)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            self.add_copy_button(parent, entry, row, 5)
            self.setup_context_menu(entry)
            
            self.pa_fields[key] = var
            row += 1
    
    def add_copy_button(self, parent, entry_widget, row, col):
        """Add a copy button next to an entry widget"""
        copy_btn = ttk.Button(parent, text="📋", width=3, 
                              command=lambda: self.copy_to_clipboard(entry_widget.get()))
        copy_btn.grid(row=row, column=col, padx=2, pady=3)
        return copy_btn
    
    def setup_context_menu(self, widget):
        """Setup right-click context menu for copy/paste"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Copy", command=lambda: self.copy_widget_text(widget))
        context_menu.add_command(label="Paste", command=lambda: self.paste_to_widget(widget))
        context_menu.add_command(label="Select All", command=lambda: self.select_all_widget(widget))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        widget.bind("<Button-3>", show_context_menu)  # Right-click
        if isinstance(widget, tk.Entry):
            widget.bind("<Control-a>", lambda e: self.select_all_widget(widget))
    
    def copy_widget_text(self, widget):
        """Copy text from widget to clipboard"""
        if isinstance(widget, tk.Entry):
            text = widget.get()
        elif isinstance(widget, scrolledtext.ScrolledText):
            try:
                text = widget.selection_get()
            except:
                text = widget.get("1.0", tk.END).strip()
        else:
            return
        
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("Copied to clipboard")
    
    def paste_to_widget(self, widget):
        """Paste text from clipboard to widget"""
        try:
            text = self.root.clipboard_get()
            if isinstance(widget, tk.Entry):
                widget.delete(0, tk.END)
                widget.insert(0, text)
            elif isinstance(widget, scrolledtext.ScrolledText):
                widget.insert(tk.INSERT, text)
            self.status_var.set("Pasted from clipboard")
        except:
            pass
    
    def select_all_widget(self, widget):
        """Select all text in widget"""
        if isinstance(widget, tk.Entry):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        elif isinstance(widget, scrolledtext.ScrolledText):
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
        return "break"
    
    def toggle_passwords(self):
        """Toggle password visibility"""
        if not self.password_fields:
            return
        
        # Check current state of first password field
        first_entry = list(self.password_fields.values())[0]
        current_show = first_entry.cget("show")
        new_show = "" if current_show == "*" else "*"
        
        for key, entry in self.password_fields.items():
            entry.config(show=new_show)
        
        status = "shown" if new_show == "" else "hidden"
        self.status_var.set(f"Passwords {status}")
        self.log_output(f"Password visibility: {status}")
    
    # Menu and operation methods
    
    def new_config(self):
        """Create a new configuration"""
        # Check for unsaved changes
        if self.config_modified:
            if not messagebox.askyesno("Unsaved Changes", 
                                      "You have unsaved changes. Create new configuration anyway?"):
                return
        
        self.status_var.set("Creating new configuration...")
        self.log_output("Creating new configuration...")
        # Clear all fields
        for var in self.fw_fields.values():
            var.set("")
        for var in self.pa_fields.values():
            var.set("")
        self.config_name_var.set("")
        self.encrypt_pass_var.set("")
        self.current_config = None
        self.config_file_path = None
        self.config_cipher = None
        self.config_modified = False
        self.status_var.set("New configuration ready")
        self.log_output("Configuration cleared. Ready for new configuration.")
    
    def load_config_file_direct(self, file_path, cipher):
        """Load a specific config file directly (helper function)"""
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = cipher.decrypt(encrypted_data)
            data = pickle.loads(decrypted_data)
            
            # Add metadata
            config_name = os.path.basename(file_path).split('-')[0]
            data['configName'] = config_name
            data['configCipher'] = cipher
            return data
        except Exception as e:
            raise Exception(f"Failed to decrypt/load config: {str(e)}")
    
    def load_config(self):
        """Load configuration from file"""
        if not load_settings:
            messagebox.showerror("Error", "load_settings module not available")
            return
        
        # Use list_config_files to show available configs, or use file dialog
        config_files = []
        if load_settings:
            try:
                config_files = load_settings.list_config_files(self.last_directory)
            except:
                pass
        
        # If config files found, show them in a dialog
        if config_files:
            # Create a simple dialog to select from list
            file_path = self.show_config_file_dialog(config_files)
        else:
            # Use standard file dialog
            file_path = filedialog.askopenfilename(
                title="Select Configuration File",
                filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
                initialdir=self.last_directory
            )
        
        if not file_path:
            return
        
        # Update last directory
        self.last_directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
        
        # Prompt for password
        password = simpledialog.askstring("Password", "Enter encryption password:", show="*")
        if not password:
            return
        
        try:
            # Use load_settings module to derive key
            cipher = load_settings.derive_key(password)
            
            # Load the file directly
            config_data = self.load_config_file_direct(file_path, cipher)
            
            if config_data:
                self.current_config = config_data
                self.config_cipher = cipher
                self.config_file_path = file_path
                self.populate_fields(config_data)
                self.add_to_recent_files(file_path)
                self.config_modified = False
                filename = os.path.basename(file_path)
                self.root.title(f"Palo Alto Configuration Lab - {filename}")
                self.status_var.set(f"Loaded: {filename}")
                self.log_output(f"Configuration loaded successfully from {file_path}")
                messagebox.showinfo("Success", f"Configuration loaded: {filename}")
            else:
                messagebox.showerror("Error", "Failed to load configuration. Check password.")
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error loading config: {error_msg}")
            messagebox.showerror("Error", f"Failed to load configuration:\n{error_msg}")
    
    def show_config_file_dialog(self, config_files):
        """Show a dialog to select from available config files"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Configuration File")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = [None]  # Use list to store result from nested function
        
        # Listbox with scrollbar
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Available Configuration Files:").pack(anchor=tk.W, pady=5)
        
        listbox_frame = ttk.Frame(frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Add files to listbox
        for file_path in config_files:
            file_name = os.path.basename(file_path)
            listbox.insert(tk.END, file_name)
        
        if config_files:
            listbox.selection_set(0)
            listbox.activate(0)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                result[0] = config_files[selection[0]]
                dialog.destroy()
        
        def on_double_click(event):
            on_select()
        
        listbox.bind('<Double-Button-1>', on_double_click)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Browse...", command=lambda: self.browse_other_file(dialog, result)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
        return result[0]
    
    def browse_other_file(self, parent_dialog, result):
        """Browse for a file not in the list"""
        parent_dialog.destroy()
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
            initialdir=self.last_directory
        )
        result[0] = file_path
    
    def save_config(self):
        """Save current configuration to file"""
        if not get_settings:
            messagebox.showerror("Error", "get_settings module not available")
            return
        
        if not self.config_name_var.get():
            messagebox.showwarning("Warning", "Please enter a configuration name")
            return
        
        # If we have a current file path, save to it
        if self.config_file_path and os.path.exists(self.config_file_path):
            self._save_to_file(self.config_file_path)
        else:
            # Use Save As dialog
            self.save_config_as()
    
    def save_config_as(self):
        """Save configuration with file dialog"""
        if not get_settings:
            messagebox.showerror("Error", "get_settings module not available")
            return
        
        if not self.config_name_var.get():
            messagebox.showwarning("Warning", "Please enter a configuration name")
            return
        
        # Suggest filename based on config name
        config_name = self.config_name_var.get().strip()
        suggested_filename = config_name.lower().replace(" ", "_") + "-fwdata.bin"
        
        file_path = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".bin",
            filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
            initialdir=self.last_directory,
            initialfile=suggested_filename
        )
        
        if not file_path:
            return
        
        # Update last directory
        self.last_directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
        
        # Check if file exists and ask for confirmation
        if os.path.exists(file_path):
            if not messagebox.askyesno("Confirm Overwrite", 
                                     f"File already exists:\n{os.path.basename(file_path)}\n\nOverwrite?"):
                return
        
        self._save_to_file(file_path)
    
    def _save_to_file(self, file_path):
        """Internal method to save configuration to a specific file"""
        if not get_settings:
            messagebox.showerror("Error", "get_settings module not available")
            return
        
        # Collect current field values
        fw_data = {key: var.get() for key, var in self.fw_fields.items()}
        pa_data = {key: var.get() for key, var in self.pa_fields.items()}
        
        # Get or prompt for password
        if not self.config_cipher:
            password = simpledialog.askstring("Password", "Enter encryption password:", show="*")
            if not password:
                return
            self.config_cipher = get_settings.derive_key(password)
        
        try:
            # Extract config name from filename or use entered name
            config_name = self.config_name_var.get().strip()
            if not config_name:
                config_name = os.path.basename(file_path).split('-')[0]
            
            # Use get_settings module to save config
            # Note: get_settings.save_config_to_file may prompt for overwrite, 
            # but we've already handled that, so we'll save directly
            success = self._save_config_direct(file_path, config_name, self.config_cipher, fw_data, pa_data)
            
            if success:
                self.config_file_path = file_path
                self.config_modified = False
                self.add_to_recent_files(file_path)
                self.status_var.set(f"Saved: {os.path.basename(file_path)}")
                self.log_output(f"Configuration saved successfully: {file_path}")
                # Update window title to remove asterisk
                filename = os.path.basename(file_path)
                self.root.title(f"Palo Alto Configuration Lab - {filename}")
                messagebox.showinfo("Success", f"Configuration saved:\n{os.path.basename(file_path)}")
            else:
                self.log_output("Configuration saved (no changes detected)")
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error saving config: {error_msg}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{error_msg}")
    
    def _save_config_direct(self, file_path, config_name, cipher, fw_data, pa_data):
        """Directly save config without prompts (used by GUI)"""
        try:
            # Load defaults to merge with
            defaults = get_settings.load_defaults()
            
            # Merge current data with defaults
            merged_fw = defaults['fwData'].copy()
            merged_fw.update(fw_data)
            
            merged_pa = defaults['paData'].copy()
            merged_pa.update(pa_data)
            
            # Create config dict
            config_data = {
                'fwData': merged_fw,
                'paData': merged_pa,
                'configName': config_name
            }
            
            # Encrypt and save
            encrypted_data = cipher.encrypt(pickle.dumps(config_data))
            
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            raise Exception(f"Save failed: {str(e)}")
    
    def populate_fields(self, config_data):
        """Populate GUI fields from config data"""
        fw_data = config_data.get('fwData', {})
        pa_data = config_data.get('paData', {})
        
        # Temporarily disable change tracking
        self.config_modified = False
        
        for key, var in self.fw_fields.items():
            if key in fw_data:
                var.set(str(fw_data[key]))
        
        for key, var in self.pa_fields.items():
            if key in pa_data:
                var.set(str(pa_data[key]))
        
        if 'configName' in config_data:
            self.config_name_var.set(config_data['configName'])
        
        # Re-enable change tracking
        self.config_modified = False
        
        # Bind change tracking to all fields
        self._setup_change_tracking()
    
    def _setup_change_tracking(self):
        """Setup change tracking for all fields"""
        for var in list(self.fw_fields.values()) + list(self.pa_fields.values()) + [self.config_name_var]:
            var.trace_add('write', lambda *args: self._on_field_change())
    
    def _setup_field_validation(self, entry, key, label):
        """Setup validation for a field"""
        # Determine field type for validation
        field_type = None
        if "Addr" in key and "Subnet" not in key and "URL" not in key:
            field_type = "ip"
        elif "Subnet" in key:
            field_type = "subnet"
        elif "URL" in key or "Hostname" in key:
            field_type = "url"
        
        # Setup validation on focus out
        if field_type:
            def validate_on_focusout(event):
                value = self.fw_fields[key].get() if key in self.fw_fields else self.pa_fields[key].get()
                self.validate_field(entry, field_type, value)
            entry.bind('<FocusOut>', validate_on_focusout)
    
    def _setup_auto_calculation(self):
        """Setup auto-calculation bindings after all fields are created"""
        # Untrust Address -> Subnet -> Gateway
        if "untrustAddr" in self.fw_fields and "untrustSubnet" in self.fw_fields:
            def calc_untrust_subnet(*args):
                if self.fw_fields["untrustAddr"].get():
                    self.auto_calculate_subnet("untrustAddr", "untrustSubnet")
            self.fw_fields["untrustAddr"].trace_add('write', calc_untrust_subnet)
            
            # Also bind to focus out for immediate calculation
            for widget in self.root.winfo_children():
                self._bind_autocalc_to_widget(widget, "untrustAddr", calc_untrust_subnet)
        
        if "untrustSubnet" in self.fw_fields and "untrustDFGW" in self.fw_fields:
            def calc_untrust_gateway(*args):
                if self.fw_fields["untrustSubnet"].get():
                    self.auto_calculate_gateway("untrustSubnet", "untrustDFGW")
            self.fw_fields["untrustSubnet"].trace_add('write', calc_untrust_gateway)
        
        # Trust Address -> Subnet
        if "trustAddr" in self.fw_fields and "trustSubnet" in self.fw_fields:
            def calc_trust_subnet(*args):
                if self.fw_fields["trustAddr"].get():
                    self.auto_calculate_subnet("trustAddr", "trustSubnet")
            self.fw_fields["trustAddr"].trace_add('write', calc_trust_subnet)
    
    def _bind_autocalc_to_widget(self, widget, field_key, callback):
        """Recursively find and bind to entry widget"""
        if isinstance(widget, ttk.Entry):
            for key, var in self.fw_fields.items():
                if key == field_key:
                    widget.bind('<FocusOut>', lambda e: callback())
                    return
        for child in widget.winfo_children():
            self._bind_autocalc_to_widget(child, field_key, callback)
    
    def _on_field_change(self):
        """Called when any field changes"""
        self.config_modified = True
        if self.config_file_path:
            filename = os.path.basename(self.config_file_path)
            self.root.title(f"Palo Alto Configuration Lab - {filename} *")
        else:
            self.root.title("Palo Alto Configuration Lab *")
    
    def _get_field_tooltip(self, key):
        """Get tooltip text for a field"""
        tooltips = {
            # Firewall fields
            'mgmtUrl': 'Firewall management URL (e.g., https://fw.example.com)',
            'mgmtUser': 'Firewall management username',
            'mgmtPass': 'Firewall management password',
            'untrustURL': 'Firewall untrust interface FQDN or IP',
            'untrustAddr': 'Untrust interface IP address with CIDR (e.g., 10.32.0.4/24). Subnet auto-calculated.',
            'untrustSubnet': 'Untrust network subnet in CIDR notation (e.g., 10.32.0.0/24)',
            'untrustInt': 'Untrust interface name (e.g., ethernet1/1)',
            'untrustDFGW': 'Untrust default gateway IP. Auto-calculated from subnet.',
            'trustAddr': 'Trust interface IP address with CIDR (e.g., 10.32.1.4/24). Subnet auto-calculated.',
            'trustSubnet': 'Trust network subnet in CIDR notation (e.g., 10.32.1.0/24)',
            'trustInt': 'Trust interface name (e.g., ethernet1/2)',
            'tunnelInt': 'Tunnel interface name (e.g., tunnel.1)',
            'tunnelAddr': 'Tunnel interface IP address (optional)',
            'panoramaAddr': 'Panorama server IP address',
            # Prisma Access fields
            'paManagedBy': 'How Prisma Access is managed: SCM (Prisma Access Cloud) or Panorama',
            'paTSGID': 'Prisma Access Tenant Service Group ID',
            'paApiUser': 'Prisma Access API Client ID',
            'paApiSecret': 'Prisma Access API Client Secret',
            'paInfraSubnet': 'Prisma Access infrastructure subnet',
            'paInfraBGPAS': 'Prisma Access infrastructure BGP AS number',
            'paMobUserSubnet': 'Prisma Access mobile user subnet',
            'paPortalHostname': 'Prisma Access portal hostname',
            'paSCEndpoint': 'Prisma Access Service Connection endpoint FQDN',
            'scName': 'Service Connection name',
            'scLocation': 'Service Connection location/region',
            'scSubnet': 'Service Connection subnet',
            'scTunnelName': 'Service Connection tunnel name',
            'paSCPsk': 'Service Connection pre-shared key',
            'panMgmtUrl': 'Panorama management URL',
            'panUser': 'Panorama username',
            'panPass': 'Panorama password',
        }
        return tooltips.get(key, '')
    
    def _add_tooltip(self, widget, text):
        """Add a tooltip to a widget"""
        if not text:
            return
        
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1,
                           font=("TkDefaultFont", 9), wraplength=300, justify="left")
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(text))
            self.status_var.set("Copied to clipboard")
    
    def copy_selected(self):
        """Copy selected text"""
        widget = self.root.focus_get()
        if widget:
            self.copy_widget_text(widget)
    
    def paste_selected(self):
        """Paste from clipboard"""
        widget = self.root.focus_get()
        if widget:
            self.paste_to_widget(widget)
    
    def change_password(self):
        """Change encryption password"""
        if not self.config_cipher:
            messagebox.showinfo("Info", "No configuration loaded. Password will be set when saving.")
            return
        
        old_pass = simpledialog.askstring("Old Password", "Enter current password:", show="*")
        if not old_pass:
            return
        
        new_pass = simpledialog.askstring("New Password", "Enter new password:", show="*")
        if not new_pass:
            return
        
        new_pass_confirm = simpledialog.askstring("Confirm Password", "Confirm new password:", show="*")
        if new_pass != new_pass_confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        # For now, just update the cipher
        # Full implementation would re-encrypt the config file
        self.config_cipher = get_settings.derive_key(new_pass) if get_settings else None
        self.log_output("Password changed. Remember to save configuration.")
        messagebox.showinfo("Info", "Password changed. Save configuration to apply.")
    
    def load_from_scm(self):
        """Load configuration from Prisma Access SCM"""
        if not get_settings or not load_settings:
            messagebox.showerror("Error", "Required modules not available")
            return
        
        # Create dialog for SCM credentials
        dialog = tk.Toplevel(self.root)
        dialog.title("Load from Prisma Access SCM")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {"tsg": None, "user": None, "secret": None, "cancel": True}
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enter Prisma Access SCM Credentials:", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        ttk.Label(frame, text="TSG ID:").pack(anchor=tk.W, pady=5)
        tsg_var = tk.StringVar()
        tsg_entry = ttk.Entry(frame, textvariable=tsg_var, width=40)
        tsg_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text="Client ID:").pack(anchor=tk.W, pady=5)
        user_var = tk.StringVar()
        user_entry = ttk.Entry(frame, textvariable=user_var, width=40)
        user_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text="Client Secret:").pack(anchor=tk.W, pady=5)
        secret_var = tk.StringVar()
        secret_entry = ttk.Entry(frame, textvariable=secret_var, show="*", width=40)
        secret_entry.pack(fill=tk.X, pady=2)
        
        def on_load():
            if not tsg_var.get() or not user_var.get() or not secret_var.get():
                messagebox.showwarning("Warning", "Please fill in all fields")
                return
            result["tsg"] = tsg_var.get().strip()
            result["user"] = user_var.get().strip()
            result["secret"] = secret_var.get().strip()
            result["cancel"] = False
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Load", command=on_load).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
        
        if result["cancel"]:
            return
        
        # Authenticate and load config
        try:
            self.log_output("Authenticating to Prisma Access SCM...")
            self.status_var.set("Authenticating...")
            self.root.update()
            
            access_token = load_settings.prisma_access_auth(
                result["tsg"], result["user"], result["secret"]
            )
            
            if not access_token:
                messagebox.showerror("Error", "Authentication failed. Check credentials and TSG ID.")
                self.log_output("Authentication failed")
                return
            
            self.log_output("Authentication successful. Loading configuration...")
            self.status_var.set("Loading configuration from SCM...")
            self.root.update()
            
            # Get PA config from SCM
            pa_config = get_settings.get_pa_config(access_token)
            
            if not pa_config:
                messagebox.showerror("Error", "Failed to load configuration from SCM")
                self.log_output("Failed to load configuration from SCM")
                return
            
            # Add credentials to config
            pa_config['paTSGID'] = result["tsg"]
            pa_config['paApiUser'] = result["user"]
            pa_config['paApiSecret'] = result["secret"]
            pa_config['paManagedBy'] = 'scm'
            
            # Populate Prisma Access fields
            for key, value in pa_config.items():
                if key in self.pa_fields:
                    self.pa_fields[key].set(str(value))
            
            self.config_modified = True
            self.status_var.set("Configuration loaded from SCM")
            self.log_output("Configuration loaded successfully from Prisma Access SCM")
            messagebox.showinfo("Success", "Configuration loaded from Prisma Access SCM")
            
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error loading from SCM: {error_msg}")
            messagebox.showerror("Error", f"Failed to load from SCM:\n{error_msg}")
    
    def load_from_spov(self):
        """Load configuration from SPOV questionnaire file"""
        if not get_settings:
            messagebox.showerror("Error", "get_settings module not available")
            return
        
        file_path = filedialog.askopenfilename(
            title="Select SPOV Questionnaire File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.last_directory
        )
        if not file_path:
            return
        
        self.last_directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
        
        try:
            self.log_output(f"Loading SPOV file: {file_path}")
            self.status_var.set("Loading SPOV configuration...")
            self.root.update()
            
            # Load SPOV config
            pa_config = get_settings.load_spov_questionnaire(file_path)
            
            if not pa_config:
                messagebox.showerror("Error", "Failed to load SPOV questionnaire file")
                self.log_output("Failed to load SPOV file")
                return
            
            # Populate Prisma Access fields
            for key, value in pa_config.items():
                if key in self.pa_fields:
                    self.pa_fields[key].set(str(value))
            
            # Set managed by if not set
            if 'paManagedBy' not in pa_config or not self.pa_fields['paManagedBy'].get():
                self.pa_fields['paManagedBy'].set('scm')
            
            self.config_modified = True
            self.status_var.set("SPOV configuration loaded")
            self.log_output(f"SPOV configuration loaded successfully from {file_path}")
            messagebox.showinfo("Success", f"SPOV configuration loaded:\n{os.path.basename(file_path)}")
            
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error loading SPOV file: {error_msg}")
            messagebox.showerror("Error", f"Failed to load SPOV file:\n{error_msg}")
    
    def run_initial_config(self):
        """Run configure_initial_config.py - Configure NTP/DNS/HA"""
        if not PANOS_AVAILABLE:
            messagebox.showerror("Error", "pan-os-python module not available")
            return
        
        required_fields = ['mgmtUrl', 'mgmtUser', 'mgmtPass']
        if not self.validate_required_fields(required_fields):
            return
        
        # Run in separate thread to avoid blocking GUI
        def run_operation():
            try:
                self.status_var.set("Configuring initial settings...")
                self.log_output("\n" + "="*60)
                self.log_output("Configuring Initial Firewall Settings")
                self.log_output("="*60)
                
                config = self.get_config_dict()
                fw_data = config['fwData']
                
                # Redirect stdout/stderr
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = self.TextRedirector(self.status_text)
                sys.stderr = self.TextRedirector(self.status_text)
                
                try:
                    # Establish connection
                    self.log_output(f"Connecting to firewall: {fw_data['mgmtUrl']}")
                    firewall = Firewall(fw_data["mgmtUrl"], fw_data['mgmtUser'], 
                                       fw_data["mgmtPass"], vsys=None, is_virtual=True)
                    
                    # Configure HA disabled
                    self.log_output("Configuring High Availability (disabled)...")
                    haConf = HighAvailability(enabled=False, config_sync=False, state_sync=False)
                    firewall.add(haConf)
                    haConf.apply()
                    
                    # Update DNS Settings
                    self.log_output("Configuring DNS servers (8.8.8.8, 8.8.4.4)...")
                    system = SystemSettings(dns_primary='8.8.8.8', dns_secondary='8.8.4.4')
                    
                    # Add NTP servers
                    self.log_output("Configuring NTP servers...")
                    ntp1 = NTPServerPrimary(address='0.pool.ntp.org', authentication_type='None')
                    system.add(ntp1)
                    ntp2 = NTPServerSecondary(address='1.pool.ntp.org', authentication_type='None')
                    system.add(ntp2)
                    
                    firewall.add(system)
                    system.apply()
                    
                    # Commit changes
                    self.log_output("Committing configuration...")
                    firewall.commit()
                    
                    self.log_output("Initial configuration completed successfully!")
                    self.status_var.set("Initial configuration completed")
                    messagebox.showinfo("Success", "Initial firewall configuration completed successfully!")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log_output(f"Error: {error_msg}")
                    self.status_var.set("Configuration failed")
                    messagebox.showerror("Error", f"Configuration failed:\n{error_msg}")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        
        threading.Thread(target=run_operation, daemon=True).start()
    
    def run_configure_firewall(self):
        """Run configure_firewall.py - Configure zones, interfaces, routes, policies"""
        if not PANOS_AVAILABLE:
            messagebox.showerror("Error", "pan-os-python module not available")
            return
        
        required_fields = ['mgmtUrl', 'mgmtUser', 'mgmtPass', 'untrustInt', 'untrustAddr', 
                          'trustInt', 'trustAddr', 'untrustDFGW', 'panoramaAddr']
        if not self.validate_required_fields(required_fields):
            return
        
        def run_operation():
            try:
                self.status_var.set("Configuring firewall...")
                self.log_output("\n" + "="*60)
                self.log_output("Configuring Firewall")
                self.log_output("="*60)
                
                config = self.get_config_dict()
                fw_data = config['fwData']
                
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = self.TextRedirector(self.status_text)
                sys.stderr = self.TextRedirector(self.status_text)
                
                try:
                    # Import configure_firewall logic here
                    # For now, we'll replicate the key parts
                    self.log_output(f"Connecting to firewall: {fw_data['mgmtUrl']}")
                    firewall = Firewall(fw_data["mgmtUrl"], fw_data['mgmtUser'], 
                                       fw_data["mgmtPass"], vsys=None, is_virtual=True)
                    firewall.vsys = None
                    
                    # Configure zones
                    self.log_output("Creating zones (trust, untrust)...")
                    zoneTrust = Zone(name='trust', mode='layer3')
                    zoneUntrust = Zone(name='untrust', mode='layer3')
                    firewall.add(zoneTrust)
                    firewall.add(zoneUntrust)
                    zoneTrust.create()
                    zoneUntrust.create()
                    
                    # Configure interfaces
                    self.log_output(f"Configuring untrust interface: {fw_data['untrustInt']}")
                    eth1 = EthernetInterface(fw_data['untrustInt'], mode='layer3')
                    eth1.ip = fw_data['untrustAddr']
                    firewall.add(eth1)
                    eth1.set_zone('untrust', mode='layer3', refresh=True, update=True)
                    eth1.set_virtual_router('default', refresh=True, update=True)
                    eth1.create()
                    
                    self.log_output(f"Configuring trust interface: {fw_data['trustInt']}")
                    eth2 = EthernetInterface(fw_data['trustInt'], mode='layer3')
                    eth2.ip = fw_data['trustAddr']
                    firewall.add(eth2)
                    eth2.set_zone('trust', mode='layer3', refresh=True, update=True)
                    eth2.set_virtual_router('default', refresh=True, update=True)
                    eth2.create()
                    
                    self.log_output("Committing interface configuration...")
                    firewall.commit()
                    
                    # Configure static routes
                    self.log_output("Configuring static routes...")
                    vrouter = VirtualRouter(name='default')
                    defaultRoute = StaticRoute(
                        name='default-route',
                        destination='0.0.0.0/0',
                        interface=fw_data["untrustInt"],
                        nexthop_type='ip-address',
                        nexthop=fw_data['untrustDFGW']
                    )
                    firewall.add(vrouter)
                    vrouter.add(defaultRoute)
                    defaultRoute.create()
                    firewall.commit()
                    
                    # Configure address objects
                    self.log_output("Creating address objects...")
                    addr = {}
                    addr['netTrust'] = AddressObject("Trust-Network", fw_data['trustSubnet'], 
                                                     description="Company trust network")
                    addr['netUntrust'] = AddressObject("Untrust-Network", fw_data['untrustSubnet'], 
                                                       description="Company untrust network")
                    addr['panorama'] = AddressObject("Panorama-Server", fw_data['panoramaAddr'], 
                                                     description="Panorama server")
                    
                    for i in addr:
                        firewall.add(addr[i])
                        addr[i].create()
                    firewall.commit()
                    
                    # Configure security rules
                    self.log_output("Creating security rules...")
                    base = Rulebase()
                    firewall.add(base)
                    
                    rules = []
                    rules.append(SecurityRule(
                        name='Outbound Internet',
                        description='Allow trust zone to internet',
                        fromzone=['trust'],
                        tozone=['untrust'],
                        source=["Trust-Network"],
                        destination=['any'],
                        application=['ssl','web-browsing'],
                        action='allow',
                        log_end=True
                    ))
                    rules.append(SecurityRule(
                        name='Allow Panorama Management',
                        description='Allow Panorama Management from the Internet',
                        fromzone=['untrust'],
                        tozone=['trust'],
                        source=['any'],
                        destination=[fw_data['panoramaAddr']],
                        application=['ssl','web-browsing','ssh'],
                        action='allow',
                        log_end=True
                    ))
                    rules.append(SecurityRule(
                        name='Deny All',
                        description='Deny All',
                        fromzone=['any'],
                        tozone=['any'],
                        source=['any'],
                        destination=['any'],
                        application=['any'],
                        action='deny',
                        log_end=True
                    ))
                    
                    configFail = False
                    for rule in rules:
                        try:
                            base.add(rule)
                            rule.create()
                            self.log_output(f"Security rule '{rule.name}' created successfully")
                        except Exception as e:
                            self.log_output(f"Error creating Security Rule '{rule.name}': {e}")
                            configFail = True
                    
                    if not configFail:
                        firewall.commit()
                    
                    # Configure NAT rules
                    self.log_output("Creating NAT rules...")
                    base = Rulebase()
                    firewall.add(base)
                    
                    internetNAT = NatRule(
                        name='Outbound Internet',
                        description='Allow internal systems on Trust zone to internet with PAT',
                        nat_type='ipv4',
                        fromzone=['trust'],
                        tozone=['untrust'],
                        to_interface=fw_data['untrustInt'],
                        source=['Trust-Network'],
                        source_translation_type='dynamic-ip-and-port',
                        source_translation_address_type='interface-address',
                        source_translation_interface=fw_data['untrustInt'],
                    )
                    
                    panoramaNAT = NatRule(
                        name='Panorama Management',
                        description='Allow external management of Panorama on Trust Network',
                        nat_type='ipv4',
                        fromzone=['untrust'],
                        tozone=['trust'],
                        to_interface=fw_data['untrustInt'],
                        service='service-https',
                        source=['any'],
                        destination=[fw_data['untrustAddr'][:-3]] if '/' in fw_data['untrustAddr'] else [fw_data['untrustAddr']],
                        source_translation_type='dynamic-ip-and-port',
                        source_translation_address_type='interface-address',
                        source_translation_interface=fw_data['trustInt'],
                        destination_translated_address='Panorama-Server'
                    )
                    
                    configFail = False
                    try:
                        base.add(internetNAT)
                        internetNAT.create()
                        self.log_output("Outbound NAT rule created successfully")
                    except Exception as e:
                        self.log_output(f"Error creating Outbound NAT rule: {e}")
                        configFail = True
                    
                    try:
                        base.add(panoramaNAT)
                        panoramaNAT.create()
                        self.log_output("Panorama NAT rule created successfully")
                    except Exception as e:
                        self.log_output(f"Error creating Panorama NAT rule: {e}")
                        configFail = True
                    
                    if not configFail:
                        firewall.commit()
                    
                    self.log_output("Firewall configuration completed successfully!")
                    self.status_var.set("Firewall configuration completed")
                    messagebox.showinfo("Success", "Firewall configuration completed successfully!")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log_output(f"Error: {error_msg}")
                    self.status_var.set("Configuration failed")
                    messagebox.showerror("Error", f"Configuration failed:\n{error_msg}")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        
        threading.Thread(target=run_operation, daemon=True).start()
    
    def run_service_connection(self):
        """Run configure_service_connection.py"""
        self.log_output("Configuring service connection...")
        messagebox.showinfo("Info", "Service connection configuration is complex and requires\ninteractive prompts. Please use configure_service_connection.py\nfrom the command line for now.")
    
    def get_fw_version(self):
        """Get firewall version"""
        if not PANOS_AVAILABLE:
            messagebox.showerror("Error", "pan-os-python module not available")
            return
        
        required_fields = ['mgmtUrl', 'mgmtUser', 'mgmtPass']
        if not self.validate_required_fields(required_fields):
            return
        
        def run_operation():
            try:
                self.status_var.set("Getting firewall version...")
                self.log_output("\n" + "="*60)
                self.log_output("Firewall Version Information")
                self.log_output("="*60)
                
                config = self.get_config_dict()
                fw_data = config['fwData']
                
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = self.TextRedirector(self.status_text)
                sys.stderr = self.TextRedirector(self.status_text)
                
                try:
                    self.log_output(f"Connecting to firewall: {fw_data['mgmtUrl']}")
                    firewall = Firewall(fw_data["mgmtUrl"], fw_data['mgmtUser'], 
                                       fw_data["mgmtPass"], vsys=None, is_virtual=True)
                    
                    self.log_output("Retrieving system information...")
                    version = firewall.refresh_system_info().version
                    
                    self.log_output(f"\nFirewall Version: {version}")
                    self.status_var.set(f"Firewall Version: {version}")
                    messagebox.showinfo("Firewall Version", f"Version: {version}")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log_output(f"Error: {error_msg}")
                    self.status_var.set("Failed to get version")
                    messagebox.showerror("Error", f"Failed to get firewall version:\n{error_msg}")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        
        threading.Thread(target=run_operation, daemon=True).start()
    
    def print_settings(self):
        """Print current settings"""
        self.log_output("\n" + "="*60)
        self.log_output("Current Settings")
        self.log_output("="*60)
        self.log_output("\nFirewall Configuration:")
        for key, var in sorted(self.fw_fields.items()):
            value = var.get()
            if "pass" in key.lower() or "secret" in key.lower():
                value = "************"
            self.log_output(f"  {key:20s}: {value}")
        
        self.log_output("\nPrisma Access Configuration:")
        for key, var in sorted(self.pa_fields.items()):
            value = var.get()
            if "pass" in key.lower() or "secret" in key.lower() or "psk" in key.lower():
                value = "************"
            self.log_output(f"  {key:20s}: {value}")
        self.log_output("="*60 + "\n")
    
    def log_output(self, message):
        """Add message to output log"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def get_config_dict(self):
        """Get current configuration as dictionary"""
        fw_data = {key: var.get() for key, var in self.fw_fields.items()}
        pa_data = {key: var.get() for key, var in self.pa_fields.items()}
        return {'fwData': fw_data, 'paData': pa_data}
    
    def validate_required_fields(self, required_fw_fields, required_pa_fields=None):
        """Validate that required fields are filled"""
        missing = []
        fw_data = {key: var.get() for key, var in self.fw_fields.items()}
        
        for field in required_fw_fields:
            if not fw_data.get(field):
                missing.append(f"Firewall: {field}")
        
        if required_pa_fields:
            pa_data = {key: var.get() for key, var in self.pa_fields.items()}
            for field in required_pa_fields:
                if not pa_data.get(field):
                    missing.append(f"Prisma Access: {field}")
        
        if missing:
            messagebox.showerror("Missing Fields", 
                                "Please fill in the following required fields:\n\n" + 
                                "\n".join(missing))
            return False
        return True
    
    class TextRedirector:
        """Redirect stdout/stderr to GUI text widget"""
        def __init__(self, text_widget, tag=None):
            self.text_widget = text_widget
            self.tag = tag
        
        def write(self, s):
            if s and s.strip():  # Only write non-empty content
                self.text_widget.insert(tk.END, s)
                self.text_widget.see(tk.END)
                # Schedule update in main thread
                self.text_widget.after(0, lambda: self.text_widget.update_idletasks())
            return len(s)
        
        def flush(self):
            pass
        
        def isatty(self):
            return False
    
    # Validation and auto-calculation methods
    
    def validate_ip_address(self, value):
        """Validate IP address format"""
        if not value:
            return True, ""  # Empty is OK
        try:
            ipaddress.IPv4Address(value)
            return True, ""
        except ValueError:
            return False, "Invalid IP address format"
    
    def validate_ip_network(self, value):
        """Validate IP network/subnet format"""
        if not value:
            return True, ""  # Empty is OK
        try:
            ipaddress.IPv4Network(value, strict=False)
            return True, ""
        except ValueError:
            return False, "Invalid subnet format (e.g., 192.168.1.0/24)"
    
    def validate_url(self, value):
        """Validate URL format"""
        if not value:
            return True, ""  # Empty is OK
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if url_pattern.match(value):
            return True, ""
        # Also allow FQDN without protocol
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', value):
            return True, ""
        return False, "Invalid URL format (e.g., https://example.com or example.com)"
    
    def calculate_subnet_from_ip(self, ip_value):
        """Calculate subnet from IP address (assumes /24)"""
        if not ip_value:
            return ""
        try:
            # Remove CIDR if present
            ip_str = ip_value.split('/')[0]
            interface = ipaddress.IPv4Interface(f"{ip_str}/24")
            return str(interface.network)
        except (ValueError, AttributeError):
            return ""
    
    def calculate_default_gateway(self, subnet_value):
        """Calculate default gateway (first IP in subnet)"""
        if not subnet_value:
            return ""
        try:
            network = ipaddress.IPv4Network(subnet_value, strict=False)
            return str(network[1])  # First usable IP (gateway)
        except (ValueError, AttributeError, IndexError):
            return ""
    
    def auto_calculate_subnet(self, ip_field_key, subnet_field_key):
        """Auto-calculate subnet when IP address changes"""
        ip_value = self.fw_fields[ip_field_key].get()
        if ip_value:
            subnet = self.calculate_subnet_from_ip(ip_value)
            if subnet:
                self.fw_fields[subnet_field_key].set(subnet)
                self.log_output(f"Auto-calculated {subnet_field_key}: {subnet}")
    
    def auto_calculate_gateway(self, subnet_field_key, gateway_field_key):
        """Auto-calculate gateway when subnet changes"""
        subnet_value = self.fw_fields[subnet_field_key].get()
        if subnet_value:
            gateway = self.calculate_default_gateway(subnet_value)
            if gateway:
                self.fw_fields[gateway_field_key].set(gateway)
                self.log_output(f"Auto-calculated {gateway_field_key}: {gateway}")
    
    def validate_field(self, entry_widget, field_type, value):
        """Validate a field and update visual feedback"""
        is_valid = True
        error_msg = ""
        
        if field_type == "ip":
            is_valid, error_msg = self.validate_ip_address(value)
        elif field_type == "subnet":
            is_valid, error_msg = self.validate_ip_network(value)
        elif field_type == "url":
            is_valid, error_msg = self.validate_url(value)
        
        # Update visual feedback
        if value:  # Only validate if not empty
            if is_valid:
                entry_widget.config(style="TEntry")
            else:
                entry_widget.config(style="Invalid.TEntry")
                if error_msg:
                    self.status_var.set(f"Validation: {error_msg}")
        
        return is_valid
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Palo Alto Configuration Lab GUI
Version 1.0 - Phase 3

Cross-platform GUI for managing Palo Alto firewall
and Prisma Access configurations.

Phase 3 Features:
- Field validation (IP, URL, Subnet)
- Auto-calculation (Subnet, Gateway)
- Load from SCM
- Load from SPOV file"""
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = PAConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

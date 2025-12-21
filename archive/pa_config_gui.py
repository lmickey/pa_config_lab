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
import requests

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
        self.pa_entry_widgets = {}  # Store entry widgets for PA fields to read values directly
        self.password_fields = {}  # Track password fields for show/hide toggle
        self.entry_widgets = []  # Store all entry widgets for locking/unlocking
        self.edit_mode = False  # Track edit mode state
        self.service_connections = {}  # Store service connections: {name: {location, endpoint, tunnel: {...}}}
        self.remote_networks = {}  # Store remote networks: {name: {location, tunnel: {...}}}
        self.cached_locations = None  # Cache locations so we don't reload each time
        
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
        
        # Show startup dialog to load config or create new
        self.root.after(100, self.show_startup_dialog)
    
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
        
        # Load menu
        load_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Load", menu=load_menu)
        load_menu.add_command(label="Load from SCM", command=self.load_from_scm)
        load_menu.add_command(label="Load from SPOV File (JSON)...", command=self.load_from_spov)
        load_menu.add_command(label="Load from Terraform...", command=self.load_from_terraform)
        
        # Operations menu
        operations_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Operations", menu=operations_menu)
        operations_menu.add_command(label="Configure Initial Config", command=self.run_initial_config)
        operations_menu.add_command(label="Configure Firewall", command=self.run_configure_firewall)
        operations_menu.add_command(label="Configure Service Connection", command=self.run_service_connection)
        operations_menu.add_command(label="Get Firewall Version", command=self.get_fw_version)
        operations_menu.add_separator()
        operations_menu.add_command(label="Print Settings", command=self.print_settings)
        
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
            # Show dialog with options: Save, Don't Save, Cancel
            dialog = tk.Toplevel(self.root)
            dialog.title("Unsaved Changes")
            dialog.geometry("400x150")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.focus_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            result = {"action": None}  # "save", "discard", or "cancel"
            
            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="You have unsaved changes.", 
                     font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
            ttk.Label(frame, text="What would you like to do?").pack(anchor=tk.W, pady=(0, 15))
            
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X)
            
            def on_save():
                """Save and exit"""
                dialog.destroy()
                try:
                    if not self.config_file_path:
                        # No file path, need to save as
                        file_path = filedialog.asksaveasfilename(
                            title="Save Configuration As",
                            defaultextension=".bin",
                            filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
                            initialdir=self.last_directory
                        )
                        if not file_path:
                            return  # User cancelled
                        self.config_file_path = file_path
                    
                    # Save the configuration
                    self._save_to_file(self.config_file_path)
                    result["action"] = "save"
                    self.save_preferences()
                    self.root.destroy()
                except Exception as e:
                    self.log_output(f"Error saving on exit: {str(e)}")
                    messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
            
            def on_discard():
                """Discard changes and exit"""
                result["action"] = "discard"
                dialog.destroy()
                self.save_preferences()
                self.root.destroy()
            
            def on_cancel():
                """Cancel exit"""
                result["action"] = "cancel"
                dialog.destroy()
            
            ttk.Button(button_frame, text="Save and Exit", command=on_save).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Don't Save", command=on_discard).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
            
            dialog.wait_window()
        else:
            self.save_preferences()
            self.root.destroy()
    
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
        
        # Edit button in top right
        self.edit_button = ttk.Button(config_header, text="🔒 Locked", command=self.toggle_edit_mode)
        self.edit_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)
        
        ttk.Label(config_header, text="Config Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_name_var = tk.StringVar()
        config_name_entry = ttk.Entry(config_header, textvariable=self.config_name_var, width=40, state="readonly")
        config_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.entry_widgets.append(config_name_entry)
        self.add_copy_button(config_header, config_name_entry, 0, 3)
        
        # Firewall Configuration Section - Two columns
        fw_frame = ttk.LabelFrame(main_frame, text="Firewall Configuration", padding="10")
        fw_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        fw_frame.columnconfigure(1, weight=1)
        fw_frame.columnconfigure(5, weight=1)
        
        # Create firewall fields in two columns
        self.create_firewall_fields(fw_frame)
        
        # Prisma Access Configuration Section - Two columns
        pa_frame = ttk.LabelFrame(main_frame, text="Prisma Access Configuration", padding="10")
        pa_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        pa_frame.columnconfigure(1, weight=1)
        pa_frame.columnconfigure(5, weight=1)
        
        # Create Prisma Access fields
        self.create_prisma_fields(pa_frame)
        
        # Mobile User Configuration Section
        mu_frame = ttk.LabelFrame(main_frame, text="Mobile User Configuration", padding="10")
        mu_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        mu_frame.columnconfigure(1, weight=1)
        mu_frame.columnconfigure(5, weight=1)
        
        # Create Mobile User fields
        self.create_mobile_user_fields(mu_frame)
        
        # Service Connections Section
        sc_frame = ttk.LabelFrame(main_frame, text="Service Connections", padding="10")
        sc_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        sc_frame.columnconfigure(0, weight=1)
        
        # Container for service connection list
        self.sc_list_frame = ttk.Frame(sc_frame)
        self.sc_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add button to create new service connection
        add_sc_btn = ttk.Button(sc_frame, text="+ Add Service Connection", command=self.add_service_connection)
        add_sc_btn.pack(anchor=tk.W, pady=5)
        
        # Initialize service connections display
        self.refresh_service_connections_display()
        
        # Remote Networks Section
        rn_frame = ttk.LabelFrame(main_frame, text="Remote Networks", padding="10")
        rn_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=10)
        rn_frame.columnconfigure(0, weight=1)
        
        # Container for remote network list
        self.rn_list_frame = ttk.Frame(rn_frame)
        self.rn_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add button to create new remote network
        add_rn_btn = ttk.Button(rn_frame, text="+ Add Remote Network", command=self.add_remote_network)
        add_rn_btn.pack(anchor=tk.W, pady=5)
        
        # Initialize remote networks display
        self.refresh_remote_networks_display()
        
        # Status/Output Section
        status_frame = ttk.LabelFrame(main_frame, text="Status/Output", padding="10")
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=10)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=12, wrap=tk.WORD, font=("Courier", 9))
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu to status text
        self.setup_context_menu(self.status_text)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, padding=5)
        status_bar.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=5)
        
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
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
            self.entry_widgets.append(entry)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            # Add validation and auto-calculation
            self._setup_field_validation(entry, key, label)
            
            self.add_copy_button(parent, entry, row, 2)
            if is_password:
                self.add_password_toggle_button(parent, entry, row, 3)
            self.setup_context_menu(entry)
            
            self.fw_fields[key] = var
            row += 1
        
        # Column 2
        row = 0
        for label, key, is_password in col2_fields:
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=4, sticky=tk.W, padx=5, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
            entry.grid(row=row, column=5, sticky=(tk.W, tk.E), padx=5, pady=3)
            self.entry_widgets.append(entry)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            # Add validation and auto-calculation
            self._setup_field_validation(entry, key, label)
            
            self.add_copy_button(parent, entry, row, 6)
            if is_password:
                self.add_password_toggle_button(parent, entry, row, 7)
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
            # Column 2
            # Panorama fields
            ("Panorama Mgmt URL", "panMgmtUrl", False, None),
            ("Panorama User", "panUser", False, None),
            ("Panorama Password", "panPass", True, None),
        ]
        
        # Split into two columns (Mobile User fields moved to their own section)
        col1_fields = fields[:6]  # Managed By through Infrastructure BGP AS
        col2_fields = fields[6:]  # Panorama fields
        
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
                entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
                self.entry_widgets.append(entry)
                
                # Add tooltip
                self._add_tooltip(entry, self._get_field_tooltip(key))
                
                if is_password:
                    self.password_fields[key] = entry
                
                # Store entry widget for direct value access
                self.pa_entry_widgets[key] = entry
                
                self.add_copy_button(parent, entry, row, 2)
                if is_password:
                    self.add_password_toggle_button(parent, entry, row, 3)
                self.setup_context_menu(entry)
                
                self.pa_fields[key] = var
            row += 1
        
        # Column 2
        row = 0
        for field_info in col2_fields:
            label, key, is_password = field_info[:3]
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=4, sticky=tk.W, padx=5, pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
            entry.grid(row=row, column=5, sticky=(tk.W, tk.E), padx=5, pady=3)
            self.entry_widgets.append(entry)
            
            # Add tooltip
            self._add_tooltip(entry, self._get_field_tooltip(key))
            
            if is_password:
                self.password_fields[key] = entry
            
            # Store entry widget for direct value access
            self.pa_entry_widgets[key] = entry
            
            self.add_copy_button(parent, entry, row, 6)
            if is_password:
                self.add_password_toggle_button(parent, entry, row, 7)
            self.setup_context_menu(entry)
            
            self.pa_fields[key] = var
            row += 1
    
    def create_mobile_user_fields(self, parent):
        """Create Mobile User configuration fields in two columns"""
        # Mobile User fields
        fields = [
            # Column 1
            ("Mobile User Subnet", "paMobUserSubnet", False),
            # Column 2
            ("Portal Hostname", "paPortalHostname", False),
        ]
        
        # Column 1
        row = 0
        label, key, is_password = fields[0]
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        self.entry_widgets.append(entry)
        
        # Add tooltip
        self._add_tooltip(entry, self._get_field_tooltip(key))
        
        if is_password:
            self.password_fields[key] = entry
        
        # Add validation
        self._setup_field_validation(entry, key, label)
        
        self.add_copy_button(parent, entry, row, 2)
        if is_password:
            self.add_password_toggle_button(parent, entry, row, 3)
        self.setup_context_menu(entry)
        
        self.pa_fields[key] = var
        
        # Column 2
        row = 0
        label, key, is_password = fields[1]
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=4, sticky=tk.W, padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=35, show="*" if is_password else "", state="readonly")
        entry.grid(row=row, column=5, sticky=(tk.W, tk.E), padx=5, pady=3)
        self.entry_widgets.append(entry)
        
        # Add tooltip
        self._add_tooltip(entry, self._get_field_tooltip(key))
        
        if is_password:
            self.password_fields[key] = entry
        
        # Add validation
        self._setup_field_validation(entry, key, label)
        
        self.add_copy_button(parent, entry, row, 6)
        if is_password:
            self.add_password_toggle_button(parent, entry, row, 7)
        self.setup_context_menu(entry)
        
        self.pa_fields[key] = var
    
    def refresh_service_connections_display(self):
        """Refresh the service connections list display"""
        # Clear existing widgets
        for widget in self.sc_list_frame.winfo_children():
            widget.destroy()
        
        if not self.service_connections:
            ttk.Label(self.sc_list_frame, text="No service connections configured", 
                     foreground="gray").pack(anchor=tk.W, pady=5)
            return
        
        # Sort by name
        sorted_scs = sorted(self.service_connections.items())
        
        for sc_name, sc_data in sorted_scs:
            sc_row = ttk.Frame(self.sc_list_frame)
            sc_row.pack(fill=tk.X, pady=2, padx=5)
            
            # Display only SC name
            ttk.Label(sc_row, text=sc_name).pack(side=tk.LEFT, padx=5)
            
            # Configure button
            ttk.Button(sc_row, text="Configure", 
                      command=lambda name=sc_name: self.configure_service_connection(name)).pack(side=tk.RIGHT, padx=2)
            
            # Delete button
            ttk.Button(sc_row, text="Delete", 
                      command=lambda name=sc_name: self.delete_service_connection(name)).pack(side=tk.RIGHT, padx=2)
    
    def add_service_connection(self):
        """Add a new service connection"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Service Connection")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {"name": None, "cancel": True}
        
        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Service Connection Name:", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, width=50)
        name_entry.pack(fill=tk.X, pady=5)
        name_entry.focus_set()
        
        def on_add():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a service connection name")
                return
            if name in self.service_connections:
                messagebox.showwarning("Warning", f"Service connection '{name}' already exists")
                return
            result["name"] = name
            result["cancel"] = False
            dialog.destroy()
            # Create default service connection and configure it
            self.service_connections[name] = {
                "sc_name": name,
                "region": "",
                "tunnel": {
                    "tunnel_name": "",
                    "peer": "",
                    "psk": "",
                    "peer_id": "",
                    "host_id": "",
                    "ike": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "28800 seconds"  # Industry standard: 8 hours
                    },
                    "ipsec": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "3600 seconds",  # Industry standard: 1 hour
                        "nat_traversal": "enabled"
                    }
                }
            }
            self.configure_service_connection(name)
            self.refresh_service_connections_display()
            self.config_modified = True
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Add", command=on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
    
    def _fetch_locations_with_token(self, access_token, verify_ssl=True):
        """Helper function to fetch locations using an access token
        Returns a list of location dicts with 'display', 'value', and 'continent' keys,
        grouped by continent in order: Americas, Europe, Asia, Others
        """
        url = "https://api.sase.paloaltonetworks.com/sse/config/v1/locations"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers, timeout=(30, 30), verify=verify_ssl)
        
        if response.status_code == 200:
            try:
                data = response.json()
                locations = []
                
                # Response is directly an array of location objects
                # Each object has "value", "display", and "continent" fields
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'value' in item and 'display' in item:
                            locations.append({
                                'display': item['display'],
                                'value': item['value'],
                                'continent': item.get('continent', 'Other')
                            })
                elif isinstance(data, dict):
                    # Handle wrapped response (though API returns array directly)
                    items_list = None
                    if 'data' in data and isinstance(data['data'], list):
                        items_list = data['data']
                    elif 'result' in data and isinstance(data['result'], list):
                        items_list = data['result']
                    
                    if items_list:
                        for item in items_list:
                            if isinstance(item, dict) and 'value' in item and 'display' in item:
                                locations.append({
                                    'display': item['display'],
                                    'value': item['value'],
                                    'continent': item.get('continent', 'Other')
                                })
                
                # Group by continent with specified order
                continent_order = {
                    'North America': 1,
                    'South America': 2,
                    'Europe': 3,
                    'Asia': 4
                }
                
                def get_continent_priority(continent):
                    """Get priority for sorting continents"""
                    # Check if continent contains any of our priority names
                    continent_lower = continent.lower()
                    if 'north america' in continent_lower or 'south america' in continent_lower:
                        return 1 if 'north' in continent_lower else 2
                    elif 'europe' in continent_lower:
                        return 3
                    elif 'asia' in continent_lower:
                        return 4
                    else:
                        return 5  # Others
                
                # Sort by continent priority, then by display name
                locations.sort(key=lambda x: (get_continent_priority(x['continent']), x['display']))
                
                self.log_output(f"Successfully loaded {len(locations)} locations from API")
                return locations
            except Exception as e:
                self.log_output(f"Error parsing locations response: {str(e)}")
                self.log_output(f"Response content: {response.text[:500]}")
                return []
        else:
            self.log_output(f"Failed to fetch locations: HTTP {response.status_code}")
            try:
                error_data = response.json()
                self.log_output(f"Error response JSON: {error_data}")
            except:
                self.log_output(f"Error response text: {response.text[:500]}")
            return []
    
    def get_locations_from_api(self, use_cache=True):
        """Get locations from SCM API
        If use_cache is True and locations are already cached, return cached locations
        """
        # Return cached locations if available
        if use_cache and self.cached_locations is not None:
            self.log_output("Using cached locations")
            return self.cached_locations
        
        if not load_settings:
            self.log_output("load_settings module not available for location fetching")
            return []
        
        # Check if we have SCM credentials
        tsg_id = self.pa_fields.get('paTSGID', None)
        api_user = self.pa_fields.get('paApiUser', None)
        api_secret = self.pa_fields.get('paApiSecret', None)
        
        if not tsg_id or not api_user or not api_secret:
            self.log_output("SCM credentials not available for location fetching")
            return []
        
        # Get values from StringVar - use exact same pattern as load_from_scm()
        try:
            tsg_val = tsg_id.get().strip() if tsg_id else ""
            user_val = api_user.get().strip() if api_user else ""
            secret_val = api_secret.get().strip() if api_secret else ""
        except Exception as e:
            self.log_output(f"Error reading credential fields: {str(e)}")
            return []
        
        if not tsg_val or not user_val or not secret_val:
            self.log_output("SCM credentials are empty - cannot fetch locations. Please ensure TSG ID, API User, and API Secret are filled in.")
            return []
        
        try:
            # Use the exact same authentication method as load_from_scm() which works
            # But add detailed logging to see what's happening
            self.log_output("Authenticating to fetch locations...")
            
            # Call the auth function directly with better error handling
            scm_url = "https://auth.apps.paloaltonetworks.com/oauth2/access_token"
            scope = f'tsg_id:{tsg_val}'
            param_values = {'grant_type': 'client_credentials', 'scope': scope}
            
            auth_response = requests.post(scm_url, auth=(user_val, secret_val), params=param_values)
            
            if auth_response.status_code == 200:
                try:
                    response_json = auth_response.json()
                    access_token = response_json.get('access_token')
                    if access_token:
                        self.log_output("Authentication successful, fetching locations...")
                        locations = self._fetch_locations_with_token(access_token, verify_ssl=True)
                        # Cache the locations
                        self.cached_locations = locations
                        return locations
                    else:
                        self.log_output(f"Authentication succeeded but no 'access_token' in response")
                        self.log_output(f"Response keys: {list(response_json.keys())}")
                        return []
                except Exception as json_err:
                    self.log_output(f"Error parsing auth response: {str(json_err)}")
                    self.log_output(f"Response text: {auth_response.text[:200]}")
                    return []
            else:
                error_detail = ""
                try:
                    error_json = auth_response.json()
                    error_detail = error_json.get('error_description', error_json.get('error', ''))
                except:
                    error_detail = auth_response.text[:200] if auth_response.text else ""
                
                self.log_output(f"Authentication failed with status {auth_response.status_code}")
                if error_detail:
                    self.log_output(f"Error details: {error_detail}")
                return []
        except Exception as e:
            self.log_output(f"Error fetching locations: {str(e)}")
            import traceback
            self.log_output(traceback.format_exc())
            return []
    
    def configure_service_connection(self, sc_name):
        """Configure a service connection"""
        if sc_name not in self.service_connections:
            return
        
        sc_data = self.service_connections[sc_name]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Configure Service Connection: {sc_name}")
        dialog.geometry("700x900")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame with scrollbar
        main_canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        frame = ttk.Frame(scrollable_frame, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Service Connection Name
        basic_frame = ttk.LabelFrame(frame, text="Service Connection Information", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(basic_frame, text="SC Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        sc_name_var = tk.StringVar(value=sc_data.get("sc_name", sc_name))
        sc_name_entry = ttk.Entry(basic_frame, textvariable=sc_name_var, width=50)
        sc_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        basic_frame.columnconfigure(1, weight=1)
        
        ttk.Label(basic_frame, text="Location:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        location_var = tk.StringVar(value=sc_data.get("region", ""))
        location_combo = ttk.Combobox(basic_frame, textvariable=location_var, width=47, state="readonly")
        location_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Show "Loading..." while fetching locations
        location_combo.set("Loading...")
        location_combo.config(state="readonly")
        
        # Load locations from API when dialog opens
        def update_location_combo(locations):
            """Update the location combobox with fetched locations
            locations is a list of dicts with 'display', 'value', and 'continent' keys
            """
            # Check if dialog/widget still exists (might have been closed)
            try:
                if not dialog.winfo_exists():
                    return
            except:
                return
            
            # Check if dialog/widget still exists (might have been closed)
            try:
                if not dialog.winfo_exists() or not location_combo.winfo_exists():
                    return
            except:
                return
            
            try:
                if locations:
                    # Group locations by continent for display
                    grouped_locations = {}
                    for loc in locations:
                        continent = loc.get('continent', 'Other')
                        if continent not in grouped_locations:
                            grouped_locations[continent] = []
                        grouped_locations[continent].append(loc)
                    
                    # Build display list with continent headers
                    display_values = []
                    value_map = {}  # Map display string to value
                    
                    # Order continents: Americas first, then Europe, then Asia, then Others
                    continent_order = ['North America', 'South America', 'Europe', 'Asia']
                    other_continents = [c for c in grouped_locations.keys() if c not in continent_order]
                    ordered_continents = [c for c in continent_order if c in grouped_locations] + sorted(other_continents)
                    
                    for continent in ordered_continents:
                        continent_locs = grouped_locations[continent]
                        # Add continent header if multiple continents
                        if len(ordered_continents) > 1:
                            display_values.append(f"--- {continent} ---")
                        # Add locations for this continent
                        for loc in continent_locs:
                            display_str = loc['display']
                            display_values.append(display_str)
                            value_map[display_str] = loc['value']
                    
                    # Check again before updating widget
                    try:
                        if dialog.winfo_exists() and location_combo.winfo_exists():
                            location_combo['values'] = display_values
                            
                            # Get the configured value from sc_data (region value, not display name)
                            configured_region_value = sc_data.get("region", "")
                            current_display_val = location_var.get()
                            
                            # Try to find matching display name for the configured region value
                            matched_display = None
                            if configured_region_value:
                                # Look for display name that maps to this region value
                                for display, value in value_map.items():
                                    if value == configured_region_value:
                                        matched_display = display
                                        break
                            
                            # Set the combobox value
                            if matched_display:
                                # Found matching display name for configured region
                                location_combo.set(matched_display)
                                location_var.set(matched_display)
                            elif current_display_val and current_display_val in display_values:
                                # Current display value is valid, keep it
                                location_combo.set(current_display_val)
                            elif configured_region_value and configured_region_value in display_values:
                                # Configured value is a display name, use it
                                location_combo.set(configured_region_value)
                                location_var.set(configured_region_value)
                            elif display_values:
                                # Default to first actual location (skip continent headers)
                                first_location = None
                                for val in display_values:
                                    if not val.startswith("---"):
                                        first_location = val
                                        break
                                if first_location:
                                    location_combo.set(first_location)
                                    location_var.set(first_location)
                            else:
                                # No locations available, clear "Loading..."
                                location_combo.set("")
                                location_var.set("")
                    except Exception as e:
                        self.log_output(f"Error setting location value: {str(e)}")
                        import traceback
                        self.log_output(traceback.format_exc())
                else:
                    # If API call failed, allow manual entry
                    try:
                        if dialog.winfo_exists() and location_combo.winfo_exists():
                            current_val = sc_data.get("region", "")
                            if current_val:
                                location_combo['values'] = [current_val]
                                location_combo.set(current_val)
                            else:
                                location_combo.set("")
                            location_combo.config(state="normal")
                    except:
                        pass
            except Exception as e:
                self.log_output(f"Error updating location combo: {str(e)}")
                import traceback
                self.log_output(traceback.format_exc())
                # Fallback to manual entry
                try:
                    if dialog.winfo_exists() and location_combo.winfo_exists():
                        current_val = sc_data.get("region", "")
                        if current_val:
                            location_combo['values'] = [current_val]
                            location_combo.set(current_val)
                        else:
                            location_combo.set("")
                        location_combo.config(state="normal")
                except:
                    pass
        
        # Store location mapping for converting display to value on save
        # Use a list wrapper so it can be modified in nested functions
        location_display_to_value = {}
        
        def load_locations_threaded():
            """Load locations in background thread"""
            nonlocal location_display_to_value
            try:
                # Use cached locations if available
                locations = self.get_locations_from_api(use_cache=True)
                # Build mapping from display to value
                location_display_to_value.clear()
                for loc in locations:
                    location_display_to_value[loc['display']] = loc['value']
                # Update UI in main thread - check if dialog still exists
                try:
                    if dialog.winfo_exists():
                        dialog.after(0, lambda: update_location_combo(locations))
                except:
                    pass
            except Exception as e:
                self.log_output(f"Error loading locations in thread: {str(e)}")
                try:
                    if dialog.winfo_exists():
                        dialog.after(0, lambda: update_location_combo([]))
                except:
                    pass
        
        # Start loading locations in background thread after dialog is shown
        dialog.update_idletasks()
        threading.Thread(target=load_locations_threaded, daemon=True).start()
        
        # Tunnel Configuration
        tunnel_frame = ttk.LabelFrame(frame, text="Tunnel Configuration", padding="10")
        tunnel_frame.pack(fill=tk.X, pady=5)
        
        tunnel_data = sc_data.get("tunnel", {})
        
        ttk.Label(tunnel_frame, text="Tunnel Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        tunnel_name_var = tk.StringVar(value=tunnel_data.get("tunnel_name", ""))
        tunnel_name_entry = ttk.Entry(tunnel_frame, textvariable=tunnel_name_var, width=50)
        tunnel_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        tunnel_frame.columnconfigure(1, weight=1)
        
        ttk.Label(tunnel_frame, text="Peer:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        peer_var = tk.StringVar(value=tunnel_data.get("peer", ""))
        peer_entry = ttk.Entry(tunnel_frame, textvariable=peer_var, width=50)
        peer_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(tunnel_frame, text="Pre-shared Key:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        psk_var = tk.StringVar(value=tunnel_data.get("psk", ""))
        psk_entry = ttk.Entry(tunnel_frame, textvariable=psk_var, show="*", width=50)
        psk_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.add_password_toggle_button(tunnel_frame, psk_entry, 2, 2)
        
        ttk.Label(tunnel_frame, text="Peer ID:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        peer_id_var = tk.StringVar(value=tunnel_data.get("peer_id", ""))
        peer_id_entry = ttk.Entry(tunnel_frame, textvariable=peer_id_var, width=50)
        peer_id_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(tunnel_frame, text="Host ID:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        host_id_var = tk.StringVar(value=tunnel_data.get("host_id", ""))
        host_id_entry = ttk.Entry(tunnel_frame, textvariable=host_id_var, width=50)
        host_id_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # IKE Configuration
        ike_frame = ttk.LabelFrame(frame, text="IKE Configuration", padding="10")
        ike_frame.pack(fill=tk.X, pady=5)
        
        ike_data = tunnel_data.get("ike", {})
        
        # Standard Palo Alto IKE Encryption options
        ike_encryption_options = ["aes-128-cbc", "aes-192-cbc", "aes-256-cbc", "3des-cbc"]
        
        ttk.Label(ike_frame, text="Encryption:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ike_encryption_var = tk.StringVar(value=ike_data.get("encryption", ike_data.get("auth", "")))
        ike_encryption_combo = ttk.Combobox(ike_frame, textvariable=ike_encryption_var, values=ike_encryption_options, width=47, state="readonly")
        ike_encryption_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ike_frame.columnconfigure(1, weight=1)
        
        # Standard Palo Alto Hash options
        hash_options = ["sha1", "sha256", "sha384", "sha512", "md5"]
        
        ttk.Label(ike_frame, text="Hash:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ike_hash_var = tk.StringVar(value=ike_data.get("hash", ""))
        ike_hash_combo = ttk.Combobox(ike_frame, textvariable=ike_hash_var, values=hash_options, width=47, state="readonly")
        ike_hash_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Standard Palo Alto DH Group options
        dh_group_options = ["group1", "group2", "group5", "group14", "group19", "group20", "group21"]
        
        ttk.Label(ike_frame, text="DH Group:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ike_dh_var = tk.StringVar(value=ike_data.get("dh_group", ""))
        ike_dh_combo = ttk.Combobox(ike_frame, textvariable=ike_dh_var, values=dh_group_options, width=47, state="readonly")
        ike_dh_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Time field with number + unit dropdown
        ttk.Label(ike_frame, text="Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ike_time_frame = ttk.Frame(ike_frame)
        ike_time_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Parse existing time value, default to 8 hours (28800 seconds) if empty
        ike_time_value = ike_data.get("time", "28800 seconds")
        ike_time_num = "28800"
        ike_time_unit = "seconds"
        if ike_time_value:
            # Try to parse format like "3600 seconds" or "1 hours"
            parts = str(ike_time_value).split()
            if len(parts) >= 2:
                ike_time_num = parts[0]
                ike_time_unit = parts[1]
            elif len(parts) == 1:
                ike_time_num = parts[0]
        
        ike_time_num_var = tk.StringVar(value=ike_time_num)
        ike_time_num_entry = ttk.Entry(ike_time_frame, textvariable=ike_time_num_var, width=15)
        ike_time_num_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ike_time_unit_var = tk.StringVar(value=ike_time_unit)
        ike_time_unit_combo = ttk.Combobox(ike_time_frame, textvariable=ike_time_unit_var, 
                                          values=["seconds", "hours", "days"], width=12, state="readonly")
        ike_time_unit_combo.pack(side=tk.LEFT)
        
        # IPSec Configuration
        ipsec_frame = ttk.LabelFrame(frame, text="IPSec Configuration", padding="10")
        ipsec_frame.pack(fill=tk.X, pady=5)
        
        ipsec_data = tunnel_data.get("ipsec", {})
        # Force NAT Traversal to always be enabled in the data structure
        # This ensures it's always checked regardless of what was saved
        if "ipsec" in tunnel_data:
            tunnel_data["ipsec"]["nat_traversal"] = "enabled"
        else:
            ipsec_data["nat_traversal"] = "enabled"
        
        # Standard Palo Alto IPSec Encryption options
        ipsec_encryption_options = ["aes-128-gcm", "aes-256-gcm", "aes-128-cbc", "aes-256-cbc"]
        
        ttk.Label(ipsec_frame, text="Encryption:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_encryption_var = tk.StringVar(value=ipsec_data.get("encryption", ipsec_data.get("auth", "")))
        ipsec_encryption_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_encryption_var, values=ipsec_encryption_options, width=47, state="readonly")
        ipsec_encryption_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ipsec_frame.columnconfigure(1, weight=1)
        
        ttk.Label(ipsec_frame, text="Hash:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_hash_var = tk.StringVar(value=ipsec_data.get("hash", ""))
        ipsec_hash_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_hash_var, values=hash_options, width=47, state="readonly")
        ipsec_hash_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(ipsec_frame, text="DH Group:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_dh_var = tk.StringVar(value=ipsec_data.get("dh_group", ""))
        ipsec_dh_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_dh_var, values=dh_group_options, width=47, state="readonly")
        ipsec_dh_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Time field with number + unit dropdown
        ttk.Label(ipsec_frame, text="Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_time_frame = ttk.Frame(ipsec_frame)
        ipsec_time_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Parse existing time value, default to 1 hour (3600 seconds) if empty
        ipsec_time_value = ipsec_data.get("time", "3600 seconds")
        ipsec_time_num = "3600"
        ipsec_time_unit = "seconds"
        if ipsec_time_value:
            # Try to parse format like "3600 seconds" or "1 hours"
            parts = str(ipsec_time_value).split()
            if len(parts) >= 2:
                ipsec_time_num = parts[0]
                ipsec_time_unit = parts[1]
            elif len(parts) == 1:
                ipsec_time_num = parts[0]
        
        ipsec_time_num_var = tk.StringVar(value=ipsec_time_num)
        ipsec_time_num_entry = ttk.Entry(ipsec_time_frame, textvariable=ipsec_time_num_var, width=15)
        ipsec_time_num_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ipsec_time_unit_var = tk.StringVar(value=ipsec_time_unit)
        ipsec_time_unit_combo = ttk.Combobox(ipsec_time_frame, textvariable=ipsec_time_unit_var, 
                                            values=["seconds", "hours", "days"], width=12, state="readonly")
        ipsec_time_unit_combo.pack(side=tk.LEFT)
        
        ttk.Label(ipsec_frame, text="NAT Traversal:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        # NAT Traversal should ALWAYS be checked/enabled, regardless of what's in the loaded config
        nat_traversal_var = tk.BooleanVar(value=True)
        nat_traversal_check = ttk.Checkbutton(ipsec_frame, variable=nat_traversal_var, state="disabled")
        nat_traversal_check.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        def on_save():
            new_name = sc_name_var.get().strip()
            original_name = sc_name  # Store original name
            
            if new_name != original_name and new_name in self.service_connections:
                messagebox.showerror("Error", f"Service connection '{new_name}' already exists")
                return
            
            # Update name if changed
            if new_name != original_name:
                self.service_connections[new_name] = self.service_connections.pop(original_name)
                current_sc_name = new_name
            else:
                current_sc_name = original_name
            
            sc_data = self.service_connections[current_sc_name]
            sc_data["sc_name"] = new_name
            
            # Convert display name to value (region) if needed
            location_display = location_var.get().strip()
            
            # Validate location - don't allow continent headers or empty values
            if not location_display:
                messagebox.showerror("Error", "Please select a location")
                return
            elif location_display.startswith("---"):
                messagebox.showerror("Error", "Please select an actual location, not a continent header")
                return
            
            # Check if it's a display name and convert to value, otherwise use as-is
            location_value = location_display_to_value.get(location_display, location_display)
            
            # Additional validation: ensure the value is not a continent header
            if location_value.startswith("---"):
                messagebox.showerror("Error", "Invalid location selected")
                return
            
            sc_data["region"] = location_value
            
            # Build time strings from number + unit, use defaults if empty
            ike_time_str = ""
            ike_time_num_val = ike_time_num_var.get().strip()
            if ike_time_num_val:
                ike_time_str = f"{ike_time_num_val} {ike_time_unit_var.get()}"
            else:
                ike_time_str = "28800 seconds"  # Default: 8 hours
            
            ipsec_time_str = ""
            ipsec_time_num_val = ipsec_time_num_var.get().strip()
            if ipsec_time_num_val:
                ipsec_time_str = f"{ipsec_time_num_val} {ipsec_time_unit_var.get()}"
            else:
                ipsec_time_str = "3600 seconds"  # Default: 1 hour
            
            sc_data["tunnel"] = {
                "tunnel_name": tunnel_name_var.get().strip(),
                "peer": peer_var.get().strip(),
                "psk": psk_var.get().strip(),
                "peer_id": peer_id_var.get().strip(),
                "host_id": host_id_var.get().strip(),
                "ike": {
                    "encryption": ike_encryption_var.get().strip(),
                    "hash": ike_hash_var.get().strip(),
                    "dh_group": ike_dh_var.get().strip(),
                    "time": ike_time_str
                },
                "ipsec": {
                    "encryption": ipsec_encryption_var.get().strip(),
                    "hash": ipsec_hash_var.get().strip(),
                    "dh_group": ipsec_dh_var.get().strip(),
                    "time": ipsec_time_str,
                    # NAT Traversal should always be "enabled" - force it regardless of checkbox state
                    "nat_traversal": "enabled"
                }
            }
            self.config_modified = True
            self.refresh_service_connections_display()
            dialog.destroy()
            messagebox.showinfo("Success", f"Service connection '{new_name}' configured successfully")
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Save", command=on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
    
    def delete_service_connection(self, sc_name):
        """Delete a service connection"""
        if messagebox.askyesno("Confirm Delete", f"Delete service connection '{sc_name}'?"):
            del self.service_connections[sc_name]
            self.config_modified = True
            self.refresh_service_connections_display()
    
    def refresh_remote_networks_display(self):
        """Refresh the remote networks list display"""
        # Clear existing widgets
        for widget in self.rn_list_frame.winfo_children():
            widget.destroy()
        
        if not self.remote_networks:
            ttk.Label(self.rn_list_frame, text="No remote networks configured", 
                     foreground="gray").pack(anchor=tk.W, pady=5)
            return
        
        # Sort by name
        sorted_rns = sorted(self.remote_networks.items())
        
        for rn_name, rn_data in sorted_rns:
            rn_row = ttk.Frame(self.rn_list_frame)
            rn_row.pack(fill=tk.X, pady=2, padx=5)
            
            # Display only RN name
            ttk.Label(rn_row, text=rn_name).pack(side=tk.LEFT, padx=5)
            
            # Configure button
            ttk.Button(rn_row, text="Configure", 
                      command=lambda name=rn_name: self.configure_remote_network(name)).pack(side=tk.RIGHT, padx=2)
            
            # Delete button
            ttk.Button(rn_row, text="Delete", 
                      command=lambda name=rn_name: self.delete_remote_network(name)).pack(side=tk.RIGHT, padx=2)
    
    def add_remote_network(self):
        """Add a new remote network"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Remote Network")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {"name": None, "cancel": True}
        
        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Remote Network Name:", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, width=50)
        name_entry.pack(fill=tk.X, pady=5)
        name_entry.focus_set()
        
        def on_add():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a remote network name")
                return
            if name in self.remote_networks:
                messagebox.showwarning("Warning", f"Remote network '{name}' already exists")
                return
            result["name"] = name
            result["cancel"] = False
            dialog.destroy()
            # Create default remote network and configure it
            self.remote_networks[name] = {
                "rn_name": name,
                "region": "",
                "tunnel": {
                    "tunnel_name": "",
                    "peer": "",
                    "psk": "",
                    "peer_id": "",
                    "host_id": "",
                    "ike": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "28800 seconds"  # Industry standard: 8 hours
                    },
                    "ipsec": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "3600 seconds",  # Industry standard: 1 hour
                        "nat_traversal": "enabled"
                    }
                }
            }
            self.configure_remote_network(name)
            self.refresh_remote_networks_display()
            self.config_modified = True
        
        def on_cancel():
            result["cancel"] = True
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Add", command=on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
    
    def configure_remote_network(self, rn_name):
        """Configure a remote network"""
        if rn_name not in self.remote_networks:
            return
        
        rn_data = self.remote_networks[rn_name]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Configure Remote Network: {rn_name}")
        dialog.geometry("700x900")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame with scrollbar
        main_canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        frame = ttk.Frame(scrollable_frame, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Remote Network Name
        basic_frame = ttk.LabelFrame(frame, text="Remote Network Information", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(basic_frame, text="RN Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        rn_name_var = tk.StringVar(value=rn_data.get("rn_name", rn_name))
        rn_name_entry = ttk.Entry(basic_frame, textvariable=rn_name_var, width=50)
        rn_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        basic_frame.columnconfigure(1, weight=1)
        
        ttk.Label(basic_frame, text="Location:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        location_var = tk.StringVar(value=rn_data.get("region", ""))
        location_combo = ttk.Combobox(basic_frame, textvariable=location_var, width=47, state="readonly")
        location_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Show "Loading..." while fetching locations
        location_combo.set("Loading...")
        location_combo.config(state="readonly")
        
        # Load locations from API when dialog opens
        def update_location_combo(locations):
            """Update the location combobox with fetched locations
            locations is a list of dicts with 'display', 'value', and 'continent' keys
            """
            # Check if dialog/widget still exists (might have been closed)
            try:
                if not dialog.winfo_exists():
                    return
            except:
                return
            
            # Check if dialog/widget still exists (might have been closed)
            try:
                if not dialog.winfo_exists() or not location_combo.winfo_exists():
                    return
            except:
                return
            
            try:
                if locations:
                    # Group locations by continent for display
                    grouped_locations = {}
                    for loc in locations:
                        continent = loc.get('continent', 'Other')
                        if continent not in grouped_locations:
                            grouped_locations[continent] = []
                        grouped_locations[continent].append(loc)
                    
                    # Build display list with continent headers
                    display_values = []
                    value_map = {}  # Map display string to value
                    
                    # Order continents: Americas first, then Europe, then Asia, then Others
                    continent_order = ['North America', 'South America', 'Europe', 'Asia']
                    other_continents = [c for c in grouped_locations.keys() if c not in continent_order]
                    ordered_continents = [c for c in continent_order if c in grouped_locations] + sorted(other_continents)
                    
                    for continent in ordered_continents:
                        continent_locs = grouped_locations[continent]
                        # Add continent header if multiple continents
                        if len(ordered_continents) > 1:
                            display_values.append(f"--- {continent} ---")
                        # Add locations for this continent
                        for loc in continent_locs:
                            display_str = loc['display']
                            display_values.append(display_str)
                            value_map[display_str] = loc['value']
                    
                    # Check again before updating widget
                    try:
                        if dialog.winfo_exists() and location_combo.winfo_exists():
                            location_combo['values'] = display_values
                            
                            # Get the configured value from rn_data (region value, not display name)
                            configured_region_value = rn_data.get("region", "")
                            current_display_val = location_var.get()
                            
                            # Try to find matching display name for the configured region value
                            matched_display = None
                            if configured_region_value:
                                # Look for display name that maps to this region value
                                for display, value in value_map.items():
                                    if value == configured_region_value:
                                        matched_display = display
                                        break
                            
                            # Set the combobox value
                            if matched_display:
                                # Found matching display name for configured region
                                location_combo.set(matched_display)
                                location_var.set(matched_display)
                            elif current_display_val and current_display_val in display_values:
                                # Current display value is valid, keep it
                                location_combo.set(current_display_val)
                            elif configured_region_value and configured_region_value in display_values:
                                # Configured value is a display name, use it
                                location_combo.set(configured_region_value)
                                location_var.set(configured_region_value)
                            elif display_values:
                                # Default to first actual location (skip continent headers)
                                first_location = None
                                for val in display_values:
                                    if not val.startswith("---"):
                                        first_location = val
                                        break
                                if first_location:
                                    location_combo.set(first_location)
                                    location_var.set(first_location)
                            else:
                                # No locations available, clear "Loading..."
                                location_combo.set("")
                                location_var.set("")
                    except Exception as e:
                        self.log_output(f"Error setting location value: {str(e)}")
                        import traceback
                        self.log_output(traceback.format_exc())
                else:
                    # If API call failed, allow manual entry
                    try:
                        if dialog.winfo_exists() and location_combo.winfo_exists():
                            current_val = rn_data.get("region", "")
                            if current_val:
                                location_combo['values'] = [current_val]
                                location_combo.set(current_val)
                            else:
                                location_combo.set("")
                            location_combo.config(state="normal")
                    except:
                        pass
            except Exception as e:
                self.log_output(f"Error updating location combo: {str(e)}")
                import traceback
                self.log_output(traceback.format_exc())
                # Fallback to manual entry
                try:
                    if dialog.winfo_exists() and location_combo.winfo_exists():
                        current_val = rn_data.get("region", "")
                        if current_val:
                            location_combo['values'] = [current_val]
                            location_combo.set(current_val)
                        else:
                            location_combo.set("")
                        location_combo.config(state="normal")
                except:
                    pass
        
        # Store location mapping for converting display to value on save
        location_display_to_value = {}
        
        def load_locations_threaded():
            """Load locations in background thread"""
            nonlocal location_display_to_value
            try:
                # Use cached locations if available
                locations = self.get_locations_from_api(use_cache=True)
                # Build mapping from display to value
                location_display_to_value.clear()
                for loc in locations:
                    location_display_to_value[loc['display']] = loc['value']
                # Update UI in main thread - check if dialog still exists
                try:
                    if dialog.winfo_exists():
                        dialog.after(0, lambda: update_location_combo(locations))
                except:
                    pass
            except Exception as e:
                self.log_output(f"Error loading locations in thread: {str(e)}")
                try:
                    if dialog.winfo_exists():
                        dialog.after(0, lambda: update_location_combo([]))
                except:
                    pass
        
        # Start loading locations in background thread after dialog is shown
        dialog.update_idletasks()
        threading.Thread(target=load_locations_threaded, daemon=True).start()
        
        # Tunnel Configuration
        tunnel_frame = ttk.LabelFrame(frame, text="Tunnel Configuration", padding="10")
        tunnel_frame.pack(fill=tk.X, pady=5)
        
        tunnel_data = rn_data.get("tunnel", {})
        
        ttk.Label(tunnel_frame, text="Tunnel Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        tunnel_name_var = tk.StringVar(value=tunnel_data.get("tunnel_name", ""))
        tunnel_name_entry = ttk.Entry(tunnel_frame, textvariable=tunnel_name_var, width=50)
        tunnel_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        tunnel_frame.columnconfigure(1, weight=1)
        
        ttk.Label(tunnel_frame, text="Peer:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        peer_var = tk.StringVar(value=tunnel_data.get("peer", ""))
        peer_entry = ttk.Entry(tunnel_frame, textvariable=peer_var, width=50)
        peer_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(tunnel_frame, text="Pre-shared Key:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        psk_var = tk.StringVar(value=tunnel_data.get("psk", ""))
        psk_entry = ttk.Entry(tunnel_frame, textvariable=psk_var, show="*", width=50)
        psk_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.add_password_toggle_button(tunnel_frame, psk_entry, 2, 2)
        
        ttk.Label(tunnel_frame, text="Peer ID:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        peer_id_var = tk.StringVar(value=tunnel_data.get("peer_id", ""))
        peer_id_entry = ttk.Entry(tunnel_frame, textvariable=peer_id_var, width=50)
        peer_id_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(tunnel_frame, text="Host ID:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        host_id_var = tk.StringVar(value=tunnel_data.get("host_id", ""))
        host_id_entry = ttk.Entry(tunnel_frame, textvariable=host_id_var, width=50)
        host_id_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # IKE Configuration
        ike_frame = ttk.LabelFrame(frame, text="IKE Configuration", padding="10")
        ike_frame.pack(fill=tk.X, pady=5)
        
        ike_data = tunnel_data.get("ike", {})
        
        # Standard Palo Alto IKE Encryption options
        ike_encryption_options = ["aes-128-cbc", "aes-192-cbc", "aes-256-cbc", "3des-cbc"]
        
        ttk.Label(ike_frame, text="Encryption:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ike_encryption_var = tk.StringVar(value=ike_data.get("encryption", ike_data.get("auth", "")))
        ike_encryption_combo = ttk.Combobox(ike_frame, textvariable=ike_encryption_var, values=ike_encryption_options, width=47, state="readonly")
        ike_encryption_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ike_frame.columnconfigure(1, weight=1)
        
        # Standard Palo Alto Hash options
        hash_options = ["sha1", "sha256", "sha384", "sha512", "md5"]
        
        ttk.Label(ike_frame, text="Hash:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ike_hash_var = tk.StringVar(value=ike_data.get("hash", ""))
        ike_hash_combo = ttk.Combobox(ike_frame, textvariable=ike_hash_var, values=hash_options, width=47, state="readonly")
        ike_hash_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Standard Palo Alto DH Group options
        dh_group_options = ["group1", "group2", "group5", "group14", "group19", "group20", "group21"]
        
        ttk.Label(ike_frame, text="DH Group:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ike_dh_var = tk.StringVar(value=ike_data.get("dh_group", ""))
        ike_dh_combo = ttk.Combobox(ike_frame, textvariable=ike_dh_var, values=dh_group_options, width=47, state="readonly")
        ike_dh_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Time field with number + unit dropdown
        ttk.Label(ike_frame, text="Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ike_time_frame = ttk.Frame(ike_frame)
        ike_time_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Parse existing time value, default to 8 hours (28800 seconds) if empty
        ike_time_value = ike_data.get("time", "28800 seconds")
        ike_time_num = "28800"
        ike_time_unit = "seconds"
        if ike_time_value:
            # Try to parse format like "3600 seconds" or "1 hours"
            parts = str(ike_time_value).split()
            if len(parts) >= 2:
                ike_time_num = parts[0]
                ike_time_unit = parts[1]
            elif len(parts) == 1:
                ike_time_num = parts[0]
        
        ike_time_num_var = tk.StringVar(value=ike_time_num)
        ike_time_num_entry = ttk.Entry(ike_time_frame, textvariable=ike_time_num_var, width=15)
        ike_time_num_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ike_time_unit_var = tk.StringVar(value=ike_time_unit)
        ike_time_unit_combo = ttk.Combobox(ike_time_frame, textvariable=ike_time_unit_var, 
                                          values=["seconds", "hours", "days"], width=12, state="readonly")
        ike_time_unit_combo.pack(side=tk.LEFT)
        
        # IPSec Configuration
        ipsec_frame = ttk.LabelFrame(frame, text="IPSec Configuration", padding="10")
        ipsec_frame.pack(fill=tk.X, pady=5)
        
        ipsec_data = tunnel_data.get("ipsec", {})
        # Force NAT Traversal to always be enabled in the data structure
        if "ipsec" in tunnel_data:
            tunnel_data["ipsec"]["nat_traversal"] = "enabled"
        else:
            ipsec_data["nat_traversal"] = "enabled"
        
        # Standard Palo Alto IPSec Encryption options
        ipsec_encryption_options = ["aes-128-gcm", "aes-256-gcm", "aes-128-cbc", "aes-256-cbc"]
        
        ttk.Label(ipsec_frame, text="Encryption:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_encryption_var = tk.StringVar(value=ipsec_data.get("encryption", ipsec_data.get("auth", "")))
        ipsec_encryption_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_encryption_var, values=ipsec_encryption_options, width=47, state="readonly")
        ipsec_encryption_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ipsec_frame.columnconfigure(1, weight=1)
        
        ttk.Label(ipsec_frame, text="Hash:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_hash_var = tk.StringVar(value=ipsec_data.get("hash", ""))
        ipsec_hash_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_hash_var, values=hash_options, width=47, state="readonly")
        ipsec_hash_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(ipsec_frame, text="DH Group:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_dh_var = tk.StringVar(value=ipsec_data.get("dh_group", ""))
        ipsec_dh_combo = ttk.Combobox(ipsec_frame, textvariable=ipsec_dh_var, values=dh_group_options, width=47, state="readonly")
        ipsec_dh_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Time field with number + unit dropdown
        ttk.Label(ipsec_frame, text="Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ipsec_time_frame = ttk.Frame(ipsec_frame)
        ipsec_time_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Parse existing time value, default to 1 hour (3600 seconds) if empty
        ipsec_time_value = ipsec_data.get("time", "3600 seconds")
        ipsec_time_num = "3600"
        ipsec_time_unit = "seconds"
        if ipsec_time_value:
            # Try to parse format like "3600 seconds" or "1 hours"
            parts = str(ipsec_time_value).split()
            if len(parts) >= 2:
                ipsec_time_num = parts[0]
                ipsec_time_unit = parts[1]
            elif len(parts) == 1:
                ipsec_time_num = parts[0]
        
        ipsec_time_num_var = tk.StringVar(value=ipsec_time_num)
        ipsec_time_num_entry = ttk.Entry(ipsec_time_frame, textvariable=ipsec_time_num_var, width=15)
        ipsec_time_num_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ipsec_time_unit_var = tk.StringVar(value=ipsec_time_unit)
        ipsec_time_unit_combo = ttk.Combobox(ipsec_time_frame, textvariable=ipsec_time_unit_var, 
                                            values=["seconds", "hours", "days"], width=12, state="readonly")
        ipsec_time_unit_combo.pack(side=tk.LEFT)
        
        ttk.Label(ipsec_frame, text="NAT Traversal:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        # NAT Traversal should ALWAYS be checked/enabled, regardless of what's in the loaded config
        nat_traversal_var = tk.BooleanVar(value=True)
        nat_traversal_check = ttk.Checkbutton(ipsec_frame, variable=nat_traversal_var, state="disabled")
        nat_traversal_check.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        def on_save():
            new_name = rn_name_var.get().strip()
            original_name = rn_name  # Store original name
            
            if new_name != original_name and new_name in self.remote_networks:
                messagebox.showerror("Error", f"Remote network '{new_name}' already exists")
                return
            
            # Update name if changed
            if new_name != original_name:
                self.remote_networks[new_name] = self.remote_networks.pop(original_name)
                current_rn_name = new_name
            else:
                current_rn_name = original_name
            
            rn_data = self.remote_networks[current_rn_name]
            rn_data["rn_name"] = new_name
            
            # Convert display name to value (region) if needed
            location_display = location_var.get().strip()
            
            # Validate location - don't allow continent headers or empty values
            if not location_display:
                messagebox.showerror("Error", "Please select a location")
                return
            elif location_display.startswith("---"):
                messagebox.showerror("Error", "Please select an actual location, not a continent header")
                return
            
            # Check if it's a display name and convert to value, otherwise use as-is
            location_value = location_display_to_value.get(location_display, location_display)
            
            # Additional validation: ensure the value is not a continent header
            if location_value.startswith("---"):
                messagebox.showerror("Error", "Invalid location selected")
                return
            
            rn_data["region"] = location_value
            
            # Build time strings from number + unit, use defaults if empty
            ike_time_str = ""
            ike_time_num_val = ike_time_num_var.get().strip()
            if ike_time_num_val:
                ike_time_str = f"{ike_time_num_val} {ike_time_unit_var.get()}"
            else:
                ike_time_str = "28800 seconds"  # Default: 8 hours
            
            ipsec_time_str = ""
            ipsec_time_num_val = ipsec_time_num_var.get().strip()
            if ipsec_time_num_val:
                ipsec_time_str = f"{ipsec_time_num_val} {ipsec_time_unit_var.get()}"
            else:
                ipsec_time_str = "3600 seconds"  # Default: 1 hour
            
            rn_data["tunnel"] = {
                "tunnel_name": tunnel_name_var.get().strip(),
                "peer": peer_var.get().strip(),
                "psk": psk_var.get().strip(),
                "peer_id": peer_id_var.get().strip(),
                "host_id": host_id_var.get().strip(),
                "ike": {
                    "encryption": ike_encryption_var.get().strip(),
                    "hash": ike_hash_var.get().strip(),
                    "dh_group": ike_dh_var.get().strip(),
                    "time": ike_time_str
                },
                "ipsec": {
                    "encryption": ipsec_encryption_var.get().strip(),
                    "hash": ipsec_hash_var.get().strip(),
                    "dh_group": ipsec_dh_var.get().strip(),
                    "time": ipsec_time_str,
                    # NAT Traversal should always be "enabled" - force it regardless of checkbox state
                    "nat_traversal": "enabled"
                }
            }
            self.config_modified = True
            self.refresh_remote_networks_display()
            dialog.destroy()
            messagebox.showinfo("Success", f"Remote network '{new_name}' configured successfully")
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Save", command=on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
    
    def delete_remote_network(self, rn_name):
        """Delete a remote network"""
        if messagebox.askyesno("Confirm Delete", f"Delete remote network '{rn_name}'?"):
            del self.remote_networks[rn_name]
            self.config_modified = True
            self.refresh_remote_networks_display()
    
    def add_copy_button(self, parent, entry_widget, row, col):
        """Add a copy button next to an entry widget"""
        copy_btn = ttk.Button(parent, text="📋", width=3, 
                              command=lambda: self.copy_to_clipboard(entry_widget.get()))
        copy_btn.grid(row=row, column=col, padx=2, pady=3)
        return copy_btn
    
    def add_password_toggle_button(self, parent, entry_widget, row, col):
        """Add an eye icon button to toggle password visibility"""
        def toggle_password():
            current_show = entry_widget.cget("show")
            if current_show == "*":
                entry_widget.config(show="")
                toggle_btn.config(text="🙈")
            else:
                entry_widget.config(show="*")
                toggle_btn.config(text="👁")
        
        toggle_btn = ttk.Button(parent, text="👁", width=3, command=toggle_password)
        toggle_btn.grid(row=row, column=col, padx=2, pady=3)
        return toggle_btn
    
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
    
    def toggle_edit_mode(self):
        """Toggle edit mode on/off"""
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.unlock_all_fields()
            self.edit_button.config(text="🔓 Editing")
            self.status_var.set("Edit mode enabled - fields are editable")
        else:
            self.lock_all_fields()
            self.edit_button.config(text="🔒 Locked")
            self.status_var.set("Edit mode disabled - fields are locked")
    
    def lock_all_fields(self):
        """Lock all entry fields"""
        for entry in self.entry_widgets:
            entry.config(state="readonly")
    
    def unlock_all_fields(self):
        """Unlock all entry fields"""
        for entry in self.entry_widgets:
            entry.config(state="normal")
    
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
        self.current_config = None
        self.config_file_path = None
        self.config_cipher = None
        self.config_modified = False
        self.service_connections = {}
        self.remote_networks = {}
        # Ensure fields are locked unless in edit mode
        if not self.edit_mode:
            self.lock_all_fields()
        self.refresh_service_connections_display()
        self.refresh_remote_networks_display()
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
        
        # Use list_config_files to show available configs, or use file dialog (suppress CLI output)
        config_files = []
        if load_settings:
            try:
                # Redirect stdout to suppress print statements from list_config_files
                with redirect_stdout(io.StringIO()):
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
    
    def show_startup_dialog(self):
        """Show startup dialog to load config or create new"""
        if not load_settings:
            # If load_settings not available, just start with new config
            return
        
        # Get list of available config files (suppress CLI output)
        config_files = []
        try:
            # Redirect stdout to suppress print statements from list_config_files
            with redirect_stdout(io.StringIO()):
                config_files = load_settings.list_config_files(self.last_directory)
        except:
            pass
        
        # Sort config files by modification time (most recent first)
        if config_files:
            config_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Configuration")
        dialog.geometry("550x450")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        result = {"action": None, "file_path": None}  # action: "load", "new", "save_and_exit", or None
        
        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Check if there are unsaved changes
        has_unsaved_changes = self.config_modified
        
        if has_unsaved_changes:
            ttk.Label(frame, text="You have unsaved changes.", 
                     font=("", 10, "bold"), foreground="orange").pack(anchor=tk.W, pady=(0, 5))
            ttk.Label(frame, text="Select a configuration to load or create a new one:", 
                     font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        else:
            ttk.Label(frame, text="Select a configuration to load or create a new one:", 
                     font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Listbox with scrollbar
        listbox_frame = ttk.Frame(frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=("", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Add "New Configuration" as first option
        listbox.insert(0, "📄 New Configuration")
        
        # Add config files
        for file_path in config_files:
            file_name = os.path.basename(file_path)
            listbox.insert(tk.END, f"📁 {file_name}")
        
        # Select most recent file (index 1, since index 0 is "New Configuration")
        # If there are config files, select the first one (most recent)
        if config_files:
            listbox.selection_set(1)
            listbox.activate(1)
        else:
            # No config files, select "New Configuration"
            listbox.selection_set(0)
            listbox.activate(0)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_index = selection[0]
                if selected_index == 0:
                    # New Configuration selected
                    result["action"] = "new"
                    dialog.destroy()
                else:
                    # Config file selected
                    file_index = selected_index - 1  # Subtract 1 for "New Configuration"
                    if file_index < len(config_files):
                        result["file_path"] = config_files[file_index]
                        result["action"] = "load"
                        dialog.destroy()
        
        def on_double_click(event):
            on_select()
        
        listbox.bind('<Double-Button-1>', on_double_click)
        listbox.bind('<Return>', lambda e: on_select())
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def on_save_and_exit():
            """Save current configuration and exit dialog"""
            if not self.config_file_path:
                # No file path, need to save as
                file_path = filedialog.asksaveasfilename(
                    title="Save Configuration As",
                    defaultextension=".bin",
                    filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
                    initialdir=self.last_directory
                )
                if not file_path:
                    return
                self.config_file_path = file_path
            
            # Save the configuration
            try:
                self._save_to_file(self.config_file_path)
                result["action"] = "save_and_exit"
                dialog.destroy()
            except Exception as e:
                self.log_output(f"Error saving before exit: {str(e)}")
                messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
        
        ttk.Button(button_frame, text="Load Selected", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Browse...", command=lambda: self.browse_startup_file(dialog, result)).pack(side=tk.LEFT, padx=5)
        
        # Add "Save and Exit" button if there are unsaved changes
        if has_unsaved_changes:
            ttk.Button(button_frame, text="Save and Exit", command=on_save_and_exit).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Make Enter key work
        dialog.bind('<Return>', lambda e: on_select())
        
        dialog.wait_window()
        
        # Handle the result
        if result["action"] == "save_and_exit":
            # Configuration was saved, dialog is already closed
            # Just return - the save was handled in on_save_and_exit
            return
        elif result["action"] == "new":
            self.new_config()
        elif result["action"] == "load" and result["file_path"]:
            self.load_config_file(result["file_path"])
    
    def browse_startup_file(self, parent_dialog, result):
        """Browse for a file not in the list"""
        parent_dialog.destroy()
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")],
            initialdir=self.last_directory
        )
        if file_path:
            result["file_path"] = file_path
            result["action"] = "load"
    
    def load_config_file(self, file_path):
        """Load a specific config file (helper for startup dialog)"""
        if not load_settings:
            messagebox.showerror("Error", "load_settings module not available")
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
                'configName': config_name,
                'serviceConnections': self.service_connections,
                'remoteNetworks': self.remote_networks
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
        
        # Load service connections from config_data (new format takes precedence)
        if 'serviceConnections' in config_data and config_data['serviceConnections']:
            # Use the saved service connections directly
            self.service_connections = config_data['serviceConnections'].copy()
            # Ensure NAT Traversal is always enabled for all service connections
            for sc_name, sc_data in self.service_connections.items():
                if 'tunnel' in sc_data and 'ipsec' in sc_data['tunnel']:
                    sc_data['tunnel']['ipsec']['nat_traversal'] = 'enabled'
        else:
            # Extract Service Connection data from SC fields (legacy support)
            self.service_connections = {}
            sc_name = pa_data.get('scName', '').strip()
            if sc_name:
                self.service_connections[sc_name] = {
                    "sc_name": sc_name,
                    "region": pa_data.get('scLocation', ''),
                    "tunnel": {
                        "tunnel_name": pa_data.get('scTunnelName', ''),
                        "peer": "",
                        "psk": pa_data.get('paSCPsk', ''),
                        "peer_id": "",
                        "host_id": "",
                    "ike": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "28800 seconds"
                    },
                    "ipsec": {
                        "encryption": "",
                        "hash": "",
                        "dh_group": "",
                        "time": "3600 seconds",
                        "nat_traversal": "enabled"  # Always enabled
                    }
                    }
                }
        
        # Load remote networks from config_data
        if 'remoteNetworks' in config_data and config_data['remoteNetworks']:
            # Use the saved remote networks directly
            self.remote_networks = config_data['remoteNetworks'].copy()
            # Ensure NAT Traversal is always enabled for all remote networks
            for rn_name, rn_data in self.remote_networks.items():
                if 'tunnel' in rn_data and 'ipsec' in rn_data['tunnel']:
                    rn_data['tunnel']['ipsec']['nat_traversal'] = 'enabled'
        else:
            self.remote_networks = {}
        
        # Refresh service connections and remote networks displays
        self.refresh_service_connections_display()
        self.refresh_remote_networks_display()
        
        # Re-enable change tracking
        self.config_modified = False
        
        # Bind change tracking to all fields
        self._setup_change_tracking()
        
        # Ensure fields are locked unless in edit mode
        if not self.edit_mode:
            self.lock_all_fields()
    
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
        dialog.geometry("500x320")  # Increased height to show buttons
        dialog.transient(self.root)
        dialog.grab_set()
        
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
        
        # Status label for feedback
        status_label = ttk.Label(frame, text="", foreground="red")
        status_label.pack(anchor=tk.W, pady=5)
        
        def on_load():
            # Clear previous status
            status_label.config(text="")
            
            if not tsg_var.get() or not user_var.get() or not secret_var.get():
                status_label.config(text="Please fill in all fields")
                return
            
            tsg = tsg_var.get().strip()
            user = user_var.get().strip()
            secret = secret_var.get().strip()
            
            # Disable buttons during processing
            load_btn.config(state="disabled")
            cancel_btn.config(state="disabled")
            status_label.config(text="Authenticating...", foreground="blue")
            dialog.update()
            
            try:
                self.log_output("Authenticating to Prisma Access SCM...")
                self.status_var.set("Authenticating...")
                self.root.update()
                
                access_token = load_settings.prisma_access_auth(tsg, user, secret)
                
                if not access_token:
                    status_label.config(text="Authentication failed. Check credentials and TSG ID.", foreground="red")
                    load_btn.config(state="normal")
                    cancel_btn.config(state="normal")
                    self.log_output("Authentication failed")
                    return
                
                status_label.config(text="Loading configuration...", foreground="blue")
                dialog.update()
                
                self.log_output("Authentication successful. Loading configuration...")
                self.status_var.set("Loading configuration from SCM...")
                self.root.update()
                
                # Get PA config from SCM
                pa_config = get_settings.get_pa_config(access_token)
                
                if not pa_config:
                    status_label.config(text="Failed to load configuration from SCM", foreground="red")
                    load_btn.config(state="normal")
                    cancel_btn.config(state="normal")
                    self.log_output("Failed to load configuration from SCM")
                    return
                
                # Add credentials to config
                pa_config['paTSGID'] = tsg
                pa_config['paApiUser'] = user
                pa_config['paApiSecret'] = secret
                pa_config['paManagedBy'] = 'scm'
                
                # Populate Prisma Access fields
                for key, value in pa_config.items():
                    if key in self.pa_fields:
                        self.pa_fields[key].set(str(value))
                
                self.config_modified = True
                # Lock fields unless in edit mode
                if not self.edit_mode:
                    self.lock_all_fields()
                self.status_var.set("Configuration loaded from SCM")
                self.log_output("Configuration loaded successfully from Prisma Access SCM")
                
                # Close dialog on success
                dialog.destroy()
                messagebox.showinfo("Success", "Configuration loaded from Prisma Access SCM")
                
            except Exception as e:
                error_msg = str(e)
                status_label.config(text=f"Error: {error_msg}", foreground="red")
                load_btn.config(state="normal")
                cancel_btn.config(state="normal")
                self.log_output(f"Error loading from SCM: {error_msg}")
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        load_btn = ttk.Button(button_frame, text="Load", command=on_load)
        load_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Focus on first entry
        tsg_entry.focus_set()
        
        dialog.wait_window()
    
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
            # Lock fields unless in edit mode
            if not self.edit_mode:
                self.lock_all_fields()
            self.status_var.set("SPOV configuration loaded")
            self.log_output(f"SPOV configuration loaded successfully from {file_path}")
            messagebox.showinfo("Success", f"SPOV configuration loaded:\n{os.path.basename(file_path)}")
            
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error loading SPOV file: {error_msg}")
            messagebox.showerror("Error", f"Failed to load SPOV file:\n{error_msg}")
    
    def load_from_terraform(self):
        """Load configuration from Terraform output"""
        if not get_settings:
            messagebox.showerror("Error", "get_settings module not available")
            return
        
        # Create dialog for Terraform input
        dialog = tk.Toplevel(self.root)
        dialog.title("Load from Terraform")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Paste Terraform Configuration Output:", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        # Text widget for multi-line input
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        terraform_text = scrolledtext.ScrolledText(text_frame, height=15, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        terraform_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=terraform_text.yview)
        
        result = {"lines": None, "cancel": True}
        
        def on_load():
            content = terraform_text.get("1.0", tk.END).strip()
            if not content:
                messagebox.showwarning("Warning", "Please paste Terraform configuration output")
                return
            
            # Split into lines and filter empty lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                messagebox.showwarning("Warning", "No valid configuration lines found")
                return
            
            result["lines"] = lines
            result["cancel"] = False
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Load", command=on_load).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # Focus on text widget
        terraform_text.focus_set()
        
        dialog.wait_window()
        
        if result["cancel"] or not result["lines"]:
            return
        
        try:
            self.log_output(f"Loading Terraform configuration...")
            self.status_var.set("Loading Terraform configuration...")
            self.root.update()
            
            # Load Terraform config - the function modifies fwData in place, so we need to call it differently
            # Create a wrapper that returns the data
            fw_config = {}
            # Set defaults
            fw_config["tunnelInt"] = "tunnel.1"
            fw_config["tunnelAddr"] = "192.168.1.1/32"
            
            value_map = {
                'ngfw_untrust_fqdn': 'untrustURL',
                'ngfw_mgmt_fqdn': 'mgmtUrl',
                'ngfw_default_route': 'untrustDFGW',
                'ngfw_trust_address': 'trustAddr',
                'ngfw_untrust_address': 'untrustAddr',
                'ngfw_trust_interface': 'trustInt',
                'ngfw_untrust_interface': 'untrustInt',
                'username': 'mgmtUser',
                'password': 'mgmtPass'
            }
            
            for line in result["lines"]:
                if '=' in line:
                    key = line.split('=')[0].strip('" ')
                    value = line.split('=')[1].strip('" ')
                    if key in value_map:
                        fw_config[value_map[key]] = value
            
            if not fw_config or len(fw_config) <= 2:  # Only defaults
                messagebox.showerror("Error", "Failed to parse Terraform configuration. Please check the format.")
                self.log_output("Failed to parse Terraform configuration")
                return
            
            # Calculate subnet and gateway if not present
            if 'untrustAddr' in fw_config and 'untrustSubnet' not in fw_config:
                try:
                    fw_config['untrustSubnet'] = str(ipaddress.IPv4Interface(fw_config['untrustAddr']).network)
                except:
                    pass
            
            if 'untrustSubnet' in fw_config and 'untrustDFGW' not in fw_config:
                try:
                    fw_config['untrustDFGW'] = str(ipaddress.IPv4Network(fw_config['untrustSubnet'])[1])
                except:
                    pass
            
            if 'trustAddr' in fw_config and 'trustSubnet' not in fw_config:
                try:
                    fw_config['trustSubnet'] = str(ipaddress.IPv4Interface(fw_config['trustAddr']).network)
                except:
                    pass
            
            # Populate Firewall fields
            for key, value in fw_config.items():
                if key in self.fw_fields:
                    self.fw_fields[key].set(str(value))
            
            self.config_modified = True
            # Lock fields unless in edit mode
            if not self.edit_mode:
                self.lock_all_fields()
            self.status_var.set("Terraform configuration loaded")
            self.log_output(f"Terraform configuration loaded successfully")
            messagebox.showinfo("Success", "Terraform configuration loaded successfully")
            
        except Exception as e:
            error_msg = str(e)
            self.log_output(f"Error loading Terraform configuration: {error_msg}")
            messagebox.showerror("Error", f"Failed to load Terraform configuration:\n{error_msg}")
    
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
        
        # Service Connections Section
        self.log_output("\nService Connections:")
        if self.service_connections:
            for sc_name, sc_data in sorted(self.service_connections.items()):
                self.log_output(f"\n  Service Connection: {sc_name}")
                self.log_output(f"    Location (region): {sc_data.get('region', 'N/A')}")
                
                tunnel_data = sc_data.get('tunnel', {})
                if tunnel_data:
                    self.log_output(f"    Tunnel Name: {tunnel_data.get('tunnel_name', 'N/A')}")
                    self.log_output(f"    Peer: {tunnel_data.get('peer', 'N/A')}")
                    psk = tunnel_data.get('psk', '')
                    self.log_output(f"    Pre-shared Key: {'************' if psk else 'N/A'}")
                    self.log_output(f"    Peer ID: {tunnel_data.get('peer_id', 'N/A')}")
                    self.log_output(f"    Host ID: {tunnel_data.get('host_id', 'N/A')}")
                    
                    ike_data = tunnel_data.get('ike', {})
                    if ike_data:
                        self.log_output(f"    IKE:")
                        self.log_output(f"      Encryption: {ike_data.get('encryption', 'N/A')}")
                        self.log_output(f"      Hash: {ike_data.get('hash', 'N/A')}")
                        self.log_output(f"      DH Group: {ike_data.get('dh_group', 'N/A')}")
                        self.log_output(f"      Time: {ike_data.get('time', 'N/A')}")
                    
                    ipsec_data = tunnel_data.get('ipsec', {})
                    if ipsec_data:
                        self.log_output(f"    IPSec:")
                        self.log_output(f"      Encryption: {ipsec_data.get('encryption', 'N/A')}")
                        self.log_output(f"      Hash: {ipsec_data.get('hash', 'N/A')}")
                        self.log_output(f"      DH Group: {ipsec_data.get('dh_group', 'N/A')}")
                        self.log_output(f"      Time: {ipsec_data.get('time', 'N/A')}")
                        self.log_output(f"      NAT Traversal: {ipsec_data.get('nat_traversal', 'N/A')}")
        else:
            self.log_output("  No service connections configured")
        
        # Remote Networks Section
        self.log_output("\nRemote Networks:")
        if self.remote_networks:
            for rn_name, rn_data in sorted(self.remote_networks.items()):
                self.log_output(f"\n  Remote Network: {rn_name}")
                self.log_output(f"    Location (region): {rn_data.get('region', 'N/A')}")
                
                tunnel_data = rn_data.get('tunnel', {})
                if tunnel_data:
                    self.log_output(f"    Tunnel Name: {tunnel_data.get('tunnel_name', 'N/A')}")
                    self.log_output(f"    Peer: {tunnel_data.get('peer', 'N/A')}")
                    psk = tunnel_data.get('psk', '')
                    self.log_output(f"    Pre-shared Key: {'************' if psk else 'N/A'}")
                    self.log_output(f"    Peer ID: {tunnel_data.get('peer_id', 'N/A')}")
                    self.log_output(f"    Host ID: {tunnel_data.get('host_id', 'N/A')}")
                    
                    ike_data = tunnel_data.get('ike', {})
                    if ike_data:
                        self.log_output(f"    IKE:")
                        self.log_output(f"      Encryption: {ike_data.get('encryption', 'N/A')}")
                        self.log_output(f"      Hash: {ike_data.get('hash', 'N/A')}")
                        self.log_output(f"      DH Group: {ike_data.get('dh_group', 'N/A')}")
                        self.log_output(f"      Time: {ike_data.get('time', 'N/A')}")
                    
                    ipsec_data = tunnel_data.get('ipsec', {})
                    if ipsec_data:
                        self.log_output(f"    IPSec:")
                        self.log_output(f"      Encryption: {ipsec_data.get('encryption', 'N/A')}")
                        self.log_output(f"      Hash: {ipsec_data.get('hash', 'N/A')}")
                        self.log_output(f"      DH Group: {ipsec_data.get('dh_group', 'N/A')}")
                        self.log_output(f"      Time: {ipsec_data.get('time', 'N/A')}")
                        self.log_output(f"      NAT Traversal: {ipsec_data.get('nat_traversal', 'N/A')}")
        else:
            self.log_output("  No remote networks configured")
        
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
        config_dict = {
            'fwData': fw_data, 
            'paData': pa_data, 
            'serviceConnections': self.service_connections,
            'remoteNetworks': self.remote_networks
        }
        return config_dict
    
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

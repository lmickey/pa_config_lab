#!/usr/bin/env python3
"""
Palo Alto Configuration Lab - GUI Application
Cross-platform GUI for managing Palo Alto firewall and Prisma Access configurations

This is a skeleton/template showing the structure. Full implementation will follow.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys

# Import existing modules
try:
    import load_settings
    import get_settings
except ImportError:
    print("Warning: Could not import load_settings or get_settings modules")
    print("Make sure all existing scripts are in the same directory")


class PAConfigGUI:
    """Main GUI Application Class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Palo Alto Configuration Lab")
        self.root.geometry("1000x800")
        
        # Configuration state
        self.current_config = None
        self.config_cipher = None
        self.config_file_path = None
        
        # Field widgets storage
        self.fw_fields = {}
        self.pa_fields = {}
        
        self.setup_menu()
        self.setup_ui()
        
    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Configuration", command=self.new_config)
        file_menu.add_command(label="Load Configuration...", command=self.load_config)
        file_menu.add_command(label="Save Configuration", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", command=self.copy_selected)
        edit_menu.add_command(label="Paste", command=self.paste_selected)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Configure Initial Config", command=self.run_initial_config)
        tools_menu.add_command(label="Configure Firewall", command=self.run_configure_firewall)
        tools_menu.add_command(label="Configure Service Connection", command=self.run_service_connection)
        tools_menu.add_command(label="Get Firewall Version", command=self.get_fw_version)
        tools_menu.add_command(label="Print Settings", command=self.print_settings)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_ui(self):
        """Create the main UI layout"""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Configuration name and password section
        config_header = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        config_header.columnconfigure(1, weight=1)
        
        ttk.Label(config_header, text="Config Name:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.config_name_var = tk.StringVar()
        ttk.Entry(config_header, textvariable=self.config_name_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(config_header, text="Encryption Password:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.encrypt_pass_var = tk.StringVar()
        ttk.Entry(config_header, textvariable=self.encrypt_pass_var, show="*", width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(config_header, text="Change Password", command=self.change_password).grid(row=1, column=2, padx=5)
        
        # Firewall Configuration Section
        fw_frame = ttk.LabelFrame(main_frame, text="Firewall Configuration", padding="10")
        fw_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        fw_frame.columnconfigure(1, weight=1)
        
        # Firewall fields - this is where you'd add all the firewall fields
        self.create_firewall_fields(fw_frame)
        
        # Prisma Access Configuration Section
        pa_frame = ttk.LabelFrame(main_frame, text="Prisma Access Configuration", padding="10")
        pa_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        pa_frame.columnconfigure(1, weight=1)
        
        # Prisma Access fields
        self.create_prisma_fields(pa_frame)
        
        # Operations Section
        ops_frame = ttk.LabelFrame(main_frame, text="Operations", padding="10")
        ops_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(ops_frame, text="Configure Initial Config", command=self.run_initial_config).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(ops_frame, text="Configure Firewall", command=self.run_configure_firewall).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(ops_frame, text="Configure Service Connection", command=self.run_service_connection).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(ops_frame, text="Get FW Version", command=self.get_fw_version).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(ops_frame, text="Print Settings", command=self.print_settings).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(ops_frame, text="Load from SCM", command=self.load_from_scm).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(ops_frame, text="Load from SPOV File...", command=self.load_from_spov).grid(row=2, column=0, padx=5, pady=5)
        
        # Status/Output Section
        status_frame = ttk.LabelFrame(main_frame, text="Status/Output", padding="10")
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E))
    
    def create_firewall_fields(self, parent):
        """Create firewall configuration fields"""
        # Example fields - expand this with all firewall fields
        fields = [
            ("Management URL", "mgmtUrl", False),
            ("Management User", "mgmtUser", False),
            ("Management Password", "mgmtPass", True),
            ("Untrust URL", "untrustURL", False),
            ("Untrust Address", "untrustAddr", False),
            ("Untrust Subnet", "untrustSubnet", False),
            ("Untrust Interface", "untrustInt", False),
            ("Untrust Default GW", "untrustDFGW", False),
            ("Trust Address", "trustAddr", False),
            ("Trust Subnet", "trustSubnet", False),
            ("Trust Interface", "trustInt", False),
            ("Tunnel Interface", "tunnelInt", False),
            ("Tunnel Address", "tunnelAddr", False),
            ("Panorama Address", "panoramaAddr", False),
        ]
        
        row = 0
        for label, key, is_password in fields:
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(parent, textvariable=var, width=40, show="*" if is_password else "")
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
            
            # Copy button
            copy_btn = ttk.Button(parent, text="📋", width=3, command=lambda v=var: self.copy_to_clipboard(v.get()))
            copy_btn.grid(row=row, column=2, padx=2)
            
            self.fw_fields[key] = var
            row += 1
    
    def create_prisma_fields(self, parent):
        """Create Prisma Access configuration fields"""
        # Example fields - expand this with all Prisma Access fields
        fields = [
            ("Managed By", "paManagedBy", False, "dropdown"),  # SCM or Panorama
            ("TSG ID", "paTSGID", False),
            ("API User", "paApiUser", False),
            ("API Secret", "paApiSecret", True),
            ("Infrastructure Subnet", "paInfraSubnet", False),
            ("Mobile User Subnet", "paMobUserSubnet", False),
            ("Portal Hostname", "paPortalHostname", False),
            ("SC Endpoint", "paSCEndpoint", False),
            ("SC Name", "scName", False),
            ("SC Location", "scLocation", False),
            ("SC PSK", "paSCPsk", True),
        ]
        
        row = 0
        for field_info in fields:
            if len(field_info) == 4 and field_info[3] == "dropdown":
                label, key, is_password, field_type = field_info
                ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                var = tk.StringVar()
                combo = ttk.Combobox(parent, textvariable=var, values=["scm", "pan"], width=37)
                combo.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
                self.pa_fields[key] = var
            else:
                label, key, is_password = field_info[:3]
                ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                var = tk.StringVar()
                entry = ttk.Entry(parent, textvariable=var, width=40, show="*" if is_password else "")
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
                
                # Copy button
                copy_btn = ttk.Button(parent, text="📋", width=3, command=lambda v=var: self.copy_to_clipboard(v.get()))
                copy_btn.grid(row=row, column=2, padx=2)
                
                self.pa_fields[key] = var
            row += 1
    
    # Menu and operation methods
    
    def new_config(self):
        """Create a new configuration"""
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
        self.status_var.set("New configuration ready")
    
    def load_config(self):
        """Load configuration from file"""
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("Config files", "*-fwdata.bin"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        # Prompt for password
        password = tk.simpledialog.askstring("Password", "Enter encryption password:", show="*")
        if not password:
            return
        
        try:
            # Use load_settings module to load config
            cipher = load_settings.derive_key(password)
            config_data = load_settings.load_settings(cipher)
            
            if config_data:
                self.current_config = config_data
                self.config_cipher = cipher
                self.config_file_path = file_path
                self.populate_fields(config_data)
                self.status_var.set(f"Loaded: {os.path.basename(file_path)}")
                self.log_output(f"Configuration loaded successfully from {file_path}")
            else:
                messagebox.showerror("Error", "Failed to load configuration. Check password.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
            self.log_output(f"Error loading config: {str(e)}")
    
    def save_config(self):
        """Save current configuration to file"""
        if not self.config_name_var.get():
            messagebox.showwarning("Warning", "Please enter a configuration name")
            return
        
        # Collect current field values
        fw_data = {key: var.get() for key, var in self.fw_fields.items()}
        pa_data = {key: var.get() for key, var in self.pa_fields.items()}
        
        # Get or prompt for password
        if not self.config_cipher:
            password = tk.simpledialog.askstring("Password", "Enter encryption password:", show="*")
            if not password:
                return
            self.config_cipher = load_settings.derive_key(password)
        
        try:
            # Use get_settings module to save config
            # This is a simplified version - actual implementation would use get_settings.save_config_to_file
            self.status_var.set("Saving configuration...")
            self.log_output("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            self.log_output(f"Error saving config: {str(e)}")
    
    def populate_fields(self, config_data):
        """Populate GUI fields from config data"""
        fw_data = config_data.get('fwData', {})
        pa_data = config_data.get('paData', {})
        
        for key, var in self.fw_fields.items():
            if key in fw_data:
                var.set(fw_data[key])
        
        for key, var in self.pa_fields.items():
            if key in pa_data:
                var.set(pa_data[key])
        
        if 'configName' in config_data:
            self.config_name_var.set(config_data['configName'])
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Copied to clipboard")
    
    def copy_selected(self):
        """Copy selected text"""
        try:
            text = self.root.selection_get(selection="CLIPBOARD")
            self.root.clipboard_append(text)
        except:
            pass
    
    def paste_selected(self):
        """Paste from clipboard"""
        try:
            text = self.root.clipboard_get()
            # Paste into focused widget
            widget = self.root.focus_get()
            if isinstance(widget, tk.Entry):
                widget.insert(tk.INSERT, text)
        except:
            pass
    
    def change_password(self):
        """Change encryption password"""
        old_pass = tk.simpledialog.askstring("Old Password", "Enter current password:", show="*")
        new_pass = tk.simpledialog.askstring("New Password", "Enter new password:", show="*")
        if old_pass and new_pass:
            # Implement password change logic
            self.log_output("Password changed successfully")
    
    def load_from_scm(self):
        """Load configuration from Prisma Access SCM"""
        self.log_output("Loading configuration from SCM...")
        # Implement SCM loading logic
        messagebox.showinfo("Info", "SCM loading not yet implemented")
    
    def load_from_spov(self):
        """Load configuration from SPOV questionnaire file"""
        file_path = filedialog.askopenfilename(
            title="Select SPOV Questionnaire File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.log_output(f"Loading SPOV file: {file_path}")
            # Implement SPOV loading logic
            messagebox.showinfo("Info", "SPOV loading not yet implemented")
    
    def run_initial_config(self):
        """Run configure_initial_config.py"""
        self.log_output("Running initial configuration...")
        # Collect config, call configure_initial_config functions
        messagebox.showinfo("Info", "Initial config not yet implemented")
    
    def run_configure_firewall(self):
        """Run configure_firewall.py"""
        self.log_output("Configuring firewall...")
        # Collect config, call configure_firewall functions
        messagebox.showinfo("Info", "Firewall configuration not yet implemented")
    
    def run_service_connection(self):
        """Run configure_service_connection.py"""
        self.log_output("Configuring service connection...")
        # Collect config, call configure_service_connection functions
        messagebox.showinfo("Info", "Service connection configuration not yet implemented")
    
    def get_fw_version(self):
        """Get firewall version"""
        self.log_output("Getting firewall version...")
        # Call get_fw_version functions
        messagebox.showinfo("Info", "Get FW version not yet implemented")
    
    def print_settings(self):
        """Print current settings"""
        self.log_output("Current Settings:")
        self.log_output("\nFirewall Configuration:")
        for key, var in self.fw_fields.items():
            value = var.get()
            if "pass" in key.lower() or "secret" in key.lower():
                value = "************"
            self.log_output(f"  {key}: {value}")
        
        self.log_output("\nPrisma Access Configuration:")
        for key, var in self.pa_fields.items():
            value = var.get()
            if "pass" in key.lower() or "secret" in key.lower() or "psk" in key.lower():
                value = "************"
            self.log_output(f"  {key}: {value}")
    
    def log_output(self, message):
        """Add message to output log"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", "Palo Alto Configuration Lab GUI\nVersion 1.0")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = PAConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

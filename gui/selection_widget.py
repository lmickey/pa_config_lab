"""
Selection widget for choosing components to push.

This module provides the UI for selecting specific components 
(folders, snippets, objects) from the currently loaded configuration.
The selection UI uses a card-based hierarchical list design.
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from gui.widgets.selection_list import SelectionListWidget

logger = logging.getLogger(__name__)


class SelectionWidget(QWidget):
    """Widget for selecting components from loaded config to push."""
    
    # Signal emitted when selection is ready
    selection_ready = pyqtSignal(object)  # (selected_items)
    
    # Signal to request destination tenant connection
    destination_tenant_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the selection widget."""
        super().__init__(parent)
        
        self.current_config = None
        self.full_config = None  # For dependency resolution
        self.selected_items = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Use the new card-based selection list widget
        self.selection_list = SelectionListWidget(self)
        self.selection_list.selection_ready.connect(self._on_selection_ready)
        self.selection_list.destination_tenant_requested.connect(
            lambda: self.destination_tenant_requested.emit()
        )
        
        layout.addWidget(self.selection_list)
    
    def set_config(self, config: Dict[str, Any]):
        """
        Set the current configuration to work with.
        
        Args:
            config: Configuration dictionary from pull or loaded file
        """
        self.current_config = config
        self.full_config = config  # Same for now, could be different for dependency resolution
        self.selected_items = None  # Reset selection
        
        # Pass to the selection list
        self.selection_list.set_config(config)
    
    def populate_destination_tenants(self, tenants: List[Dict[str, Any]]):
        """
        Populate the destination tenant dropdown with saved tenants.
        
        Args:
            tenants: List of tenant dicts with 'name' key
        """
        self.selection_list.populate_destination_tenants(tenants)
    
    def set_destination_connected(
        self, 
        connected: bool, 
        folders: List[str] = None, 
        snippets: List[str] = None
    ):
        """
        Update the destination connection status.
        
        Args:
            connected: Whether connected to destination tenant
            folders: List of available folders in destination
            snippets: List of available snippets in destination
        """
        self.selection_list.set_destination_connected(connected, folders, snippets)
    
    def get_destination_api_client(self):
        """Get the destination tenant API client."""
        return self.selection_list.get_destination_api_client()
    
    def get_destination_name(self) -> str:
        """Get the destination tenant name."""
        return self.selection_list.get_destination_name()
    
    def add_items_to_selection(self, items: List[Dict]):
        """
        Add items to the current selection (e.g., missing dependencies).
        
        Args:
            items: List of item dicts with 'name', 'type', 'data' keys
        """
        if hasattr(self.selection_list, 'add_items_to_selection'):
            self.selection_list.add_items_to_selection(items)
    
    def _on_selection_ready(self, selection: Dict[str, Any]):
        """Handle selection ready from the list widget."""
        # Run dependency analysis
        try:
            from prisma.dependencies.dependency_resolver import DependencyResolver
            from gui.dialogs.dependency_confirmation_dialog import DependencyConfirmationDialog
            
            resolver = DependencyResolver()
            
            # Build config from selection for dependency analysis
            selected_config = {
                'security_policies': {
                    'folders': selection.get('folders', []),
                    'snippets': selection.get('snippets', [])
                },
                'objects': selection.get('objects', {}),
                'infrastructure': selection.get('infrastructure', {})
            }
            
            # Find required dependencies
            required_deps = resolver.find_required_dependencies(selected_config, self.full_config)
            
            # Check if there are actually any dependencies
            has_deps = False
            if required_deps:
                has_deps = (
                    len(required_deps.get('folders', [])) > 0 or
                    len(required_deps.get('snippets', [])) > 0 or
                    sum(len(v) for v in required_deps.get('objects', {}).values() if isinstance(v, list)) > 0 or
                    len(required_deps.get('profiles', [])) > 0 or
                    sum(len(v) if isinstance(v, list) else 1 for v in required_deps.get('infrastructure', {}).values()) > 0
                )
            
            if has_deps:
                # Show dependency confirmation dialog
                dep_dialog = DependencyConfirmationDialog(required_deps, self)
                if not dep_dialog.exec():
                    return  # User cancelled
                
                # Add dependencies to selection
                selection = self._merge_dependencies(selection, required_deps)
            
            # Store final selection
            self.selected_items = selection
            
            # Emit signal
            self.selection_ready.emit(self.selected_items)
            
        except ImportError:
            # Dependency resolver not available, proceed without it
            logger.warning("Dependency resolver not available, proceeding without dependency analysis")
            self.selected_items = selection
            self.selection_ready.emit(self.selected_items)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Dependency Analysis Error",
                f"Error analyzing dependencies:\n{str(e)}\n\nProceeding without dependency validation."
            )
            self.selected_items = selection
            self.selection_ready.emit(self.selected_items)
    
    def _merge_dependencies(self, selected: Dict[str, Any], required_deps: Dict[str, Any]) -> Dict[str, Any]:
        """Merge required dependencies into selection."""
        # Merge folders
        if 'folders' in required_deps:
            existing_names = {f.get('name') for f in selected.get('folders', [])}
            for folder in required_deps['folders']:
                if folder.get('name') not in existing_names:
                    selected.setdefault('folders', []).append(folder)
        
        # Merge snippets
        if 'snippets' in required_deps:
            existing_names = {s.get('name') for s in selected.get('snippets', [])}
            for snippet in required_deps['snippets']:
                if snippet.get('name') not in existing_names:
                    selected.setdefault('snippets', []).append(snippet)
        
        # Merge objects
        if 'objects' in required_deps:
            for obj_type, obj_list in required_deps['objects'].items():
                if obj_type not in selected.get('objects', {}):
                    selected.setdefault('objects', {})[obj_type] = []
                
                existing_names = {o.get('name') for o in selected['objects'][obj_type]}
                for obj in obj_list:
                    if obj.get('name') not in existing_names:
                        selected['objects'][obj_type].append(obj)
        
        # Merge profiles
        if 'profiles' in required_deps:
            selected['profiles'] = required_deps['profiles']
        
        # Merge infrastructure
        if 'infrastructure' in required_deps:
            for infra_type, infra_list in required_deps['infrastructure'].items():
                if infra_type not in selected.get('infrastructure', {}):
                    selected.setdefault('infrastructure', {})[infra_type] = []
                
                existing_names = {i.get('name', i.get('id')) for i in selected['infrastructure'][infra_type]}
                for item in infra_list:
                    item_name = item.get('name', item.get('id'))
                    if item_name not in existing_names:
                        selected['infrastructure'][infra_type].append(item)
        
        return selected
    
    def get_selected_items(self) -> Dict[str, Any]:
        """Get the current selection."""
        return self.selection_list.get_selected_items()

"""
UI Table Management Mixin.

Handles the population, formatting, and interactive features (tooltips, word wrap)
of the 32-column Production Breakdown table.
"""
import os
from PySide6.QtWidgets import QTableWidgetItem
from src.core.models import MMS_CATEGORIES

class TableManagerMixin:
    def populate_table(self, scenes):
        """Fills the Review Tab table with all 32 columns from core.models."""
        self.table.setRowCount(len(scenes))
        
        # List of element categories in the exact order they appear in your CSV (columns 7 to 29)
        element_categories = [
            "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props", "Camera",
            "Special Effects", "Wardrobe", "Makeup/Hair", "Animals", "Animal Wrangler",
            "Music", "Sound", "Art Department", "Set Dressing", "Greenery", 
            "Special Equipment", "Security", "Additional Labor", "Visual Effects", 
            "Mechanical Effects", "Miscellaneous", "Notes"
        ]

        for row, scene in enumerate(scenes):

            def create_item(text):
                val = str(text) if text is not None else ""
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                return item
            
            # Header & Info (Cols 0-6)
            self.table.setItem(row, 0, create_item(str(scene.scene_number)))
            self.table.setItem(row, 1, create_item(scene.int_ext))
            self.table.setItem(row, 2, create_item(scene.set_name))
            self.table.setItem(row, 3, create_item(scene.day_night))
            self.table.setItem(row, 4, create_item(scene.total_pages_display))
            self.table.setItem(row, 5, create_item(scene.synopsis))
            self.table.setItem(row, 6, create_item(scene.description))
            
            # Element Categories (Cols 7-29)
            for i, cat_name in enumerate(element_categories):
                # Filter elements belonging to this category and join their names
                elements_str = ", ".join([e.name for e in scene.elements if e.category == cat_name])
                self.table.setItem(row, 7 + i, create_item(elements_str))
                
            # Final Analysis Columns (Cols 30-31)
            self.table.setItem(row, 30, create_item(scene.continuity_notes or ""))
            
            # Review Flags - using 'note' and 'flag_type' from your ReviewFlag model
            flag_texts = [f"[{f.flag_type}] {f.note}" for f in scene.flags]
            self.table.setItem(row, 31, create_item(" | ".join(flag_texts)))

            # After filling, if Wrap is enabled, resize immediately
            if self.chk_wrap.isChecked():
                self.table.resizeRowsToContents()

    def toggle_word_wrap(self, enabled):
        """Switches between condensed single-line and expanded wrapped text."""
        self.table.setWordWrap(enabled)
        
        if enabled:
            # Expand: Wrap text and make rows as tall as needed
            self.table.resizeRowsToContents()
        else:
            # Collapse: Force rows back to a standard height (e.g., 30 pixels)
            for i in range(self.table.rowCount()):
                self.table.setRowHeight(i, 30)
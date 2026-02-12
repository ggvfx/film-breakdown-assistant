"""
Data Exporter Module.

Exports analyzed Scene objects into three formats:
1. Excel (.xlsx) - Detailed review sheet with specific formatting.
2. CSV (.csv) - Full diagnostic interchange (Identical to Excel data).
3. Movie Magic (.sex) - Clean scheduling import (No diagnostic/continuity notes).
"""

import pandas as pd
import logging
from lxml import etree as ET
from typing import List
from src.core.models import Scene, MMS_CATEGORIES

class DataExporter:
    """
    Handles multi-format production data exports.
    """

    def _get_flattened_row(self, scene: Scene, delimiter: str = "\n") -> dict:
        """
        Helper to create a row. 
        Adjusts formatting based on the delimiter (newline for Excel, pipe/semicolon for CSV).
        STRICT COLUMN ORDER: Header -> Narrative -> MMS Categories -> Continuity -> Flags.
        """
        # 1. Header & Narrative
        row = {
            "Scene": scene.scene_number,
            "Int/Ext": scene.int_ext,
            "Set": scene.set_name,
            "Day/Night": scene.day_night,
            "Pages": scene.total_pages_display,
            "Synopsis": scene.synopsis.replace("\n", " ").strip(),
            "Description": scene.description.replace("\n", " ").strip() if delimiter != "\n" else scene.description
        }

        # 2. Add MMS Categories (Departments)
        for category in MMS_CATEGORIES:
            matching = [
                f"{e.name.upper()} ({e.count})" if e.count not in ['1', ''] else e.name.upper() 
                for e in scene.elements if e.category == category
            ]
            row[category] = delimiter.join(matching)

        # 3. Add Diagnostic Data at the end
        # Flatten continuity notes for CSV as well
        cont_notes = scene.continuity_notes
        if delimiter != "\n":
            cont_notes = cont_notes.replace("\n", " | ")
            
        row["Continuity Notes"] = cont_notes
        
        flag_list = [f"[{f.flag_type}] {f.note} (Sev: {f.severity})" for f in scene.flags]
        row["Review Flags"] = delimiter.join(flag_list)
        
        return row

    def export_to_csv(self, scenes: List[Scene], file_path: str):
        """
        Exports the FULL diagnostic breakdown to CSV.
        """
        try:
            data = [self._get_flattened_row(s, delimiter="; ") for s in scenes]
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logging.info(f"CSV Export successful: {file_path}")
        except Exception as e:
            logging.error(f"CSV Export failed: {e}")

    def export_to_excel(self, scenes: List[Scene], file_path: str):
        """
        Comprehensive review sheet for AD validation with column formatting.
        """
        data = [self._get_flattened_row(s, delimiter="\n") for s in scenes]
        df = pd.DataFrame(data)

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Breakdown Review')
            workbook  = writer.book
            worksheet = writer.sheets['Breakdown Review']
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            
            # Formatting Column Widths
            worksheet.set_column('A:E', 12, wrap_format)  # Header
            worksheet.set_column('F:G', 45, wrap_format)  # Narrative
            worksheet.set_column('H:ZZ', 25, wrap_format) # Categories & Diagnostics

    def export_to_mms(self, scenes: List[Scene], file_path: str):
        """
        Generates a CLEAN .sex (XML) file for Movie Magic Scheduling.
        Excludes Flags and Continuity Notes to prevent MMS import errors.
        """
        try:
            root = ET.Element("PROJECT", version="1.0")
            for s in scenes:
                scene_tag = ET.SubElement(root, "SCENE")
                ET.SubElement(scene_tag, "NUMBER").text = str(s.scene_number)
                ET.SubElement(scene_tag, "PAGES").text = s.total_pages_display
                ET.SubElement(scene_tag, "INT_EXT").text = s.int_ext
                ET.SubElement(scene_tag, "SET").text = s.set_name
                ET.SubElement(scene_tag, "DAY_NIGHT").text = s.day_night
                ET.SubElement(scene_tag, "SYNOPSIS").text = s.synopsis
                # Note: We provide Description but skip Flags/Continuity for MMS
                ET.SubElement(scene_tag, "DESCRIPTION").text = s.description

                elements_root = ET.SubElement(scene_tag, "ELEMENTS")
                for e in s.elements:
                    el_tag = ET.SubElement(elements_root, "ELEMENT")
                    ET.SubElement(el_tag, "NAME").text = e.name.upper()
                    ET.SubElement(el_tag, "CATEGORY").text = e.category

            tree = ET.ElementTree(root)
            with open(file_path, "wb") as f:
                f.write(ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
            
            logging.info(f"Movie Magic (.sex) Export successful: {file_path}")
        except Exception as e:
            logging.error(f"Movie Magic Export failed: {e}")
            raise

    
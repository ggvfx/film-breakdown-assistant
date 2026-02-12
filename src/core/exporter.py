import pandas as pd
from typing import List, Dict, Any
from src.core.models import MMS_CATEGORIES

class DataExporter:
    """
    Handles exports for testing and validation.
    Retains all narrative data (Synopsis, Description) and AI diagnostics.
    """

    def export_to_excel(self, scenes: List[Dict[str, Any]], file_path: str):
        """
        Creates a comprehensive review sheet. No data left behind.
        """
        flattened_data = []
        
        for scene in scenes:
            # --- NEW PAGE LOGIC START ---
            w = scene.get('pages_whole', 0)
            e = scene.get('pages_eighths', 0)
            
            if w > 0:
                display_pages = f"{w} {e}/8" if e > 0 else f"{w}"
            else:
                display_pages = f"{e}/8"
            # --- NEW PAGE LOGIC END ---

            # 1. Core Header & Narrative Info (Updated "Pages" line)
            row = {
                "Scene": scene.get("scene_number"),
                "Int/Ext": scene.get("int_ext"),
                "Set": scene.get("set_name"),
                "Day/Night": scene.get("day_night"),
                "Pages": display_pages,
                "Synopsis": scene.get("synopsis"),
                "Description": scene.get("description")
            }

            # 2. Add MMS Categories with diagnostic info
            for category in MMS_CATEGORIES:
                elements = scene.get('elements', [])
                matching = []
                
                for e in elements:
                    if isinstance(e, dict):
                        # --- SANITIZATION START ---
                        name = str(e.get('name', '')).strip()
                        category_match = e.get('category') == category
                        
                        # Filter out hallucinations like "null", "none", or empty names
                        is_valid = name and name.lower() not in ['null', 'none', 'n/a', '((none))']
                        
                        if category_match and is_valid:
                            count = str(e.get('count', '1')).strip().lower()
                            
                            # Clean up the count and remove brackets for single items
                            if count in ['1', 'none', 'null', '', '0', '((none))']:
                                entry = f"{name.upper()}"
                            else:
                                entry = f"{name.upper()} ({count})"
                                
                            matching.append(entry)
                        # --- SANITIZATION END ---
                    else:
                        # Fallback for raw strings
                        if category == "Miscellaneous" and str(e).lower() not in ['null', 'none']:
                            matching.append(f"{str(e).upper()}")
                
                row[category] = "\n".join(matching)

            # 2.5 Add Continuity Notes AFTER departments
            row["Continuity Notes"] = scene.get("continuity_notes", "")

            # 3. Handle Review Flags
            formatted_flags = []
            for f in scene.get("review_flags", []):
                # Since these are now ReviewFlag objects or dicts from models.py
                if hasattr(f, 'flag_type'): # It's a Pydantic object
                    formatted_flags.append(f"[{f.flag_type}] {f.note} (Sev: {f.severity})")
                elif isinstance(f, dict): # It's a dict
                    formatted_flags.append(f"[{f.get('flag_type')}] {f.get('note')} (Sev: {f.get('severity')})")
            
            row["Review Flags"] = "\n".join(formatted_flags)

            flattened_data.append(row)

        # Create DataFrame and apply formatting
        df = pd.DataFrame(flattened_data)
        
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Breakdown Review')
            
            workbook  = writer.book
            worksheet = writer.sheets['Breakdown Review']
            
            # Format: Wrap text and align to top so long descriptions are readable
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            
            # Set widths: Narratives get more room, headers get less
            worksheet.set_column('A:D', 10, wrap_format)  # Scene, Int/Ext, etc
            worksheet.set_column('F:G', 40, wrap_format)  # Synopsis & Description
            worksheet.set_column('H:Z', 25, wrap_format)  # Categories

        print(f"Validation Export successful: {file_path}")
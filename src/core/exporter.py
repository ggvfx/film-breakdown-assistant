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
                "Pages": display_pages,  # <--- Use the new display_pages variable
                "Synopsis": scene.get("synopsis"),
                "Description": scene.get("description"),
            }

            # 2. Add MMS Categories with diagnostic info
            for category in MMS_CATEGORIES:
                elements = scene.get('elements', [])
                matching = []
                
                for e in elements:
                    if e.get('category') == category:
                        # Format: Item (Count) [Source | Confidence]
                        source_abbr = "Expl" if e.get('source') == "explicit" else "Impl"
                        conf = e.get('confidence', 0)
                        
                        entry = f"{e.get('name')} ({e.get('count', '1')}) [{source_abbr} | {conf:.2f}]"
                        matching.append(entry)
                
                row[category] = "\n".join(matching)

            # 3. Add Review Flags for the AD
            row["Review Flags"] = "\n".join([
                f"[{f['flag_type']}] {f['note']} (Sev: {f['severity']})" 
                for f in scene.get('flags', [])
            ])

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
"""
flag_agent.py
-------------
Role: Production Safety & Risk Assessment for Llama 3.1 8B
"""
# No need to redefine ReviewFlag here, we use the central one from models.py

def get_flag_prompt(scene_text: str, elements_summary: str, scene_num: str) -> str:
    return f"""
    TASK: Production Safety & Risk Scan - Scene {scene_num}
    
    SCENE TEXT:
    {scene_text}
    
    EXTRACTED ELEMENTS:
    {elements_summary}

    --- MANDATORY LOGIC ---
    Scan both the text and elements for the following categories and generate a flag if the criteria are met:

    1. REGULATORY: Any mentions of minors, babies, or legal age filming restrictions. 
       -> Severity 3 (Legal requirement).

    2. SENSITIVE: Any content involving intimacy, nudity, or physical romance. 
       -> Severity 2 (Closed set and Intimacy Coordinator needed).

    3. SAFETY: ANY item harvested in the 'Stunts' category, or text describing physical risks like combat, falls, or specialized movement (e.g. vaulting). 
       -> Severity 3 (Stunt Coordinator Required).

    4. WEAPONRY: Any props involving firearms, blades, or explosives. 
       -> Severity 3 (Armorer needed).

    5. LOGISTICS: High-complexity environments like weather effects, large crowds, animals, or significant vehicle coordination. 
       -> Severity 1 (High cost/prep).

    6. EQUIPMENT: Specialized production gear like drones, underwater rigs, or car mounts. 
       -> Severity 1 (High cost/prep).

    --- OUTPUT FORMAT ---
    Return ONLY JSON: 
    {{
        "review_flags": [
            {{
                "flag_type": "string",
                "note": "string",
                "severity": integer
            }}
        ]
    }}
    If no flags are found, return {{"review_flags": []}}.
    """
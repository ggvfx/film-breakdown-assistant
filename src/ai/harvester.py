"""
AI Harvester Templates for Script Analysis.
Split into Core (Pass 1), Set (Pass 2), Action (Pass 3), Gear (Pass 4) for maximum accuracy.
"""

from typing import List

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are a professional Film Assistant Director (AD) specializing in technical script breakdowns.
Your task is to extract production elements and metadata from script text.
Your goal is 100% accuracy for Movie Magic Scheduling. 
You prioritize technical precision over creative writing.
You MUST output ONLY valid JSON.
"""

def get_core_prompt(
    scene_text: str, 
    scene_num: str,
    set_name: str,
    day_night: str,
    int_ext: str,
    selected_core_cats: List[str],
    conservative: bool = True,
    implied: bool = False
) -> str:
    """Pass 1: Narrative summaries plus 'Active' elements (Cast, BG, Stunts)."""
    
    categories_str = ", ".join(selected_core_cats)

   # Dynamic Logic Rules
    logic_rules = ""
    if conservative:
        # Focuses strictly on the physical reality described in action blocks
        logic_rules += "- CONSERVATIVE: Only extract items explicitly used or present in ACTION LINES. Ignore items mentioned in DIALOGUE that do not physically appear.\n"
    else:
        # Allows for production prep based on character intent
        logic_rules += "- LIBERAL: Extract items mentioned in DIALOGUE if they imply a physical requirement for the scene (e.g., a character discussing a specific prop they are holding).\n"

    if implied:
        logic_rules += "- IMPLIED: Automatically add required labor (e.g., if a child is mentioned, add 'Teacher' or 'Guardian').\n"
    
    return f"""
    TASK: Narrative and Core element breakdown for Scene {scene_num}.

    CONTEXT:
    Scene: {scene_num}
    Location: {int_ext} {set_name} - {day_night}

    --- 1. SUMMARIES ---
    - SCENE SUMMARIES:
        - 'synopsis': High-level unique event summary of scene (Max 6 words). 
        - 'description': 1-2 sentences of the plot beats.
    - ELEMENTS: Extract every item in these categories: [{categories_str}].

    - CATEGORY DEFINITIONS (STRICT):
        - Cast Members: Named characters only. Include age if in script. NO COUNT.
        - Background Actors: Unnamed people groups. REQUIRES COUNT.
        - Stunts: Physical actions or risk (e.g. VAULTING, JUMPING, FIGHTING). Extract the action verb only.

    --- 2. EXTRACTION RULES ---
        - ELEMENT SEARCH: Scan Action AND Dialogue. Only extract specific requirements.
        - NAME FORMAT: UPPERCASE names. Strip all counts and ages from the name string.
        - CAST NO COUNT: Named characters only. NEVER include a numeric count or parentheses.
        - CAST AGE: The number in parentheses (e.g., "JAX (32)") is an AGE, not a count. DO NOT extract it.
        - BACKGROUND COUNT: You MUST provide a numeric estimate in parentheses for Background groups (e.g., "BYSTANDERS (10)").
        - ANTI-HALLUCINATION: Do not extract names from these instructions. Only extract entities explicitly in the SCRIPT TEXT.
        - STUNTS: Extract the ACTION verb only (e.g. DIVING). NEVER extract sounds (NO "PINGING") or objects (NO "VANS").
        - NO INFERENCE: Only extract items explicitly named. Do not assume items exist based on the location.
        - COUNT LOGIC: If a quantity is mentioned, include it in parentheses in the name field, e.g., "ITEM NAME (6)". For single items, just provide the name.
        - ZERO-FILL: If a category is empty, return [].
        
    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "synopsis": "string",
        "description": "string",
        "elements": [
            {{
                "name": "UPPERCASE NAME",
                "category": "string",
                "count": "string"
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """

def get_set_prompt(
    scene_text: str, 
    scene_num: str,
    selected_tech_cats: List[str],
    conservative: bool = True,
    implied: bool = False
) -> str:
    """Pass 2: Physical Set element extraction."""
    
    categories_str = ", ".join(selected_tech_cats)

     # Dynamic Logic Rules
    logic_rules = ""
    if conservative:
        # Focuses strictly on the physical reality described in action blocks
        logic_rules += "- CONSERVATIVE: Only extract items explicitly used or present in ACTION LINES. Ignore items mentioned in DIALOGUE that do not physically appear.\n"
    else:
        # Allows for production prep based on character intent
        logic_rules += "- LIBERAL: Extract items mentioned in DIALOGUE if they imply a physical requirement for the scene (e.g., a character discussing a specific prop they are holding).\n"

    
    return f"""
    TASK: Technical element extraction for Scene {scene_num}.

    --- 1. CATEGORY REFERENCE (FOR DEFINITION ONLY) ---
    {categories_str}
        - Vehicles: Picture cars.
		- Art Department: Fixed architecture/large set builds.
        - Set Dressing: Items on set NOT handled by actors.
        - Greenery: Physical plants or landscaping required on set.
		- Mechanical Effects: Large-scale physical machinery. Note: Different from SFX like fire/smoke.

    --- 2. EXTRACTION RULES ---
    {logic_rules}
        - ELEMENT SEARCH: Scan Action AND Dialogue for every production item. Be skeptical. Only extract an item if it is a specific requirement. Avoid "Atmosphere" or "General Vibe" items unless they are physical production requirements.
        - NAME FORMAT: Use UPPERCASE for names. Strip all counts from the name string.
        - NO INFERENCE: Only extract items explicitly named.
        - ZERO-FILL: If a category is empty, return []. NEVER use "null", "none", or "N/A".
        - COUNT LOGIC: If a quantity is mentioned, include it in parentheses in the name field, e.g., "ITEM NAME (6)". For single items, just provide the name.

    --- 3. FINAL VALIDATION (ZERO-HALLUCINATION CHECK) ---
        - NO INFERENCE: Only extract items explicitly named. Do not assume "Ivy" exists just because of a garden location.
        - NO EXAMPLE BLEED: Do NOT extract items from the "CATEGORY REFERENCE" section unless they are literally in the SCRIPT TEXT.
        - SKEPTICISM: If you cannot find the literal word in the script, do not extract it. Avoid "Atmosphere" or "General Vibe" items.


    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "elements": [
            {{
                "name": "UPPERCASE NAME",
                "category": "string",
                "count": "string"
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """

def get_action_prompt(
    scene_text: str, 
    scene_num: str,
    selected_tech_cats: List[str],
    conservative: bool = True,
    implied: bool = False
) -> str:
    """Pass 3: Action element extraction."""
    
    categories_str = ", ".join(selected_tech_cats)

     # Dynamic Logic Rules
    logic_rules = ""
    if conservative:
        # Focuses strictly on the physical reality described in action blocks
        logic_rules += "- CONSERVATIVE: Only extract items explicitly used or present in ACTION LINES. Ignore items mentioned in DIALOGUE that do not physically appear.\n"
    else:
        # Allows for production prep based on character intent
        logic_rules += "- LIBERAL: Extract items mentioned in DIALOGUE if they imply a physical requirement for the scene (e.g., a character discussing a specific prop they are holding).\n"

    if implied:
        logic_rules += "- IMPLIED LABOR: If an animal is present, you MUST add 'ANIMAL WRANGLER' to the elements. If a weapon is present, you MUST add 'ARMORER'. If a child/minor is present, you MUST add 'TEACHER'.\n"
    
    return f"""
    TASK: Technical element extraction for Scene {scene_num}.

    --- 1. CATEGORY REFERENCE (FOR DEFINITION ONLY) ---
    {categories_str}
        - Props: Handheld objects handled by cast.
        - Special Effects: Extract items only when physical requirements are present. 
            *If the text says "BOOM" or "BANG," extract "EXPLOSION". 
            *If bullets "PING" or "WHIZ," extract "BULLET HITS". 
            *If the ground is "RAIN-SLICKED" or "WET," extract "WET DOWN". 
            *Always extract "FIRE," "SMOKE," "SNOW," or "FOG" if mentioned. 
            *If the script says "SHATTER" or "SMASH," extract "BREAKING GLASS". 
            *Do not list these triggers if they are not in the script.
        - Wardrobe: Specific clothing mentioned that isn't standard.
        - Makeup/Hair: Prosthetics, wounds, or specific styles.
        - Animals: Any living creature. Requires 'Animal Wrangler' as implied.
        - Animal Wrangler: Required if there is a living animal required.
		- Visual Effects: Items requiring post-production or effects not based in reality.
		- Additional Labor: Extra crew needed (e.g., ARMORERs for weapons, TEACHER (if children involved)).

    --- 2. EXTRACTION RULES ---
    {logic_rules}
        - ELEMENT SEARCH: Scan Action AND Dialogue for every production item. Be skeptical. Only extract an item if it is a specific requirement. Avoid "Atmosphere" or "General Vibe" items unless they are physical production requirements.
        - NAME FORMAT: Use UPPERCASE for names. Strip all counts from the name string. (Correct: "BYSTANDERS").
        - SPECIAL EFFECTS: Extract an element for any "TRIGGER" or "ELEMENTAL" word found. Do not interpret these as sounds; they are physical requirements for the set.
        - NO INFERENCE: Only extract items explicitly named. Do not assume items exist just because of the location.
        - ZERO-FILL: If a category is empty, return []. NEVER use "null", "none", or "N/A".
        - COUNT LOGIC: If a quantity is mentioned, include it in parentheses in the name field, e.g., "ITEM NAME (6)". For single items, just provide the name.

    --- 3. FINAL VALIDATION (ZERO-HALLUCINATION CHECK) ---
        - NO INFERENCE: Only extract items explicitly named. Do not assume "Ivy" exists just because of a garden location.
        - NO EXAMPLE BLEED: Do NOT extract items from the "CATEGORY REFERENCE" section unless they are literally in the SCRIPT TEXT.
        - SKEPTICISM: If you cannot find the literal word in the script, do not extract it. Avoid "Atmosphere" or "General Vibe" items.


    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "elements": [
            {{
                "name": "UPPERCASE NAME",
                "category": "string",
                "count": "string"
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """

def get_gear_prompt(
    scene_text: str, 
    scene_num: str,
    selected_tech_cats: List[str],
    conservative: bool = True,
    implied: bool = False
) -> str:
    """Pass 4: Gear element extraction."""
    
    categories_str = ", ".join(selected_tech_cats)

     # Dynamic Logic Rules
    logic_rules = ""
    if conservative:
        # Focuses strictly on the physical reality described in action blocks
        logic_rules += "- CONSERVATIVE: Only extract items explicitly used or present in ACTION LINES. Ignore items mentioned in DIALOGUE that do not physically appear.\n"
    else:
        # Allows for production prep based on character intent
        logic_rules += "- LIBERAL: Extract items mentioned in DIALOGUE if they imply a physical requirement for the scene (e.g., a character discussing a specific prop they are holding).\n"

    return f"""
    TASK: Technical element extraction for Scene {scene_num}.

    --- 1. CATEGORY REFERENCE (FOR DEFINITION ONLY) ---
    {categories_str}
        - Camera: Specialized camera equipment only. 
        - Music: Diegetic music or instruments only. 
        - Sound: Specific on-set sound recording needs. 
        - Special Equipment: Specialized production machinery. NO vehicles. NO props.
        - Security: (For human entry only).
        - Miscellaneous: Strictly for PERMITS or LEGAL clearances. NO physical objects.
        - Notes: (For human entry only).
        - REJECT: Do not use 'Notes' or 'Security'. NEVER output the category name (e.g. "CAMERA") as an item.

    --- 2. EXTRACTION RULES ---
    {logic_rules}
        - ELEMENT SEARCH: Scan Action AND Dialogue.
        - NAME FORMAT: UPPERCASE name. Strip all counts from the string.
        - ANTI-HALLUCINATION: NEVER output the category name itself (e.g., "CAMERA") as an element.
        - NO EXAMPLE BLEED: Do not extract vehicles, props, cash, or prompt examples (like "Technocrane"). If it is a physical object, ignore it in this pass.
        - PROP REJECTION: If a character can hold it (CASH, BAGS, DETONATOR), it is a PROP. Do not put it in Gear or Misc.
        - NO INFERENCE: Only extract items explicitly named.
        - ZERO-FILL: If a category is empty, return [].
        - COUNT LOGIC: If a quantity is mentioned, include it in parentheses in the name field, e.g., "ITEM NAME (6)". For single items, just provide the name.

    --- 3. FINAL VALIDATION (ZERO-HALLUCINATION CHECK) ---
        - NO INFERENCE: Only extract items explicitly named. Do not assume "Ivy" exists just because of a garden location.
        - NO EXAMPLE BLEED: Do NOT extract items from the "CATEGORY REFERENCE" section unless they are literally in the SCRIPT TEXT.
        - SKEPTICISM: If you cannot find the literal word in the script, do not extract it. Avoid "Atmosphere" or "General Vibe" items.


    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "elements": [
            {{
                "name": "UPPERCASE NAME",
                "category": "string",
                "count": "string"
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """

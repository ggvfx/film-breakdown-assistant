"""
AI Harvester Templates for Script Analysis.

This module focuses strictly on extraction of production elements. 
Header data is provided by the Parser to ensure 100% accuracy for 
Movie Magic Scheduling exports.
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

def get_breakdown_prompt(
    scene_text: str, 
    selected_categories: List[str], 
    scene_num: str,
    set_name: str,
    day_night: str,
    int_ext: str
) -> str:
    """
    Constructs the prompt for Llama 3.2. Provides known header info as context.
    Fixed to address departmental drift and missing continuity.
    """
    
    categories_str = ", ".join(selected_categories)
    
    return f"""
    TASK: Perform a technical breakdown of Scene {scene_num}.

    CONTEXT:
    Scene: {scene_num}
    Location: {int_ext} {set_name} - {day_night}


    --- 1. SUMMARIES ---
    - LENGTH: Estimate scene length in 8ths of a page (e.g., 4/8, 1 2/8).
    - SCENE SUMMARIES:
       - 'synopsis': High-level unique event summary of scene (Max 6 words). 
       - 'description': 1-2 sentences of the plot beats.
    - ELEMENTS: Extract every item in these categories: [{categories_str}].

    - CATEGORY DEFINITIONS (STRICT):
        - Cast Members: Named characters only. Include age if in script (e.g. JAX (32)). NO COUNT.
        - Background Actors: Unnamed people groups. REQUIRES COUNT. (e.g. TWENTY BYSTANDERS, POLICE).
        - Stunts: Physical risk (e.g. VAULTING, JUMPING, FIGHTS).
        - Vehicles: Picture cars (e.g. GETAWAY VAN, 4 POLICE CRUISERS).
        - Props: Handheld objects handled by cast (e.g. DUFFEL BAGS, GUNS, CASH).
        - Camera: Specialized camera needs mentioned in action (e.g. HANDHELD, STEADICAM, POV SHOT, GOPRO).
        - Special Effects (SFX): Physical effects (e.g. BREAKAWAY GLASS, EXPLOSIONS, RAIN, SMOKE, FIRE, SNOW, WET DOWN, SQUIB HITS).
        - Wardrobe: Specific clothing mentioned that isn't standard (e.g. TUXEDO, BLOODY SHIRT).
        - Makeup/Hair: Prosthetics, wounds, or specific styles (e.g. FACIAL SCAR, CLOWN MAKEUP).
        - Animals: Any living creature (e.g. DOG). Requires 'Animal Wrangler' as implied.
        - Animal Wrangler: Required if there is a living animal required.
        - Music: Specific songs or instruments mentioned as being played on camera (Diegetic music). Do not include score/soundtrack unless a character reacts to it.
        - Sound: Specific sound effects that require sync or on-set timing (e.g., LOUD CRASH, SIRENS, GUNSHOT ECHO).
        - Art Department: Fixed architecture/large set builds (e.g. MARBLE PILLARS, BANK VAULT DOOR).
        - Set Dressing: Items on set NOT handled by actors (e.g. STACKS OF CASH on shelves).
        - Greenery: Plants or landscaping (e.g., POTTED PALMS, IVY).
        - Special Equipment: Technical gear (e.g., UNDERWATER HOUSING, DRONE, CRANE).
        - Security: 
        - Additional Labor: Extra crew needed (e.g., ARMORERs for weapons, TEACHER (if children involved)).
        - Visual Effects (VFX): Items requiring post-production or effects not based in reality (e.g., GREEN SCREEN, DIGITAL DOUBLE, MAGIC SPELL EFFECT, ALIEN CREATURE).
        - Mechanical Effects: Large-scale physical machinery (e.g., GIMBALS, HYDRAULIC RIGS, BREAKAWAY WALLS). Note: Different from SFX like fire/smoke.
        - Miscellaneous: Items that are critical but don't fit anywhere else. Examples: "Legal clearance for a logo," "Specific weather conditions needed," or "Coordinating with local precinct" or "requires wet-down of the street," or "Extreme heat—need cooling tents."
        - Notes:
        - REJECT: Do not use 'Notes' or 'Security'. These are for human entry only.
        
    --- 2. EXTRACTION RULES ---
        - ELEMENT SEARCH: Scan Action AND Dialogue for every production item.
        - NAME FORMAT: Use UPPERCASE for names. Strip all counts from the name string. (Correct: "BYSTANDERS").
        - CAST vs BG: Named characters = 'Cast Members'. Unnamed groups/crowds = 'Background Actors'.
        - STUNTS & SFX: If it is an action (falls, fights) or an effect (explosions, rain, shattering), you MUST extract it.
        - NO INFERENCE: Only extract items explicitly named. Do not assume "Ivy" or "Cameras" exist just because of the location.
        - ZERO-FILL: If a category is empty, return []. NEVER use "null", "none", or "N/A".
        - COUNT LOGIC: Only provide 'count' for 2 or more. If 1, leave 'count' as 1.
   

    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "pages_whole": integer,
        "pages_eighths": integer,
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
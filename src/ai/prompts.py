"""
AI Prompt Templates for Script Analysis.

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
    """
    
    categories_str = ", ".join(selected_categories)
    
    return f"""
    TASK: Perform a technical breakdown of Scene {scene_num}.

    SCENE CONTEXT:
    Location: {int_ext}. {set_name} - {day_night}
    
    SCENE TEXT:
    {scene_text}


    --- 1. SUMMARIES ---
    - 'length': Estimate the scene length in 8ths of a page (e.g., 4/8, 1 2/8).
    - 'synopsis': High-level action (Max 6 words). Describe the EVENT, not the genre.
         RULE: Must uniquely identify the narrative beat. Do not repeat slugline info. Focus on the action transition (e.g., 'Team breaches the perimeter' vs. 'Team loads the cash').
         BAD: "Heists"
         GOOD: "Jax and Mira breach the vault"
         
    - 'description': A concise 1-2 sentence summary of the plot beats. 
         Focus on narrative progression. Avoid technical or stylistic descriptions.

    --- 2. ELEMENTS ---
         Extract every item belonging to these categories: [{categories_str}]. If none are present for the category, leave blank.
    - CRITICAL INSTRUCTION: TECHNICAL MINING
    Scan both Action and Dialogue lines. Many logistical requirements (like 'stacks of cash' or 'guns') appear only in dialogue. If an item is mentioned as being handled, present, or required, it is NOT "flavor text"—it is a logistical requirement and MUST be extracted.

    - CATEGORY DEFINITIONS (GUIDE RAILS):
        - Cast Members: Specific named characters (e.g. JAX (32), MIRA, DR. ARIS). NO COUNT.
        - Background Actors: Unnamed/generic groups (e.g. BYSTANDERS, POLICE, SCIENTISTS). REQUIRES COUNT. Living humans/groups. NO INANIMATE OBJECTS.
        - Stunts: Specialized physical action (e.g. VAULTING, JUMPING, FIGHTS, FALLS, PRECISION DRIVING).
        - Vehicles: Picture vehicles only (e.g. GETAWAY VAN, 4 POLICE CRUISERS)
        - Props: Handheld tools/objects cast interact with (e.g. DUFFEL BAGS, GUNS, CASH).
        - Camera: Specialized camera needs mentioned in action (e.g., HANDHELD, STEADICAM, POV SHOT, GOPRO).
        - Special Effects (SFX): Practical onset effects (e.g., EXPLOSIONS, BREAKAWAY GLASS, RAIN, SMOKE, FIRE, SNOW, WET DOWN, SQUIB HITS).
        - Wardrobe: Specific clothing mentioned that isn't standard (e.g., TUXEDO, BLOODY SHIRT).
        - Makeup/Hair: Prosthetics, wounds, or specific styles (e.g., FACIAL SCAR, CLOWN MAKEUP).
        - Animals: Any living creature (e.g. DOG). Requires 'Animal Wrangler' as implied.
        - Animal Wrangler: Required if there is a living animal.
        - Music: Specific songs or instruments mentioned as being played on camera (Diegetic music). Do not include score/soundtrack unless a character reacts to it.
        - Sound: Specific sound effects that require sync or on-set timing (e.g., LOUD CRASH, SIRENS, GUNSHOT ECHO).
        - Art Department: Large custom builds or specific set needs (e.g., CRASHED SATELLITE). Large set pieces (MARBLE PILLARS, BANK VAULT DOORS).
        - Set Dressing: Items that stay on set and aren't handled by actors (e.g., CURTAINS, OLD BOOKS).
        - Greenery: Plants or landscaping (e.g., POTTED PALMS, IVY).
        - Special Equipment: Technical gear (e.g., UNDERWATER HOUSING, DRONE, CRANE).
        - Security: 
        - Additional Labor: Extra crew needed (e.g., MASK MAKERS, CHOREOGRAPHERS, PUPPETEERS, TEACHER (if children involved), ARMORERS).
        - Visual Effects (VFX): Items requiring post-production or effects not based in reality (e.g., GREEN SCREEN, DIGITAL DOUBLE, MAGIC SPELL EFFECT, ALIEN CREATURE).
        - Mechanical Effects: Large-scale physical machinery (e.g., GIMBALS, HYDRAULIC RIGS, BREAKAWAY WALLS). Note: Different from SFX like fire/smoke.
        - Miscellaneous: Items that are critical but don't fit anywhere else. Examples: "Legal clearance for a logo," "Specific weather conditions needed," or "Coordinating with local precinct" or "requires wet-down of the street," or "Extreme heat—need cooling tents."
        - Notes:
        - REJECT: Do not use 'Notes' or 'Security'. These are for human entry only.
        
        [Routing Note: Buildings/Locations are NOT elements. Cars are VEHICLES, not PROPS.]

    --- 3. ELEMENT FORMATTING ---
    - 'name': UPPERCASE. If age is in script, include it for Cast (e.g. JAX (32)). 
    - 'count': How many? (e.g., "6", "2", or "1"). Use "1" as default. Digit string (e.g. "20"). For Cast Members, no count.
    - 'source': 'explicit' if literally in text, 'implied' if it must exist (e.g. 'Smoke' for a 'Fire').
    - 'confidence': score between 0.0 and 1.0.
    - EXCLUSIONS:
        
    - SPECIFICITY: If the script says '4 cruisers', the element name is 'POLICE CRUISERS' and count is '4'.

    --- 4. REVIEW FLAG SCANNING ---
    If you detect the following keywords, you MUST generate a 'ReviewFlag' entry:
    - REGULATORY: 'Minor', 'Child', 'Baby' -> Severity 3 (Legal requirement).
    - SENSITIVE: 'Intimacy', 'Nudity', 'Kiss' -> Severity 2 (Closed set needed).
    - SAFETY: 'Fire', 'Explosion', 'Fight', 'Fall' -> Severity 3 (Stunt Coordinator needed).
    - WEAPONRY: 'Gun', 'Knife', 'Sword' -> Severity 3 (Armorer needed).
    - LOGISTICS: 'Rain', 'Water', 'Car', 'Animal' -> Severity 1 (High cost/prep).
    - EQUIPMENT: 'Cranes', 'Drones', 'Underwater' -> Severity 1 (High cost/prep).
   
    - EXCLUSIONS:
        - Do not list inanimate objects (like 'PRECINCT' or 'CAR') as people. 
        - If an item is a vehicle, put it in 'Vehicles'. If it's a tool, 'Props'.
        - Do not list buildings as people.
        - NEVER ignore items mentioned in dialogue. A gun mentioned in a line of dialogue ("He's got a gun!") is an EXPLICIT prop/weaponry element, even if not described in action lines.
        - Do not include buildings or locations as elements.

    FINAL DIRECTIVE: 
    Perform a deep scan of all character dialogue. Extract all mentioned props and weapons to ensure 100% production readiness.

    OUTPUT FORMAT ONLY VALID JSON:
    {{
        "pages_whole": integer,
        "pages_eighths": integer,
        "synopsis": "string",
        "description": "string",
        "elements": [
            {{
                "name": "string",
                "category": "string",
                "count": "string",
                "source": "explicit/implied",
                "confidence": float
            }}
        ],
        "flags": [
            {{
                "flag_type": "string",
                "note": "string",
                "severity": integer
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """
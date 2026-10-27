"""Evidence-backed US display defaults; does not rename native game strings."""
from copy import deepcopy
import re

ETC_SHA256 = '6a561dc19076a6825bb55a38c8d189db91fb4807f1d7221a04edec20a3cde7e6'
NPC_NAMES = dict(zip(range(256, 289), (
    'Beaumont', 'Thyea', 'Talis', 'Yustel', 'Jess', 'Ronan', 'Sybill', 'Sierra',
    'Olen', 'Lyman', 'Jaylen', 'Zane', 'Septimus', 'Nadia', 'Myra', 'Bonaire',
    'Phineas', 'Kline', 'Giles', 'Kisha', 'Elene', 'Gustav', 'Bergus', 'Nestus',
    'Meade', 'Rumi', 'Wendell', 'Yuri', 'Naomi', 'Nava', 'Cephas', 'Lutas', 'Fein')))
NPC_NAMES.update({302:'Meia', 331:'Elene (dead)', 332:'Bonaire (dead)',
    333:'Myra (dead)', 334:'Nadia (dead)', 339:'Sara', 349:'Meia (young)',
    354:'Lurvy', 399:'Keysmith', 400:'Meia (YM08 variant)'})
ENGLISH_LABELS={360:'Meia (bound)'}
NATIVE_OTHER = {378:'Miming (king)', 446:'Corrupted God Ronan',
    493:'Nirude (residual thought)', 495:'Nirude (with body)', 506:'Zazan'}
USER_NAMES = {416:'Kohei',227:"Jess's Chest",329:'Puku', 335:'Slime', 401:'Mud Man', 431:'Sludge',
    418:'Melzas', 463:'Final Melzas', 476:'Soul Leech', 479:'Dark Dragon',
    289:'Dog', 355:"Meia's Mother", 434:'Kline Nightmare',
    452:'Sara 1',453:'Sara 2',497:'Ancient Golem',
    488:'Corpse Worm',485:'Watcher In The Water',
    500:'Twin Demons',
    392:'Killer',461:'Treant',440:'Shadow',
    338:'Gragg (axe)',341:'Gragg (mace)',344:'Gragg (iron armor)',
    410:'Sand Worm',425:'Mummy',454:'Mummy',
    437:'Turtle',441:'Turtle (Red)',428:'Reaper',467:'Roach',
    1:'Spring Bean',358:'Worshiper',507:"Zazan's Rock",508:"Zazan's Underling",
    438:'Non-Enemy Turtle Shell',462:'Treant Projectile'}
# 2026-10-08 (user): drop "Generic", bomb-rod lids are Bombable Rocks.
USER_NAMES.update({241:'Bombable Rock (Side)',242:'Bombable Rock (Top)',243:'Bombable Rock (Vertical)',
    254:'Signpost',290:'Barrel',291:'Jar',292:'Wooden Crate',293:'Rock'})
USER_NAMES.update({402:'Sailor'})
# 2026-10-10 (user): stairway covers are progression blocks; class 383 is the pushable library stool (Sanctuary puzzle).
USER_NAMES.update({327:'Progression Block (Small)',328:'Progression Block (Large)',383:'Tri-Color Switch (Red)',346:'Nirude Face Statue',345:'Nirude Finger Switch',340:'Spring Bean Pot',325:'Iron Gate (Small)',326:'Iron Gate (Large)',323:'Locked Door (Small)',324:'Locked Door (Large)',314:'Boulder (Small)',315:'Boulder (Large)',310:'Spike Ball (Small)',311:'Spike Ball (Large)',301:'Switch (Step On)',298:'Pushable Pillar (One Tile)',430:'Pushable Pillar',295:'Boulder (Breakable By Iron Flail) 1',296:'Boulder (Breakable By Iron Flail) 2',294:'Magic Vase',291:'Vase',241:'Bombable Rock (Left Side)',234:'Power Glove Rock'})
USER_NAMES.update({409:'Spring Bean Pot (Active)',340:'Spring Bean Pot',408:'Torla Platform'})
# 2026-10-13 (user): the source label 'Bubble .0-1-2 Stand-On / .3-4 Non-Stand' was unclear; which
# bubble it is (stand-on or rising) is picked in the event editor's Behaviour list.
USER_NAMES.update({397:'Bubble'})
# 2026-10-13 (user): two pattern plates; the stock class is the static one (tools/native_pattern_plate_profile.py).
USER_NAMES.update({364:'Pattern Plate Star'})
# 2026-10-14 (user): the two-colour box is two entries, Blue Block (this one, facing down) and Red Block.
USER_NAMES.update({361:'Blue Block'})
# 2026-10-14 (user): renames.
USER_NAMES.update({344:'Gragg (Flail)',441:'Red Turtle',452:'Sara',453:'Shrine Demon',454:'Shrine Mummy',412:'Wilda'})
# 2026-10-15 (user): King Miming and the Bonaire variant of his nightmare are NPCs.
USER_NAMES.update({378:'King Miming',379:'Bonaire (YM03 Variant)'})
# 2026-10-18 (user): Merrick, captain of the Klark ship (US ETC name bank 417), is an NPC.
USER_NAMES.update({417:'Merrick'})
# 2026-10-18 (user): Puku and Slime names swapped (329 Puku, 335 Slime).
USER_NAMES_2026_10_18={329,335,417}
# 2026-10-22 (user): 298 moves one tile in its Direction; 430 is the other pushable pillar.
USER_NAMES.update({297:'Herb Grass',251:'Laser Orb',237:'SaveBook'})
# 2026-10-22 (user): mark the freezable fire. Flame 319's map-443 variant (D: 87 80 07, Ice Wand
# element) freezes; Launcher fireballs freeze with the "Fireballs freezable" option (BizHawk 2026-10-22).
USER_NAMES.update({319:'Fireball (Freezable)'})
# 2026-10-27 (user): Nirude (With Body) is just Nirude.
USER_NAMES.update({495:'Nirude',373:'Log (Carryable)',478:'Soul Leech Slime',494:'Reptilicus Maximus',447:'Ronan Beam'})   # 373 was 'Log (Carryable), Small Iron Ball'
USER_NAMES_2026_10_27={495,373,478,494,447}
USER_NAMES_2026_10_22={298,430,297,251,319,237}
USER_NAMES_2026_10_15={378,379}
USER_NAMES_2026_10_10={408,409,327,328,383,346,345,340,325,326,323,324,314,315,310,311,301,298,295,296,294,291,241,234}
USER_NAMES_2026_10_08={241,242,243,254,290,291,292,293,402}
USER_NAMES_2026_10_06={227,392,461,440,338,341,344,410,425,454,437,441,428,467}
USER_NAMES_2026_10_07={1,358,507,508,438,461,462}
US_SPELLINGS={'Muruta':'Murgg','Roein':'Ronan','Klein':'Kline','Mimming':'Miming','Nilude':'Nirude','Zoldia':'Zorgia',
    'Element':'Ancient Golem','Centipede':'Corpse Worm','Abyss':'Watcher In The Water',
    'Beam Brothers':'Twin Demons','Beam Brother':'Twin Demon',
    'Iron ball wall':'Flail Wall'}
NAME_DEFAULT_VERSION=50


def user_name_basis(index):
    if index in USER_NAMES_2026_10_27:return 'user confirmed 2026-10-27'
    if index in USER_NAMES_2026_10_22:return 'user confirmed 2026-10-22'
    if index in USER_NAMES_2026_10_18:return 'user confirmed 2026-10-18'
    if index in USER_NAMES_2026_10_15:return 'user confirmed 2026-10-15'
    if index in USER_NAMES_2026_10_10:return 'user confirmed 2026-10-10'
    if index in USER_NAMES_2026_10_08:return 'user confirmed 2026-10-08'
    if index in USER_NAMES_2026_10_07:return 'user confirmed 2026-10-07'
    return 'user confirmed 2026-10-06' if index in USER_NAMES_2026_10_06 else 'user confirmed 2026-10-05'


def capitalize_words(name):
    """Capitalise the first letter of every word (user request 2026-10-07).

    Only lowercase word starts change; apostrophe suffixes (Zazan's) and the
    rest of each word keep their case."""
    return re.sub(r"(?<![\w'\u2019])([a-z])",lambda m:m.group(1).upper(),name)


def default_name(index, entry, kind):
    """Return display name and provenance; generic source labels stay unverified."""
    legacy = entry['text_en'].lstrip('◆')
    name = legacy
    basis = 'upstream descriptive label; official US name unverified'
    if index in ENGLISH_LABELS:
        name=ENGLISH_LABELS[index]
        basis='Confirmed US character name with descriptive source variant'
    if index in NPC_NAMES or index in NATIVE_OTHER:
        name = NPC_NAMES.get(index, NATIVE_OTHER.get(index))
        basis = 'US ETC_USA.R native name bank; variant qualifier from upstream'
    if index in USER_NAMES:
        name = USER_NAMES[index]
        basis = user_name_basis(index)
    untrimmed=name
    substitutions=[]
    if index not in USER_NAMES:
        for old,new in US_SPELLINGS.items():
            changed=re.sub(r'\b'+re.escape(old)+r'\b',new,name)
            if changed!=name:substitutions.append(dict(source=old,us=new));name=changed
    if kind in ('enemy','boss') or name.startswith('Projectile'):   # projectiles too: 'Projectile Lv.1' is 'Projectile' (user 2026-10-27)
        name=re.sub(r'\s+Lv\.\s*\d+\s*$', '', name, flags=re.IGNORECASE)
    name=capitalize_words(name)
    aliases = sorted({untrimmed, legacy, entry['text_en'].lstrip('◆'), entry['text_fr'].split(' (')[0]} - {name, ''})
    meta = dict(default_name=name, name_basis=basis, name_aliases=aliases,
                name_verified=index in NPC_NAMES or index in NATIVE_OTHER or index in USER_NAMES,
                name_default_version=NAME_DEFAULT_VERSION)
    if substitutions:
        meta.update(us_spelling_substitutions=substitutions,
            spelling_basis='Confirmed US spelling; variant/component qualifier remains descriptive')
    if index in NPC_NAMES or index in NATIVE_OTHER:
        meta.update(name_module='ETC_USA.R', name_module_sha256=ETC_SHA256,
                    name_table_index=index, name_pointer_file_offset=index*2)
    return name, meta


def apply_default_name(row, index, entry, kind):
    """Refresh untouched defaults, retaining explicit or independently changed names."""
    name, meta = default_name(index, entry, kind)
    source = row.setdefault('source', {})
    old = row.get('name', '')
    previous = source.get('default_name')
    legacy = entry['text_fr'].split(' (')[0] if kind == 'npc' else entry['text_en'].lstrip('◆')
    generic = old.startswith(('Enemy / sprite definition', 'Item definition', 'Unknown /', 'Unused source definition'))
    untouched = old == previous if previous is not None else old in {legacy, entry['text_en'].lstrip('◆')}
    if not row.get('clone_of') and not source.get('user_named') and (generic or untouched):
        row['name'] = name
    meta['name_aliases']=sorted(set(meta['name_aliases'])|set(source.get('name_aliases',[]))|
        ({previous} if isinstance(previous,str) and previous!=name else set()))
    source.update(deepcopy(meta))
    return row


def refresh_database_names(database):
    """Refresh cached source labels without reading/rescanning any retail map."""
    from database_catalogue import entity_names, classify, MISC_PARTS
    names=entity_names();changed=[]
    for row in database.definitions:
        source=row.get('source',{})
        index=source.get('catalogue_index',source.get('balance_entry'))
        if type(index) is not int or not 0<=index<len(names):continue
        if row['kind'] in ('item','weapon','armor'):continue
        entry=names[index]
        if 'empty' in entry['text_en'].lower() or entry['text_en']=='END':continue
        if index in MISC_PARTS and not row.get('clone_of') and row.get('kind')!='unclassified':row['kind']='unclassified'
        before=row['name'];apply_default_name(row,index,entry,classify(index,entry['text_en']))
        if row['name']!=before:changed.append(dict(class_id=row['id'],catalogue_index=index,
            old_name=before,name=row['name']))
    return changed


"""Mod-project content definitions; storage only, not proof of engine support.

Definitions are portable JSON and may be cloned freely. A definition becomes
an in-game type only after it is linked to compatible retail records/assets or
supported by an injected runtime change.
"""
from copy import deepcopy
import hashlib
import csv
from pathlib import Path
import json

KINDS = ("npc", "enemy", "boss", "object", "item", "weapon", "armor", "player", "unclassified")
OBJECT_REACTIONS = ("player_touch", "player_standing", "sword", "flail", "bow",
                    "fire_wand", "ice_wand", "bomb", "spring_bean", "objects")
DEFAULT_ANIMATIONS = [{"name": "idle", "ticks_per_frame": 8, "frames": [0]}]
TEMPLATES = {
    "unclassified": {"sprite_reference": None, "notes": "Identify before use.", "animations": DEFAULT_ANIMATIONS},
    "npc": {"world_sprite": None, "dialogue_sprite": None,
            "dialogue_graph": [], "palette_shift": {"hue_degrees": 0}, "animations": DEFAULT_ANIMATIONS},
    "enemy": {"source_sprite": None, "max_hp": None,
              "contact_damage": None, "palette_shift": {"hue_degrees": 0},
              "attacks": [], "animations": DEFAULT_ANIMATIONS},
    "boss": {"source_sprite": None, "max_hp": None,
             "contact_damage": None, "palette_shift": {"hue_degrees": 0},
             "attacks": [], "animations": DEFAULT_ANIMATIONS},
    "object": {"source_sprite": None, "destructible": False, "throwable": False,
               "reacts_to_hit": False, "spawns_drops": False,
               "breaks_when_thrown": False, "contained_item_class_id": None,
               "active_by_default": False, "activation_one_way": False,
               "remember_state_until_area_exit": False,
               "animations": DEFAULT_ANIMATIONS,
               "reactions": {trigger: {"activate": False, "destroy": False}
                             for trigger in OBJECT_REACTIONS}},
    "item": {"effect": "", "use_damage": None, "healing_hp": None,
             "healing_mp": None, "money": None, "animations": DEFAULT_ANIMATIONS},
    "weapon": {"slot": None, "damage": None, "charge_frames": None,
               "attack_animation_frames": None, "attacks": [], "animations": DEFAULT_ANIMATIONS},
    "armor": {"slot": None, "animations": DEFAULT_ANIMATIONS},
    "player": {"max_hp": None, "max_mp": None, "starting_money": None,
               "base_attack": None, "base_defense": None, "animations": DEFAULT_ANIMATIONS},
}


SOURCE_EMPTY_BUT_USED={416:'Kohei',417:'Merrick'}   # 417: Merrick, captain of the Klark ship (US name bank; ship maps 389-391, Inoa map 134)   # named 'Empty' in the source list, but a real NPC (Inoa map 143)

class ContentDatabase:
    def __init__(self, document=None, copy=True):
        # copy=False adopts a document the caller already copied (event drafts).
        document = (deepcopy(document) if copy else document) if document is not None else {
            "format": "alundra-content-database-v1", "definitions": [], "instances": [], "event_graphs": []}
        if document.get("format") != "alundra-content-database-v1" or not isinstance(document.get("definitions"), list):
            raise ValueError("Unsupported content database")
        document.setdefault("instances", [])
        document.setdefault("event_graphs", [])
        if not isinstance(document["instances"], list):
            raise ValueError("Content database instances must be a list")
        if not isinstance(document["event_graphs"], list):
            raise ValueError("Event graphs must be a list")
        self.document = document
        seen = set()
        for row in self.document["definitions"]:
            self._validate(row)
            if row["id"] in seen:
                raise ValueError("Duplicate definition ID")
            seen.add(row["id"])
        instance_ids=set();definition_ids={row["id"] for row in self.definitions}
        item_kinds={row["id"] for row in self.definitions if row["kind"] in ("item","weapon","armor")}
        for row in self.definitions:
            if row["kind"]=="object":
                item_id=row["data"].get("contained_item_class_id")
                if item_id is not None and item_id not in item_kinds:
                    raise ValueError("Object contents must reference an existing item class")
        for instance in self.document["instances"]:
            if not isinstance(instance,dict) or not isinstance(instance.get("id"),str):
                raise ValueError("Each database instance needs a stable ID")
            if instance["id"] in instance_ids:raise ValueError("Duplicate database instance ID")
            instance_ids.add(instance["id"])
            if type(instance.get("map_id")) is not int or not 0<=instance["map_id"]<2547:
                raise ValueError("Database instance has an invalid map ID")
            if type(instance.get("entity_index")) is not int or instance["entity_index"]<0:
                raise ValueError("Database instance has an invalid entity index")
            class_id=instance.get("class_id")
            if class_id is not None and class_id not in definition_ids:
                raise ValueError("Database instance refers to a missing class")
        from event_graph import validate_event_graph
        event_ids=set()
        for event in self.document["event_graphs"]:
            validate_event_graph(event)
            if event["id"] in event_ids:raise ValueError("Duplicate standalone event ID")
            event_ids.add(event["id"])
            self._validate_event_classes(event)

    def _validate_event_classes(self, event):
        """Keep project event placements attached to real placeable classes."""
        item_kinds={row["id"] for row in self.definitions if row["kind"] in ("item","weapon","armor")}
        def validate_item_page(page):
            # 2026-10-23: an item page is the game's own pickup while the page is in force;
            # its actions run after the pickup. Only what cannot apply to a picked-up item is refused.
            trigger=page.get("trigger",event.get("trigger"))
            # Death / Activate are kept and ignored (an item never fires them, user 2026-10-23); Hit runs on a hit
            if trigger not in (None,"interact","touch","autorun","parallel","hit","death","activate"):
                raise ValueError(f"An item page's actions run when it is picked up or hit; the {trigger} trigger does not apply to an item (choose Player Touch, Interact or Hit)")
            def walk(rows):
                for row in rows or []:
                    yield row
                    for key in ("then","else","commands"):
                        if isinstance(row.get(key),list):yield from walk(row[key])
            rows=list(walk(page.get("commands")))+[r for h in page.get("trigger_actions",[]) for r in walk(h.get("commands"))]
            if any(row.get("type") in ("change_animation","move_actor","face_actor") for row in rows):
                raise ValueError("The item is gone once picked up, so its actions cannot move, turn or animate This event")
        def validate_placed_class(class_id):
            if class_id is None:return
            row=next((item for item in self.definitions if item["id"]==class_id),None)
            if row is None:raise ValueError("Event placement refers to a missing database class")
            if row["kind"] in ("item","weapon","armor"):
                source=row.get('source',{})
                catalogue=source.get('catalogue_index')
                item=source.get('item_id')
                if type(item) is not int or not 1<=item<=89 or catalogue!=item+30:
                    raise ValueError('Placed inventory class needs an existing native item identity')
                # The compiler still checks exact native definition changes and
                # verifies a real ground-pickup donor in the loaded game data.
            elif row["kind"] not in ("npc","enemy","boss","object"):
                raise ValueError("Choose a native pickup, NPC, enemy, boss, or object class for map placement")
            elif type(row.get("source",{}).get("boss_part_of")) is int and not row.get("clone_of") and row["kind"]=="boss" and not row["source"].get("observed_maps"):
                parent=next((r for r in self.definitions if r.get("source",{}).get("catalogue_index")==row["source"]["boss_part_of"] and not r.get("clone_of")),None)
                raise ValueError(f"{row['name']} is a part of {parent['name'] if parent else 'a boss'}: place the boss, its parts come with it")
        validate_placed_class(event.get("class_id"))
        def validate_commands(commands):
            for command in commands:
                if command["type"]=="spawn_class":
                    row=next((item for item in self.definitions if item["id"]==command["class_id"]),None)
                    if row is None:raise ValueError("Spawn command refers to a missing database class")
                    if row["kind"] not in ("npc","enemy","boss","object"):
                        raise ValueError("Spawn command requires an NPC, enemy, boss, or object class")
                if command["type"]=="give_item":
                    row=next((item for item in self.definitions if item["id"]==command["item_class_id"]),None)
                    if row is None or row["kind"] not in ("item","weapon","armor"):
                        raise ValueError("Give item command must refer to an existing item class")
                if command["type"]=="if":
                    validate_commands(command["then"]);validate_commands(command["else"])
        for page in event["pages"]:
            page_class=page.get("class_id",event.get("class_id"))
            validate_placed_class(page_class)
            if page_class in item_kinds:validate_item_page(page)
            if "contained_item_class_id" in page:
                item_id=page["contained_item_class_id"]
                if item_id is not None and item_id not in item_kinds:
                    raise ValueError("Chest contents must reference an existing item, weapon, or armour class")
                if item_id is not None:
                    placed=next((item for item in self.definitions if item["id"]==page_class),None)
                    if not placed or placed.get("kind")!="object" or placed.get("source",{}).get("catalogue_index")!=30:
                        raise ValueError("Only the native Chest class can have an assigned chest item")
            validate_commands(page["commands"])
            for handler in page.get('trigger_actions',[]):
                validate_commands(handler.get('commands',[]))

    @property
    def definitions(self):
        return self.document["definitions"]

    def to_json(self):
        return deepcopy(self.document)

    def _validate(self, row):
        if not isinstance(row, dict) or row.get("kind") not in KINDS:
            raise ValueError("Definition must have a supported kind")
        if not isinstance(row.get("id"), str) or not row["id"] or len(row["id"]) > 80:
            raise ValueError("Definition needs a short stable ID")
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            raise ValueError("Definition needs a name")
        if not isinstance(row.get("data"), dict):
            raise ValueError("Definition data must be an object")
        row.setdefault("class_key",row["id"])
        if not isinstance(row["class_key"],str) or not row["class_key"] or len(row["class_key"])>100:
            raise ValueError("Class key must be a short non-empty string")
        data = row["data"]
        palette=data.get('palette_shift')
        if palette is not None and (not isinstance(palette,dict) or type(palette.get('hue_degrees',0)) is not int or not -360<=palette.get('hue_degrees',0)<=360):
            raise ValueError('Palette hue must be an integer rotation of -360..360 degrees')
        if palette is not None and (type(palette.get('saturation_percent',100)) is not int or not 0<=palette.get('saturation_percent',100)<=200):
            raise ValueError('Colour saturation must be a whole percent of 0..200')
        speed=data.get('speed_percent',100)
        if type(speed) is not int or not 25<=speed<=500:
            raise ValueError('Animation and attack speed must be a whole percent of 25..500')
        move=data.get('move_speed_percent',100)
        if type(move) is not int or not 25<=move<=500:
            raise ValueError('Movement speed must be a whole percent of 25..500')
        spawns=data.get('spawn_attacks',[])
        if not isinstance(spawns,list) or len(spawns)>32:
            raise ValueError('New attacks must be a list of at most 32 rows')
        for spawn in spawns:
            if not isinstance(spawn,dict) or not isinstance(spawn.get('class_id'),str) or type(spawn.get('animation')) is not int or not 0<=spawn['animation']<=255:
                raise ValueError('Each new attack needs an animation (0-255) and a class to spawn')
            if type(spawn.get('frame',0)) is not int or not 0<=spawn.get('frame',0)<=255:
                raise ValueError('A new attack\'s frame must be 0-255')
            if any(type(spawn.get(k,0)) is not int or not -512<=spawn.get(k,0)<=512 for k in ('dx','dy','dz')):
                raise ValueError('New attack offsets must be whole pixels within 512')
        animations = data.get("animations", [])
        if not isinstance(animations, list) or len(animations) > 64:
            raise ValueError("Animations must be a list of at most 64 sequences")
        animation_names = set()
        for animation in animations:
            if not isinstance(animation, dict) or not isinstance(animation.get("name"), str) or not animation["name"].strip():
                raise ValueError("Each animation needs a name")
            if animation["name"] in animation_names:
                raise ValueError("Animation names must be unique per definition")
            animation_names.add(animation["name"])
            speed = animation.get("ticks_per_frame")
            frames = animation.get("frames")
            if type(speed) is not int or not 1 <= speed <= 255 or not isinstance(frames, list) or not frames or len(frames) > 256 or any(type(frame) is not int or not 0 <= frame <= 255 for frame in frames):
                raise ValueError("Animation speed must be 1-255 and frames must be IDs 0-255")
        if row["kind"] == "object":
            for field in ("destructible", "throwable", "reacts_to_hit", "spawns_drops", "breaks_when_thrown",
                          "active_by_default", "activation_one_way", "remember_state_until_area_exit"):
                if type(data.get(field, False)) is not bool:
                    raise ValueError(f"Object property {field} must be a checkbox value")
            reactions = data.get("reactions", {})
            if not isinstance(reactions, dict) or set(reactions) - set(OBJECT_REACTIONS):
                raise ValueError("Object has an unsupported reaction trigger")
            for trigger, response in reactions.items():
                if not isinstance(response, dict) or any(type(response.get(key, False)) is not bool for key in ("activate", "destroy")):
                    raise ValueError(f"Invalid Activate/Destroy options for {trigger}")

    def new(self, kind, name=None, template_id=None):
        if kind not in KINDS:
            raise ValueError("Unknown definition kind")
        template = self.get(template_id) if template_id is not None else None
        if template is not None and template['kind'] != kind:
            raise ValueError('Choose a template of the same type')
        used = {row["id"] for row in self.definitions}
        number = 1
        while f"{kind}:{number:04d}" in used:
            number += 1
        row = {"id": f"{kind}:{number:04d}", "kind": kind,
               "class_key": f"{kind}:{number:04d}",
               "name": name or f"New {kind.title()} {number}",
               "source": {"build_sha256": None, "sprite_id": None},
               "data": deepcopy(TEMPLATES[kind])}
        if template is not None:
            row['source'] = deepcopy(template.get('source', {}))
            row['clone_of'] = template['id']
            row['data'] = deepcopy(template['data'])
        self._validate(row)
        self.definitions.append(row)
        return row

    def duplicate(self, definition_id):
        source = self.get(definition_id)
        row = self.new(source["kind"], source["name"] + " Copy")
        row["source"] = deepcopy(source.get("source", {}))
        row["clone_of"] = source["id"]
        row["data"] = deepcopy(source["data"])
        return row

    def get(self, definition_id):
        for row in self.definitions:
            if row["id"] == definition_id:
                return row
        raise ValueError("Definition no longer exists")

    def replace(self, definition_id, row):
        self._validate(row)
        if row["id"] != definition_id:
            raise ValueError("Definition IDs cannot be changed")
        if row["kind"]=="object":
            item_id=row["data"].get("contained_item_class_id")
            if item_id is not None and self.get(item_id)["kind"] not in ("item","weapon","armor"):
                raise ValueError("Object contents must reference an item class")
        if any(other["id"] == definition_id for other in self.definitions if other is not self.get(definition_id)):
            raise ValueError("Duplicate definition ID")
        old = self.get(definition_id)
        self.definitions[self.definitions.index(old)] = deepcopy(row)
        if old != row:
            for listener in list(DEFINITION_LISTENERS):listener(self, definition_id)


    def delete(self, definition_id):
        row = self.get(definition_id)
        def uses_class(commands):
            return any(command.get("class_id")==definition_id or command.get("item_class_id")==definition_id or
                       (command.get("type")=="if" and (uses_class(command.get("then",[])) or uses_class(command.get("else",[]))))
                       for command in commands)
        for event in self.document["event_graphs"]:
            if event.get("class_id")==definition_id or any(
                page.get("class_id",event.get("class_id"))==definition_id or uses_class(page.get("commands",[])) or
                any(uses_class(handler.get('commands',[])) for handler in page.get('trigger_actions',[]))
                for page in event.get("pages",[])
            ):
                raise ValueError("This class is used by a map event; remove its event references first")
        self.definitions.remove(row)
        for instance in self.document["instances"]:
            if instance.get("class_id")==definition_id:instance["class_id"]=None
        if row["kind"] in ("item","weapon","armor"):
            for other in self.definitions:
                if other["kind"]=="object" and other["data"].get("contained_item_class_id")==definition_id:
                    other["data"]["contained_item_class_id"]=None

    def _map_entities(self, datas):
        """Cache optional map observations; catalogue definitions never require maps."""
        if datas is None:return []
        from map_inspector import inspect_map
        import struct
        digest=hashlib.sha256(datas).hexdigest()
        if getattr(self,'_map_cache_digest',None)==digest:return self._map_cache_entities
        entries=[];failures=[]
        tell=getattr(self,'_map_progress',None)   # (the editor's loading bar: maps read so far)
        for map_id in range(483):
            if tell is not None and map_id%8==0:
                try:tell(map_id/483)
                except Exception:pass
            try:
                entities=inspect_map(datas,map_id)['entities']
                for entity in entities:
                    offset=int(entity['offset'],16)
                    if offset<0 or offset+6>=len(datas):raise ValueError('Entity outside game data')
                entries.extend((map_id,entity) for entity in entities)
            except (ValueError,IndexError,KeyError,struct.error) as exc:
                failures.append({'map_id':map_id,'error':str(exc)})
        self._map_cache_digest=digest;self._map_cache_entities=entries
        self.document['map_index_errors']=failures
        return entries

    def scan_instances(self, datas, source_datas=None):
        """Index current placements while keeping identity tied to their base build."""
        from map_inspector import inspect_map
        digest=hashlib.sha256(source_datas if source_datas is not None else datas).hexdigest()
        old={(row.get("source",{}).get("build_sha256"),row["map_id"],row["entity_index"]):row.get("class_id")
             for row in self.document["instances"]}
        instances=[];definition_ids={row["id"] for row in self.definitions}
        by_sprite={}
        for row in self.definitions:
            source=row.get('source',{})
            if source.get('build_sha256') in (None,digest):
                by_sprite.setdefault(source.get('sprite_id'),[]).append(row)
        for map_id,entity in self._map_entities(datas):
            index=entity["index"];offset=int(entity["offset"],16);sprite=datas[offset+6]
            key=(digest,map_id,index)
            candidates=by_sprite.get(sprite,[])
            class_id=old.get(key)
            if class_id not in definition_ids:
                class_id=candidates[0]["id"] if len(candidates)==1 else None
            instances.append({"id":f"{digest[:12]}:map:{map_id}:entity:{index}",
                "map_id":map_id,"entity_index":index,"class_id":class_id,
                "source":{"build_sha256":digest,"sprite_id":sprite,
                          "offset":entity["offset"]}})
        self.document["instances"]=instances
        return instances

    def assign_instance(self, instance_id, class_id):
        if class_id is not None:self.get(class_id)
        for instance in self.document["instances"]:
            if instance["id"]==instance_id:
                instance["class_id"]=class_id;return instance
        raise ValueError("Database instance no longer exists")

    def new_event_graph(self, map_id, name="New map event", x=0, y=0,
                        class_id=None):
        from event_graph import new_event_graph
        used={row["id"] for row in self.document["event_graphs"]}|set(self.document.get('deleted_event_ids',[]));number=1
        while f"event:{number:04d}" in used:number+=1
        row=new_event_graph(f"event:{number:04d}",map_id,name,x,y,class_id)
        from object_activation import default_event_trigger
        definition=next((r for r in self.definitions if r['id']==class_id),None)
        from event_graph import class_event_name
        name=class_event_name(row['name'],definition)
        if name!=row['name']:row['name']=self.lettered_event_name(map_id,name,None)
        row['pages'][0]['trigger']=default_event_trigger(definition)
        self._validate_event_classes(row)
        self.document["event_graphs"].append(row)
        return row

    def lettered_event_name(self, map_id, base, event_id):
        """Distinct name on one map: the second ``base`` makes them A, B, C.."""
        from event_graph import lettered_name
        others=[e for e in self.document["event_graphs"] if e["map_id"]==map_id and e["id"]!=event_id]
        name,rename=lettered_name(base,[e["name"] for e in others])
        if rename:
            next(e for e in others if e["name"]==base)["name"]=rename
        return name

    def replace_event_graph(self, event_id, row):
        from event_graph import validate_event_graph
        row=validate_event_graph(row)
        if row["id"]!=event_id:raise ValueError("Standalone event IDs cannot be changed")
        index=next((i for i,event in enumerate(self.document["event_graphs"]) if event["id"]==event_id),None)
        if index is None:raise ValueError("Standalone event no longer exists")
        self._validate_event_classes(row)
        self.document["event_graphs"][index]=row
        return row

    def delete_event_graph(self, event_id):
        events=self.document["event_graphs"]
        index=next((i for i,event in enumerate(events) if event["id"]==event_id),None)
        if index is None:raise ValueError("Standalone event no longer exists")
        return events.pop(index)

    def duplicate_event_graph(self,event_id,map_id,x,y):
        """Clone a project-authored map event at a new tile with fresh IDs."""
        from copy import deepcopy
        source=next((row for row in self.document['event_graphs'] if row['id']==event_id),None)
        if source is None:raise ValueError('Select an event that still exists')
        if source.get('native_binding'):
            raise ValueError('A bound retail event cannot be copied as a new native process yet')
        if type(map_id) is not int or not 0<=map_id<2547 or type(x) is not int or type(y) is not int or not 0<=x<256 or not 0<=y<256:
            raise ValueError('Choose a valid destination map tile')
        placeholder=self.new_event_graph(map_id,source['name']+' copy',x,y)
        clone=deepcopy(source);clone['id']=placeholder['id'];clone['map_id']=map_id
        _,_,width,height=clone['region'];clone['region']=[x,y,width,height]
        suffix=clone['id'].split(':')[-1]
        for number,page in enumerate(clone['pages'],1):page['id']=f'page:{suffix}:{number:04d}'
        return self.replace_event_graph(clone['id'],clone)

    def discover_map_sprites(self, datas, map_id):
        """Index sprite IDs seen in one map without guessing NPC/enemy identity."""
        from map_inspector import inspect_map
        info = inspect_map(datas, map_id)
        existing = {row.get("source", {}).get("sprite_id") for row in self.definitions
                    if row.get("source", {}).get("build_sha256") in (None, hashlib.sha256(datas).hexdigest())}
        added = []
        for entity in info["entities"]:
            offset = int(entity["offset"], 16)
            sprite = datas[offset + 6]
            if sprite in existing:
                continue
            row = self.new("unclassified", f"Unclassified map sprite {sprite:02X}")
            row["data"]["sprite_reference"] = sprite
            row["source"] = {"build_sha256": None, "sprite_id": sprite,
                             "observed_map": map_id, "identity": "unclassified"}
            added.append(row)
            existing.add(sprite)
        return added

    def scan_all_map_sprites(self, datas):
        """Collect observed entity sprite IDs and map locations, without naming AI."""
        from map_inspector import inspect_map
        digest = hashlib.sha256(datas).hexdigest()
        uses = {}
        for map_id,entity in self._map_entities(datas):
            sprite = datas[int(entity["offset"], 16) + 6]
            uses.setdefault(sprite, set()).add(map_id)
        existing = {row.get("source", {}).get("sprite_id") for row in self.definitions
                    if row.get("source", {}).get("build_sha256") == digest}
        added = []
        for sprite, maps in sorted(uses.items()):
            if sprite in existing:
                continue
            row = self.new("unclassified", f"Unclassified map sprite {sprite:02X}")
            row["data"]["sprite_reference"] = sprite
            row["source"] = {"build_sha256": digest, "sprite_id": sprite,
                             "observed_maps": sorted(maps), "identity": "unclassified"}
            added.append(row)
        return added

    def import_balance_table(self, data, *, preserve_existing=False):
        """Index source records and tiers, keeping unknown combat fields raw."""
        from enemy_definition import BalanceTable
        table = BalanceTable(data)
        digest = hashlib.sha256(data).hexdigest()
        names = {}
        names_path = Path(__file__).resolve().parents[1] / "data" / "item-slots.csv"
        if names_path.is_file():
            with names_path.open(newline="", encoding="utf-8") as stream:
                names = {int(row["item_id"], 16): row["name"] for row in csv.DictReader(stream)}
        from database_catalogue import item_names,entity_names,classify,item_kind
        from catalogue_names import default_name
        items=item_names();names.update({i:row['name'] for i,row in enumerate(items)})
        catalogue=entity_names()
        seen = {row.get("source", {}).get("balance_entry") for row in self.definitions
                if not row.get('clone_of') and (preserve_existing or row.get("source", {}).get("balance_sha256") == digest)}
        added = []
        from database_catalogue import EMPTY_US_SLOTS, HIDDEN_CATALOGUE
        for entry, chain in enumerate(table.chains):
            if entry in seen or entry in EMPTY_US_SLOTS or entry in HIDDEN_CATALOGUE:
                continue   # no sprite / never placed (Elene and Nadia (dead), Alicia...): not database entries
            # Global sprite30 is the actual Chest class. Inventory item0 is
            # the no-item sentinel, not another placeable pickup definition.
            is_item = 0x1f <= entry < min(0x80, len(table.chains))
            item_id = entry - 0x1e if is_item else None
            label = names.get(item_id, f"Item definition {item_id:02X}") if is_item else f"Enemy / sprite definition {entry:02X}"
            kind = item_kind(item_id,items) if is_item else "enemy"
            if not is_item and entry<len(catalogue):
                source_name=catalogue[entry]['text_en']
                if 'empty' in source_name.lower() or source_name=='END':kind='unclassified';label=f'Unused source definition {entry:03X}'
                else:
                    kind=classify(entry,source_name);label=source_name.lstrip('◆')
                    label,_=default_name(entry,catalogue[entry],kind)
            row = self.new(kind, label)
            tiers = [table.record(entry, tier) for tier in range(len(chain))]
            row["source"] = {"balance_sha256": digest, "balance_entry": entry,
                             "tier_offsets": [record["offset"] for record in tiers],
                             "identity": "source balance entry; semantic role may need verification"}
            if not is_item and entry<len(catalogue) and kind!='unclassified':
                row['source'].update(default_name(entry,catalogue[entry],kind)[1])
            row["data"]["balance_tiers"] = [
                {"threshold": record["level"], "max_hp": record["max_hp"],
                 "damage_responses_raw": record["damage_responses"],
                 "attacks_raw": record["attacks"]}
                for record in tiers]
            if tiers:
                row["data"]["max_hp"] = tiers[0]["max_hp"]
                row["data"]["attacks"] = tiers[0]["attacks"]
                if kind in ('enemy','boss'):
                    row['data']['damage_responses_raw'] = deepcopy(tiers[0]['damage_responses'])
            row['source']['native_data_baseline']=deepcopy(row['data'])
            added.append(row)
        return added

    def populate_catalogue(self, datas=None):
        """Name source definitions and associate previews using each entity's bank bit.

        Catalogue categories are source-reported/editor groupings, not recovered AI.
        User-renamed entries and clones are preserved.
        """
        from database_catalogue import entity_names, item_names, classify, item_kind, graphic_maps, COMMIT
        from catalogue_names import default_name, apply_default_name
        from map_inspector import inspect_map
        names=entity_names();items=item_names();digest=hashlib.sha256(datas).hexdigest() if datas is not None else None
        legacy_path=Path(__file__).resolve().parents[1]/'extras/game edits/src/game/data/item.json'
        legacy_items=json.loads(legacy_path.read_text(encoding='utf-8')) if legacy_path.is_file() else []
        self._merge_balance_catalogue_duplicates()
        uses={};graphics=graphic_maps(datas) if datas is not None else {}
        for map_id,entity in self._map_entities(datas):
            offset=int(entity["offset"],16)
            index=datas[offset+6]+(256 if datas[offset+5]&128 else 0)
            uses.setdefault(index,set()).add(map_id)
        existing={r.get("source",{}).get("catalogue_index"):r for r in self.definitions if not r.get("clone_of") and not r.get("source",{}).get("alundra_npc") and not r.get("source",{}).get("own_slot")}
        balance={r.get("source",{}).get("balance_entry"):r for r in self.definitions if not r.get("clone_of")}
        for index,entry in enumerate(names):
            name=entry["text_en"]
            if index in SOURCE_EMPTY_BUT_USED:name,entry=SOURCE_EMPTY_BUT_USED[index],dict(entry,text_en=SOURCE_EMPTY_BUT_USED[index])
            from database_catalogue import EMPTY_US_SLOTS, HIDDEN_CATALOGUE
            if index in EMPTY_US_SLOTS or index in HIDDEN_CATALOGUE:
                row=existing.get(index) or balance.get(index)
                used=row is not None and any(i.get('class_id')==row['id'] for i in self.document['instances'])
                if row is not None and not used and not row.get('clone_of'):
                    self.document['definitions'].remove(row)
                continue
            if "empty" in name.lower() or name=="END":
                row=balance.get(index)
                if row and row['name'].startswith('Enemy / sprite definition'):
                    row['kind']='unclassified';row['name']=f'Unused source definition {index:03X}'
                continue
            kind=classify(index,name)
            if index in SOURCE_EMPTY_BUT_USED:kind='npc'
            if kind=="item" and 30<=index<128:
                item_id=index-30
                if item_id<len(items):name=items[item_id]["name"]
                kind=item_kind(item_id,items)
            if kind not in ('item','weapon','armor'):
                name=default_name(index,entry,kind)[0]
            row=existing.get(index) or balance.get(index)
            if row is not None and kind in ('item','weapon','armor') and 30<=index<128 and index-30<len(items) and items[index-30].get('native_metadata'):
                from native_item_catalogue import generated_default
                prior=legacy_items[index-30] if index-30<len(legacy_items) else None
                if not generated_default(row,items[index-30],prior) and row['kind'] in ('item','weapon','armor'):
                    kind=row['kind']
            if row is None:row=self.new(kind,name.lstrip("◆"))
            elif row["name"].startswith(("Enemy / sprite definition", "Item definition", "Unknown /", "Unused source definition")):
                row["name"]=name.lstrip("◆")
            row["kind"]=kind
            for key,value in TEMPLATES[kind].items():row["data"].setdefault(key,deepcopy(value))
            source=row.setdefault("source",{})
            if kind not in ('item','weapon','armor'):
                apply_default_name(row,index,entry,kind)
            source.update(catalogue_index=index,catalogue_commit=COMMIT,
                          catalogue_path="AlundraTools/AlundraTools/EntityNames.csv",
                          catalogue_line=index+2,category_basis="source name and editor grouping")
            if datas is not None:source['graphic_maps']=graphics.get(index,[])
            if index in uses:
                source.update(sprite_id=index&255,sprite_bank=index>>8,observed_maps=sorted(uses[index]),build_sha256=digest)
            if kind in ("item","weapon","armor") and 30<=index<128:
                source["item_id"]=index-30
                if index-30<len(items):
                    info=items[index-30]
                    if info.get('native_metadata'):
                        from native_item_catalogue import apply_default
                        apply_default(row,info,legacy_items[index-30] if index-30<len(legacy_items) else None)
                    else:
                        source.setdefault('item_label_basis','Fallback labels; native item resource unavailable')
                    for key,src in [('slot','slot'),('price','goldValue'),('max_quantity','maxQuantity')]:
                        if src in info and row['data'].get(key) is None:row['data'][key]=info[src]
            # Keep native source values separate from requested class edits.
            # For older projects reconstruct only known defaults/source tiers,
            # never declare their currently edited values to be native behavior.
            if 'native_data_baseline' not in source:
                baseline=deepcopy(TEMPLATES[kind])
                tiers=row['data'].get('balance_tiers',[])
                if tiers:
                    baseline.update(balance_tiers=deepcopy(tiers),max_hp=tiers[0]['max_hp'],attacks=deepcopy(tiers[0]['attacks_raw']))
                source['native_data_baseline']=baseline
            baseline=source['native_data_baseline']
            for key,value in TEMPLATES[kind].items():baseline.setdefault(key,deepcopy(value))
            if kind in ('item','weapon','armor') and 30<=index<128 and index-30<len(items):
                for key,src in [('slot','slot'),('price','goldValue'),('max_quantity','maxQuantity')]:
                    if src in items[index-30] and baseline.get(key) is None:baseline[key]=deepcopy(items[index-30][src])
        # Prefer the bank-specific named class to earlier unidentified graphics.
        named={r["source"]["catalogue_index"]:r["id"] for r in self.definitions
               if "catalogue_index" in r.get("source",{}) and not r.get("clone_of")}
        for instance in self.document["instances"]:
            if datas is None:continue
            offset=int(instance["source"]["offset"],16)
            if offset<0 or offset+6>=len(datas):continue
            index=datas[offset+6]+(256 if datas[offset+5]&128 else 0)
            old=instance.get("class_id")
            if old is None or self.get(old)["kind"]=="unclassified":instance["class_id"]=named.get(index,old)
        # Retire only untouched, unreferenced preliminary sprite guesses. Named
        # bank-specific classes now represent these graphics without duplicates.
        referenced={r.get('class_id') for r in self.document['instances']}
        def command_refs(commands):
            for command in commands:
                referenced.update((command.get('class_id'),command.get('item_class_id')))
                if command.get('type')=='if':command_refs(command.get('then',[]));command_refs(command.get('else',[]))
        for event in self.document['event_graphs']:
            referenced.add(event.get('class_id'))
            for page in event['pages']:
                referenced.add(page.get('class_id'));command_refs(page.get('commands',[]))
                for handler in page.get('trigger_actions',[]):command_refs(handler.get('commands',[]))
        for row in list(self.definitions):
            if (row['kind']=='unclassified' and row['id'] not in referenced and
                row['name'].startswith('Unclassified map sprite ') and
                row['data'].get('notes')=='Identify before use.' and
                row['data'].get('animations')==DEFAULT_ANIMATIONS and
                row['data'].get('sprite_reference')==row.get('source',{}).get('sprite_id')):
                self.definitions.remove(row)
        self.ensure_meia_player();self.ensure_alundra_npc();self.ensure_kohei();self.ensure_flush_switch();self.ensure_side_rocks();self.ensure_heal_tiles();self.ensure_pattern_plates();self.ensure_floor_switch();self.ensure_warp_panel();self.ensure_save_portal();self.ensure_color_blocks();self.ensure_nirude_statue_variants();self.ensure_tricolor_switches();self.ensure_pushable_stool();self.ensure_block_switches();self.ensure_sara_demons();self.ensure_npc_variants();self.ensure_talking_bosses();self.ensure_sages();self.ensure_drop_names();self.ensure_boss_parts()
        from placement_catalogue import annotate_placement_sources
        annotate_placement_sources(self)
        return self.definitions

    DROP_NAMES={114:('Dew of Life','Small Life Drop'),115:('Drop of Life','Life Drop'),116:('Water of Life','Large Life Drop'),
                111:('Small Crystal','Magic Drop'),112:('Large Crystal','Large Magic Drop')}   # user 2026-10-18

    # Boss catalogue index -> the catalogue indices (map-local sprite slots, slot+256) of the parts,
    # projectiles and effects its own code creates (2026-10-19 audit of ai_spawned_slots / the
    # unused local sprites of the boss's home map). A part has no placed copy of its own in the
    # game: the boss creates it, so it is linked to its boss instead of being placed alone.
    BOSS_PARTS={412:(413,414,415),418:(419,420,423,424),446:(447,448,450),463:(464,465),471:(472,),
                476:(477,478),479:(480,481),485:(484,486,487),488:(458,489,490,491,492,504,505),
                495:(496,502,503),497:(498,499),500:(470,501),506:(483,507,508),509:(469,510,511)}

    def ensure_boss_parts(self):
        """Link every boss to the parts its fight creates (source.boss_parts on the boss,
        source.boss_part_of on the part). Placing the boss brings the parts' art and spawn
        templates; a part cannot be placed alone (see _validate_event_classes)."""
        def native(index):
            return next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==index
                         and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        linked=[]
        for boss,parts in self.BOSS_PARTS.items():
            row=native(boss)
            if row is None:continue
            row['source']['boss_parts']=list(parts)
            for part in parts:
                child=native(part)
                if child is not None and child is not row:
                    child['source']['boss_part_of']=boss;linked.append(part)
        return linked

    def ensure_drop_names(self):
        for row in self.definitions:
            pair=self.DROP_NAMES.get(row.get('source',{}).get('catalogue_index'))
            if pair and row.get('kind')=='item' and not row.get('clone_of') and row.get('name')==pair[0]:row['name']=pair[1]

    def ensure_meia_player(self):
        """Second Player entry (Meia). Stores settings in the mod project only.

        Meia is not a native player character; Build game does not use this
        entry. Her NPC sprite (catalogue 302) is referenced for the thumbnail."""
        row=next((r for r in self.definitions if r.get('source',{}).get('player_slot')=='meia'),None)
        npc=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==302 and not r.get('clone_of')),None)
        if row is None:
            row=self.new('player','Meia')
            row['data'].update(starting_equipment=[],starting_stats=None)
            row['source']={'player_slot':'meia','export':'settings stored only; not a native player character'}
        if npc is not None:row['source']['graphic_source']=deepcopy(npc.get('source',{}))
        return row

    def ensure_kohei(self):
        """Kohei (catalogue 416, Inoa map 143): the source name list calls him
        'Empty', so he was left out of the NPC list. Added as an NPC."""
        if any(r.get('source',{}).get('catalogue_index')==416 and not r.get('clone_of') for r in self.definitions):return None
        model=next((r for r in self.definitions if r['kind']=='npc' and type(r.get('source',{}).get('catalogue_index')) is int and r['source']['catalogue_index']>=256 and not r.get('clone_of')),None)
        row=self.new('npc','Kohei')
        source=deepcopy(model.get('source',{})) if model else {}
        source.update(catalogue_index=416,balance_entry=416,sprite_id=416&255,sprite_bank=1,observed_maps=[143],graphic_maps=[143])
        for key in ('alundra_npc','player_slot','default_facing'):source.pop(key,None)
        row['source']=source
        return row

    def ensure_alundra_npc(self):
        """Alundra in the NPC list (user 2026-10-11): his sprite (global 0) placed
        as an NPC that stands, talks and runs events like any NPC. Placed from the
        game's own Alundra map actors (cutscene stand-ins), not the player."""
        row=next((r for r in self.definitions if r.get('source',{}).get('alundra_npc')),None)
        if row is not None and row['kind']!='npc':row['kind']='npc';row['name']='Alundra (NPC)'   # never in the Player tab
        player=next((r for r in self.definitions if r['kind']=='player' and r.get('source',{}).get('catalogue_index')==0),None)
        if row is None and player is not None:
            row=self.new('npc','Alundra (NPC)')
            source=deepcopy(player.get('source',{}));source.pop('balance_entry',None);source['alundra_npc']=True
            row['source']=source
        return row

    def ensure_side_rocks(self):
        """Bombable Rock (Side) as two entries: the stock class facing left, and a
        copy facing right (the game turns one class with the actor's direction)."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==241 and not r.get('clone_of')),None)
        if base is None:return None
        base['source']['default_facing']='left'
        row=next((r for r in self.definitions if r.get('clone_of')==base['id'] and r.get('source',{}).get('default_facing')=='right'),None)
        if row is None:
            row=self.new('object','Bombable Rock (Right Side)',template_id=base['id'])
        row['source'].update(deepcopy(base.get('source',{})));row['source']['default_facing']='right';row['source']['user_named']=True
        return row

    def retire_flush_switch(self):
        """Switch (Step On, Flush) is replaced by Step On Switch (Floor)
        (user 2026-10-14): its events become floor switches."""
        flush=[r for r in self.definitions if r.get('source',{}).get('variant')=='flush_top']
        if not flush:return 0
        base=self.ensure_floor_switch()
        if base is None:return 0
        ids={r['id'] for r in flush};moved=0
        for graph in self.document.get('event_graphs',[]):
            hit=False
            if graph.get('class_id') in ids:graph['class_id']=base['id'];hit=True
            for page in graph.get('pages',[]):
                if page.get('class_id') in ids:page['class_id']=base['id'];hit=True
            if hit:moved+=1
        self.definitions[:]=[r for r in self.definitions if r['id'] not in ids]
        return moved

    def ensure_pattern_plates(self):
        """Pattern Plates (catalogue 364): Pattern Plate Star / Moon / Water / Sun
        (static, the symbol is the plate's direction: down, up, left, right)
        and Pattern Plate (Changing), which shows the four in turn as on map 400
        (tools/native_pattern_plate_profile.py)."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==364 and not r.get('clone_of')),None)
        if base is None:return None
        base['source']['default_facing']='down';base['source']['plate_symbol']=0
        for symbol,(name,facing) in enumerate((('Pattern Plate Star','down'),('Pattern Plate Moon','up'),('Pattern Plate Water','left'),('Pattern Plate Sun','right'))):
            if symbol==0:continue
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='pattern_static' and r['source'].get('plate_symbol')==symbol),None)
            if row is None:row=self.new('object',name,template_id=base['id'])
            row['source'].update(deepcopy(base.get('source',{})));row['source'].update(variant='pattern_static',plate_symbol=symbol,default_facing=facing,user_named=True)
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='pattern_cycle'),None)
        if row is None:
            row=self.new('object','Pattern Plate (Changing)',template_id=base['id'])
        row['source'].update(deepcopy(base.get('source',{})));row['source']['variant']='pattern_cycle';row['source']['user_named']=True
        row['source'].pop('default_facing',None);row['source'].pop('plate_symbol',None)
        row['source']['observed_maps']=[400]+[m for m in base.get('source',{}).get('observed_maps',[]) if m!=400]
        return row

    def ensure_color_blocks(self):
        """Red/Blue Two-Color Box (catalogue 361, Ancient Shrine maps 41 / 42) as
        two entries: Blue Block (the box facing down) and Red Block (facing
        right); the game picks the colour by the box's direction. Each runs
        the scripts of a game box of its own colour (map 41)."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==361 and not r.get('clone_of')),None)
        if base is None:return None
        base['source'].update(default_facing='down',fixed_donor=[41,7])
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='red_block'),None)
        if row is None:row=self.new('object','Red Block',template_id=base['id'])
        row['source'].update(deepcopy(base.get('source',{})));row['source'].update(variant='red_block',default_facing='right',fixed_donor=[41,9],user_named=True)
        return row

    def ensure_nirude_statue_variants(self):
        """Nirude Face Statue (catalogue 346) entries that shoot, as in Nirude's Lair
        (user 2026-10-24): Fire (map 35), Homing Fire (map 38), Laser (map 36). The room
        loop that fires is built per placement (native_nirude_statue_variants)."""
        from native_nirude_statue_variants import VARIANTS
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==346 and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        if base is None:return []
        rows=[]
        for key,v in VARIANTS.items():
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='nirude_statue' and r['source'].get('statue_variant')==key),None)
            if row is None:row=self.new('object',v['name'],template_id=base['id'])
            source=deepcopy(base.get('source',{}))
            source.update(variant='nirude_statue',statue_variant=key,fixed_donor=list(v['statue']),user_named=True,
                          observed_maps=[v['statue'][0]]+[m for m in source.get('observed_maps',[]) if m!=v['statue'][0]])
            row['source']=source;rows.append(row)
        return rows

    def ensure_pushable_stool(self):
        """Stool (Pushable): the Sanctuary library stool (catalogue 383, map 137 entity 2), its
        talk/tick programs made by native_pushable_stool (one tile in any allowed direction)."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==383 and not r.get('clone_of')),None)
        if base is None:return None
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='push_stool'),None)
        if row is None:row=self.new('object','Stool (Pushable)',template_id=base['id'])
        source=deepcopy(base.get('source',{}))
        for key in ('default_facing','lit_color'):source.pop(key,None)
        source.update(variant='push_stool',fixed_donor=[137,2],observed_map=137,user_named=True,
                      observed_maps=[137]+[m for m in source.get('observed_maps',[]) if m!=137])
        row['source']=source
        return row

    def ensure_tricolor_switches(self):
        """Three-Color Switch (catalogue 383, Coastal Cave map 75) as three entries; the
        game lights it by the switch's direction (animation 1: down red, up green,
        left yellow), as placed on map 75 (entities 42 / 40 / 58).  Same class and
        scripts; the variants only set the direction (user 2026-10-17)."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==383 and not r.get('clone_of')),None)
        if base is None:return None
        base['source'].update(default_facing='down',variant='tricolor',lit_color='red')
        if not base['source'].get('user_named'):base['name']='Tri-Color Switch (Red)'
        row=None
        for color,facing in (('Green','up'),('Yellow','left')):
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='tricolor' and r['source'].get('lit_color')==color.lower()),None)
            if row is None:row=self.new('object',f'Tri-Color Switch ({color})',template_id=base['id'])
            row['source'].update(deepcopy(base.get('source',{})));row['source'].update(variant='tricolor',lit_color=color.lower(),default_facing=facing,user_named=True)
        return row

    def ensure_npc_variants(self):
        """King Miming (378) and Bonaire's YM03 variant (379, his nightmare: the
        Bonaire who hides as a rock) go in the NPC list (user 2026-10-15); they
        were Objects. They place like any NPC (standard NPC body box)."""
        changed=[]
        for index,name in ((378,'King Miming'),(379,'Bonaire (YM03 Variant)')):
            row=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==index and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
            if row is None:continue
            if row['kind']!='npc':row['kind']='npc';changed.append(index)
            if row.get('name') in ('King Mimming','Miming (King)','Miming (king)','Bojes & rock (YM03)','Bojes & Rock (YM03)'):
                row['name']=name;row['source']['user_named']=True
            if index==379:row['source']['npc_variant_of']=271   # Bonaire
        return changed

    def ensure_sages(self):
        """The sages as NPCs (sage_npc): each is its crest map's own effect sprite."""
        from sage_npc import SAGES,OLD_NAMES
        rows=[]
        for key,name,donor in SAGES:
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='sage' and r['source'].get('sage')==key),None)
            if row is None:row=self.new('npc',name)
            elif row.get('name') in OLD_NAMES:row['name']=name   # placeholder names become the sage's own name
            row['kind']='npc'
            row['source'].update(variant='sage',sage=key,sage_map=donor,user_named=True,
                                 export='crest map effect sprite 0 (standing) + talk on an invisible block')
            rows.append(row)
        return rows

    TALKING_BOSSES=((418,'Melzas (NPC)',[415,1]),(509,'Zorgia (NPC)',[388,1]))

    def ensure_talking_bosses(self):
        """Bosses that talk with a character portrait, as NPCs (user 2026-10-18):
        each uses a cutscene copy of the boss from the game (no fight):
        Melzas from Sybill cutscene 4 (map 415), Zorgia from Nirude's Lair cutscene 2 (map 388)."""
        rows=[]
        for index,name,donor in self.TALKING_BOSSES:
            base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==index and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
            if base is None:continue
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='npc_version' and r['source'].get('catalogue_index')==index),None)
            if row is None:row=self.new('npc',name);row['clone_of']=base['id']
            row['source'].update(deepcopy(base.get('source',{})))
            row['source'].update(variant='npc_version',fixed_donor=list(donor),user_named=True,
                                 observed_maps=[donor[0]]+[m for m in base.get('source',{}).get('observed_maps',[]) if m!=donor[0]])
            rows.append(row)
        return rows

    def ensure_sara_demons(self):
        """One Sara boss, and the enemies that share her art (user 2026-10-14):
        * Sara (452, boss): the boss fight copy, Bonaire's Dream 3 (map 47 entity 1);
        * Demon (452, enemy): the plain demon of the dreams (map 54 entity 15, 13 copies);
        * Shrine Demon (453, enemy): the Lake Shrine demon (was "Sara 2")."""
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==452 and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        if base is not None:
            if base.get('name') in ('Sara 1','Sara1','Sara'):base['name']='Sara'
            base['kind']='boss'
            base['source'].update(fixed_donor=[47,1],user_named=True)
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='demon'),None)
            if row is None:
                row=self.new('boss','Demon',template_id=base['id'])
            row['kind']='enemy'
            keep={k:row['source'][k] for k in ('native_data_baseline','balance_entry','balance_sha256','tier_offsets') if k in row.get('source',{})}   # its own stats (map 54), not Sara's
            row['source'].update(deepcopy(base.get('source',{})));row['source'].update(keep);row['source'].update(variant='demon',fixed_donor=[54,15],user_named=True)
            if row['source'].get('native_data_baseline')==base.get('source',{}).get('native_data_baseline') and row.get('data',{}).get('balance_tiers')!=base.get('data',{}).get('balance_tiers'):
                row['source']['native_data_baseline']=deepcopy(row['data'])   # an older refresh copied Sara's stats over the Demon's own
        # Nirude (Residual Thought) talks and does not fight (user 2026-10-14): an NPC
        nirude=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==493 and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        if nirude is not None:
            nirude['kind']='npc';nirude['source'].update(fixed_donor=[388,0],user_named=True)
        # Wilda (412) is the whole boss: the head brings its body and breath (user 2026-10-14)
        wilda=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==412 and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        if wilda is not None and wilda.get('name') in ('Wilda (Head)','Wilda (head)'):
            wilda['name']='Wilda';wilda['source']['user_named']=True
        shrine=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==453 and not r.get('clone_of') and not r.get('source',{}).get('variant')),None)
        if shrine is not None:
            shrine['kind']='enemy'
            if shrine.get('name') in ('Sara 2','Sara2'):shrine['name']='Shrine Demon'
            shrine['source']['user_named']=True
        return base

    def ensure_warp_panel(self):
        """Warp Panel: the save rooms' floor panel as an object; its event asks
        where it leads and the build puts a warp on its four tiles."""
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='warp_panel'),None)
        if row is None:
            row=self.new('object','Warp Panel')
            row['source']={'build_sha256':None,'sprite_id':None,'variant':'warp_panel','user_named':True,
                           'export':'floor panel (map 452) + a warp on its four tiles'}
        return row

    def ensure_save_portal(self):
        """Save Room Portal: the save rooms' swirling way back (tools/save_portal.py)."""
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='save_portal'),None)
        if row is None:
            row=self.new('object','Save Room Portal')
            row['source']={'build_sha256':None,'sprite_id':None,'variant':'save_portal','user_named':True,
                           'export':'panel (map 452) + swirl (global effect 24) + warp back'}
        return row

    def ensure_floor_switch(self):
        """Step On Switch (Floor): the step-on switch's top drawn as a floor tile,
        stepped on like a healing tile; its Activate actions run each time
        Alundra steps on it (tools/heal_tile.py draws it)."""
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='floor_switch'),None)
        if row is None:
            row=self.new('object','Step On Switch (Floor)')
            row['source']={'build_sha256':None,'sprite_id':None,'variant':'floor_switch','user_named':True,
                           'export':'floor tile picture + Player Touch event on that tile'}
        return row

    def ensure_block_switches(self):
        """Block Switch (Lowers Blue / Red): the orb from Giles' nightmare that
        raises and lowers the Red and Blue Blocks (tools/block_switch.py copies
        the orb sprite from map 41 and builds its map-event program)."""
        rows=[]
        for lowers,name in (('blue','Block Switch (Lowers Blue)'),('red','Block Switch (Lowers Red)')):
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='block_switch' and r['source'].get('lowers')==lowers),None)
            if row is None:
                row=self.new('object',name)
                row['source']={'build_sha256':None,'sprite_id':None,'variant':'block_switch','lowers':lowers,'user_named':True,
                               'export':"Giles' nightmare orb (map 41 effect sprite 0) + its map event program"}
            rows.append(row)
        return rows

    def ensure_heal_tiles(self):
        """Healing Tile (Life) / (Magic): the save rooms' red and green floor
        plates as objects (tools/heal_tile.py draws the plate and builds the
        save room's own healing program where one is placed)."""
        from heal_tile import NAMES
        rows=[]
        for kind,name in NAMES.items():
            row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='heal_tile' and r['source'].get('heal_tile')==kind),None)
            if row is None:
                row=self.new('object',name)
                row['source']={'build_sha256':None,'sprite_id':None,'variant':'heal_tile','heal_tile':kind,'user_named':True,
                               'export':'save room healing tile (map 452): floor plate + its map event program'}
            rows.append(row)
        return rows

    def ensure_flush_switch(self):
        """'Switch (Step On, Flush)': the step-on switch (catalogue 301) drawn as
        only its lit top, level with the floor (tools/flush_switch.py builds its
        sprite on each map where it is placed). Same controller and Activate
        contents as the step-on switch."""
        row=next((r for r in self.definitions if r.get('source',{}).get('variant')=='flush_top'),None)
        if True:return self.retire_flush_switch()   # replaced by Step On Switch (Floor)
        base=next((r for r in self.definitions if r.get('source',{}).get('catalogue_index')==301 and not r.get('clone_of')),None)
        if base is None:return row
        if row is None:
            row=self.new('object','Switch (Step On, Flush)',template_id=base['id'])
        row['source'].update(deepcopy(base.get('source',{})));row['source']['variant']='flush_top'
        row['source']['user_named']=True
        return row

    def _merge_balance_catalogue_duplicates(self):
        """Join duplicate imports of one native type, preserving authored edits."""
        named={r.get('source',{}).get('catalogue_index'):r for r in self.definitions
               if r.get('source',{}).get('catalogue_index') is not None and not r.get('clone_of')}
        for row in list(self.definitions):
            source=row.get('source',{});index=source.get('balance_entry')
            target=named.get(index)
            if target is None or target is row or row.get('clone_of') or source.get('catalogue_index') is not None:continue
            baseline=source.get('native_data_baseline')
            reserved_default = (index==30 and row['name'] in ('Nothing','Unnamed item 00','Item definition 00')
                and not source.get('user_named'))
            if reserved_default:
                def referenced(value):
                    if isinstance(value,dict):
                        return any((key in ('class_id','item_class_id','clone_of','template_class_id','spawned_by_class_id')
                                    and child==row['id']) or referenced(child) for key,child in value.items())
                    if isinstance(value,list):return any(referenced(child) for child in value)
                    return False
                # Preserve user projects that explicitly reference the old row;
                # only untouched auto-generated, unreferenced duplicates retire.
                if referenced(self.document):continue
            # Only automatically-created, unedited source rows can be retired.
            if baseline is None or row['data']!=baseline or (row['name']!=target['name'] and not reserved_default):
                source['catalogue_index']=index
                continue
            target_source=target.setdefault('source',{})
            target_baseline=target_source.setdefault('native_data_baseline',deepcopy(TEMPLATES[target['kind']]))
            for key in ('balance_entry','balance_sha256','tier_offsets'):
                if key in source:target_source[key]=deepcopy(source[key])
            for key,value in baseline.items():
                current=target['data'].get(key)
                if key not in target['data'] or current==target_baseline.get(key):target['data'][key]=deepcopy(value)
                target_baseline[key]=deepcopy(value)
            old_id,new_id=row['id'],target['id']
            def remap(value):
                if isinstance(value,dict):
                    for key,child in value.items():
                        if key in ('class_id','item_class_id','clone_of','template_class_id','spawned_by_class_id') and child==old_id:value[key]=new_id
                        else:remap(child)
                elif isinstance(value,list):
                    for child in value:remap(child)
            remap(self.document)
            self.definitions.remove(row)

    def placement_rows(self, category, include_components=False):
        """Placement tabs preserve database classes and expose parts separately."""
        from placement_catalogue import placement_rows
        return placement_rows(self, category, include_components)

    @classmethod
    def from_json_text(cls, text):
        return cls(json.loads(text))


# Called as listener(database, definition_id) after a class changes, so placed
# events (instances of the class) can be redrawn at once.
DEFINITION_LISTENERS = []

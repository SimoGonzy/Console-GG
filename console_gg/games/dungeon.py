"""Dungeon crawler for Console GG."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random

from console_gg.stats import load_stats, record_metric, record_outcome, save_stats
from console_gg.ui import clear_screen, color, frame, read_key


Position = tuple[int, int]

PLAYER = "@"
EXIT = ">"
WALL = "#"
MONSTER = "M"
BOSS = "B"
POTION = "+"
TREASURE = "$"
WEAPON = "/"
KEY = "k"
ARMOR = "]"
SHRINE = "^"
SECRET_DOOR = "D"
FLOOR = "."
UNKNOWN = "?"

DIRECTIONS: dict[str, Position] = {
    "w": (0, -1),
    "a": (-1, 0),
    "s": (0, 1),
    "d": (1, 0),
}
KEY_ALIASES = {
    "w": "w",
    "a": "a",
    "s": "s",
    "d": "d",
    "h": "w",
    "k": "a",
    "p": "s",
    "m": "d",
    "up": "w",
    "left": "a",
    "down": "s",
    "right": "d",
    "q": "q",
}
MONSTER_DAMAGE = 3
POTION_HEAL = 4
MONSTER_SCORE = 10
TREASURE_SCORE = 25
EXIT_SCORE = 50
BOSS_SCORE = 100
VISION_RADIUS = 4
ARMOR_HEALTH_BONUS = 4
ARMOR_DEFENSE_BONUS = 1
INTENT_CYCLES = {
    "Custode": {
        1: ("strike", "guard", "charge", "heavy"),
    },
    "Re delle Sale": {
        1: ("strike", "charge", "heavy", "guard"),
        2: ("heavy", "guard", "strike", "heavy"),
    },
}
PORTAL_BOONS = {
    "health": ("health", "Benedizione vitale: +4 vita massima e +4 HP."),
    "attack": ("attack", "Benedizione feroce: attacco +1."),
    "defense": ("defense", "Benedizione di ferro: difesa +1."),
}
PORTAL_BOON_KEYS = {
    "h": "health",
    "a": "attack",
    "d": "defense",
}
NEIGHBOR_STEPS: tuple[Position, ...] = ((0, -1), (-1, 0), (0, 1), (1, 0))
BOSS_PORTRAITS = {
    "Custode": {
        1: [
            r"   /\   ",
            r"  [##]  ",
            r"  /__\  ",
        ],
    },
    "Re delle Sale": {
        1: [
            r"  .--.  ",
            r" /_[]_\ ",
            r"  /__\  ",
        ],
        2: [
            r"  /\_/\\",
            r" { O.O }",
            r"  > ^ < ",
        ],
    },
}


@dataclass(frozen=True)
class Room:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Position:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class Boss:
    name: str
    position: Position
    hp: int
    attack: int
    aggro_range: int = 5
    alert: bool = False
    max_hp: int | None = None
    intent_index: int = 0
    phase: int = 1

    def __post_init__(self) -> None:
        if self.max_hp is None:
            self.max_hp = self.hp


@dataclass
class GameState:
    width: int
    height: int
    player: Position
    exit: Position
    walls: set[Position] = field(default_factory=set)
    monsters: set[Position] = field(default_factory=set)
    potions: set[Position] = field(default_factory=set)
    treasures: set[Position] = field(default_factory=set)
    armor: set[Position] = field(default_factory=set)
    shrines: set[Position] = field(default_factory=set)
    secret_doors: set[Position] = field(default_factory=set)
    health: int = 12
    max_health: int = 12
    score: int = 0
    alive: bool = True
    won: bool = False
    rooms: list[Room] = field(default_factory=list)
    explored: set[Position] = field(default_factory=set)
    weapons: set[Position] = field(default_factory=set)
    keys: set[Position] = field(default_factory=set)
    inventory: dict[str, int] = field(
        default_factory=lambda: {"potions": 0, "keys": 0, "oro": 0}
    )
    attack: int = 2
    defense: int = 0
    bosses: dict[Position, Boss] = field(default_factory=dict)
    active_boss: Position | None = None
    dungeon_level: int = 1
    bosses_defeated: int = 0


def create_dungeon(seed: int | None = None, dungeon_level: int = 1) -> GameState:
    """Create a deterministic multi-room dungeon when a seed is provided."""
    rng = random.Random(seed)
    level_bonus = max(0, dungeon_level - 1)
    width = 40
    height = 18
    rooms = _generate_rooms(rng, width, height)
    floor = _carve_rooms_and_corridors(rooms)
    walls = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in floor
    }

    player = rooms[0].center
    exit_position = rooms[-1].center
    secret_doors = set(_secret_doors_for_rooms(rooms, max_doors=3))
    guaranteed_keys = _guaranteed_key_cells(
        rooms,
        len(secret_doors),
        occupied={player, exit_position, *secret_doors},
    )
    reserved_cells = {player, exit_position, *secret_doors, *guaranteed_keys}
    open_cells = [cell for cell in sorted(floor) if cell not in reserved_cells]
    rng.shuffle(open_cells)

    monster_count = min(12, 8 + level_bonus)
    potion_count = 5
    treasure_count = 5
    weapon_count = 2
    key_count = 4
    armor_count = 2
    shrine_count = 3

    cursor = 0
    monsters = set(open_cells[cursor : cursor + monster_count])
    cursor += monster_count
    potions = set(open_cells[cursor : cursor + potion_count])
    cursor += potion_count
    treasures = set(open_cells[cursor : cursor + treasure_count])
    cursor += treasure_count
    weapons = set(open_cells[cursor : cursor + weapon_count])
    cursor += weapon_count
    keys = set(guaranteed_keys)
    keys.update(open_cells[cursor : cursor + key_count])
    cursor += key_count
    armor = set(open_cells[cursor : cursor + armor_count])
    cursor += armor_count
    shrines = set(open_cells[cursor : cursor + shrine_count])

    boss_cells = [rooms[-2].center, rooms[-1].center]
    bosses = {
        boss_cells[0]: Boss(
            "Custode",
            boss_cells[0],
            hp=14 + 4 * level_bonus,
            attack=3 + level_bonus // 2,
            aggro_range=6,
        ),
        boss_cells[1]: Boss(
            "Re delle Sale",
            boss_cells[1],
            hp=22 + 6 * level_bonus,
            attack=4 + level_bonus,
            aggro_range=7,
        ),
    }
    for boss_cell in boss_cells:
        monsters.discard(boss_cell)
        potions.discard(boss_cell)
        treasures.discard(boss_cell)
        weapons.discard(boss_cell)
        keys.discard(boss_cell)
        armor.discard(boss_cell)
        shrines.discard(boss_cell)
        secret_doors.discard(boss_cell)

    state = GameState(
        width=width,
        height=height,
        player=player,
        exit=exit_position,
        walls=walls,
        monsters=monsters,
        potions=potions,
        treasures=treasures,
        weapons=weapons,
        keys=keys,
        armor=armor,
        shrines=shrines,
        secret_doors=secret_doors,
        bosses=bosses,
        rooms=rooms,
        health=16,
        max_health=16,
        dungeon_level=dungeon_level,
    )
    update_visibility(state)
    return state


def update_visibility(state: GameState, radius: int = VISION_RADIUS) -> None:
    px, py = state.player
    for y in range(py - radius, py + radius + 1):
        for x in range(px - radius, px + radius + 1):
            if 0 <= x < state.width and 0 <= y < state.height:
                if abs(px - x) + abs(py - y) <= radius:
                    state.explored.add((x, y))


def normalize_move_key(key: str) -> str | None:
    if not key:
        return None
    return KEY_ALIASES.get(key.strip().lower())


def current_intent(boss: Boss) -> str:
    phases = INTENT_CYCLES.get(boss.name, {})
    cycle = phases.get(boss.phase) or phases.get(1) or ("strike",)
    return cycle[boss.intent_index % len(cycle)]


def next_boss_intent(boss: Boss) -> str:
    """Compatibility name for the next visible boss action."""
    return current_intent(boss)


def shortest_step(
    state: GameState,
    start: Position,
    target: Position,
    allow_target_occupied: bool = False,
) -> Position:
    if start == target:
        return start

    target_blocked = (
        target in state.walls
        or target in state.secret_doors
        or target in state.monsters
        or (target in state.bosses and target != start)
    )
    if target_blocked and not allow_target_occupied:
        return start

    blocked = set(state.walls) | set(state.secret_doors) | set(state.monsters)
    blocked.update(position for position in state.bosses if position != start and position != target)
    if allow_target_occupied:
        blocked.discard(target)

    queue = deque([start])
    previous: dict[Position, Position | None] = {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == target:
            break
        for dx, dy in NEIGHBOR_STEPS:
            neighbor = (x + dx, y + dy)
            if neighbor in previous or neighbor in blocked:
                continue
            nx, ny = neighbor
            if 0 <= nx < state.width and 0 <= ny < state.height:
                previous[neighbor] = (x, y)
                queue.append(neighbor)

    if target not in previous:
        return start

    step = target
    while previous[step] != start:
        parent = previous[step]
        if parent is None:
            return start
        step = parent
    return step


def find_path(
    state: GameState,
    start: Position,
    target: Position,
    *,
    allow_target_occupied: bool = False,
) -> Position:
    """Return the next BFS step toward a target."""
    return shortest_step(
        state,
        start,
        target,
        allow_target_occupied=allow_target_occupied,
    )


def choose_portal_boon(choice: str, default: str = "health") -> str:
    """Map a portal prompt choice to a valid boon key."""
    return PORTAL_BOON_KEYS.get(choice.strip().lower(), default)


def apply_portal_boon(state: GameState, boon: str) -> None:
    if boon == "health":
        state.max_health += 4
        state.health = min(state.max_health, state.health + 4)
        return
    if boon == "attack":
        state.attack += 1
        return
    if boon == "defense":
        state.defense += 1
        return
    raise ValueError(f"Unknown portal boon: {boon}")


def move_player(
    state: GameState,
    direction: str,
    boon: str | None = None,
    next_seed: int | None = None,
) -> str:
    """Move the player one tile and resolve collisions."""
    command = normalize_move_key(direction) or direction.lower().strip()
    if state.active_boss is not None:
        return "Sei in battaglia: scegli attacca, difendi, pozione o fuggi."
    if not state.alive:
        return "Sei sconfitto e non puoi muoverti."
    if state.won:
        return "Hai gia trovato l'uscita."
    if command not in DIRECTIONS:
        return "Usa W, A, S o D per muoverti."

    dx, dy = DIRECTIONS[command]
    target = (state.player[0] + dx, state.player[1] + dy)
    messages: list[str] = []
    if target in state.secret_doors:
        state.inventory.setdefault("keys", 0)
        if state.inventory["keys"] <= 0:
            return "Un passaggio segreto e' chiuso. Serve una chiave."
        state.inventory["keys"] -= 1
        state.secret_doors.remove(target)
        messages.append("Apri un passaggio segreto con una chiave.")
    if _is_blocked(state, target):
        return "Sbatti contro un muro."
    if target in state.bosses:
        state.active_boss = target
        state.bosses[target].alert = True
        return f"{state.bosses[target].name} ti sfida. Inizia la battaglia!"
    if target == state.exit and state.bosses:
        return "L'uscita e' sigillata: sconfiggi prima i boss."

    if target in state.monsters:
        damage = max(1, MONSTER_DAMAGE - state.defense)
        state.health = max(0, state.health - damage)
        if state.health == 0:
            state.alive = False
            return "Un mostro ti ha sconfitto."
        state.monsters.remove(target)
        state.score += MONSTER_SCORE
        messages.append(f"Sconfiggi un mostro e subisci {damage} danni.")

    state.player = target
    messages.extend(_collect_items(state, target))

    if target == state.exit:
        if boon is not None:
            apply_portal_boon(state, boon)
            messages.append(PORTAL_BOONS[boon][1])
        next_level = state.dungeon_level + 1
        advance_to_next_dungeon(state, seed=next_seed)
        messages.append(f"Il portale si apre: scendi nel dungeon {next_level}.")

    update_visibility(state)
    return " ".join(messages) if messages else "Avanzi nel dungeon."


def advance_enemies(state: GameState) -> str:
    """Advance alert bosses toward the player."""
    messages: list[str] = []
    occupied = set(state.walls) | state.monsters | {state.player}
    new_bosses: dict[Position, Boss] = {}

    for position, boss in list(state.bosses.items()):
        boss.position = position
        distance = _distance(position, state.player)
        if distance <= boss.aggro_range:
            boss.alert = True
        if boss.alert:
            next_position = shortest_step(
                state,
                position,
                state.player,
                allow_target_occupied=True,
            )
            if next_position == state.player:
                state.active_boss = position
                boss.position = position
                new_bosses[position] = boss
                messages.append(f"{boss.name} ti raggiunge. Battaglia!")
            elif next_position not in occupied and next_position not in new_bosses:
                boss.position = next_position
                new_bosses[next_position] = boss
                messages.append(f"{boss.name} si avvicina.")
            else:
                new_bosses[position] = boss
        else:
            new_bosses[position] = boss

    state.bosses = new_bosses
    if state.active_boss is not None and state.active_boss not in state.bosses:
        for position, boss in state.bosses.items():
            if boss.alert and _distance(position, state.player) <= 1:
                state.active_boss = position
                break
    return " ".join(messages)


def battle_turn(state: GameState, action: str) -> str:
    if state.active_boss is None:
        return "Non sei in battaglia."
    boss = state.bosses[state.active_boss]
    _sync_boss_phase(boss)
    command = action.lower().strip()

    if command in {"a", "attacca"}:
        damage = state.attack
        if current_intent(boss) == "guard":
            damage = max(1, damage // 2)
        boss.hp -= damage
        if boss.hp <= 0:
            defeated_name = boss.name
            del state.bosses[state.active_boss]
            state.active_boss = None
            state.score += BOSS_SCORE
            state.bosses_defeated += 1
            if not state.bosses:
                return f"{defeated_name} sconfitto. Il sigillo dell'uscita si spezza."
            return f"{defeated_name} sconfitto. Il dungeon trema."
        _sync_boss_phase(boss)
        return f"Colpisci {boss.name} per {damage}. " + _boss_response(
            state,
            boss,
            defending=False,
        )

    if command in {"d", "difendi"}:
        return "Alzi la guardia. " + _boss_response(state, boss, defending=True)

    if command in {"p", "pozione"}:
        if state.inventory.get("potions", 0) <= 0:
            return "Non hai pozioni. " + _boss_response(state, boss, defending=False)
        state.inventory["potions"] -= 1
        before = state.health
        state.health = min(state.max_health, state.health + POTION_HEAL)
        healed = state.health - before
        return f"Bevi una pozione e recuperi {healed} HP. " + _boss_response(
            state, boss, defending=False
        )

    if command in {"f", "fuggi"}:
        state.active_boss = None
        return f"Ti sganci da {boss.name}, ma resta in allerta."

    return "Comando battaglia non valido."


def render_dungeon(state: GameState, use_fog: bool = False) -> str:
    """Render the dungeon as an ASCII grid."""
    rows: list[str] = []
    for y in range(state.height):
        cells: list[str] = []
        for x in range(state.width):
            position = (x, y)
            if use_fog and position not in state.explored:
                cells.append(UNKNOWN)
            else:
                cells.append(_tile_at(state, position))
        rows.append("".join(cells))
    return "\n".join(rows)


def advance_to_next_dungeon(state: GameState, seed: int | None = None) -> None:
    """Mutate state into the next dungeon while preserving player progression."""
    next_level = state.dungeon_level + 1
    carried_inventory = dict(state.inventory)
    for key in ("potions", "keys", "oro"):
        carried_inventory.setdefault(key, 0)
    carried_attack = state.attack
    carried_defense = state.defense
    carried_max_health = state.max_health
    carried_health = state.health
    carried_score = state.score + EXIT_SCORE
    carried_bosses_defeated = state.bosses_defeated

    next_state = create_dungeon(seed=seed, dungeon_level=next_level)
    next_state.inventory = carried_inventory
    next_state.attack = carried_attack
    next_state.defense = carried_defense
    next_state.max_health = carried_max_health
    next_state.health = min(
        carried_max_health,
        max(carried_health + POTION_HEAL, carried_max_health // 2),
    )
    next_state.score = carried_score
    next_state.bosses_defeated = carried_bosses_defeated

    state.__dict__.update(next_state.__dict__)
    update_visibility(state)


def play() -> None:
    """Run the interactive dungeon game."""
    state = create_dungeon()
    message = "Esplora le sale. I boss ti sentono se ti avvicini."

    while state.alive and not state.won:
        clear_screen()
        if state.active_boss is not None:
            print(_render_battle_screen(state, message))
            command = read_key(color("\n[A]ttacca [D]ifendi [P]ozione [F]uggi > ", "yellow"), default="f")
            message = battle_turn(state, command)
            continue

        print(_render_screen(state, message))
        command = read_key(color("\n> ", "yellow"), default="q").strip().lower()
        if command in {"q", "quit", "exit"}:
            print(color("Ti ritiri dal dungeon.", "magenta"))
            return
        boon = None
        if _is_unlocked_exit_move(state, command):
            boon_key = read_key(
                color("\nPortale [H/A/D] > ", "yellow"),
                default="h",
            ).strip().lower()
            boon = choose_portal_boon(boon_key)
        message = move_player(state, command, boon=boon)
        if state.alive and not state.won and state.active_boss is None:
            enemy_message = advance_enemies(state)
            if enemy_message:
                message = f"{message} {enemy_message}"

    clear_screen()
    print(_render_screen(state, "Vittoria!" if state.won else "Game over."))
    _record_completed_run(state)
    if state.won:
        print(color("Sei scappato dal dungeon.", "green"))
    else:
        print(color("Il dungeon si prende un altro avventuriero.", "red"))


def main() -> None:
    play()


def _generate_rooms(rng: random.Random, width: int, height: int) -> list[Room]:
    rooms: list[Room] = []
    attempts = 0
    while len(rooms) < 7 and attempts < 200:
        attempts += 1
        room_width = rng.randint(5, 8)
        room_height = rng.randint(3, 5)
        x = rng.randint(1, width - room_width - 2)
        y = rng.randint(1, height - room_height - 2)
        room = Room(x, y, room_width, room_height)
        if all(not _rooms_overlap(room, other) for other in rooms):
            rooms.append(room)
    if len(rooms) < 5:
        rooms = [
            Room(2, 2, 7, 4),
            Room(13, 2, 7, 4),
            Room(25, 3, 8, 4),
            Room(8, 10, 7, 5),
            Room(23, 11, 8, 4),
        ]
    rooms.sort(key=lambda room: room.center)
    return rooms


def _carve_rooms_and_corridors(rooms: list[Room]) -> set[Position]:
    floor: set[Position] = set()
    for room in rooms:
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                floor.add((x, y))
    for left, right in zip(rooms, rooms[1:]):
        floor.update(_corridor(left.center, right.center))
    return floor


def _corridor(start: Position, end: Position) -> set[Position]:
    return set(_corridor_path(start, end))


def _corridor_path(start: Position, end: Position) -> list[Position]:
    floor: list[Position] = []
    x, y = start
    end_x, end_y = end
    step_x = 1 if end_x >= x else -1
    while x != end_x:
        floor.append((x, y))
        x += step_x
    step_y = 1 if end_y >= y else -1
    while y != end_y:
        floor.append((x, y))
        y += step_y
    floor.append(end)
    return floor


def _secret_doors_for_rooms(rooms: list[Room], max_doors: int) -> list[Position]:
    doors: list[Position] = []
    used: set[Position] = set()
    for left, right in list(zip(rooms, rooms[1:]))[:max_doors]:
        path = _corridor_path(left.center, right.center)
        candidates = [
            cell
            for cell in path
            if cell not in used and not any(_position_in_room(cell, room) for room in rooms)
        ]
        if not candidates:
            candidates = [
                cell
                for cell in path
                if cell not in used and cell not in {left.center, right.center}
            ]
        if candidates:
            door = candidates[len(candidates) // 2]
            doors.append(door)
            used.add(door)
    return doors


def _guaranteed_key_cells(
    rooms: list[Room],
    key_count: int,
    occupied: set[Position],
) -> set[Position]:
    keys: set[Position] = set()
    for index in range(key_count):
        room = rooms[min(index, len(rooms) - 1)]
        center = room.center
        candidates = sorted(
            _room_cells(room),
            key=lambda cell: (abs(cell[0] - center[0]) + abs(cell[1] - center[1]), cell),
        )
        for candidate in candidates:
            if candidate not in occupied:
                keys.add(candidate)
                occupied.add(candidate)
                break
    return keys


def _room_cells(room: Room) -> set[Position]:
    return {
        (x, y)
        for y in range(room.y, room.y + room.height)
        for x in range(room.x, room.x + room.width)
    }


def _position_in_room(position: Position, room: Room) -> bool:
    x, y = position
    return room.x <= x < room.x + room.width and room.y <= y < room.y + room.height


def _rooms_overlap(first: Room, second: Room) -> bool:
    return not (
        first.x + first.width + 1 < second.x
        or second.x + second.width + 1 < first.x
        or first.y + first.height + 1 < second.y
        or second.y + second.height + 1 < first.y
    )


def _collect_items(state: GameState, target: Position) -> list[str]:
    messages: list[str] = []
    state.inventory.setdefault("potions", 0)
    state.inventory.setdefault("keys", 0)
    state.inventory.setdefault("oro", 0)

    if target in state.potions:
        state.potions.remove(target)
        state.inventory["potions"] += 1
        before = state.health
        state.health = min(state.max_health, state.health + POTION_HEAL)
        healed = state.health - before
        messages.append(f"Bevi una pozione e recuperi {healed} HP.")

    if target in state.treasures:
        state.treasures.remove(target)
        state.inventory["oro"] += TREASURE_SCORE
        state.score += TREASURE_SCORE
        messages.append(f"Raccogli un tesoro da {TREASURE_SCORE} punti.")

    if target in state.weapons:
        state.weapons.remove(target)
        state.attack += 2
        messages.append("Trovi una lama antica. Attacco +2.")

    if target in state.keys:
        state.keys.remove(target)
        state.inventory["keys"] += 1
        messages.append("Raccogli una chiave consumata.")

    if target in state.armor:
        state.armor.remove(target)
        state.max_health += ARMOR_HEALTH_BONUS
        state.health = min(state.max_health, state.health + ARMOR_HEALTH_BONUS)
        state.defense += ARMOR_DEFENSE_BONUS
        messages.append("Indossi una corazza runica. Vita e difesa aumentano.")

    if target in state.shrines:
        state.shrines.remove(target)
        healed = state.max_health - state.health
        state.health = state.max_health
        messages.append(f"Una fontana ti rigenera: recuperi {healed} HP.")

    return messages


def _boss_response(state: GameState, boss: Boss, defending: bool) -> str:
    intent = current_intent(boss)
    response: str
    if intent == "guard":
        response = f"{boss.name} si chiude in guardia."
    elif intent == "charge":
        response = f"{boss.name} carica potere."
    else:
        heavy = intent == "heavy"
        response = _boss_counterattack(state, boss, defending, heavy=heavy)
        if heavy and state.alive:
            response = f"Colpo pesante. {response}"
    boss.intent_index += 1
    return response


def _boss_counterattack(state: GameState, boss: Boss, defending: bool, heavy: bool = False) -> str:
    base_damage = boss.attack + 2 if heavy else boss.attack
    damage = max(1, base_damage - state.defense)
    if defending:
        damage = max(1, damage // 2)
    state.health = max(0, state.health - damage)
    if state.health == 0:
        state.alive = False
        state.active_boss = None
        return f"{boss.name} ti manda al tappeto."
    return f"{boss.name} risponde: -{damage} HP."


def _is_blocked(state: GameState, position: Position) -> bool:
    x, y = position
    return (
        x < 0
        or x >= state.width
        or y < 0
        or y >= state.height
        or position in state.walls
    )


def _distance(left: Position, right: Position) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _sync_boss_phase(boss: Boss) -> None:
    if boss.name == "Re delle Sale" and boss.phase < 2 and boss.hp <= boss.max_hp // 2:
        boss.phase = 2
        boss.intent_index = 0


def _step_toward(start: Position, target: Position) -> Position:
    x, y = start
    tx, ty = target
    if abs(tx - x) >= abs(ty - y) and tx != x:
        return (x + (1 if tx > x else -1), y)
    if ty != y:
        return (x, y + (1 if ty > y else -1))
    return start


def _tile_at(state: GameState, position: Position) -> str:
    if position == state.player:
        return PLAYER
    if position == state.exit:
        return EXIT
    if position in state.walls:
        return WALL
    if position in state.bosses:
        return BOSS
    if position in state.monsters:
        return MONSTER
    if position in state.potions:
        return POTION
    if position in state.treasures:
        return TREASURE
    if position in state.weapons:
        return WEAPON
    if position in state.keys:
        return KEY
    if position in state.armor:
        return ARMOR
    if position in state.shrines:
        return SHRINE
    if position in state.secret_doors:
        return SECRET_DOOR
    return FLOOR


def _render_screen(state: GameState, message: str) -> str:
    status = (
        f"Liv {state.dungeon_level}  HP {state.health}/{state.max_health}  "
        f"ATK {state.attack}  DEF {state.defense}  "
        f"Pozioni {state.inventory.get('potions', 0)}  Chiavi {state.inventory.get('keys', 0)}  "
        f"Score {state.score}"
    )
    legend_one = "@ tu  # muro  ? ignoto  M mostro  B boss"
    legend_two = "+ pozione  / lama  ] corazza  ^ fontana"
    legend_three = "k chiave  D porta segreta  $ oro  > portale"
    lines = render_dungeon(state, use_fog=True).splitlines()
    lines.extend(["", status, message, "", legend_one, legend_two, legend_three, "WASD/frecce: muovi   Q: esci"])
    return color(frame("DUNGEON", lines, width=88), "cyan")


def _render_battle_screen(state: GameState, message: str) -> str:
    boss = state.bosses[state.active_boss] if state.active_boss is not None else None
    boss_line = "Nessun boss"
    portrait: list[str] = []
    intent_line = "Intento: -"
    if boss is not None:
        _sync_boss_phase(boss)
        phase_marker = f"  FASE {boss.phase}" if boss.phase > 1 else ""
        boss_line = f"{boss.name}{phase_marker} HP {boss.hp}/{boss.max_hp}  ATK {boss.attack}"
        portrait = BOSS_PORTRAITS.get(boss.name, {}).get(
            boss.phase,
            BOSS_PORTRAITS.get(boss.name, {}).get(1, []),
        )
        intent_line = f"Intento: {current_intent(boss)}"
    lines = [
        boss_line,
        intent_line,
        f"Tu HP {state.health}/{state.max_health}  ATK {state.attack}  DEF {state.defense}",
        "",
        *portrait,
        *([] if not portrait else [""]),
        message,
        "",
        "[A]ttacca  [D]ifendi  [P]ozione  [F]uggi",
    ]
    return color(frame("BATTAGLIA", lines, width=72), "magenta")


def _is_unlocked_exit_move(state: GameState, command: str) -> bool:
    normalized = normalize_move_key(command) or command.lower().strip()
    if normalized not in DIRECTIONS or state.bosses:
        return False
    dx, dy = DIRECTIONS[normalized]
    return (state.player[0] + dx, state.player[1] + dy) == state.exit


def _record_completed_run(state: GameState, stats: dict | None = None) -> None:
    if state.alive and not state.won:
        return
    game_stats = stats if stats is not None else load_stats()
    record_outcome(game_stats, "dungeon", won=state.won)
    record_metric(game_stats, "dungeon", "best_score", state.score)
    record_metric(game_stats, "dungeon", "deepest_level", state.dungeon_level)
    record_metric(game_stats, "dungeon", "bosses_defeated", state.bosses_defeated)
    if stats is None:
        save_stats(game_stats)


if __name__ == "__main__":
    main()

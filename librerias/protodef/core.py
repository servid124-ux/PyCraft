"""
protodef/core.py

Motor central de la librería. La clase Protocol carga un protocol.json
(o un dict de tipos equivalente) y sabe:

    protocol.read_type(type_def, reader, scope, fields)   -> valor python
    protocol.write_type(type_def, value, writer, scope, fields)

    protocol.parse_packet(state, direction, data: bytes) -> ParsedPacket
    protocol.serialize_packet(state, direction, name, params: dict) -> bytes

Tipos compuestos soportados (definidos como ["tipoBase", opciones]):
    container       - lista ordenada de campos con nombre
    array           - lista homogénea, con count fijo, countType, o
                       count-referenciando-otro-campo
    switch          - elige el tipo según el valor de otro campo (compareTo)
    mapper          - traduce un entero crudo a un nombre simbólico (y viceversa)
    option          - valor opcional precedido por un bool ("presente?")
    bitfield        - empaqueta/desempaqueta sub-campos de N bits cada uno
    bitflags        - entero interpretado como conjunto de flags con nombre
    buffer          - bytes crudos, con longitud fija o por countType/count
    pstring         - string con longitud prefijada por countType (varint, u16, etc)
    entityMetadataLoop - lista de entradas hasta encontrar un terminador
    topBitSetTerminatedArray - lista que termina cuando el bit más alto del
                       primer byte leído en una entrada NO está seteado
                       (patrón de listas LEB128-like)

Los tipos primitivos (varint, i32, bool, cstring, etc.) viven en
primitives.py y se resuelven por nombre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .io import Reader, Writer
from .primitives import PRIMITIVES
from .conditions import eval_condition
from .errors import (
    UnknownTypeError,
    InvalidTypeDefinition,
    SwitchCaseNotFound,
)

TypeDef = Any  # str | [str, dict] -- no tipamos más estricto por simplicidad


@dataclass
class ParsedPacket:
    name: str
    params: dict[str, Any]
    bytes_read: int


@dataclass
class Scope:
    """Representa un 'state.direction' (p.ej. play.toClient) con sus tipos propios,
    que tienen prioridad sobre los tipos globales del protocolo."""

    types: dict[str, TypeDef] = field(default_factory=dict)


class Protocol:
    """
    Carga y representa un protocol.json completo.

    Estructura esperada del dict de entrada (mismo formato que
    node-minecraft-protocol / node-protodef):

        {
          "types": { "<nombre>": <typeDef>, ... },
          "<state>": {
             "toClient": { "types": { ... } },
             "toServer": { "types": { ... } }
          },
          ...
        }

    Los nombres de tipo se resuelven primero contra el scope local
    (state.direction.types) y si no aparecen ahí, contra los tipos globales.
    """

    def __init__(self, protocol_json: dict[str, Any]):
        self.raw = protocol_json
        self.global_types: dict[str, TypeDef] = protocol_json.get("types", {})
        self._scopes: dict[tuple[str, str], Scope] = {}

        for state_name, state_val in protocol_json.items():
            if state_name == "types" or not isinstance(state_val, dict):
                continue
            for direction in ("toClient", "toServer"):
                if direction in state_val:
                    self._scopes[(state_name, direction)] = Scope(
                        types=state_val[direction].get("types", {})
                    )

        self._composite_handlers: dict[str, Callable] = {
            "container": self._read_container,
            "array": self._read_array,
            "switch": self._read_switch,
            "mapper": self._read_mapper,
            "option": self._read_option,
            "bitfield": self._read_bitfield,
            "bitflags": self._read_bitflags,
            "buffer": self._read_buffer,
            "pstring": self._read_pstring,
            "entityMetadataLoop": self._read_entity_metadata_loop,
            "topBitSetTerminatedArray": self._read_top_bit_set_terminated_array,
        }
        self._composite_write_handlers: dict[str, Callable] = {
            "container": self._write_container,
            "array": self._write_array,
            "switch": self._write_switch,
            "mapper": self._write_mapper,
            "option": self._write_option,
            "bitfield": self._write_bitfield,
            "bitflags": self._write_bitflags,
            "buffer": self._write_buffer,
            "pstring": self._write_pstring,
            "entityMetadataLoop": self._write_entity_metadata_loop,
            "topBitSetTerminatedArray": self._write_top_bit_set_terminated_array,
        }

    # -------------------------------------------------------------------
    # Resolución de nombres de tipo
    # -------------------------------------------------------------------

    def get_scope(self, state: str, direction: str) -> Scope:
        try:
            return self._scopes[(state, direction)]
        except KeyError:
            raise UnknownTypeError(f"{state}.{direction} (state/direction no definido)")

    def _resolve_named_type(self, name: str, scope: Scope | None) -> TypeDef | None:
        if scope is not None and name in scope.types:
            return scope.types[name]
        if name in self.global_types:
            return self.global_types[name]
        return None

    # -------------------------------------------------------------------
    # Lectura
    # -------------------------------------------------------------------

    def read_type(self, type_def: TypeDef, r: Reader, scope: Scope | None,
                   fields: dict[str, Any], root: dict | None = None,
                   parent: dict | None = None) -> Any:
        if isinstance(type_def, str):
            if type_def in PRIMITIVES:
                return PRIMITIVES[type_def].read(r)
            resolved = self._resolve_named_type(type_def, scope)
            if resolved is None:
                raise UnknownTypeError(type_def)
            return self.read_type(resolved, r, scope, fields, root, parent)

        if isinstance(type_def, list) and len(type_def) == 2:
            base, opts = type_def
            handler = self._composite_handlers.get(base)
            if handler is None:
                raise UnknownTypeError(f"(tipo base compuesto) {base}")
            return handler(opts, r, scope, fields, root, parent)

        raise InvalidTypeDefinition(type_def)

    # ---- container ------------------------------------------------------

    def _read_container(self, opts: list[dict], r: Reader, scope: Scope,
                          fields: dict, root: dict | None, parent: dict | None) -> dict:
        result: dict[str, Any] = {}
        effective_root = root if root is not None else result
        for f in opts:
            if "condition" in f:
                if not eval_condition(f["condition"], result, effective_root, fields):
                    continue
            value = self.read_type(f["type"], r, scope, result, effective_root, result)
            if f.get("anon"):
                if isinstance(value, dict):
                    result.update(value)
            else:
                result[f["name"]] = value
        return result

    def _write_container(self, opts: list[dict], value: dict, w: Writer, scope: Scope,
                           fields: dict, root: dict | None, parent: dict | None) -> None:
        data = value or {}
        effective_root = root if root is not None else data
        for f in opts:
            if "condition" in f:
                if not eval_condition(f["condition"], data, effective_root, fields):
                    continue
            if f.get("anon"):
                self.write_type(f["type"], data, w, scope, data, effective_root, data)
            else:
                self.write_type(f["type"], data.get(f["name"]), w, scope, data, effective_root, data)

    # ---- array ------------------------------------------------------------

    def _read_array(self, opts: dict, r: Reader, scope: Scope,
                      fields: dict, root, parent) -> list:
        if "count" in opts:
            count = fields[opts["count"]]
        elif "countType" in opts:
            count = self.read_type(opts["countType"], r, scope, fields, root, parent)
        else:
            raise InvalidTypeDefinition("array requiere 'count' o 'countType'")

        item_type = opts["type"]
        return [self.read_type(item_type, r, scope, fields, root, parent) for _ in range(count)]

    def _write_array(self, opts: dict, value: list, w: Writer, scope: Scope,
                       fields: dict, root, parent) -> None:
        items = value or []
        if "countType" in opts:
            self.write_type(opts["countType"], len(items), w, scope, fields, root, parent)
        # si usa "count" (referencia a otro campo), el caller debe haber
        # escrito ese campo antes (responsabilidad del container que arma 'fields')
        item_type = opts["type"]
        for item in items:
            self.write_type(item_type, item, w, scope, fields, root, parent)

    # ---- switch -------------------------------------------------------------

    def _resolve_compare_value(self, opts: dict, fields: dict, root, parent) -> Any:
        compare_to = opts["compareTo"]
        if compare_to.startswith("fields."):
            return eval_condition(compare_to, fields, root, parent)
        if compare_to in fields:
            return fields[compare_to]
        try:
            return eval_condition(compare_to, fields, root, parent)
        except Exception:
            return None

    def _read_switch(self, opts: dict, r: Reader, scope: Scope,
                       fields: dict, root, parent) -> Any:
        compare_val = self._resolve_compare_value(opts, fields, root, parent)
        case_key = str(compare_val) if not isinstance(compare_val, str) else compare_val
        case_type = opts["fields"].get(case_key, opts["fields"].get(compare_val))
        if case_type is None:
            if "default" in opts:
                return self.read_type(opts["default"], r, scope, fields, root, parent)
            raise SwitchCaseNotFound(opts["compareTo"], compare_val)
        return self.read_type(case_type, r, scope, fields, root, parent)

    def _write_switch(self, opts: dict, value: Any, w: Writer, scope: Scope,
                        fields: dict, root, parent) -> None:
        compare_val = self._resolve_compare_value(opts, fields, root, parent)
        case_key = str(compare_val) if not isinstance(compare_val, str) else compare_val
        case_type = opts["fields"].get(case_key, opts["fields"].get(compare_val))
        if case_type is None:
            if "default" in opts:
                return self.write_type(opts["default"], value, w, scope, fields, root, parent)
            raise SwitchCaseNotFound(opts["compareTo"], compare_val)
        return self.write_type(case_type, value, w, scope, fields, root, parent)

    # ---- mapper (entero <-> nombre simbólico) --------------------------------

    def _read_mapper(self, opts: dict, r: Reader, scope: Scope,
                       fields: dict, root, parent) -> Any:
        raw = self.read_type(opts["type"], r, scope, fields, root, parent)
        mappings = opts["mappings"]
        # normalizamos las keys del mapping (que pueden venir como "0x00",
        # "0x1f", "31", etc.) a entero, para no depender del formato exacto
        # con el que esté escrito el protocol.json
        for key, mapped_name in mappings.items():
            key_int = int(key, 16) if key.lower().startswith("0x") else int(key)
            if key_int == raw:
                return mapped_name
        return raw  # sin mapping conocido: se devuelve el valor crudo

    def _write_mapper(self, opts: dict, value: Any, w: Writer, scope: Scope,
                        fields: dict, root, parent) -> None:
        mappings = opts["mappings"]
        if isinstance(value, str):
            numeric = None
            for k, v in mappings.items():
                if v == value:
                    numeric = int(k, 16) if k.startswith("0x") else int(k)
                    break
            if numeric is None:
                raise InvalidTypeDefinition(
                    f"mapper: no se encontró mapping inverso para {value!r}"
                )
        else:
            numeric = value
        self.write_type(opts["type"], numeric, w, scope, fields, root, parent)

    # ---- option (presente si un bool previo es true) -------------------------

    def _read_option(self, opts: TypeDef, r: Reader, scope: Scope,
                       fields: dict, root, parent) -> Any:
        present = PRIMITIVES["bool"].read(r)
        if not present:
            return None
        return self.read_type(opts, r, scope, fields, root, parent)

    def _write_option(self, opts: TypeDef, value: Any, w: Writer, scope: Scope,
                        fields: dict, root, parent) -> None:
        present = value is not None
        PRIMITIVES["bool"].write(present, w)
        if present:
            self.write_type(opts, value, w, scope, fields, root, parent)

    # ---- bitfield (sub-campos empaquetados en N bits) -------------------------

    def _read_bitfield(self, opts: list[dict], r: Reader, scope: Scope,
                         fields: dict, root, parent) -> dict:
        total_bits = sum(f["size"] for f in opts)
        if total_bits % 8 != 0:
            raise InvalidTypeDefinition("bitfield: total de bits debe ser múltiplo de 8")
        num_bytes = total_bits // 8
        raw_bytes = r.read_bytes(num_bytes)
        big = int.from_bytes(raw_bytes, "big")

        result: dict[str, Any] = {}
        bits_left = total_bits
        for f in opts:
            bits_left -= f["size"]
            mask = (1 << f["size"]) - 1
            val = (big >> bits_left) & mask
            if f.get("signed") and val >= (1 << (f["size"] - 1)):
                val -= 1 << f["size"]
            result[f["name"]] = val
        return result

    def _write_bitfield(self, opts: list[dict], value: dict, w: Writer, scope: Scope,
                          fields: dict, root, parent) -> None:
        total_bits = sum(f["size"] for f in opts)
        num_bytes = total_bits // 8
        big = 0
        for f in opts:
            v = value.get(f["name"], 0) & ((1 << f["size"]) - 1)
            big = (big << f["size"]) | v
        w.write_bytes(big.to_bytes(num_bytes, "big"))

    # ---- bitflags (entero como set de flags con nombre) ------------------------

    def _read_bitflags(self, opts: dict, r: Reader, scope: Scope,
                         fields: dict, root, parent) -> dict[str, bool]:
        raw = self.read_type(opts["type"], r, scope, fields, root, parent)
        flag_names: list[str] = opts["flags"]
        big_endian = opts.get("big", False)
        result: dict[str, bool] = {}
        names = list(reversed(flag_names)) if big_endian else flag_names
        for i, flag_name in enumerate(names):
            if flag_name is None:
                continue
            result[flag_name] = bool((raw >> i) & 1)
        return result

    def _write_bitflags(self, opts: dict, value: dict, w: Writer, scope: Scope,
                          fields: dict, root, parent) -> None:
        flag_names: list[str] = opts["flags"]
        big_endian = opts.get("big", False)
        names = list(reversed(flag_names)) if big_endian else flag_names
        raw = 0
        for i, flag_name in enumerate(names):
            if flag_name is None:
                continue
            if value.get(flag_name):
                raw |= (1 << i)
        self.write_type(opts["type"], raw, w, scope, fields, root, parent)

    # ---- buffer (bytes crudos) ------------------------------------------------

    def _read_buffer(self, opts: dict, r: Reader, scope: Scope,
                       fields: dict, root, parent) -> bytes:
        if "count" in opts:
            count = fields[opts["count"]]
        elif "countType" in opts:
            count = self.read_type(opts["countType"], r, scope, fields, root, parent)
        elif opts.get("rest"):
            count = r.remaining
        else:
            raise InvalidTypeDefinition("buffer requiere 'count', 'countType' o 'rest'")
        return r.read_bytes(count)

    def _write_buffer(self, opts: dict, value: bytes, w: Writer, scope: Scope,
                        fields: dict, root, parent) -> None:
        data = value or b""
        if "countType" in opts:
            self.write_type(opts["countType"], len(data), w, scope, fields, root, parent)
        w.write_bytes(data)

    # ---- pstring (string con longitud prefijada configurable) -----------------

    def _read_pstring(self, opts: dict, r: Reader, scope: Scope,
                        fields: dict, root, parent) -> str:
        count_type = opts.get("countType", "varint")
        encoding = opts.get("encoding", "utf-8")
        if "count" in opts:
            length = fields[opts["count"]]
        else:
            length = self.read_type(count_type, r, scope, fields, root, parent)
        data = r.read_bytes(length)
        return data.decode(encoding)

    def _write_pstring(self, opts: dict, value: str, w: Writer, scope: Scope,
                         fields: dict, root, parent) -> None:
        count_type = opts.get("countType", "varint")
        encoding = opts.get("encoding", "utf-8")
        data = value.encode(encoding)
        if "count" not in opts:
            self.write_type(count_type, len(data), w, scope, fields, root, parent)
        w.write_bytes(data)

    # ---- entityMetadataLoop (lista hasta encontrar terminador) -----------------

    def _read_entity_metadata_loop(self, opts: dict, r: Reader, scope: Scope,
                                      fields: dict, root, parent) -> list:
        """
        opts:
          endVal: valor (int) que indica fin de la lista al leerlo como `endType`
          endType: tipo a usar para leer el "índice" de cada entrada (default 'u8')
          type: tipo del resto de cada entrada (se lee solo si el índice leído
                no es el terminador). Recibe fields={'index': <índice leído>}.

        Cada entrada resultante queda como {'index': N, ...resto de campos}.
        """
        end_val = opts.get("endVal", 0xFF)
        end_type = opts.get("endType", "u8")
        item_type = opts["type"]

        result = []
        while True:
            index = self.read_type(end_type, r, scope, fields, root, parent)
            if index == end_val:
                break
            entry_fields = {"index": index}
            entry = self.read_type(item_type, r, scope, entry_fields, root, parent)
            if isinstance(entry, dict):
                entry = {"index": index, **entry}
            else:
                entry = {"index": index, "value": entry}
            result.append(entry)
        return result

    def _is_container_type(self, type_def: TypeDef, scope: Scope) -> bool:
        """Resuelve (sin leer/escribir bytes) si un tipo es, en el fondo, un
        container -- para saber si una entrada de entityMetadataLoop debe
        pasarse como dict completo o desenvuelta en 'value'."""
        seen: set[str] = set()
        current = type_def
        while isinstance(current, str):
            if current in seen:
                return False  # ciclo raro, no asumimos container
            seen.add(current)
            if current in PRIMITIVES:
                return False
            resolved = self._resolve_named_type(current, scope)
            if resolved is None:
                return False
            current = resolved
        if isinstance(current, list) and len(current) == 2:
            return current[0] == "container"
        return False

    def _write_entity_metadata_loop(self, opts: dict, value: list, w: Writer, scope: Scope,
                                       fields: dict, root, parent) -> None:
        end_val = opts.get("endVal", 0xFF)
        end_type = opts.get("endType", "u8")
        item_type = opts["type"]
        is_container = self._is_container_type(item_type, scope)

        for entry in (value or []):
            index = entry["index"]
            self.write_type(end_type, index, w, scope, fields, root, parent)
            rest = {k: v for k, v in entry.items() if k != "index"}
            payload = rest if is_container else rest.get("value")
            self.write_type(item_type, payload, w, scope, {"index": index}, root, parent)
        self.write_type(end_type, end_val, w, scope, fields, root, parent)

    # ---- topBitSetTerminatedArray ------------------------------------------------

    def _read_top_bit_set_terminated_array(self, opts: dict, r: Reader, scope: Scope,
                                              fields: dict, root, parent) -> list:
        """
        Lee entradas de `type` mientras el bit más alto (0x80) del PRIMER byte
        de cada entrada esté seteado. Patrón típico de listas LEB128-like
        en RakNet / formatos custom (cada entrada "anuncia" si hay otra después).
        """
        item_type = opts["type"]
        result = []
        while True:
            start_offset = r.offset
            item = self.read_type(item_type, r, scope, fields, root, parent)
            result.append(item)
            first_byte = r.buffer[start_offset]
            if not (first_byte & 0x80):
                break
        return result

    def _write_top_bit_set_terminated_array(self, opts: dict, value: list, w: Writer, scope: Scope,
                                               fields: dict, root, parent) -> None:
        """
        Al escribir, el llamador es responsable de que cada item ya traiga el
        bit alto seteado salvo el último (esto refleja el protocolo real: el
        marcador de continuación suele ser parte de los datos del propio item,
        no algo que este wrapper pueda inventar).
        """
        item_type = opts["type"]
        items = value or []
        for item in items:
            self.write_type(item_type, item, w, scope, fields, root, parent)

    # -------------------------------------------------------------------
    # Escritura
    # -------------------------------------------------------------------

    def write_type(self, type_def: TypeDef, value: Any, w: Writer, scope: Scope | None,
                    fields: dict[str, Any], root: dict | None = None,
                    parent: dict | None = None) -> None:
        if isinstance(type_def, str):
            if type_def in PRIMITIVES:
                PRIMITIVES[type_def].write(value, w)
                return
            resolved = self._resolve_named_type(type_def, scope)
            if resolved is None:
                raise UnknownTypeError(type_def)
            return self.write_type(resolved, value, w, scope, fields, root, parent)

        if isinstance(type_def, list) and len(type_def) == 2:
            base, opts = type_def
            handler = self._composite_write_handlers.get(base)
            if handler is None:
                raise UnknownTypeError(f"(tipo base compuesto) {base}")
            return handler(opts, value, w, scope, fields, root, parent)

        raise InvalidTypeDefinition(type_def)

    # -------------------------------------------------------------------
    # API de alto nivel: paquetes completos
    # -------------------------------------------------------------------

    def parse_packet(self, state: str, direction: str, data: bytes) -> ParsedPacket:
        scope = self.get_scope(state, direction)
        r = Reader(data)
        packet = self.read_type("packet", r, scope, {})
        return ParsedPacket(name=packet["name"], params=packet["params"], bytes_read=r.offset)

    def serialize_packet(self, state: str, direction: str, name: str, params: dict) -> bytes:
        scope = self.get_scope(state, direction)
        w = Writer()
        self.write_type("packet", {"name": name, "params": params}, w, scope, {})
        return w.result()

    # acceso directo a un tipo nombrado (sin pasar por "packet"), útil para tests
    # y para parsear/serializar sub-estructuras sueltas (p.ej. un slot, un NBT)
    def read_named(self, state: str, direction: str, type_name: str, data: bytes) -> Any:
        scope = self.get_scope(state, direction)
        r = Reader(data)
        return self.read_type(type_name, r, scope, {})

    def write_named(self, state: str, direction: str, type_name: str, value: Any) -> bytes:
        scope = self.get_scope(state, direction)
        w = Writer()
        self.write_type(type_name, value, w, scope, {})
        return w.result()

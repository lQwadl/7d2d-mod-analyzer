from collections import defaultdict

SAFE_ATTRIBUTE_SPLITS = {
    # node_type base -> safe attribute names
    "lootgroup": {"prob", "count", "qualitytemplate"},
    "item": {"quality", "count", "stacksize"},
}


def _node_from_target(target):
    # target examples: 'item:gunAK47/property:Quality' or 'item:gunAK47/attr:prob'
    parts = target.split("/")
    node = parts[0]  # 'item:gunAK47'
    quals = parts[1:] if len(parts) > 1 else []
    return node, quals


def _intent_severity(intent_a: str, intent_b: str):
    pair = {intent_a, intent_b}
    if intent_a == intent_b == "extend":
        return "safe"
    if "extend" in pair and ("override" in pair or "replace" in pair):
        return "warn"  # override vs extend
    if intent_a == intent_b == "override":
        return "error"  # competing set
    if intent_a == intent_b == "replace":
        return "error"
    if "remove" in pair and ("reference" in pair or "extend" in pair or "override" in pair):
        return "error"  # remove vs any
    # default conservative warn when both modify
    if intent_a != intent_b:
        return "warn"
    return "info"


def detect_conflicts(mods):
    # Clear existing conflicts
    for mod in mods:
        mod.conflicts = []

    def _is_patch(mod) -> bool:
        try:
            if getattr(mod, "is_patch", False):
                return True
            nm = (getattr(mod, "name", "") or "").lower()
            return nm.startswith("999_conflictpatch_") or nm.startswith("conflictpatch_")
        except Exception:
            return False

    def _is_ui_xml_file(file_key: str) -> bool:
        """Return True for XUi/XUI_* UI XML files.

        The game error reported by the user references paths like:
          XUI_Common/styles.xml
          XUI_Menu/controls.xml

        Our analyzer normalizes to lowercase forward-slash paths.
        """

        try:
            fk = str(file_key or "").replace("\\", "/").lower()
        except Exception:
            fk = ""
        if not fk:
            return False
        if fk == "ui.xml" or fk == "windows.xml":
            return True
        if fk.startswith("xui/") or "/xui/" in fk:
            return True
        if fk.startswith("xui_") or "/xui_" in fk:
            return True
        if "xui" in fk and fk.endswith("styles.xml"):
            return True
        if "xui" in fk and fk.endswith("controls.xml"):
            return True
        return False

    def _ui_xml_patch_suggestion(file_key: str) -> str:
        try:
            pretty = str(file_key or "").replace("\\", "/")
        except Exception:
            pretty = ""
        if not pretty:
            pretty = "XUI_*/.../*.xml"
        return (
            "UI XML patching is order-sensitive (last loaded wins). "
            f"If the game logs ERR XML loader: Patching '{pretty}' ... failed or shows a NullReference, "
            "first try swapping the order of these two mods and re-test; keep the intended UI winner later."
        )

    def _intent_rank(intent: str | None) -> int:
        # Higher = should load later (wins).
        # This is intentionally conservative.
        m = {
            "remove": 40,
            "replace": 30,
            "override": 20,
            "modify": 10,
            "extend": 0,
        }
        return int(m.get(str(intent or "").strip().lower(), -1))

    def _recommend_pair_order(
        a,
        b,
        *,
        file: str | None,
        dom_a: str | None = None,
        dom_b: str | None = None,
    ) -> tuple[str, str, str]:
        """Return (front, back, reason).

        "front" loads earlier; "back" loads later.
        "back" is the effective winner when "last loaded wins".
        """

        name_a = str(getattr(a, "name", "") or "")
        name_b = str(getattr(b, "name", "") or "")

        # First: dependency + tier/category policy (global signals)
        try:
            from logic.resolution_policy import compute_dependency_graph, decide_winner

            deps = compute_dependency_graph(mods)
            d = decide_winner(
                mods,
                mod_a_name=name_a,
                mod_b_name=name_b,
                conflict_type="load_order_priority",
                file=str(file or ""),
                target="",
                deps=deps,
            )
            return d.front, d.back, d.reason
        except Exception:
            pass

        # Second: semantic intent hint (tie-breaker)
        try:
            ra = _intent_rank(dom_a)
            rb = _intent_rank(dom_b)
            if ra != rb and (ra >= 0 and rb >= 0):
                if ra > rb:
                    return name_b, name_a, f"'{dom_a}' changes should apply after '{dom_b}' (last loaded wins)."
                return name_a, name_b, f"'{dom_b}' changes should apply after '{dom_a}' (last loaded wins)."
        except Exception:
            pass

        # Fall back to current numeric load_order to preserve the existing winner.
        try:
            loa = int(getattr(a, "load_order", 0))
            lob = int(getattr(b, "load_order", 0))
            if loa != lob:
                if loa > lob:
                    return name_b, name_a, "Preserving current winner (higher load_order loads later)."
                return name_a, name_b, "Preserving current winner (higher load_order loads later)."
        except Exception:
            pass

        # Final fallback: deterministic by name.
        if (name_a or "").lower() <= (name_b or "").lower():
            return name_a, name_b, "No strong signal; deterministic fallback by name."
        return name_b, name_a, "No strong signal; deterministic fallback by name."

    # Pre-compute resolver targets: if a later patch touches a target, earlier conflicts are resolved.
    # Keying scheme matches semantic path: (system-or-file, target)
    resolver_max_order = {}
    try:
        for pm in mods:
            if not _is_patch(pm):
                continue
            order = int(getattr(pm, "load_order", 10**9))
            for e in getattr(pm, "semantic_edits", []) or []:
                k = (e.get("system") or e.get("file"), e.get("target"))
                if k[1]:
                    resolver_max_order[k] = max(resolver_max_order.get(k, -1), order)
            for file, targets in (getattr(pm, "xml_targets", {}) or {}).items():
                for t in targets or set():
                    k = (file, t)
                    resolver_max_order[k] = max(resolver_max_order.get(k, -1), order)
    except Exception:
        resolver_max_order = {}
    # per-mod seen signatures to avoid duplicate conflict entries
    seen = defaultdict(set)
    # Compare mods pairwise
    for i, mod_a in enumerate(mods):
        # Disabled mods should not participate in conflict detection
        if (
            (not bool(getattr(mod_a, "enabled", True)))
            or getattr(mod_a, "user_disabled", False)
            or getattr(mod_a, "disabled", False)
        ):
            continue
        for mod_b in mods[i + 1 :]:
            # Do not emit conflicts that involve patch mods; patches are resolvers by design.
            if _is_patch(mod_a) or _is_patch(mod_b):
                continue

            if (
                (not bool(getattr(mod_b, "enabled", True)))
                or getattr(mod_b, "user_disabled", False)
                or getattr(mod_b, "disabled", False)
            ):
                continue

            try:
                max_pair_order = max(
                    int(getattr(mod_a, "load_order", 0)),
                    int(getattr(mod_b, "load_order", 0)),
                )
            except Exception:
                max_pair_order = 0
            # Prefer semantic edits when available
            edits_a = getattr(mod_a, "semantic_edits", []) or []
            edits_b = getattr(mod_b, "semantic_edits", []) or []

            if edits_a and edits_b:
                # group by (system, target)
                by_key_a = defaultdict(list)
                by_key_b = defaultdict(list)
                for e in edits_a:
                    # If system is unknown (None), include file in the key to avoid cross-file collisions.
                    key = (e.get("system") or e.get("file"), e.get("target"))
                    by_key_a[key].append(e)
                for e in edits_b:
                    key = (e.get("system") or e.get("file"), e.get("target"))
                    by_key_b[key].append(e)

                shared_keys = set(by_key_a.keys()).intersection(by_key_b.keys())
                for sys_target in shared_keys:
                    # Resolved when a later patch touches the same sys/target
                    try:
                        if resolver_max_order.get(sys_target, -1) > max_pair_order:
                            continue
                    except Exception:
                        pass
                    sa = by_key_a[sys_target]
                    sb = by_key_b[sys_target]
                    # compare intents pairwise (coarse)
                    intents_a = {e.get("intent") for e in sa}
                    intents_b = {e.get("intent") for e in sb}
                    # choose dominant intent (override > replace > remove > extend > modify)
                    order = ["override", "replace", "remove", "extend", "modify"]
                    dom_a = next((i for i in order if i in intents_a), None)
                    dom_b = next((i for i in order if i in intents_b), None)

                    sev = _intent_severity(dom_a or "modify", dom_b or "modify")

                    system, target = sys_target
                    file = None
                    # find a representative file name
                    if sa:
                        file = sa[0].get("file")
                    elif sb:
                        file = sb[0].get("file")

                    if sev == "safe":
                        continue

                    if sev == "error":
                        suggestion = "Choose one mod or separate scope; competing changes."
                        reason = f"Both mods modify the same target '{target}' in {system or file} with competing intents ({dom_a} vs {dom_b})."
                        level = "error"
                        if dom_a == dom_b and dom_a in ("override", "replace"):
                            conflict_type = "xml_override"
                        elif "remove" in {dom_a, dom_b}:
                            # treat as ownership conflict; still primary xml override for taxonomy
                            conflict_type = "xml_override"
                        else:
                            conflict_type = "xml_override"
                    elif sev == "warn":
                        suggestion = "Order override after extend or review changes."
                        reason = f"Override vs extend on '{target}' in {system or file}."
                        level = "warn"
                        # treat as load order/merge concern
                        conflict_type = "load_order_priority"
                    else:
                        suggestion = "Usually safe; different intents on same target."
                        reason = f"Different intents on '{target}' in {system or file}."
                        level = "info"
                        # Keep taxonomy strict: informational conflicts are log_only
                        conflict_type = "log_only"

                    # UI XML patch conflicts are order-sensitive (last-loaded wins) and can manifest
                    # as game-side null refs if nodes are removed/changed earlier.
                    if file and _is_ui_xml_file(file):
                        level = "warn"
                        conflict_type = "load_order_priority"
                        reason = (
                            f"Multiple mods patch UI XML target '{target}' in {file}; "
                            "order-sensitive (last loaded wins)."
                        )
                        suggestion = _ui_xml_patch_suggestion(file)

                    # Provide deterministic order recommendation for load-order resolvable conflicts.
                    recommended_front = ""
                    recommended_back = ""
                    recommended_reason = ""
                    if str(conflict_type or "").strip().lower() == "load_order_priority":
                        try:
                            rf, rb, rr = _recommend_pair_order(mod_a, mod_b, file=file, dom_a=dom_a, dom_b=dom_b)
                            recommended_front, recommended_back, recommended_reason = rf, rb, rr
                        except Exception:
                            pass

                    conflict = {
                        "level": level,
                        "file": file,
                        "target": target,
                        "system": system,
                        "with": mod_b.name,
                        "reason": reason,
                        "suggestion": suggestion,
                        "conflict_type": conflict_type,
                        "recommended_front": recommended_front,
                        "recommended_back": recommended_back,
                        "recommended_reason": recommended_reason,
                    }

                    sig = (
                        conflict["level"],
                        conflict.get("system"),
                        conflict.get("file"),
                        conflict["with"],
                        conflict["reason"],
                    )
                    if sig not in seen[mod_a.name]:
                        mod_a.conflicts.append(conflict)
                        seen[mod_a.name].add(sig)
                    conflict_b = conflict.copy()
                    conflict_b["with"] = mod_a.name
                    sigb = (
                        conflict_b["level"],
                        conflict_b.get("system"),
                        conflict_b.get("file"),
                        conflict_b["with"],
                        conflict_b["reason"],
                    )
                    if sigb not in seen[mod_b.name]:
                        mod_b.conflicts.append(conflict_b)
                        seen[mod_b.name].add(sigb)

                # continue to next pair; skip heuristic path since semantic handled
                continue

            # --- Asset overlaps (non-XML): textures/audio/models/prefabs/etc ---
            try:
                assets_a = set(getattr(mod_a, "asset_files", None) or set())
                assets_b = set(getattr(mod_b, "asset_files", None) or set())
            except Exception:
                assets_a, assets_b = set(), set()

            try:
                if assets_a and assets_b:
                    shared_assets = sorted(assets_a.intersection(assets_b))
                else:
                    shared_assets = []
            except Exception:
                shared_assets = []

            if shared_assets:
                # Avoid spamming: emit per-asset when small, otherwise aggregate.
                max_individual = 3
                if len(shared_assets) <= max_individual:
                    paths = shared_assets
                    for rel in paths:
                        conflict = {
                            "level": "warn",
                            "file": "assets",
                            "target": f"asset:{rel}",
                            "with": mod_b.name,
                            "reason": "Both mods provide the same non-XML asset path (last loaded wins).",
                            "suggestion": "Adjust load order to choose the visual/audio winner (last loaded wins).",
                            "conflict_type": "asset_conflict",
                        }
                        sig = (
                            conflict["level"],
                            conflict["file"],
                            conflict["target"],
                            conflict["with"],
                            conflict["reason"],
                        )
                        if sig not in seen[mod_a.name]:
                            mod_a.conflicts.append(conflict)
                            seen[mod_a.name].add(sig)
                        conflict_b = conflict.copy()
                        conflict_b["with"] = mod_a.name
                        sigb = (
                            conflict_b["level"],
                            conflict_b["file"],
                            conflict_b["target"],
                            conflict_b["with"],
                            conflict_b["reason"],
                        )
                        if sigb not in seen[mod_b.name]:
                            mod_b.conflicts.append(conflict_b)
                            seen[mod_b.name].add(sigb)
                else:
                    conflict = {
                        "level": "warn",
                        "file": "assets",
                        "target": f"asset:multiple({len(shared_assets)})",
                        "with": mod_b.name,
                        "reason": f"Both mods provide {len(shared_assets)} of the same non-XML asset paths (last loaded wins).",
                        "suggestion": "Adjust load order to choose the visual/audio winner (last loaded wins).",
                        "conflict_type": "asset_conflict",
                        "asset_paths": shared_assets[:20],
                    }
                    sig = (
                        conflict["level"],
                        conflict["file"],
                        conflict["target"],
                        conflict["with"],
                        conflict["reason"],
                    )
                    if sig not in seen[mod_a.name]:
                        mod_a.conflicts.append(conflict)
                        seen[mod_a.name].add(sig)
                    conflict_b = conflict.copy()
                    conflict_b["with"] = mod_a.name
                    sigb = (
                        conflict_b["level"],
                        conflict_b["file"],
                        conflict_b["target"],
                        conflict_b["with"],
                        conflict_b["reason"],
                    )
                    if sigb not in seen[mod_b.name]:
                        mod_b.conflicts.append(conflict_b)
                        seen[mod_b.name].add(sigb)

            # consider files both mods touched at target level (heuristic fallback)
            files_a = set(mod_a.xml_targets.keys()) if getattr(mod_a, "xml_targets", None) else set()
            files_b = set(mod_b.xml_targets.keys()) if getattr(mod_b, "xml_targets", None) else set()

            common_files = files_a.intersection(files_b)

            for file in common_files:
                targets_a = mod_a.xml_targets.get(file, set())
                targets_b = mod_b.xml_targets.get(file, set())

                # compute shared exact targets
                shared = targets_a.intersection(targets_b)

                # Remove targets resolved by a later patch
                if shared:
                    try:
                        shared = {t for t in shared if resolver_max_order.get((file, t), -1) <= max_pair_order}
                    except Exception:
                        pass

                # Aggregate per-file conflict: prefer ERROR if any exact shared targets
                if shared:
                    target_str = ", ".join(sorted(shared))

                    if mod_a.is_overhaul and not mod_b.is_overhaul:
                        suggestion = f"'{mod_a.name}' is an overhaul and should load after '{mod_b.name}'"
                    elif mod_b.is_overhaul and not mod_a.is_overhaul:
                        suggestion = f"'{mod_b.name}' is an overhaul and should load after '{mod_a.name}'"
                    else:
                        suggestion = "Adjust load order or remove one mod"

                    reason = f"Both mods modify the same targets in {file}"
                    core_defs = {"items.xml", "blocks.xml", "entityclasses.xml", "buffs.xml"}

                    if _is_ui_xml_file(file):
                        # UI XML conflicts are resolvable by load order only.
                        # Mark as load_order_priority so they show up and can be reordered.
                        conflict = {
                            "level": "warn",
                            "file": file,
                            "target": target_str,
                            "with": mod_b.name,
                            "reason": f"Multiple mods patch UI XML targets in {file}",
                            "suggestion": _ui_xml_patch_suggestion(file),
                            "conflict_type": "load_order_priority",
                        }
                        try:
                            rf, rb, rr = _recommend_pair_order(mod_a, mod_b, file=file)
                            conflict["recommended_front"] = rf
                            conflict["recommended_back"] = rb
                            conflict["recommended_reason"] = rr
                        except Exception:
                            pass
                    else:
                        ctype = "duplicate_id" if file in core_defs else "xml_override"
                        conflict = {
                            "level": "error",
                            "file": file,
                            "target": target_str,
                            "with": mod_b.name,
                            "reason": reason,
                            "suggestion": suggestion,
                            "conflict_type": ctype,
                        }

                    sig = (conflict["level"], conflict["file"], conflict["with"], conflict["reason"])
                    if sig not in seen[mod_a.name]:
                        mod_a.conflicts.append(conflict)
                        seen[mod_a.name].add(sig)

                    conflict_b = conflict.copy()
                    conflict_b["with"] = mod_a.name
                    sigb = (conflict_b["level"], conflict_b["file"], conflict_b["with"], conflict_b["reason"])
                    if sigb not in seen[mod_b.name]:
                        mod_b.conflicts.append(conflict_b)
                        seen[mod_b.name].add(sigb)
                    continue

                # map targets by node for warn/info detection
                nodes_a = defaultdict(set)
                nodes_b = defaultdict(set)
                for t in targets_a:
                    node, quals = _node_from_target(t)
                    nodes_a[node].update(quals)
                for t in targets_b:
                    node, quals = _node_from_target(t)
                    nodes_b[node].update(quals)

                # check for warn conditions (same node different qualifiers)
                warn_found = False
                for node in set(nodes_a.keys()).intersection(nodes_b.keys()):
                    quals_a = nodes_a[node]
                    quals_b = nodes_b[node]

                    node_type = node.split(":")[0].lower()
                    attr_a = {q.split(":", 1)[1].lower() for q in quals_a if ":" in q}
                    attr_b = {q.split(":", 1)[1].lower() for q in quals_b if ":" in q}

                    if attr_a and attr_b and attr_a.isdisjoint(attr_b):
                        safe_attrs = SAFE_ATTRIBUTE_SPLITS.get(node_type, set())
                        if attr_a.issubset(safe_attrs) and attr_b.issubset(safe_attrs):
                            continue

                    warn_found = True

                if warn_found:
                    if mod_a.is_overhaul and not mod_b.is_overhaul:
                        suggestion = f"'{mod_a.name}' is an overhaul and should load after '{mod_b.name}'"
                    elif mod_b.is_overhaul and not mod_a.is_overhaul:
                        suggestion = f"'{mod_b.name}' is an overhaul and should load after '{mod_a.name}'"
                    else:
                        suggestion = "Adjust load order or review attribute changes"

                    reason = f"Both mods modify the same node(s) in {file}"
                    if _is_ui_xml_file(file):
                        reason = f"Both mods patch UI XML nodes in {file}"
                        suggestion = _ui_xml_patch_suggestion(file)

                    conflict = {
                        "level": "warn",
                        "file": file,
                        "target": None,
                        "with": mod_b.name,
                        "reason": reason,
                        "suggestion": suggestion,
                        "conflict_type": "load_order_priority",
                    }

                    try:
                        rf, rb, rr = _recommend_pair_order(mod_a, mod_b, file=file)
                        conflict["recommended_front"] = rf
                        conflict["recommended_back"] = rb
                        conflict["recommended_reason"] = rr
                    except Exception:
                        pass

                    sig = (conflict["level"], conflict["file"], conflict["with"], conflict["reason"])
                    if sig not in seen[mod_a.name]:
                        mod_a.conflicts.append(conflict)
                        seen[mod_a.name].add(sig)
                    conflict_b = conflict.copy()
                    conflict_b["with"] = mod_a.name
                    sigb = (conflict_b["level"], conflict_b["file"], conflict_b["with"], conflict_b["reason"])
                    if sigb not in seen[mod_b.name]:
                        mod_b.conflicts.append(conflict_b)
                        seen[mod_b.name].add(sigb)
                    continue

                # If no error or warn, but both touched the file
                if targets_a or targets_b:
                    # If a later patch touched this file, suppress noisy info-level conflicts
                    try:
                        if any(
                            resolver_max_order.get((file, t), -1) > max_pair_order
                            for t in (targets_a.union(targets_b) or set())
                        ):
                            continue
                    except Exception:
                        pass

                    if _is_ui_xml_file(file):
                        conflict = {
                            "level": "warn",
                            "file": file,
                            "target": None,
                            "with": mod_b.name,
                            "reason": f"Both mods patch UI XML in {file}",
                            "suggestion": _ui_xml_patch_suggestion(file),
                            "conflict_type": "load_order_priority",
                        }
                        try:
                            rf, rb, rr = _recommend_pair_order(mod_a, mod_b, file=file)
                            conflict["recommended_front"] = rf
                            conflict["recommended_back"] = rb
                            conflict["recommended_reason"] = rr
                        except Exception:
                            pass
                    else:
                        if mod_a.is_overhaul and not mod_b.is_overhaul:
                            suggestion = f"'{mod_a.name}' is an overhaul and should load after '{mod_b.name}'"
                        elif mod_b.is_overhaul and not mod_a.is_overhaul:
                            suggestion = f"'{mod_b.name}' is an overhaul and should load after '{mod_a.name}'"
                        else:
                            suggestion = "These mods touch the same file but different targets; usually informational."

                        conflict = {
                            "level": "info",
                            "file": file,
                            "target": None,
                            "with": mod_b.name,
                            "reason": f"Both mods modify different targets in {file}",
                            "suggestion": suggestion,
                            "conflict_type": "log_only",
                        }

                    sig = (conflict["level"], conflict["file"], conflict["with"], conflict["reason"])
                    if sig not in seen[mod_a.name]:
                        mod_a.conflicts.append(conflict)
                        seen[mod_a.name].add(sig)
                    conflict_b = conflict.copy()
                    conflict_b["with"] = mod_a.name
                    sigb = (conflict_b["level"], conflict_b["file"], conflict_b["with"], conflict_b["reason"])
                    if sigb not in seen[mod_b.name]:
                        mod_b.conflicts.append(conflict_b)
                        seen[mod_b.name].add(sigb)

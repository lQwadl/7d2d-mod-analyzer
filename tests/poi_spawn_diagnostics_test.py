import os
from tests._test_tmp import temp_dir


def _mkfile(path: str, content: str = "x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class DummyMod:
    def __init__(self, name: str, path: str, load_order: int):
        self.name = name
        self.path = path
        self.load_order = load_order
        self.disabled = False
        self.is_patch = False
        self.is_overhaul = False
        self.categories = []
        self.category = "Miscellaneous"
        self.conflicts = []


def test_poi_spawn_diagnostics_emits_actionable_warnings():
    from logic.load_order_engine import compute_load_order

    with temp_dir("poi_diag_") as root:
        td = str(root)
        # Worldgen mod shipping rwgmixer
        better_gen = os.path.join(td, "010_BetterGeneration")
        _mkfile(os.path.join(better_gen, "Config", "rwgmixer.xml"))

        # Injector mod shipping rwgmixer
        spawn_all = os.path.join(td, "020_spawn_all_POIs")
        _mkfile(os.path.join(spawn_all, "Config", "rwgmixer.xml"))

        # POI pack: prefab assets but no rwgmixer
        poi_pack = os.path.join(td, "030_DeluxePOIPack")
        _mkfile(os.path.join(poi_pack, "Prefabs", "castle.tts"))

        # Another rwgmixer mod that comes after injector in current order
        late_rwg = os.path.join(td, "040_LateWorldgen")
        _mkfile(os.path.join(late_rwg, "Config", "rwgmixer.xml"))

        mods = [
            DummyMod("010_Better Generation", better_gen, load_order=10),
            DummyMod("020_spawn_all_POIs", spawn_all, load_order=20),
            DummyMod("030_Deluxe POI Pack", poi_pack, load_order=30),
            DummyMod("040_LateWorldgen", late_rwg, load_order=40),
        ]

        _ordered, report = compute_load_order(mods)
        text = "\n".join(report.warnings)

        assert "POIs not spawning" in text
        assert "Prefab-only POI packs" in text
        assert "spawn_all_POIs" in text
        assert "rwgmixer.xml" in text

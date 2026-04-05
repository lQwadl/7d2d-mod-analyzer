class Mod:
    def __init__(self, name, path):
        self.name = name
        self.path = path

        # Enable/disable state used throughout detection, export, and UI.
        # These are intentionally simple attributes (not persisted here).
        self.enabled = True
        self.user_disabled = False
        self.install_id = None

        self.systems = set()
        self.xml_files = set()
        # more granular xml targets: { filename: set(target_identifiers) }
        self.xml_targets = {}
        # semantic edits extracted from XML patch operations
        # list of dicts:
        #   {
        #     'file': str,
        #     'system': str,
        #     'xpath': str,
        #     'op': str,
        #     'intent': str,
        #     'target': str,
        #     'value': str,
        #   }
        self.semantic_edits = []
        self.is_overhaul = False
        self.conflicts = []
        self.redundant_reason = None
        # Symlink / source metadata
        self.is_symlink = False
        self.symlink_target = None
        self.source = None
        # Disabled flags for UI/export (e.g., older duplicate versions)
        self.disabled = False
        self.disabled_reason = None

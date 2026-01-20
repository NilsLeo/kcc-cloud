from enum import Enum


class DeviceProfile(Enum):
    K1 = {"id": "K1", "label": "Kindle 1"}
    K11 = {"id": "K11", "label": "Kindle 11"}
    K2 = {"id": "K2", "label": "Kindle 2"}
    K34 = {"id": "K34", "label": "Kindle Keyboard/Touch"}
    K578 = {"id": "K578", "label": "Kindle"}
    KDX = {"id": "KDX", "label": "Kindle DX/DXG"}
    KPW = {"id": "KPW", "label": "Kindle Paperwhite 1/2"}
    KV = {"id": "KV", "label": "Kindle Paperwhite 3/4/Voyage/Oasis"}
    KPW5 = {"id": "KPW5", "label": "Kindle Paperwhite 5/Signature Edition"}
    KO = {"id": "KO", "label": "Kindle Oasis 2/3/Paperwhite 12/Colorsoft 12"}
    KS = {"id": "KS", "label": "Kindle Scribe"}

    KoMT = {"id": "KoMT", "label": "Kobo Mini/Touch"}
    KoG = {"id": "KoG", "label": "Kobo Glo"}
    KoGHD = {"id": "KoGHD", "label": "Kobo Glo HD"}
    KoA = {"id": "KoA", "label": "Kobo Aura"}
    KoAHD = {"id": "KoAHD", "label": "Kobo Aura HD"}
    KoAH2O = {"id": "KoAH2O", "label": "Kobo Aura H2O"}
    KoAO = {"id": "KoAO", "label": "Kobo Aura ONE"}
    KoN = {"id": "KoN", "label": "Kobo Nia"}
    KoC = {"id": "KoC", "label": "Kobo Clara HD/Kobo Clara 2E"}
    KoCC = {"id": "KoCC", "label": "Kobo Clara Colour"}
    KoL = {"id": "KoL", "label": "Kobo Libra H2O/Kobo Libra 2"}
    KoLC = {"id": "KoLC", "label": "Kobo Libra Colour"}
    KoF = {"id": "KoF", "label": "Kobo Forma"}
    KoS = {"id": "KoS", "label": "Kobo Sage"}
    KoE = {"id": "KoE", "label": "Kobo Elipsa"}

    Rmk1 = {"id": "Rmk1", "label": "reMarkable 1"}
    Rmk2 = {"id": "Rmk2", "label": "reMarkable 2"}
    RmkPP = {"id": "RmkPP", "label": "reMarkable Paper Pro"}

    OTHER = {"id": "OTHER", "label": "Other"}

    @property
    def id(self):
        return self.value["id"]

    @property
    def label(self):
        return self.value["label"]


# Create a dictionary of all device profiles for API use
DEVICE_PROFILES = {profile.id: profile.label for profile in DeviceProfile}

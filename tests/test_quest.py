import unittest
from io import BytesIO
import cv2
import numpy as np
import qrcode
from quest_core import Quest, ROSTER, STATIONS, CARDS, payload, parse_payload, email_draft

class QuestTests(unittest.TestCase):
    def setUp(self):
        self.q = Quest()
        self.lea = self.q.activate("DEMO-264")
        self.alex = self.q.activate("DEMO-137")
        self.card = next(iter(CARDS))

    def unlock(self, person):
        for station in list(STATIONS)[:4]:
            self.q.scan(person, payload("station", station))

    def test_qr_roundtrip_and_personal_data_absence(self):
        for kind, catalog in [("person", ROSTER), ("station", STATIONS), ("reward", CARDS)]:
            for token in catalog:
                value = payload(kind, token)
                buf = BytesIO()
                qrcode.make(value).save(buf, format="PNG")
                img = cv2.imdecode(np.frombuffer(buf.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
                decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
                self.assertEqual(parse_payload(decoded), (kind, token))
                for profile in ROSTER.values():
                    self.assertNotIn(profile["email"], value)
                    self.assertNotIn(profile["code"], value)

    def test_activation_and_invalid_scans(self):
        for code in ["wrong", payload("person", self.lea), "AFJD-0264"]:
            with self.assertRaises(ValueError):
                self.q.activate(code)
        for value in ["https://elsewhere.test", "afjd:2025:person:p-8hd2v7", "afjd:2026:person:unknown"]:
            with self.assertRaises(ValueError):
                self.q.scan(self.lea, value)
        with self.assertRaises(ValueError):
            self.q.scan(self.lea, payload("person", self.lea))

    def test_demo_role_logins(self):
        before = len(self.q.active)
        self.assertEqual(self.q.demo_login("STAFF-01"), ("staff", None))
        self.assertEqual(self.q.demo_login("SCREEN-01"), ("screen", None))
        self.assertEqual(len(self.q.active), before)
        for token, profile in ROSTER.items():
            self.assertEqual(self.q.demo_login(profile["code"], __import__("quest_core").ACTIVATION_CODES[token]), ("participant", token))
        with self.assertRaises(ValueError):
            self.q.demo_login("STAFF-03")

    def test_profile_and_new_stands(self):
        self.q.update_profile(self.lea, {"name":"Lea Example", "email":"lea.new@example.test", "address":"Demo street 2", "id":"attempted-change"})
        self.assertEqual(self.q.profile(self.lea)["name"], "Lea Example")
        self.assertEqual(self.q.profile(self.lea)["id"], "AFJD-0264")
        self.assertEqual(self.q.profile(self.alex)["name"], "Alex Keller")
        with self.assertRaises(ValueError):
            self.q.update_profile(self.lea, {"name":"Lea", "email":"bad"})
        for station in ["ag-soil", "ag-farm", "fo-bowl", "fo-dairy"]:
            self.q.scan(self.lea, payload("station", station))
        self.assertEqual(self.q.completed(self.lea), {"Agriculture", "Food Production"})
        self.assertEqual(len(self.q.public_network()["visits"]), 4)
        self.assertTrue(all(0 <= target < len(STATIONS) for _,target in self.q.public_network()["visits"]))

    def test_confirmation_deduplication_and_bonus(self):
        self.unlock(self.lea)
        self.q.scan(self.lea, payload("person", self.alex))
        self.assertEqual(self.q.people(self.lea), set())
        self.q.scan(self.alex, payload("person", self.lea))
        self.assertEqual(len(self.q.pending), 1)
        self.q.confirm(self.alex, self.lea)
        self.assertEqual(self.q.people(self.lea), {self.alex})
        self.assertEqual(self.q.entries(self.lea), 2)
        self.q.scan(self.lea, payload("person", self.alex))
        self.assertEqual(self.q.entries(self.lea), 2)
        self.q.confirm(self.alex, self.lea)
        self.assertEqual(self.q.entries(self.lea), 2)
        self.assertEqual(self.q.sharing, set())

    def test_one_primary_challenge_and_duplicates(self):
        station = next(iter(STATIONS))
        for _ in range(3):
            self.q.scan(self.lea, payload("station", station))
        self.assertEqual(len(self.q.completed(self.lea)), 1)
        self.assertNotIn(self.lea, self.q.unlocked)

    def test_reward_ownership_consent_and_email(self):
        with self.assertRaises(ValueError):
            self.q.assign(self.lea, self.card, staff=True)
        self.unlock(self.lea)
        with self.assertRaises(ValueError):
            self.q.assign(self.lea, self.card)
        with self.assertRaises(ValueError):
            self.q.scan(self.lea, payload("reward", self.card))
        self.q.assign(self.lea, self.card, staff=True)
        with self.assertRaises(ValueError):
            self.q.assign(self.lea, list(CARDS)[1], staff=True)
        with self.assertRaises(ValueError):
            self.q.scan(self.alex, payload("reward", self.card))
        with self.assertRaises(ValueError):
            self.q.submit(self.alex, self.card, {"address":"Demo"}, True)
        with self.assertRaises(ValueError):
            self.q.submit(self.lea, self.card, {"address":"Demo"}, False)
        with self.assertRaises(ValueError):
            self.q.submit(self.lea, self.card, {}, True)
        self.q.submit(self.lea, self.card, {"address":"Demo street 1","organisation":"Demo School","study_programme":"Food","date_of_birth":"2000-01-01"}, True)
        with self.assertRaises(ValueError):
            self.q.submit(self.lea, self.card, {"address":"Demo"}, True)
        draft = email_draft(self.q, self.card, "svial@svial.ch")
        self.assertIn(b"To: svial@svial.ch", draft)
        self.assertIn(b"Cc: svial@svial.ch", draft)
        self.assertIn(b"X-Unsent: 1", draft)
        self.assertNotIn(b"alex@example.test", draft)
        with self.assertRaises(ValueError):
            email_draft(self.q, self.card, "svial@svial.ch\nBcc: other@example.test")

    def test_public_feed_has_no_identifiers(self):
        self.unlock(self.lea)
        counts = self.q.public_counts()
        self.assertTrue(all(type(v) is int for v in counts.values()))
        self.assertEqual(counts["visits"], 4)
        network = self.q.public_network()
        self.assertEqual(len(network["visits"]), 4)
        for p, profile in ROSTER.items():
            for private in [p, profile["name"], profile["email"], profile["id"]]:
                self.assertNotIn(private, str(network))

if __name__ == "__main__":
    unittest.main()

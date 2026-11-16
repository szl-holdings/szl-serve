import unittest

from massed_inventory import project_instance


class InventoryProjectionTests(unittest.TestCase):
    def test_provider_credentials_and_commands_never_leave_projection(self):
        row = {"uuid": "fixture-id", "name": "fixture", "ip": "192.0.2.1", "status": "Running",
               "password": "fixture-password", "username": "fixture-user",
               "command_startup": "fixture-sensitive-command", "ssh_key_names": ["private-name"],
               "region": {"name": "fixture-region", "password": "nested-secret"},
               "product": {"name": "fixture-gpu", "unknown": "nested-secret"}}
        self.assertEqual(project_instance(row), {"uuid": "fixture-id", "name": "fixture",
                         "ip": "192.0.2.1", "status": "Running", "region": "fixture-region", "product": "fixture-gpu"})

    def test_unexpected_nested_values_are_not_serialized(self):
        self.assertEqual(project_instance({"name": {"secret": "fixture"}, "region": ["fixture"]}), {})


if __name__ == "__main__":
    unittest.main()

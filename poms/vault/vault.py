import requests

from poms_app import settings


class FinmarsVault():

    def __init__(self):
        self.vault_host = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/vault'
        self.auth_token = settings.VAULT_TOKEN

    def get_headers(self):

        headers = {'X-Vault-Token': self.auth_token}

        return headers

    def get_list_engines(self,):
        url = f"{self.vault_host}/v1/sys/mounts"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def create_engine(self, engine_name):

        url = f'{self.vault_host}/v1/sys/mounts/{engine_name}'
        headers = self.get_headers()

        payload = {
            "path": engine_name,
            "type": "kv",
            "generate_signing_key": True,
            "config": {
                "id": engine_name
            },
            "options": {
                "version": 2
            },
            "id": engine_name
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            print(f'Secret engine {engine_name} created successfully')
        except Exception as e:
            print(f'Failed to create secret engine: {e}')

        return response.json()

    def get_list_secrets(self, engine_name):
        url = f"{self.vault_host}/v1/{engine_name}/metadata/?list=true"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def delete_engine(self, engine_name):
        url = f"{self.vault_host}/v1/sys/mounts/{engine_name}"
        headers = self.get_headers()
        response = requests.delete(url, headers=headers)
        return response.json()

    def create_secret(self, engine_name, secret_path, secret_data):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}"
        headers = self.get_headers()

        data = {
            'data': secret_data,
            'options': {
                'cas': 0
            }
        }

        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def get_secret_metadata(self, engine_name, secret_path):
        url = f"{self.vault_host}/v1/{engine_name}/metadata/{secret_path}"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def get_secret(self, engine_name, secret_path):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}?version=2"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def update_secret(self, engine_name, secret_path, secret_data):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}"
        headers = self.get_headers()
        response = requests.put(url, headers=headers, json=secret_data)
        return response.json()

    def delete_secret(self, engine_name, secret_path):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}"
        headers = self.get_headers()
        response = requests.delete(url, headers=headers)
        return response.json()

import logging

import requests

from poms_app import settings

_l = logging.getLogger('poms.vault')


def remove_trailing_slash_from_keys(data):
    modified_data = {}
    for key, value in data.items():
        new_key = key.rstrip('/')  # Remove trailing slash
        modified_data[new_key] = value
    return modified_data


class FinmarsVault():

    def __init__(self):
        self.vault_host = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/vault'
        self.auth_token = settings.VAULT_TOKEN

    def get_headers(self):

        headers = {'X-Vault-Token': self.auth_token}

        return headers

    #  GENERAL ACTIONS STARTS

    def get_status(self, request):

        # TODO Refactor to create more descent autohorization between backend and authorizer
        from poms.common.authentication import KeycloakAuthentication
        keycloakAuth = KeycloakAuthentication()

        token = keycloakAuth.get_auth_token_from_request(request)

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        headers["Authorization"] = "Token " + token

        url = settings.AUTHORIZER_URL + '/master-user/' + settings.BASE_API_URL + '/vault-status/'

        data = {}

        response = requests.get(url=url, json=data, headers=headers, verify=settings.VERIFY_SSL)

        return response.json()

    def seal(self):

        url = f'{self.vault_host}/v1/sys/seal/'
        headers = self.get_headers()

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            _l.info(f'Vault sealed successfully')
        except Exception as e:
            _l.info(f'Failed to seal: {e}')

    def unseal(self, request, key):

        # TODO Refactor to create more descent autohorization between backend and authorizer
        from poms.common.authentication import KeycloakAuthentication
        keycloakAuth = KeycloakAuthentication()

        token = keycloakAuth.get_auth_token_from_request(request)

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        headers["Authorization"] = "Token " + token

        url = settings.AUTHORIZER_URL + '/master-user/' + settings.BASE_API_URL + '/vault-unseal/'

        data = {
            'unseal_key': key
        }

        response = requests.put(url=url, json=data, headers=headers, verify=settings.VERIFY_SSL)

        return response.json()

    # GENERAL ACTIONS ENDS

    def get_list_engines(self, ):
        url = f"{self.vault_host}/v1/sys/mounts"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)

        response_json = response.json()

        formatted_data = remove_trailing_slash_from_keys(response_json['data'])

        filtered_keys = ["sys", "identity", "cubbyhole"]

        filtered_list = [{'engine_name': k, 'data': v} for k, v in formatted_data.items() if
                         k not in filtered_keys]

        return filtered_list

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
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            _l.info(f'Secret engine {engine_name} created successfully')
        except Exception as e:
            _l.info(f'Failed to create secret engine: {e}')

        # return response.json()

    def delete_engine(self, engine_name):
        url = f"{self.vault_host}/v1/sys/mounts/{engine_name}"
        headers = self.get_headers()
        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            _l.info(f'Secret engine {engine_name} deleted successfully')
        except Exception as e:
            _l.info(f'Failed to delete secret engine: {e}')

    def get_list_secrets(self, engine_name):
        url = f"{self.vault_host}/v1/{engine_name}/metadata/?list=true"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
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

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            _l.info(f'Secret {secret_path} created successfully')
        except Exception as e:
            _l.info(f'Failed to create secret: {e}')
        # return response.json()

    def get_secret_metadata(self, engine_name, secret_path):
        url = f"{self.vault_host}/v1/{engine_name}/metadata/{secret_path}"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def get_latest_version(self, engine_name, secret_path):

        metadata = self.get_secret_metadata(engine_name, secret_path)

        version = len(metadata['data']['versions'])

        return version

    def get_secret(self, engine_name, secret_path, version=1):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}?version={version}"
        headers = self.get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def update_secret(self, engine_name, secret_path, secret_data, version):
        url = f"{self.vault_host}/v1/{engine_name}/data/{secret_path}"
        headers = self.get_headers()

        data = {
            'data': secret_data,
            'options': {
                'cas': version
            }
        }

        try:
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            _l.info(f'Secret {secret_path} updated successfully')
        except Exception as e:
            _l.info(f'Failed to update secret: {e}')

    def delete_secret(self, engine_name, secret_path):
        url = f"{self.vault_host}/v1/{engine_name}/metadata/{secret_path}"
        headers = self.get_headers()

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            _l.info(f'Secret {secret_path} deleted successfully')
        except Exception as e:
            _l.info(f'Failed to delete secret: {e}')
